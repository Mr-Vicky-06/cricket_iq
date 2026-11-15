"""Dense semantic search and embedding package."""
from cricketiq.backend.app.retrieval.dense.base import EmbeddingProvider, DenseSearchProvider
from cricketiq.backend.app.retrieval.dense.embedding_provider import (
    LocalDeterministicEmbeddingProvider,
    SentenceTransformerEmbeddingProvider,
    build_clause_embedding_text,
    EMBEDDING_TEMPLATE_VERSION
)
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider
from cricketiq.backend.app.retrieval.dense.postgres_pgvector_search import PostgresPgVectorSearchProvider

__all__ = [
    "EmbeddingProvider",
    "DenseSearchProvider",
    "LocalDeterministicEmbeddingProvider",
    "SentenceTransformerEmbeddingProvider",
    "build_clause_embedding_text",
    "EMBEDDING_TEMPLATE_VERSION",
    "EmbeddingStore",
    "SQLiteNumPyDenseSearchProvider",
    "PostgresPgVectorSearchProvider"
]
