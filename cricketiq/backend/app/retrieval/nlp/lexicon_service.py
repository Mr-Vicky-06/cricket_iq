"""Controlled Cricket Domain Lexicon Expansion Engine (Phase 6 Gate 3).

Provides deterministic, provenance-tracked query expansion grounded in
data/corpus/lexicon/cricket_lexicon.json with hard semantic non-equivalence guardrails.
"""

from __future__ import annotations
import hashlib
import json
import re
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_LEXICON_PATH = PROJECT_ROOT / "data" / "corpus" / "lexicon" / "cricket_lexicon.json"

CONTRAST_PATTERN = re.compile(
    r"\b(?:versus|vs|not|except|difference\s+between|rather\s+than|or\s+a\s+no\s*ball)\b",
    re.IGNORECASE
)

EXACT_CLAUSE_REGEX = re.compile(
    r"(?:(?:clause|law|rule|section)\s+)?\b([0-9]{1,2}(?:\.[0-9]{1,2}(?:\.[0-9]{1,2})?)?)\b",
    re.IGNORECASE
)

# Ambiguous isolated abbreviations that must not trigger expansion in isolation
AMBIGUOUS_ABBREVIATIONS = {"b", "st", "nb", "wd", "ro"}


class LexiconReviewStatus(str, Enum):
    APPROVED = "APPROVED"
    DRAFT = "DRAFT"
    DEPRECATED = "DEPRECATED"


class LexiconTermRecord(BaseModel):
    term_id: str
    preferred_term: str
    surface_forms: List[str] = Field(default_factory=list)
    abbreviations: List[str] = Field(default_factory=list)
    spelling_variants: List[str] = Field(default_factory=list)
    colloquial_query_forms: List[str] = Field(default_factory=list)
    definition: Optional[str] = None
    term_type: Optional[str] = None
    related_terms: List[str] = Field(default_factory=list)
    distinct_from: List[str] = Field(default_factory=list)
    source_refs: List[str] = Field(default_factory=list)
    review_status: LexiconReviewStatus = LexiconReviewStatus.APPROVED


class LexiconExpansionTrace(BaseModel):
    matched_token: str
    term_id: str
    preferred_term: str
    expansion_phrases: List[str]
    matched_field: str
    distinct_from_suppressed: List[str] = Field(default_factory=list)
    provenance_source: str = "cricket_lexicon.json"


class NormalizedQueryView(BaseModel):
    raw_query: str
    normalized_text: str
    tokens: List[str]
    extracted_clause_identifiers: List[str] = Field(default_factory=list)
    expansions: List[LexiconExpansionTrace] = Field(default_factory=list)
    is_contrastive: bool = False
    contrastive_terms: List[str] = Field(default_factory=list)
    lexicon_version: str = "1.0.0"
    lexicon_hash: str = ""


class LexiconValidationError(Exception):
    """Raised when lexicon JSON asset fails validation."""
    pass


