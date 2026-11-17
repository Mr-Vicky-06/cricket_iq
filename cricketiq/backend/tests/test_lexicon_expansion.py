"""Unit and Regression Tests for Controlled Lexicon Query Expansion (Phase 6 Gate 3).

Validates:
- Lexicon validation and approved status gating
- Query immutability
- 10 hard semantic non-equivalence invariants
- Contrast and negation preservation
- Longest-phrase matching and abbreviation protection
- Bounded expansion counts (K <= 2 phrases, N <= 3 terms)
"""

import pytest
from pathlib import Path

from cricketiq.backend.app.retrieval.nlp.lexicon_service import (
    LexiconValidator,
    LexiconExpansionService,
    NormalizedQueryView,
    LexiconValidationError
)


@pytest.fixture
def lexicon_service() -> LexiconExpansionService:
    return LexiconExpansionService()


# -----------------------------------------------------------------------------
# 1. Validation & Schema Tests
# -----------------------------------------------------------------------------

def test_lexicon_validator_passes_on_corpus_asset(lexicon_service: LexiconExpansionService):
    """Test that existing committed cricket_lexicon.json satisfies all validation rules."""
    assert len(lexicon_service.terms) == 20
    assert lexicon_service.lexicon_version == "1.0.0"
    assert len(lexicon_service.lexicon_hash) == 64


def test_lexicon_validator_detects_malformed_asset():
    """Test that LexiconValidator flags missing fields or duplicate IDs."""
    malformed = {
        "terms": [
            {"term_id": "T1", "preferred_term": "Term 1", "review_status": "APPROVED", "distinct_from": ["T2"]},
            {"term_id": "T1", "preferred_term": "Duplicate T1", "review_status": "APPROVED", "distinct_from": ["T3"]}
        ]
    }
    errors = LexiconValidator.validate(malformed)
    assert any("Duplicate term_id 'T1'" in err for err in errors)


# -----------------------------------------------------------------------------
# 2. Query Immutability Tests
# -----------------------------------------------------------------------------

def test_query_immutability(lexicon_service: LexiconExpansionService):
    """Test that raw_query is preserved byte-identically."""
    raw = "What is the penalty for a BEAMER in a test match?"
    view = lexicon_service.expand_query(raw)
    assert view.raw_query == raw
    assert "beamer" in view.tokens
    assert len(view.expansions) >= 1
    assert view.expansions[0].term_id == "CRIC_DELIV_BEAMER"


# -----------------------------------------------------------------------------
# 3. Hard Semantic Non-Equivalence Invariants
# -----------------------------------------------------------------------------

def test_invariant_retired_hurt_never_expands_to_retired_out(lexicon_service: LexiconExpansionService):
    """Test Invariant 1: Retired hurt must never expand to Retired out."""
    view = lexicon_service.expand_query("Can a batter who is retired hurt bat again?")
    assert any(exp.term_id == "CRIC_DISMISS_RETIRED_HURT" for exp in view.expansions)
    for exp in view.expansions:
        for phrase in exp.expansion_phrases:
            assert "out" not in phrase.lower().split(), f"Leaked 'out' into retired hurt: {phrase}"


def test_invariant_wide_and_no_ball_mutual_exclusion(lexicon_service: LexiconExpansionService):
    """Test Invariant 2: Wide ball never injects No ball and vice versa."""
    view_wb = lexicon_service.expand_query("When does the umpire call a wide delivery?")
    wb_exp = [exp for exp in view_wb.expansions if exp.term_id == "CRIC_DELIV_WIDE_BALL"]
    assert len(wb_exp) == 1
    for phrase in wb_exp[0].expansion_phrases:
        assert "no ball" not in phrase.lower()

    view_nb = lexicon_service.expand_query("Penalty for bowling a no-ball overstepping")
    nb_exp = [exp for exp in view_nb.expansions if exp.term_id == "CRIC_DELIV_NO_BALL"]
    assert len(nb_exp) == 1
    for phrase in nb_exp[0].expansion_phrases:
        assert "wide" not in phrase.lower()


def test_invariant_run_out_and_stumped_distinct(lexicon_service: LexiconExpansionService):
    """Test Invariant 3: Run out and Stumped remain strictly distinct."""
    view_st = lexicon_service.expand_query("Can a batter be stumped off a wide?")
    st_exp = [exp for exp in view_st.expansions if exp.term_id == "CRIC_DISMISS_STUMPED"]
    assert len(st_exp) == 1
    for phrase in st_exp[0].expansion_phrases:
        assert "run out" not in phrase.lower()


