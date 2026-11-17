"""Unit tests for ContextExtractor."""

import pytest
from cricketiq.backend.app.api.schemas.query import MatchContextInput
from cricketiq.backend.app.application.context_extractor import ContextExtractor
from cricketiq.backend.app.database.models import CricketFormat, GenderCategory, DocumentAuthority


@pytest.fixture
def extractor():
    return ContextExtractor()


def test_extract_t20i_format(extractor):
    ctx, prov = extractor.extract("Can a batter be out on a free hit in a T20I match?")
    assert ctx.format == CricketFormat.T20I
    assert "format" in prov
    assert "t20i" in prov["format"]


def test_extract_odi_and_women(extractor):
    ctx, prov = extractor.extract("What is the powerplay rule in Women's ODI cricket?")
    assert ctx.format == CricketFormat.ODI
    assert ctx.category == GenderCategory.WOMENS
    assert ctx.cricket_level == "international"


def test_extract_test_match(extractor):
    ctx, prov = extractor.extract("How many overs are bowled in a day in Test cricket?")
    assert ctx.format == CricketFormat.TEST
    assert ctx.cricket_level == "international"


def test_extract_domestic_ipl_screening(extractor):
    ctx, prov = extractor.extract("Can an impact player be substituted during an IPL game?")
    assert ctx.cricket_level == "domestic"
    assert ctx.competition == "IPL"


def test_extract_domestic_bbl_screening(extractor):
    ctx, prov = extractor.extract("What is the bash boost point rule in the Big Bash?")
    assert ctx.cricket_level == "domestic"
    assert ctx.competition == "BBL"


def test_extract_dates_from_query(extractor):
    ctx, prov = extractor.extract("Rules for the match played on 2026-11-15 in T20I")
    assert ctx.match_date == "2026-11-15"
    assert ctx.format == CricketFormat.T20I


def test_explicit_input_override(extractor):
    explicit = MatchContextInput(
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        series_start_date="2026-10-05",
        applicable_rules=DocumentAuthority.ICC,
    )
    ctx, prov = extractor.extract("Can a bowler deliver a bouncer?", explicit_input=explicit)
    assert ctx.format == CricketFormat.TEST
    assert ctx.category == GenderCategory.MENS
    assert ctx.series_start_date == "2026-10-05"
    assert ctx.governing_body == "ICC"
    assert prov["format"] == "explicit_input"