class LexiconValidator:
    """Validates structure, uniqueness, and consistency of cricket lexicon asset."""

    @staticmethod
    def validate(lexicon_data: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        if not isinstance(lexicon_data, dict):
            return ["Lexicon asset must be a JSON object"]

        terms = lexicon_data.get("terms")
        if not isinstance(terms, list) or len(terms) == 0:
            return ["Lexicon must contain non-empty 'terms' list"]

        seen_ids: Set[str] = set()
        seen_prefs: Dict[str, str] = {}
        phrase_to_owner: Dict[str, Tuple[str, str]] = {}

        # Pass 1: Required non-empty fields, ID uniqueness, and valid review status
        for idx, t in enumerate(terms):
            if not isinstance(t, dict):
                errors.append(f"Term at index {idx} must be a dictionary")
                continue

            tid = t.get("term_id")
            if not tid or not isinstance(tid, str) or not tid.strip():
                errors.append(f"Term at index {idx} has invalid or missing 'term_id'")
                continue
            if tid in seen_ids:
                errors.append(f"Duplicate term_id '{tid}' at index {idx}")
            seen_ids.add(tid)

            pref = t.get("preferred_term")
            if not pref or not isinstance(pref, str) or not pref.strip():
                errors.append(f"Term '{tid}' missing or empty 'preferred_term'")
            else:
                seen_prefs[pref.lower().strip()] = tid

            defn = t.get("definition")
            if not defn or not isinstance(defn, str) or not defn.strip():
                errors.append(f"Term '{tid}' missing or empty 'definition'")

            ttype = t.get("term_type")
            if not ttype or not isinstance(ttype, str) or not ttype.strip():
                errors.append(f"Term '{tid}' missing or empty 'term_type'")

            refs = t.get("source_refs")
            if not refs or not isinstance(refs, list) or len(refs) == 0:
                errors.append(f"Term '{tid}' missing or empty 'source_refs'")

            status = t.get("review_status")
            if status not in [s.value for s in LexiconReviewStatus]:
                errors.append(f"Term '{tid}' has invalid review_status: {status}")

            distinct = t.get("distinct_from")
            if status == LexiconReviewStatus.APPROVED.value and (not distinct or not isinstance(distinct, list)):
                errors.append(f"Approved term '{tid}' must have non-empty 'distinct_from' list")

        # Pass 2: Surface form conflict detection and self-referential distinct_from
        for t in terms:
            tid = t.get("term_id")
            if not tid or tid not in seen_ids:
                continue

            pref_clean = (t.get("preferred_term") or "").lower().strip()

            # Self-referential distinct_from
            distinct_list = t.get("distinct_from") or []
            for d in distinct_list:
                d_str = str(d).lower().strip()
                if d_str == pref_clean or d == tid:
                    errors.append(f"Term '{tid}' contains self-referential 'distinct_from' link to '{d}'")

            # Conflicting surface forms across terms
            for field_name in ["surface_forms", "spelling_variants", "colloquial_query_forms"]:
                for phrase in t.get(field_name) or []:
                    p_clean = str(phrase).lower().strip()
                    if not p_clean:
                        continue
                    # Deliberate single-owner exception: mankad/mankading routes exclusively to CRIC_NON_STRIKER_RUN_OUT
                    if p_clean in ["mankad", "mankading"]:
                        continue
                    if p_clean in phrase_to_owner:
                        owner_tid, owner_field = phrase_to_owner[p_clean]
                        if owner_tid != tid:
                            errors.append(
                                f"Conflicting surface phrase '{p_clean}' found in '{tid}' ({field_name}) "
                                f"and '{owner_tid}' ({owner_field})"
                            )
                    else:
                        phrase_to_owner[p_clean] = (tid, field_name)

        return errors


class LexiconExpansionService:
    """Provides controlled, non-equivalence-guarded query expansion."""

    def __init__(self, lexicon_path: Optional[Path] = None):
        self.lexicon_path = lexicon_path or DEFAULT_LEXICON_PATH
        self.terms: Dict[str, LexiconTermRecord] = {}
        self.phrase_to_term: Dict[str, str] = {}
        self.lexicon_version = "1.0.0"
        self.lexicon_hash = ""
        self._load_and_index()

    def _load_and_index(self) -> None:
        if not self.lexicon_path.exists():
            raise FileNotFoundError(f"Lexicon file missing: {self.lexicon_path}")

        raw_bytes = self.lexicon_path.read_bytes()
        self.lexicon_hash = hashlib.sha256(raw_bytes).hexdigest()
        data = json.loads(raw_bytes.decode("utf-8"))

        errors = LexiconValidator.validate(data)
        if errors:
            raise LexiconValidationError(f"Lexicon validation failed: {errors}")

        self.lexicon_version = data.get("lexicon_version", "1.0.0")

        # Load approved terms only
        for t_dict in data.get("terms", []):
            rec = LexiconTermRecord(**t_dict)
            if rec.review_status == LexiconReviewStatus.APPROVED:
                self.terms[rec.term_id] = rec

        # Build longest-phrase-first index
        phrase_map: Dict[str, Tuple[str, str]] = {}
        for tid, rec in self.terms.items():
            # 1. Preferred term
            pref_clean = rec.preferred_term.lower().strip()
            phrase_map[pref_clean] = (tid, "preferred_term")

            # 2. Surface forms
            for sf in rec.surface_forms:
                clean = sf.lower().strip()
                if clean and clean not in phrase_map:
                    phrase_map[clean] = (tid, "surface_forms")

            # 3. Spelling variants
            for sv in rec.spelling_variants:
                clean = sv.lower().strip()
                if clean and clean not in phrase_map:
                    phrase_map[clean] = (tid, "spelling_variants")

            # 4. Colloquial query forms
            for cq in rec.colloquial_query_forms:
                clean = cq.lower().strip()
                if clean:
                    # Reconciliation Policy: route 'mankad' exclusively to CRIC_NON_STRIKER_RUN_OUT
                    if clean in ["mankad", "mankading"]:
                        phrase_map[clean] = ("CRIC_NON_STRIKER_RUN_OUT", "colloquial_query_forms")
                    elif clean not in phrase_map:
                        phrase_map[clean] = (tid, "colloquial_query_forms")

        self.phrase_to_term = phrase_map

    def expand_query(
        self,
        raw_query: str,
        candidate_document_ids: Optional[List[str]] = None,
        max_matched_terms: int = 3,
        max_phrases_per_term: int = 2
    ) -> NormalizedQueryView:
        """Derive controlled query expansions preserving raw query immutability.
        
        Hard Semantic Invariants (Phase 6 Gate 3):
        - Enforces strict hard caps: max_matched_terms <= 3, max_phrases_per_term <= 2.
        - Preserves exact raw_query string unaltered in NormalizedQueryView.raw_query.
        - Never expands across distinct_from boundaries.
        - Suppresses cross-expansion when contrastive intent or distinct_from pairs are detected.
        - Gating: 'free hit' expansion requires ODI or T20I in candidate_document_ids.
        - Gating: 'beamer' is narrower than 'no ball'; generic 'no ball' never injects 'beamer'.
        - Gating: 'mankad' maps exclusively to Law/Clause 38.3 (CRIC_NON_STRIKER_RUN_OUT).
        - Gating: 'retired hurt' never expands to 'retired out'.
        - Isolated ambiguous abbreviations ('b', 'st', 'nb', 'wd', 'ro') are rejected.
        """
        # Hard caps enforcement regardless of caller arguments
        eff_max_matched = min(max(max_matched_terms, 1), 3)
        eff_max_phrases = min(max(max_phrases_per_term, 1), 2)

        raw_clean = raw_query.strip()
        query_lower = raw_clean.lower()

        # 1. Extract exact dotted clause numbers
        clause_matches = EXACT_CLAUSE_REGEX.findall(raw_clean)
        extracted_clauses = [m for m in clause_matches if m]

        # 2. Basic tokenization
        tokens = [w for w in re.split(r"[\s,;?!\(\)]+", query_lower) if w]

        # 3. Detect contrastive intent (e.g., 'versus', 'vs', 'difference between', 'wide and no ball')
        is_contrastive = bool(CONTRAST_PATTERN.search(query_lower))
        if "wide" in query_lower and ("no ball" in query_lower or "no-ball" in query_lower or "noball" in query_lower):
            is_contrastive = True

        # 4. Longest-phrase candidate matching
        matched_traces: List[LexiconExpansionTrace] = []
        matched_term_ids: Set[str] = set()
        matched_records: Dict[str, LexiconTermRecord] = {}

        # Sort candidate phrases by length descending
        sorted_phrases = sorted(self.phrase_to_term.keys(), key=lambda p: len(p), reverse=True)

        for phrase in sorted_phrases:
            if len(matched_term_ids) >= eff_max_matched:
                break

            # Exact word-boundary match
            pattern = r"\b" + re.escape(phrase) + r"\b"
            if re.search(pattern, query_lower):
                # Filter out isolated ambiguous abbreviations
                if phrase in AMBIGUOUS_ABBREVIATIONS:
                    continue

                # Filter out 'wide' when used as dimension (e.g. 'how wide is the crease')
                if phrase == "wide" and any(k in query_lower for k in ["how wide", "crease wide", "pitch wide", "bat wide"]):
                    continue

                tid, field_name = self.phrase_to_term[phrase]
                if tid in matched_term_ids:
                    continue

                term_rec = self.terms[tid]
                matched_records[tid] = term_rec
                matched_term_ids.add(tid)

        # Generic distinct_from contrast check across matched terms
        for tid1, rec1 in matched_records.items():
            for tid2, rec2 in matched_records.items():
                if tid1 != tid2:
                    pref2_low = rec2.preferred_term.lower()
                    if any(d.lower() == pref2_low for d in rec1.distinct_from):
                        is_contrastive = True

        for phrase in sorted_phrases:
            pattern = r"\b" + re.escape(phrase) + r"\b"
            if not re.search(pattern, query_lower):
                continue
            if phrase in AMBIGUOUS_ABBREVIATIONS:
                continue
            if phrase == "wide" and any(k in query_lower for k in ["how wide", "crease wide", "pitch wide", "bat wide"]):
                continue

            tid, field_name = self.phrase_to_term[phrase]
            if tid not in matched_records or any(t.term_id == tid for t in matched_traces):
                continue

            term_rec = matched_records[tid]

            # Determine candidate expansions (K <= 2)
            candidate_expansions: List[str] = []
            if term_rec.preferred_term.lower() != phrase:
                candidate_expansions.append(term_rec.preferred_term)

            for sf in term_rec.surface_forms:
                sf_low = sf.lower()
                if sf_low != phrase and sf_low != term_rec.preferred_term.lower():
                    candidate_expansions.append(sf)
                    break

            # Enforce Semantic Invariants & Context Gating:
            # 1. Free Hit applicability gating: only eligible for Limited Overs formats (ODI / T20I)
            if tid == "CRIC_DELIV_FREE_HIT" and candidate_document_ids:
                has_free_hit = any("ODI" in d or "T20I" in d for d in candidate_document_ids)
                if not has_free_hit:
                    # Gated out in Test and universal MCC Laws baseline
                    candidate_expansions = []

            # 2. Beamer: generic 'no ball' never injects 'beamer'
            if tid == "CRIC_DELIV_NO_BALL":
                candidate_expansions = [
                    e for e in candidate_expansions
                    if "beamer" not in e.lower() and "high full" not in e.lower()
                ]

            # 3. Retired hurt: never include 'retired out'
            if tid == "CRIC_DISMISS_RETIRED_HURT":
                candidate_expansions = [e for e in candidate_expansions if "out" not in e.lower().split()]

            # 4. Contrastive suppression: if contrastive query, suppress expansions across mutually distinct terms
            if is_contrastive:
                candidate_expansions = []

            trace = LexiconExpansionTrace(
                matched_token=phrase,
                term_id=tid,
                preferred_term=term_rec.preferred_term,
                expansion_phrases=candidate_expansions[:eff_max_phrases],
                matched_field=field_name,
                distinct_from_suppressed=term_rec.distinct_from
            )
            matched_traces.append(trace)
            if len(matched_traces) >= eff_max_matched:
                break

        # Normalize text view (safe punctuation cleanup, keeping original words)
        normalized_text = re.sub(r"[^\w\s\.\-]", " ", raw_clean)
        normalized_text = re.sub(r"\s+", " ", normalized_text).strip()

        return NormalizedQueryView(
            raw_query=raw_query,  # Exact input string immutability preserved
            normalized_text=normalized_text,
            tokens=tokens,
            extracted_clause_identifiers=extracted_clauses,
            expansions=matched_traces,
            is_contrastive=is_contrastive,
            contrastive_terms=list(matched_term_ids) if is_contrastive else [],
            lexicon_version=self.lexicon_version,
            lexicon_hash=self.lexicon_hash
        )

    def build_fts_query(self, view: NormalizedQueryView) -> str:
        """Formulate a sanitized, bounded FTS5 query string with expansion phrases."""
        # 1. Sanitize original query tokens
        clean_tokens = [re.sub(r'[^\w\-]', '', t) for t in view.tokens if t and len(t) > 1]
        
        # Preserve key hyphenated terms
        base_clause = " ".join(clean_tokens) if clean_tokens else view.normalized_text

        if not view.expansions:
            return base_clause

        # Append expansion phrases with disjunction OR
        expansion_parts: List[str] = []
        for exp in view.expansions:
            for phrase in exp.expansion_phrases:
                phrase_clean = re.sub(r'[^\w\s\-]', '', phrase).strip()
                if " " in phrase_clean:
                    expansion_parts.append(f'"{phrase_clean}"')
                else:
                    expansion_parts.append(phrase_clean)

        if expansion_parts:
            # Formulate: (original query) OR ("expansion phrase")
            return f"({base_clause}) OR {' OR '.join(expansion_parts)}"
        return base_clause
