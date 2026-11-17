"""Match Context Extractor for CricketIQ.

Extracts structured MatchContext from natural language query text and merges
explicit user-provided MatchContextInput parameters with provenance tracking.
"""

from __future__ import annotations
import re
from datetime import datetime, date
from typing import Optional, Tuple, Dict, Any

from cricketiq.backend.app.api.schemas.query import MatchContextInput
from cricketiq.backend.app.database.models import (
    MatchContext,
    CricketFormat,
    GenderCategory,
    DocumentAuthority,
)

DOMESTIC_COMPETITIONS = {
    "ipl": "IPL",
    "indian premier league": "IPL",
    "bbl": "BBL",
    "big bash": "BBL",
    "psl": "PSL",
    "pakistan super league": "PSL",
    "cpl": "CPL",
    "caribbean premier league": "CPL",
    "the hundred": "THE_HUNDRED",
    "ranji": "RANJI",
    "ranji trophy": "RANJI",
    "county": "COUNTY",
    "county championship": "COUNTY",
    "smat": "SMAT",
    "syed mushtaq ali": "SMAT",
    "vitality blast": "VITALITY_BLAST",
}

DATE_REGEX = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")


class ContextExtractor:
    """Extracts and harmonizes MatchContext from natural language and explicit input."""

    def extract(
        self,
        query: str,
        explicit_input: Optional[MatchContextInput] = None
    ) -> Tuple[MatchContext, Dict[str, Any]]:
        """Extract MatchContext and return alongside an extraction provenance trace."""
        provenance: Dict[str, str] = {}
        q_lower = query.lower()

        # 1. Start with defaults
        cricket_level = "international"
        governing_body: Optional[str] = None
        competition: Optional[str] = None
        match_format: Optional[CricketFormat] = None
        gender_cat: Optional[GenderCategory] = None
        series_start_date: Optional[str] = None
        match_date: Optional[str] = None
        season: Optional[str] = None

        # 2. Check for domestic leagues in query
        for keyword, comp_id in DOMESTIC_COMPETITIONS.items():
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, q_lower):
                cricket_level = "domestic"
                competition = comp_id
                provenance["competition"] = f"inferred_from_query:{keyword}"
                provenance["cricket_level"] = "inferred_domestic"
                break

        # 3. Detect Format from query if not already set
        if not match_format:
            if re.search(r"\bt20i\b|\btwenty20 international\b", q_lower):
                match_format = CricketFormat.T20I
                provenance["format"] = "inferred_from_query:t20i"
            elif re.search(r"\bodi\b|\bone[-\s]day\b|\b50[-\s]over\b", q_lower):
                match_format = CricketFormat.ODI
                provenance["format"] = "inferred_from_query:odi"
            elif re.search(r"\btest\b|\btest match\b|\btests\b", q_lower):
                match_format = CricketFormat.TEST
                provenance["format"] = "inferred_from_query:test"
            elif re.search(r"\bt20\b|\btwenty20\b", q_lower):
                match_format = CricketFormat.T20I
                provenance["format"] = "inferred_from_query:t20_generic"

        # 4. Detect Category (Gender) from query
        if re.search(r"\bwomen'?s?\b|\bfemale\b", q_lower):
            gender_cat = GenderCategory.WOMENS
            provenance["category"] = "inferred_from_query:womens"
        elif re.search(r"\bmen'?s?\b|\bmale\b", q_lower):
            gender_cat = GenderCategory.MENS
            provenance["category"] = "inferred_from_query:mens"

        # 5. Detect Competition from query
        if not competition:
            if re.search(r"\bwtc\b|\bworld test championship\b", q_lower):
                competition = "WTC"
                match_format = CricketFormat.TEST
                provenance["competition"] = "inferred_from_query:wtc"
            elif re.search(r"\bt20 world cup\b", q_lower):
                competition = "T20_WORLD_CUP"
                match_format = CricketFormat.T20I
                provenance["competition"] = "inferred_from_query:t20_world_cup"
            elif re.search(r"\bodi world cup\b|\bcricket world cup\b", q_lower):
                competition = "CWC"
                match_format = CricketFormat.ODI
                provenance["competition"] = "inferred_from_query:cwc"

        # 6. Detect Governing Body / Preferred Authority from query
        if re.search(r"\bmcc\b|\blaws? of cricket\b", q_lower):
            governing_body = "MCC"
            provenance["governing_body"] = "inferred_from_query:mcc"
        elif re.search(r"\bicc\b|\bplaying conditions?\b", q_lower):
            governing_body = "ICC"
            provenance["governing_body"] = "inferred_from_query:icc"

        # 7. Detect explicit ISO dates in query text
        date_matches = DATE_REGEX.findall(query)
        if date_matches:
            match_date = date_matches[0]
            provenance["match_date"] = f"inferred_from_query:{match_date}"

        # 8. Override / Harmonize with explicit_input if provided
        if explicit_input:
            if explicit_input.cricket_level:
                cricket_level = explicit_input.cricket_level
                provenance["cricket_level"] = "explicit_input"
            if explicit_input.governing_body:
                governing_body = explicit_input.governing_body
                provenance["governing_body"] = "explicit_input"
            if explicit_input.competition:
                competition = explicit_input.competition
                provenance["competition"] = "explicit_input"
                # Check if explicit competition is domestic
                if competition.lower() in DOMESTIC_COMPETITIONS or any(
                    k in competition.lower() for k in DOMESTIC_COMPETITIONS
                ):
                    cricket_level = "domestic"
                    provenance["cricket_level"] = "explicit_domestic_competition"
            if explicit_input.format:
                match_format = explicit_input.format
                provenance["format"] = "explicit_input"
            if explicit_input.category:
                gender_cat = explicit_input.category
                provenance["category"] = "explicit_input"
            if explicit_input.series_start_date:
                series_start_date = (
                    explicit_input.series_start_date.isoformat()
                    if isinstance(explicit_input.series_start_date, (date, datetime))
                    else str(explicit_input.series_start_date)
                )
                provenance["series_start_date"] = "explicit_input"
            if explicit_input.match_date:
                match_date = (
                    explicit_input.match_date.isoformat()
                    if isinstance(explicit_input.match_date, (date, datetime))
                    else str(explicit_input.match_date)
                )
                provenance["match_date"] = "explicit_input"
            if explicit_input.season:
                season = explicit_input.season
                provenance["season"] = "explicit_input"
            if explicit_input.applicable_rules:
                governing_body = explicit_input.applicable_rules.value
                provenance["governing_body"] = "explicit_input"

        context = MatchContext(
            cricket_level=cricket_level,
            governing_body=governing_body,
            format=match_format,
            category=gender_cat,
            competition=competition,
            series_start_date=series_start_date,
            match_date=match_date,
            season=season,
            raw_query=query,
        )

        return context, provenance
