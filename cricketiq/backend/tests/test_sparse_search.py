"""Unit tests for SQLite FTS5 Sparse Search Provider (Gate 2).
"""

import pytest
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus, ClauseType
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider


@pytest.fixture
def seeded_repo() -> CricketIQRepository:
    """Create in-memory SQLite database with repository and sample clauses."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)

    repo = CricketIQRepository(session)

    # Add source documents
    t20_doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format="T20I",
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    test_doc = SourceDocument(
        id="ICC_TEST_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Test Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format="Test",
        official_url="https://www.icc-cricket.com/test-2026.pdf",
        sha256="2" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(t20_doc)
    repo.upsert_source_document(test_doc)

    # Add clauses
    c1 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=t20_doc.id,
        clause_number="21.18",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="In addition to the above, the delivery following a No ball shall be a free hit for whichever batter is facing it.",
        normalized_text="in addition to the above the delivery following a no ball shall be a free hit for whichever batter is facing it",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    c2 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=t20_doc.id,
        clause_number="21.18.2",
        parent_clause_id="ICC_T20I_MEN_2026:21.18",
        hierarchy_depth=3,
        heading="Free Hit Dismissals",
        original_text="For any free hit, the striker can be dismissed only under the circumstances that apply for a No ball.",
        normalized_text="for any free hit the striker can be dismissed only under the circumstances that apply for a no ball",
        clause_type=ClauseType.EXCEPTION,
        cross_references=["21.17"],
        page_start=1,
        page_end=1
    )
    c3 = RuleClause(
        id="ICC_T20I_MEN_2026:21.17",
        source_document_id=t20_doc.id,
        clause_number="21.17",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Dismissals from a No ball",
        original_text="When a No ball has been bowled, neither batter shall be out off that delivery except for Run out, Hit the ball twice or Obstructing the field.",
        normalized_text="when a no ball has been bowled neither batter shall be out off that delivery except for run out hit the ball twice or obstructing the field",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    c4 = RuleClause(
        id="ICC_TEST_MEN_2026:21.1",
        source_document_id=test_doc.id,
        clause_number="21.1",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Mode of delivery",
        original_text="The umpire shall ascertain whether the bowler intends to bowl right-handed or left-handed.",
        normalized_text="the umpire shall ascertain whether the bowler intends to bowl right handed or left handed",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )

    repo.upsert_clauses([c1, c2, c3, c4])
    return repo


def test_fts5_rebuild_and_phrase_search(seeded_repo):
    """Test FTS5 index build and phrase search for 'free hit'."""
    repo = seeded_repo
    fts = SQLiteFTSSearchProvider(repo)
    indexed_count = fts.rebuild_index()
    assert indexed_count == 4

    results = fts.search("free hit", top_k=5)
    assert len(results) >= 2
    matched_ids = [c.id for c, score in results]
    assert "ICC_T20I_MEN_2026:21.18" in matched_ids
    assert "ICC_T20I_MEN_2026:21.18.2" in matched_ids
    # Higher rank has positive score
    assert results[0][1] > 0


def test_fts5_punctuation_and_hyphenation(seeded_repo):
    """Test query with hyphenated domain term 'no-ball' and punctuation."""
    repo = seeded_repo
    fts = SQLiteFTSSearchProvider(repo)
    fts.rebuild_index()

    # Query with hyphenation and question mark
    results = fts.search("What happens if a bowler bowls a no-ball?", top_k=5)
    assert len(results) > 0
    matched_ids = [c.id for c, score in results]
    assert "ICC_T20I_MEN_2026:21.17" in matched_ids


def test_fts5_candidate_document_scoping(seeded_repo):
    """Test that candidate_document_ids strictly isolates results."""
    repo = seeded_repo
    fts = SQLiteFTSSearchProvider(repo)
    fts.rebuild_index()

    # Scope only to Test PC
    results_test = fts.search("No ball bowler", candidate_document_ids=["ICC_TEST_MEN_2026"])
    # ICC_TEST_MEN_2026:21.1 has 'bowler', but T20I clauses must NOT appear
    for c, score in results_test:
        assert c.source_document_id == "ICC_TEST_MEN_2026"

    # Empty candidate list returns zero results
    results_empty = fts.search("No ball", candidate_document_ids=[])
    assert len(results_empty) == 0


def test_fts5_sync_and_delete(seeded_repo):
    """Test updating and deleting clauses in FTS index."""
    repo = seeded_repo
    fts = SQLiteFTSSearchProvider(repo)
    fts.rebuild_index()

    # Create new clause and sync
    new_clause = RuleClause(
        id="ICC_T20I_MEN_2026:22.1",
        source_document_id="ICC_T20I_MEN_2026",
        clause_number="22.1",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Judging a Wide",
        original_text="If the bowler bowls a ball not being a No ball, the umpire shall adjudge it a Wide.",
        normalized_text="if the bowler bowls a ball not being a no ball the umpire shall adjudge it a wide",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    repo.upsert_clauses([new_clause])
    fts.sync_clause(new_clause)

    res = fts.search("Judging a Wide")
    assert len(res) > 0
    assert res[0][0].id == "ICC_T20I_MEN_2026:22.1"

    # Delete clause
    fts.delete_clause("ICC_T20I_MEN_2026:22.1")
    res_after = fts.search("Judging a Wide")
    assert not any(c.id == "ICC_T20I_MEN_2026:22.1" for c, _ in res_after)


def test_fts5_hostile_syntax_resilience(seeded_repo):
    """Test that hostile or malformed FTS syntax does not raise exceptions."""
    repo = seeded_repo
    fts = SQLiteFTSSearchProvider(repo)
    fts.rebuild_index()

    # Hostile characters that break raw FTS5 MATCH
    hostile_queries = [
        "***)))(((;;;'''''\"\"\"",
        "AND OR NOT NEAR",
        "   ",
        "",
        "\"unclosed quote",
        "nested (((( parentheses"
    ]

    for hq in hostile_queries:
        # Should gracefully return list without throwing syntax error
        res = fts.search(hq)
        assert isinstance(res, list)
