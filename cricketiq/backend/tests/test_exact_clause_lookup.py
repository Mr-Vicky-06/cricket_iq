"""Tests for Exact Clause Lookup Engine in CricketIQ."""

import pytest
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import Base, create_db_engine
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType,
    ScopeLevel, CricketFormat, GenderCategory, DocumentStatus, ClauseType
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.exact_clause_lookup import ExactClauseLookupEngine


@pytest.fixture
def seeded_repo() -> CricketIQRepository:
    eng = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=eng)
    session = Session(bind=eng)

    repo = CricketIQRepository(session)

    # Document 1: ICC T20I Men 2026
    doc1 = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        official_url="https://www.icc-cricket.com/pc",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc1)

    # Document 2: ICC Test Men 2026
    doc2 = SourceDocument(
        id="ICC_TEST_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Test Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        official_url="https://www.icc-cricket.com/pc",
        sha256="2" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc2)

    # Clauses in T20I
    c21 = RuleClause(
        id="ICC_T20I_MEN_2026:21",
        source_document_id=doc1.id,
        clause_number="21",
        heading="No Ball",
        original_text="21 NO BALL",
        page_start=1,
        page_end=1
    )
    c21_1 = RuleClause(
        id="ICC_T20I_MEN_2026:21.1",
        source_document_id=doc1.id,
        clause_number="21.1",
        parent_clause_id=c21.id,
        heading="Mode of delivery",
        original_text="21.1 Mode of delivery",
        page_start=1,
        page_end=1
    )
    c21_18 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc1.id,
        clause_number="21.18",
        parent_clause_id=c21.id,
        heading="Free Hit",
        original_text="21.18 Free Hit",
        page_start=2,
        page_end=2
    )
    c21_18_2 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=doc1.id,
        clause_number="21.18.2",
        parent_clause_id=c21_18.id,
        heading="Dismissal on Free Hit",
        original_text="For any free hit, the striker can be dismissed only under circumstances of a No ball.",
        page_start=2,
        page_end=2
    )

    # Clause in Test (same clause number 21.1 but in Test PC)
    c_test_21_1 = RuleClause(
        id="ICC_TEST_MEN_2026:21.1",
        source_document_id=doc2.id,
        clause_number="21.1",
        heading="Mode of delivery (Test)",
        original_text="21.1 Mode of delivery in Test match cricket.",
        page_start=1,
        page_end=1
    )

    repo.upsert_clauses([c21, c21_1, c21_18, c21_18_2, c_test_21_1])
    return repo


def test_exact_lookup_extracts_dotted_clause(seeded_repo):
    engine = ExactClauseLookupEngine(seeded_repo)
    matches = engine.lookup("What does clause 21.18.2 state regarding dismissals?")
    assert len(matches) == 1
    clause, score = matches[0]
    assert clause.clause_number == "21.18.2"
    assert clause.id == "ICC_T20I_MEN_2026:21.18.2"
    assert score == 1.0


def test_exact_lookup_punctuation_variations(seeded_repo):
    engine = ExactClauseLookupEngine(seeded_repo)

    # Various punctuation and phrasing
    for q in ["(Clause 21.18.2)", "Explain 21.18.2.", "rule 21.18.2?", "Law 21.18.2;"]:
        matches = engine.lookup(q)
        assert len(matches) == 1
        assert matches[0][0].clause_number == "21.18.2"


def test_exact_lookup_filters_by_candidate_document(seeded_repo):
    engine = ExactClauseLookupEngine(seeded_repo)

    # Clause 21.1 exists in both T20I and Test
    # Restrict to T20I
    t20_hits = engine.lookup("Clause 21.1", candidate_document_ids=["ICC_T20I_MEN_2026"])
    assert len(t20_hits) == 1
    assert t20_hits[0][0].id == "ICC_T20I_MEN_2026:21.1"

    # Restrict to Test
    test_hits = engine.lookup("Clause 21.1", candidate_document_ids=["ICC_TEST_MEN_2026"])
    assert len(test_hits) == 1
    assert test_hits[0][0].id == "ICC_TEST_MEN_2026:21.1"

    # If candidate document does not have the clause, return empty
    empty_hits = engine.lookup("Clause 21.18.2", candidate_document_ids=["ICC_TEST_MEN_2026"])
    assert len(empty_hits) == 0


def test_exact_lookup_no_false_positive_on_similar_numbers(seeded_repo):
    engine = ExactClauseLookupEngine(seeded_repo)
    # Searching for 21.1 should NOT match 21.18.2 or 21.18
    hits = engine.lookup("Clause 21.1", candidate_document_ids=["ICC_T20I_MEN_2026"])
    assert len(hits) == 1
    assert hits[0][0].clause_number == "21.1"
