"""End-to-End integration tests for Unified RetrievalService (Gate 5).
"""

import pytest
from datetime import date
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus,
    ClauseType, MatchContext, CricketFormat, GenderCategory
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import (
    RetrievalRequest, RetrievalOutcome, RetrievalStatus, EvidenceRole
)
from cricketiq.backend.app.retrieval.dense.embedding_provider import LocalDeterministicEmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.service import RetrievalService


@pytest.fixture
def fully_seeded_service() -> RetrievalService:
    """Setup repository with full hybrid retrieval components."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc)

    # 21.18 Free Hit (Parent)
    c1 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc.id,
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
    # 21.18.2 Free Hit Dismissals (Child, references 21.17)
    c2 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=doc.id,
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
    # 21.17 Dismissals from a No ball
    c3 = RuleClause(
        id="ICC_T20I_MEN_2026:21.17",
        source_document_id=doc.id,
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
    repo.upsert_clauses([c1, c2, c3])

    # Build sparse index
    sparse_prov = SQLiteFTSSearchProvider(repo)
    sparse_prov.rebuild_index()

    # Build dense index
    dense_embedder = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(repo, dense_embedder)
    store.build_all_embeddings()
    dense_prov = SQLiteNumPyDenseSearchProvider(repo, dense_embedder, store)

    return RetrievalService(
        repository=repo,
        sparse_provider=sparse_prov,
        dense_provider=dense_prov
    )


def test_retrieval_service_e2e_free_hit_query(fully_seeded_service):
    """End-to-end test: query for free hit dismissals retrieves primary and supporting context."""
    service = fully_seeded_service

    ctx = MatchContext(
        cricket_level="international",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date="2026-10-05",
        match_date="2026-10-06"
    )

    req = RetrievalRequest(
        query="Can a batter be run out on a free hit?",
        match_context=ctx,
        top_k_fused=5,
        include_parent_context=True,
        include_related_evidence=True
    )

    outcome = service.retrieve(req)

    assert outcome.status == RetrievalStatus.SUCCESS
    assert len(outcome.hits) >= 2

    clause_nums = [h.clause_number for h in outcome.hits]
    # Primary hit or related support must contain free hit dismissals
    assert "21.18.2" in clause_nums or "21.18" in clause_nums
    # Cross-reference to 21.17 must be included
    assert "21.17" in clause_nums

    # Verify diagnostics are populated
    diag = outcome.query_diagnostics
    assert "total_retrieval_ms" in diag
    assert "sparse_search_ms" in diag
    assert "dense_search_ms" in diag
    assert "fusion_ms" in diag
    assert "expansion_ms" in diag
    assert diag["total_retrieval_ms"] >= 0


def test_retrieval_service_exact_clause_e2e(fully_seeded_service):
    """End-to-end test: direct query for Clause 21.18.2 returns exact hit as top primary match."""
    service = fully_seeded_service

    ctx = MatchContext(
        cricket_level="international",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        series_start_date="2026-10-05",
        match_date="2026-10-06"
    )

    req = RetrievalRequest(
        query="What is clause 21.18.2?",
        match_context=ctx
    )

    outcome = service.retrieve(req)
    assert outcome.status == RetrievalStatus.SUCCESS
    assert len(outcome.hits) > 0
    top_hit = outcome.hits[0]
    assert top_hit.clause_number == "21.18.2"
    assert top_hit.evidence_role == EvidenceRole.PRIMARY
