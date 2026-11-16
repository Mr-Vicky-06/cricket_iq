"""Tests for Cricket Domain Lexicon, Ontology, and Disambiguation Mappings."""

import json
from pathlib import Path
import pytest


@pytest.fixture
def lexicon_data():
    root = Path(__file__).resolve().parent.parent.parent.parent
    lex_file = root / "data" / "corpus" / "lexicon" / "cricket_lexicon.json"
    assert lex_file.exists(), f"Lexicon file missing at {lex_file}"
    with open(lex_file, "r", encoding="utf-8") as f:
        return json.load(f)


def test_lexicon_schema_and_version(lexicon_data):
    assert "lexicon_version" in lexicon_data
    assert "terms" in lexicon_data
    assert len(lexicon_data["terms"]) >= 15


def test_lexicon_critical_distinctions(lexicon_data):
    term_map = {t["term_id"]: t for t in lexicon_data["terms"]}

    # 1. Retired Hurt vs Retired Out
    assert "CRIC_DISMISS_RETIRED_OUT" in term_map
    assert "CRIC_DISMISS_RETIRED_HURT" in term_map
    assert "Retired hurt" in term_map["CRIC_DISMISS_RETIRED_OUT"]["distinct_from"]
    assert "Retired out" in term_map["CRIC_DISMISS_RETIRED_HURT"]["distinct_from"]

    # 2. Run Out vs Stumped
    assert "CRIC_DISMISS_RUN_OUT" in term_map
    assert "CRIC_DISMISS_STUMPED" in term_map
    assert "Stumped" in term_map["CRIC_DISMISS_RUN_OUT"]["distinct_from"]
    assert "Run out" in term_map["CRIC_DISMISS_STUMPED"]["distinct_from"]

    # 3. No Ball vs Wide Ball
    assert "CRIC_DELIV_NO_BALL" in term_map
    assert "CRIC_DELIV_WIDE_BALL" in term_map
    assert "Wide ball" in term_map["CRIC_DELIV_NO_BALL"]["distinct_from"]
    assert "No ball" in term_map["CRIC_DELIV_WIDE_BALL"]["distinct_from"]


def test_colloquial_alias_coverage(lexicon_data):
    term_map = {t["term_id"]: t for t in lexicon_data["terms"]}

    # Non-striker run out must map to Mankad
    mankad_term = term_map["CRIC_NON_STRIKER_RUN_OUT"]
    assert any("mankad" in s.lower() for s in mankad_term["surface_forms"] + mankad_term["colloquial_query_forms"])
    assert "Law 38.3" in mankad_term["source_refs"][0]

    # Beamer must map to High full-pitched delivery
    beamer_term = term_map["CRIC_DELIV_BEAMER"]
    assert any("beamer" in s.lower() for s in beamer_term["surface_forms"] + beamer_term["colloquial_query_forms"])
    assert "Law 41.7" in beamer_term["source_refs"][0] or "Clause 21.5" in beamer_term["source_refs"][1]


def test_every_term_has_official_source_reference(lexicon_data):
    for term in lexicon_data["terms"]:
        assert len(term["source_refs"]) > 0, f"Term {term['term_id']} lacks source_refs"
        assert term["review_status"] == "APPROVED"
