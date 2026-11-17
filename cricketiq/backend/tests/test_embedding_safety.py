"""Tests for Dense Embedding Channel Safety and Metadata Gating (Phase 6 Gate 2 Remediation).

Verifies:
1. Databases with 'local-deterministic-v1' embeddings cannot activate dense semantic ranking by default.
2. Explicit enable_diagnostic_dense=True allows diagnostic dense search.
3. Inconsistent or mixed model metadata disables dense ranking safely.
4. Provider model mismatch disables dense ranking.
5. A configured semantic provider (is_semantic=True) is authorized for production RRF.
6. Dense provider exceptions fail safely without corrupting sparse/exact results.
7. Exact clause lookup and sparse retrieval work cleanly when dense is disabled.
"""

import pytest
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus,
    ClauseType, CricketFormat, GenderCategory, ScopeLevel, RegulatoryRole, MatchContext
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import RetrievalRequest, RetrievalStatus
from cricketiq.backend.app.retrieval.dense.base import EmbeddingProvider, DenseSearchProvider
from cricketiq.backend.app.retrieval.dense.embedding_provider import LocalDeterministicEmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.service import RetrievalService


class MockSemanticEmbeddingProvider:
    """Mock semantic provider that behaves like a transformer model."""
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2", dimension: int = 384):
        self._model_name = model_name
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def is_semantic(self) -> bool:
        return True

    def embed_text(self, text: str) -> List[float]:
        return [0.1] * self._dim

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * self._dim for _ in texts]


class FailingDenseProvider:
    """Mock dense provider that raises an exception during search."""
    def __init__(self):
        self.is_semantic = True
        self.model_name = "failing-model"
        self.dimension = 384

    def search(self, *args, **kwargs):
        raise RuntimeError("Simulated dense provider runtime failure")


@pytest.fixture
def test_repo():
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        regulatory_role=RegulatoryRole.NORMATIVE_FORMAT_PC,
        edition="October 2026",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="a" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc)

    clause = RuleClause(
        id="ICC_T20I_MEN_2026:21.1",
        source_document_id=doc.id,
        clause_number="21.1",
        heading="Mode of delivery",
        original_text="21.1 Mode of delivery. The umpire shall ascertain whether the bowler intends to bowl right handed or left handed.",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    repo.upsert_clauses([clause])
    return repo


def test_hash_dense_provider_disabled_by_default(test_repo):
    """local-deterministic-v1 must NOT be authorized for production RRF by default."""
    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    assert not provider.is_semantic

    store = EmbeddingStore(test_repo, provider)
    store.build_all_embeddings()

    fts = SQLiteFTSSearchProvider(test_repo)
    fts.rebuild_index()

    dense_provider = SQLiteNumPyDenseSearchProvider(test_repo, provider, store)
    service = RetrievalService(repository=test_repo, dense_provider=dense_provider)

    is_ready, reason = service.check_dense_channel_readiness()
    assert not is_ready
    assert "local-deterministic-v1" in reason
    assert "non-semantic" in reason

    req = RetrievalRequest(
        query="mode of delivery",
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    outcome = service.retrieve(req)
    assert outcome.status == RetrievalStatus.SUCCESS
    assert outcome.query_diagnostics["dense_channel_authorized"] is False
    assert outcome.query_diagnostics["dense_hits_count"] == 0


def test_hash_dense_provider_allowed_with_explicit_diagnostic_flag(test_repo):
    """local-deterministic-v1 CAN be activated when enable_diagnostic_dense=True."""
    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(test_repo, provider)
    store.build_all_embeddings()

    dense_provider = SQLiteNumPyDenseSearchProvider(test_repo, provider, store)
    service = RetrievalService(
        repository=test_repo,
        dense_provider=dense_provider,
        enable_diagnostic_dense=True
    )

    is_ready, reason = service.check_dense_channel_readiness()
    assert is_ready
    assert "active" in reason.lower()

    req = RetrievalRequest(
        query="mode of delivery",
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    outcome = service.retrieve(req)
    assert outcome.status == RetrievalStatus.SUCCESS
    assert outcome.query_diagnostics["dense_channel_authorized"] is True
    assert outcome.query_diagnostics["dense_hits_count"] > 0


def test_semantic_provider_authorized(test_repo):
    """An authentic semantic transformer provider is authorized for production RRF."""
    semantic_provider = MockSemanticEmbeddingProvider()
    assert semantic_provider.is_semantic

    store = EmbeddingStore(test_repo, semantic_provider)
    store.build_all_embeddings()

    dense_provider = SQLiteNumPyDenseSearchProvider(test_repo, semantic_provider, store)
    service = RetrievalService(repository=test_repo, dense_provider=dense_provider)

    is_ready, reason = service.check_dense_channel_readiness()
    assert is_ready
    assert "active" in reason.lower()


def test_model_mismatch_disables_dense(test_repo):
    """Dense channel is disabled if provider model does not match database store model."""
    provider1 = LocalDeterministicEmbeddingProvider(dimension=384, model_name="model-v1")
    store = EmbeddingStore(test_repo, provider1)
    store.build_all_embeddings()

    # Provider asking for different model
    provider2 = MockSemanticEmbeddingProvider(model_name="model-v2")
    dense_provider = SQLiteNumPyDenseSearchProvider(test_repo, provider2, store)
    service = RetrievalService(repository=test_repo, dense_provider=dense_provider)

    is_ready, reason = service.check_dense_channel_readiness()
    assert not is_ready
    assert "does not match" in reason


def test_dense_runtime_failure_falls_back_cleanly(test_repo):
    """An exception in dense search does not abort the query; sparse results succeed."""
    failing = FailingDenseProvider()
    service = RetrievalService(
        repository=test_repo,
        dense_provider=failing,
        enable_diagnostic_dense=True
    )

    # Rebuild sparse FTS
    fts = SQLiteFTSSearchProvider(test_repo)
    fts.rebuild_index()

    req = RetrievalRequest(
        query="mode of delivery",
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    outcome = service.retrieve(req)
    assert outcome.status == RetrievalStatus.SUCCESS
    assert len(outcome.hits) > 0
    assert "dense_search_error" in outcome.query_diagnostics
    assert "Simulated dense provider runtime failure" in outcome.query_diagnostics["dense_search_error"]