def test_invariant_beamer_subset_of_no_ball(lexicon_service: LexiconExpansionService):
    """Test Invariant 5: Generic No ball queries never inject Beamer."""
    view_nb = lexicon_service.expand_query("Rules for front-foot no-ball delivery")
    nb_exp = [exp for exp in view_nb.expansions if exp.term_id == "CRIC_DELIV_NO_BALL"]
    assert len(nb_exp) == 1
    for phrase in nb_exp[0].expansion_phrases:
        assert "beamer" not in phrase.lower()
        assert "high full" not in phrase.lower()

    # But explicit beamer query targets high full-pitched delivery
    view_bm = lexicon_service.expand_query("What is the warning for a beamer?")
    bm_exp = [exp for exp in view_bm.expansions if exp.term_id == "CRIC_DELIV_BEAMER"]
    assert len(bm_exp) == 1
    assert "High full-pitched delivery" in bm_exp[0].expansion_phrases


def test_invariant_mankad_routes_to_non_striker_run_out(lexicon_service: LexiconExpansionService):
    """Test Invariant 6: Mankad maps to CRIC_NON_STRIKER_RUN_OUT (Law 38.3), not generic Run out."""
    view = lexicon_service.expand_query("Is mankading legal under the cricket laws?")
    assert len(view.expansions) == 1
    assert view.expansions[0].term_id == "CRIC_NON_STRIKER_RUN_OUT"
    assert view.expansions[0].matched_token in ["mankad", "mankading"]


# -----------------------------------------------------------------------------
# 4. Contrastive & Negation Handling
# -----------------------------------------------------------------------------

def test_contrastive_query_suppresses_cross_expansion(lexicon_service: LexiconExpansionService):
    """Test that queries comparing concepts (e.g. wide vs no ball) suppress cross-expansion."""
    view = lexicon_service.expand_query("What is the difference between a wide and a no ball?")
    assert view.is_contrastive is True
    # In contrastive mode, expansions are suppressed to prevent cross-contamination
    for exp in view.expansions:
        assert len(exp.expansion_phrases) == 0


def test_dimensional_wide_ignored(lexicon_service: LexiconExpansionService):
    """Test that 'wide' in a dimensional context (how wide is pitch) does not trigger Wide ball rule expansion."""
    view = lexicon_service.expand_query("How wide is the cricket pitch popping crease?")
    assert not any(exp.term_id == "CRIC_DELIV_WIDE_BALL" for exp in view.expansions)


def test_isolated_abbreviation_ignored(lexicon_service: LexiconExpansionService):
    """Test that isolated single letters 'b', 'st', 'wd', 'nb' do not trigger rule expansions."""
    view = lexicon_service.expand_query("Score was 100 for 2 in 20 overs with 5 b and 2 nb")
    # 'b' and 'nb' in isolation must not trigger full legal expansions
    assert not any(exp.term_id == "CRIC_DISMISS_BOWLED" for exp in view.expansions)


# -----------------------------------------------------------------------------
# 5. Bounding & FTS Query Formulation
# -----------------------------------------------------------------------------

def test_expansion_bounding(lexicon_service: LexiconExpansionService):
    """Test that expansion is strictly bounded: N <= 3 terms, K <= 2 phrases."""
    view = lexicon_service.expand_query("Can a batter be bowled, caught, or run out on a free hit?")
    assert len(view.expansions) <= 3
    for exp in view.expansions:
        assert len(exp.expansion_phrases) <= 2

    fts_q = lexicon_service.build_fts_query(view)
    assert fts_q.startswith("(")
    assert "OR" in fts_q


def test_lexicon_hard_caps_internal_enforcement(lexicon_service: LexiconExpansionService):
    """Caller passing high values must be hard-capped inside service to <= 3 terms and <= 2 phrases."""
    view = lexicon_service.expand_query(
        "bowled caught lbw run out stumped free hit",
        max_matched_terms=20,
        max_phrases_per_term=20
    )
    assert len(view.expansions) <= 3
    for exp in view.expansions:
        assert len(exp.expansion_phrases) <= 2


def test_raw_query_immutability_with_whitespace_and_newlines(lexicon_service: LexiconExpansionService):
    """Preserve exact raw input string including leading/trailing whitespace, tabs, and newlines."""
    complex_raw = "\t  \nWhat happens after a no ball?  \r\n  "
    view = lexicon_service.expand_query(complex_raw)
    assert view.raw_query == complex_raw
    assert view.normalized_text == "What happens after a no ball"


