"""Reciprocal Rank Fusion (RRF) for Hybrid Retrieval in CricketIQ.

Implements unweighted RRF formula: Score(d) = sum(1 / (k + rank_r(d))),
deduplicates on stable clause_id, tracks rank provenance, and applies deterministic tie-breaking.
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Optional, Any
from cricketiq.backend.app.database.models import RuleClause
from cricketiq.backend.app.retrieval.contracts import RetrievalHit, EvidenceRole


class RRFEngine:
    """Reciprocal Rank Fusion engine combining sparse and dense candidate lists."""

    def __init__(self, k: int = 60):
        if k <= 0:
            raise ValueError(f"RRF constant k must be positive, got {k}")
        self.k = k

    def fuse(
        self,
        sparse_results: List[Tuple[RuleClause, float]],
        dense_results: List[Tuple[RuleClause, float]],
        exact_results: Optional[List[Tuple[RuleClause, float]]] = None,
        top_k: int = 5
    ) -> List[RetrievalHit]:
        """Fuse ranked lists into ordered RetrievalHit records.

        Args:
            sparse_results: Ordered list of (clause, bm25_score).
            dense_results: Ordered list of (clause, cosine_similarity).
            exact_results: Optional exact clause matches.
            top_k: Number of fused hits to return.

        Returns:
            List of RetrievalHit sorted descending by fusion score.
        """
        clauses_by_id: Dict[str, RuleClause] = {}
        sparse_ranks: Dict[str, int] = {}
        dense_ranks: Dict[str, int] = {}
        rrf_scores: Dict[str, float] = {}
        is_exact_match: Dict[str, bool] = {}

        # 1. Process exact matches if present (give high confidence signal)
        if exact_results:
            for clause, _ in exact_results:
                cid = clause.id
                clauses_by_id[cid] = clause
                is_exact_match[cid] = True
                # Give exact matches an initial top-rank boost equivalent to rank 1 in both lists
                rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (2.0 / (self.k + 1))

        # 2. Process sparse ranks (1-indexed)
        for rank_idx, (clause, _) in enumerate(sparse_results):
            rank = rank_idx + 1
            cid = clause.id
            clauses_by_id[cid] = clause
            sparse_ranks[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.k + rank))

        # 3. Process dense ranks (1-indexed)
        for rank_idx, (clause, _) in enumerate(dense_results):
            rank = rank_idx + 1
            cid = clause.id
            clauses_by_id[cid] = clause
            dense_ranks[cid] = rank
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.k + rank))

        if not clauses_by_id:
            return []

        # 4. Deterministic sorting:
        # Priority: exact_match flag DESC, rrf_score DESC, best rank ASC, clause_number ASC, clause_id ASC
        def sort_key(cid: str) -> Tuple[bool, float, int, str, str]:
            exact = is_exact_match.get(cid, False)
            score = rrf_scores.get(cid, 0.0)
            s_rank = sparse_ranks.get(cid, 999999)
            d_rank = dense_ranks.get(cid, 999999)
            best_rank = min(s_rank, d_rank)
            clause = clauses_by_id[cid]
            return (exact, score, -best_rank, clause.clause_number, cid)

        sorted_clause_ids = sorted(clauses_by_id.keys(), key=sort_key, reverse=True)
        top_ids = sorted_clause_ids[:top_k]

        hits: List[RetrievalHit] = []
        for cid in top_ids:
            c = clauses_by_id[cid]
            hit = RetrievalHit(
                clause_id=c.id,
                document_id=c.source_document_id,
                clause_number=c.clause_number,
                heading=c.heading,
                original_text=c.original_text,
                normalized_text=c.normalized_text or c.original_text.lower(),
                page_start=c.page_start,
                page_end=c.page_end,
                sparse_rank=sparse_ranks.get(cid),
                dense_rank=dense_ranks.get(cid),
                rrf_score=round(rrf_scores[cid], 6),
                evidence_role=EvidenceRole.PRIMARY,
                relationship_path=[c.id]
            )
            hits.append(hit)

        return hits
