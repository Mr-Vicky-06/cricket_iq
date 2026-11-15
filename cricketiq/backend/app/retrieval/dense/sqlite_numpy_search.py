"""NumPy Dense Semantic Search Provider for SQLite Local Mode.

Calculates cosine similarity over pre-filtered candidate document vectors,
guards against NaN/Inf, and returns ranked RuleClause hits with similarity scores.
"""

from __future__ import annotations
import math
from typing import List, Tuple, Optional, Dict
import numpy as np
from sqlalchemy import select

from cricketiq.backend.app.database.models import RuleClause
from cricketiq.backend.app.database.orm_models import RuleClauseEntity
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.dense.base import DenseSearchProvider, EmbeddingProvider
from cricketiq.backend.app.retrieval.dense.embedding_store import EmbeddingStore


class SQLiteNumPyDenseSearchProvider:
    """Dense vector search using local NumPy cosine calculations."""

    def __init__(
        self,
        repository: CricketIQRepository,
        provider: EmbeddingProvider,
        store: Optional[EmbeddingStore] = None
    ):
        self.repository = repository
        self.provider = provider
        self.store = store or EmbeddingStore(repository, provider)

    def search(
        self,
        query: str,
        candidate_document_ids: Optional[List[str]] = None,
        top_k: int = 15
    ) -> List[Tuple[RuleClause, float]]:
        """Search clauses by dense vector similarity with candidate document scoping."""
        if not query or not query.strip():
            return []

        if candidate_document_ids is not None and len(candidate_document_ids) == 0:
            return []

        # 1. Embed user query
        q_raw = self.provider.embed_text(query.strip())
        if not q_raw or len(q_raw) != self.provider.dimension:
            return []

        q_arr = np.array(q_raw, dtype=np.float32)
        if not np.all(np.isfinite(q_arr)):
            return []

        q_norm = float(np.linalg.norm(q_arr))
        if q_norm == 0.0 or not math.isfinite(q_norm):
            return []

        # 2. Load candidate embeddings
        clause_vectors = self.store.load_embeddings(candidate_document_ids=candidate_document_ids)
        if not clause_vectors:
            return []

        # 3. Calculate cosine similarity
        scored_pairs: List[Tuple[str, float]] = []
        for cid, (did, c_arr) in clause_vectors.items():
            c_norm = float(np.linalg.norm(c_arr))
            if c_norm == 0.0 or not math.isfinite(c_norm):
                continue

            sim = float(np.dot(q_arr, c_arr) / (q_norm * c_norm))
            if math.isfinite(sim):
                scored_pairs.append((cid, round(sim, 6)))

        if not scored_pairs:
            return []

        # 4. Sort descending by similarity
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        top_pairs = scored_pairs[:top_k]
        top_ids = [p[0] for p in top_pairs]
        scores_by_id = {p[0]: p[1] for p in top_pairs}

        # 5. Hydrate RuleClause domain objects
        stmt = select(RuleClauseEntity).where(RuleClauseEntity.id.in_(top_ids))
        entities = {e.id: e for e in self.repository.session.scalars(stmt).all()}

        results: List[Tuple[RuleClause, float]] = []
        for cid in top_ids:
            if cid in entities:
                clause = self.repository._entity_to_rule_clause(entities[cid])
                results.append((clause, scores_by_id[cid]))

        return results
