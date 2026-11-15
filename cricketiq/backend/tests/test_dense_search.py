"""Unit tests for Dense Semantic Search with SQLite and NumPy (Gate 4).
"""

import pytest
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus, ClauseType
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.dense.embedding_provider import LocalDeterministicEmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider


@pytest.fixture
def seeded_dense_search() -> SQLiteNumPyDenseSearchProvider:
    """Create in-memory repository, populate clauses, and build vector index."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    # Documents
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

    # Clauses
    c1 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=t20_doc.id,
        clause_number="21.18",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit for whichever batter is facing it.",
        normalized_text="the delivery following a no ball shall be a free hit for whichever batter is facing it",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    c2 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=t20_doc.id,
        clause_number="21.18.2",
        parent_clause_id=c1.id,
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
    repo.upsert_clauses([c1, c2, c3])

    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(repo, provider)
    store.build_all_embeddings()

    return SQLiteNumPyDenseSearchProvider(repo, provider, store)


def test_dense_search_semantic_matching(seeded_dense_search):
    """Test semantic search for free-hit questions."""
    searcher = seeded_dense_search
    results = searcher.search("Can a batter be dismissed on a free delivery?", top_k=5)

    assert len(results) > 0
    top_clause, score = results[0]
    assert "ICC_T20I_MEN_2026" in top_clause.source_document_id
    assert -1.0 <= score <= 1.0


def test_dense_search_candidate_scoping(seeded_dense_search):
    """Test candidate document filtering prevents cross-format leakage."""
    searcher = seeded_dense_search

    # Restrict to Test document only
    results_test = searcher.search("free hit delivery", candidate_document_ids=["ICC_TEST_MEN_2026"])
    for clause, _ in results_test:
        assert clause.source_document_id == "ICC_TEST_MEN_2026"

    # Empty candidate list returns zero results
    results_empty = searcher.search("free hit", candidate_document_ids=[])
    assert len(results_empty) == 0


def test_dense_search_empty_queries(seeded_dense_search):
    """Test handling of blank, empty, or whitespace queries."""
    searcher = seeded_dense_search
    assert searcher.search("") == []
    assert searcher.search("   ") == []
