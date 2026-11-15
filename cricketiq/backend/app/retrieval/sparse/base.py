"""Sparse Search Provider Protocol and Contracts.
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Protocol
from cricketiq.backend.app.database.models import RuleClause


class SparseSearchProvider(Protocol):
    """Protocol for sparse lexical search providers."""

    def search(
        self,
        query: str,
        candidate_document_ids: Optional[List[str]] = None,
        top_k: int = 15
    ) -> List[Tuple[RuleClause, float]]:
        """Search clauses lexically within candidate documents.

        Args:
            query: User search query or text.
            candidate_document_ids: Restrict search strictly to these document IDs.
            top_k: Maximum number of candidates to return.

        Returns:
            List of (clause, relevance_score) tuples, sorted descending by score.
        """
        ...
