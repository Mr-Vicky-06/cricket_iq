"""Dense Semantic Search and Embedding Provider Protocols.
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Protocol
from cricketiq.backend.app.database.models import RuleClause


class EmbeddingProvider(Protocol):
    """Protocol for generating dense vector embeddings."""

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single string."""
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for a list of strings."""
        ...

    @property
    def dimension(self) -> int:
        """Vector dimensionality."""
        ...

    @property
    def model_name(self) -> str:
        """Model identifier and version."""
        ...


class DenseSearchProvider(Protocol):
    """Protocol for dense vector similarity search providers."""

    def search(
        self,
        query: str,
        candidate_document_ids: Optional[List[str]] = None,
        top_k: int = 15
    ) -> List[Tuple[RuleClause, float]]:
        """Search clauses by dense semantic similarity within candidate documents.

        Args:
            query: User search query.
            candidate_document_ids: Filter candidates to these documents.
            top_k: Maximum number of clauses to return.

        Returns:
            List of (clause, cosine_similarity) tuples, sorted descending.
        """
        ...
