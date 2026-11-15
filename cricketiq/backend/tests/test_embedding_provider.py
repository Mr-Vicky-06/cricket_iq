"""Unit tests for Embedding Provider and Embedding Store (Gate 3).
"""

import pytest
import numpy as np
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus, ClauseType
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.dense.embedding_provider import (
    LocalDeterministicEmbeddingProvider,
    build_clause_embedding_text,
    EMBEDDING_TEMPLATE_VERSION
)
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore


@pytest.fixture
def repo_with_clauses() -> CricketIQRepository:
    """Create in-memory repository with test documents and clauses."""
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
        format="T20I",
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc)

    c1 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc.id,
        clause_number="21.18",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit.",
        normalized_text="the delivery following a no ball shall be a free hit",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    c2 = RuleClause(
        id="ICC_T20I_MEN_2026:21.17",
        source_document_id=doc.id,
        clause_number="21.17",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Dismissals from a No ball",
        original_text="Neither batter shall be out off that delivery except for Run out.",
        normalized_text="neither batter shall be out off that delivery except for run out",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    repo.upsert_clauses([c1, c2])
    return repo


def test_local_deterministic_embedding_properties():
    """Verify dimension, determinism, and normalization of local provider."""
    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    assert provider.dimension == 384
    assert provider.model_name == "local-deterministic-v1"

    text1 = "Free Hit delivery after a No ball"
    v1 = provider.embed_text(text1)
    v2 = provider.embed_text(text1)

    assert len(v1) == 384
    # Determinism: exact match across calls
    assert v1 == v2

    # L2 Normalization
    norm = np.linalg.norm(v1)
    assert abs(norm - 1.0) < 1e-4

    # Empty text yields zero vector
    v_empty = provider.embed_text("")
    assert all(x == 0.0 for x in v_empty)


def test_embedding_text_template():
    """Verify versioned template formatting."""
    doc = SourceDocument(
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
    clause = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc.id,
        clause_number="21.18",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit.",
        normalized_text="the delivery following a no ball shall be a free hit",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )

    templated = build_clause_embedding_text(clause, doc)
    assert "[DocumentAuthority.ICC T20I October 2026]" in templated or "[ICC T20I October 2026]" in templated
    assert "Clause 21.18 - Free Hit:" in templated
    assert "The delivery following a No ball shall be a free hit." in templated
    assert EMBEDDING_TEMPLATE_VERSION == "v1"


def test_embedding_store_build_and_load(repo_with_clauses):
    """Verify atomic embedding generation and storage."""
    repo = repo_with_clauses
    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(repo, provider)

    count = store.build_all_embeddings()
    assert count == 2

    # Load all embeddings
    embeddings = store.load_embeddings()
    assert len(embeddings) == 2
    assert "ICC_T20I_MEN_2026:21.18" in embeddings

    doc_id, vec = embeddings["ICC_T20I_MEN_2026:21.18"]
    assert doc_id == "ICC_T20I_MEN_2026"
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (384,)
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-4


def test_embedding_store_validation_guards(repo_with_clauses):
    """Verify dimension mismatch and non-finite guards."""
    repo = repo_with_clauses
    provider = LocalDeterministicEmbeddingProvider(dimension=384)
    store = EmbeddingStore(repo, provider)

    # Wrong dimension
    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        store._validate_vector([0.1] * 128)

    # NaN in vector
    nan_vec = [0.1] * 384
    nan_vec[10] = float("nan")
    with pytest.raises(ValueError, match="non-finite values"):
        store._validate_vector(nan_vec)

    # Zero magnitude
    with pytest.raises(ValueError, match="zero magnitude"):
        store._validate_vector([0.0] * 384)
