"""PostgreSQL pgvector Dense Semantic Search Adapter for CricketIQ.

Implements pgvector cosine distance query with candidate document scoping.
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.models import RuleClause
from cricketiq.backend.app.database.orm_models import RuleClauseEntity
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.dense.base import EmbeddingProvider


class PostgresPgVectorSearchProvider:
    """PostgreSQL pgvector search adapter."""

    def __init__(self, repository: CricketIQRepository, provider: EmbeddingProvider):
        self.repository = repository
        self.session: Session = repository.session
        self.provider = provider

    @property
    def is_semantic(self) -> bool:
        return getattr(self.provider, "is_semantic", False)

    @property
    def model_name(self) -> str:
        return getattr(self.provider, "model_name", "unknown")

    @property
    def dimension(self) -> int:
        return getattr(self.provider, "dimension", 0)

    def search(
        self,
        query: str,
        candidate_document_ids: Optional[List[str]] = None,
        top_k: int = 15
    ) -> List[Tuple[RuleClause, float]]:
        """Search clauses using pgvector cosine distance (<=>)."""
        if not query or not query.strip():
            return []

        if candidate_document_ids is not None and len(candidate_document_ids) == 0:
            return []

        q_vec = self.provider.embed_text(query.strip())
        if not q_vec:
            return []

        params: Dict[str, Any] = {
            "query_vec": str(q_vec),
            "limit": top_k
        }

        doc_filter = ""
        if candidate_document_ids is not None:
            placeholders = []
            for i, doc_id in enumerate(candidate_document_ids):
                k = f"doc_{i}"
                placeholders.append(f":{k}")
                params[k] = doc_id
            doc_filter = f"AND document_id IN ({', '.join(placeholders)})"

        sql = f"""
            SELECT clause_id, 1 - (embedding <=> :query_vec) AS similarity
            FROM clause_embeddings
            WHERE 1=1 {doc_filter}
            ORDER BY embedding <=> :query_vec ASC
            LIMIT :limit
        """

        try:
            rows = self.session.execute(text(sql), params).fetchall()
        except Exception:
            return []

        if not rows:
            return []

        clause_ids = [r[0] for r in rows]
        scores = {r[0]: float(r[1]) for r in rows}

        stmt = select(RuleClauseEntity).where(RuleClauseEntity.id.in_(clause_ids))
        entities = {e.id: e for e in self.session.scalars(stmt).all()}

        results: List[Tuple[RuleClause, float]] = []
        for cid in clause_ids:
            if cid in entities:
                clause = self.repository._entity_to_rule_clause(entities[cid])
                results.append((clause, scores.get(cid, 0.0)))

        return results