def test_lexicon_validator_fail_closed_checks():
    """Verify validator rejects missing definition, term_type, source_refs, self-distinct, and conflict."""
    # 1. Missing definition
    bad1 = {"terms": [{
        "term_id": "T1", "preferred_term": "T1", "term_type": "TYPE",
        "source_refs": ["ref"], "review_status": "APPROVED", "distinct_from": ["T2"]
    }]}
    assert any("definition" in e for e in LexiconValidator.validate(bad1))

    # 2. Missing term_type
    bad2 = {"terms": [{
        "term_id": "T1", "preferred_term": "T1", "definition": "def",
        "source_refs": ["ref"], "review_status": "APPROVED", "distinct_from": ["T2"]
    }]}
    assert any("term_type" in e for e in LexiconValidator.validate(bad2))

    # 3. Missing source_refs
    bad3 = {"terms": [{
        "term_id": "T1", "preferred_term": "T1", "definition": "def",
        "term_type": "TYPE", "review_status": "APPROVED", "distinct_from": ["T2"]
    }]}
    assert any("source_refs" in e for e in LexiconValidator.validate(bad3))

    # 4. Self-referential distinct_from
    bad4 = {"terms": [{
        "term_id": "T1", "preferred_term": "Term One", "definition": "def",
        "term_type": "TYPE", "source_refs": ["ref"], "review_status": "APPROVED", "distinct_from": ["Term One"]
    }]}
    assert any("self-referential" in e for e in LexiconValidator.validate(bad4))

    # 5. Conflicting surface form across term IDs
    bad5 = {"terms": [
        {
            "term_id": "T1", "preferred_term": "Term One", "definition": "def1",
            "term_type": "TYPE", "source_refs": ["ref"], "review_status": "APPROVED",
            "distinct_from": ["T2"], "surface_forms": ["duplicate_phrase"]
        },
        {
            "term_id": "T2", "preferred_term": "Term Two", "definition": "def2",
            "term_type": "TYPE", "source_refs": ["ref"], "review_status": "APPROVED",
            "distinct_from": ["T1"], "surface_forms": ["duplicate_phrase"]
        }
    ]}
    assert any("Conflicting surface phrase" in e for e in LexiconValidator.validate(bad5))


def test_lexicon_applicability_aware_gating(lexicon_service: LexiconExpansionService):
    """Test format-aware gating: Free hit eligible in ODI/T20I, suppressed in Test/MCC."""
    query = "What occurs on a free hit?"
    
    # In ODI: Free hit expansion permitted
    view_odi = lexicon_service.expand_query(query, candidate_document_ids=["ICC_ODI_MEN_2026"])
    fh_exp_odi = [e for e in view_odi.expansions if e.term_id == "CRIC_DELIV_FREE_HIT"]
    assert len(fh_exp_odi) == 1
    assert len(fh_exp_odi[0].expansion_phrases) > 0

    # In T20I: Free hit expansion permitted
    view_t20 = lexicon_service.expand_query(query, candidate_document_ids=["ICC_T20I_MEN_2026"])
    fh_exp_t20 = [e for e in view_t20.expansions if e.term_id == "CRIC_DELIV_FREE_HIT"]
    assert len(fh_exp_t20) == 1
    assert len(fh_exp_t20[0].expansion_phrases) > 0

    # In Test match: Free hit expansion suppressed
    view_test = lexicon_service.expand_query(query, candidate_document_ids=["ICC_TEST_MEN_2026"])
    fh_exp_test = [e for e in view_test.expansions if e.term_id == "CRIC_DELIV_FREE_HIT"]
    assert len(fh_exp_test) == 1
    assert fh_exp_test[0].expansion_phrases == []

    # In MCC universal Laws baseline: Free hit expansion suppressed
    view_mcc = lexicon_service.expand_query(query, candidate_document_ids=["MCC_LAWS_2026"])
    fh_exp_mcc = [e for e in view_mcc.expansions if e.term_id == "CRIC_DELIV_FREE_HIT"]
    assert len(fh_exp_mcc) == 1
    assert fh_exp_mcc[0].expansion_phrases == []


def test_contrastive_queries_suppress_expansions(lexicon_service: LexiconExpansionService):
    """Verify that contrastive queries suppress cross-expansion across distinct terms."""
    # 1. wide versus no ball
    v1 = lexicon_service.expand_query("What is the difference between a wide versus no ball?")
    assert v1.is_contrastive is True
    assert all(len(e.expansion_phrases) == 0 for e in v1.expansions)

    # 2. retired hurt not retired out
    v2 = lexicon_service.expand_query("Is a batter retired hurt not retired out?")
    assert v2.is_contrastive is True
    assert all(len(e.expansion_phrases) == 0 for e in v2.expansions)

    # 3. run out versus stumped
    v3 = lexicon_service.expand_query("Explain run out versus stumped dismissal.")
    assert v3.is_contrastive is True
    assert all(len(e.expansion_phrases) == 0 for e in v3.expansions)

