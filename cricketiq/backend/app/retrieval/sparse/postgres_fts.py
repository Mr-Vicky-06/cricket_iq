"""PostgreSQL Sparse Full-Text Search Provider for CricketIQ.

Implements PostgreSQL tsvector / plainto_tsquery search with ts_rank and candidate scoping.
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Dict, Any
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.models import RuleClause
from cricketiq.backend.app.database.orm_models import RuleClauseEntity
from cricketiq.backend.app.database.repository import CricketIQRepository


class PostgresFTSSearchProvider:
    """PostgreSQL full-text search adapter using tsvector and ts_rank."""

    def __init__(self, repository: CricketIQRepository):
        self.repository = repository
        self.session: Session = repository.session

    def search(
        self,
        query: str,
        candidate_document_ids: Optional[List[str]] = None,
        top_k: int = 15
    ) -> List[Tuple[RuleClause, float]]:
        """Search clauses using PostgreSQL tsvector and plainto_tsquery."""
        if candidate_document_ids is not None and len(candidate_document_ids) == 0:
            return []

        clean_query = query.strip()
        if not clean_query:
            return []

        params: Dict[str, Any] = {
            "query": clean_query,
            "limit": top_k
        }

        doc_filter_sql = ""
        if candidate_document_ids is not None:
            placeholders = []
            for i, doc_id in enumerate(candidate_document_ids):
                k = f"doc_{i}"
                placeholders.append(f":{k}")
                params[k] = doc_id
            doc_filter_sql = f"AND source_document_id IN ({', '.join(placeholders)})"

        sql = f"""
            SELECT id,
                   ts_rank(
                       to_tsvector('english', coalesce(heading, '') || ' ' || original_text),
                       plainto_tsquery('english', :query)
                   ) AS rank
            FROM rule_clauses
            WHERE to_tsvector('english', coalesce(heading, '') || ' ' || original_text) @@ plainto_tsquery('english', :query)
            {doc_filter_sql}
            ORDER BY rank DESC
            LIMIT :limit
        """

        try:
            results = self.session.execute(text(sql), params).fetchall()
        except Exception:
            return []

        if not results:
            return []

        clause_ids = [r[0] for r in results]
        ranks = {r[0]: float(r[1]) for r in results}

        stmt = select(RuleClauseEntity).where(RuleClauseEntity.id.in_(clause_ids))
        entities = {e.id: e for e in self.session.scalars(stmt).all()}

        hits: List[Tuple[RuleClause, float]] = []
        for cid in clause_ids:
            if cid in entities:
                clause = self.repository._entity_to_rule_clause(entities[cid])
                hits.append((clause, ranks.get(cid, 0.0)))

        return hits
