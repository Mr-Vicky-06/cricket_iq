"""Unified Retrieval Service for CricketIQ.

Coordinates:
1. Applicability Resolution (Pre-search gating)
2. Exact Clause Lookup
3. Sparse Lexical Search (FTS5 / BM25)
4. Dense Semantic Search (NumPy / pgvector)
5. Reciprocal Rank Fusion (RRF)
6. Bounded Evidence Graph Expansion (Parent + Cross-references)
"""

from __future__ import annotations
import time
from typing import Optional, List, Dict, Any, Tuple

from cricketiq.backend.app.database.models import MatchContext, ApplicabilityDecision
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.core.applicability_engine import ApplicabilityEngine
from cricketiq.backend.app.retrieval.contracts import (
    RetrievalRequest, RetrievalOutcome, RetrievalStatus, RetrievalHit, EvidenceRole
)
from cricketiq.backend.app.retrieval.exact_clause_lookup import ExactClauseLookupEngine
from cricketiq.backend.app.retrieval.sparse.base import SparseSearchProvider
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.dense.base import DenseSearchProvider
from cricketiq.backend.app.retrieval.dense.sqlite_numpy_search import SQLiteNumPyDenseSearchProvider
from cricketiq.backend.app.retrieval.fusion.rrf import RRFEngine
from cricketiq.backend.app.retrieval.expansion.evidence_expander import EvidenceExpander


class RetrievalService:
    """End-to-end evidence retrieval service."""

    def __init__(
        self,
        repository: CricketIQRepository,
        applicability_engine: Optional[ApplicabilityEngine] = None,
        exact_lookup: Optional[ExactClauseLookupEngine] = None,
        sparse_provider: Optional[SparseSearchProvider] = None,
        dense_provider: Optional[DenseSearchProvider] = None,
        rrf_engine: Optional[RRFEngine] = None,
        expander: Optional[EvidenceExpander] = None,
        enable_diagnostic_dense: bool = False
    ):
        self.repository = repository
        self.applicability_engine = applicability_engine or ApplicabilityEngine()
        self.exact_lookup = exact_lookup or ExactClauseLookupEngine(repository)
        self.sparse_provider = sparse_provider or SQLiteFTSSearchProvider(repository)
        self.dense_provider = dense_provider
        self.rrf_engine = rrf_engine or RRFEngine(k=60)
        self.expander = expander or EvidenceExpander(repository)
        self.enable_diagnostic_dense = enable_diagnostic_dense

    def check_dense_channel_readiness(self) -> Tuple[bool, str]:
        """Evaluate whether dense semantic search is authorized to participate in RRF ranking.

        Guarantees:
        - local-deterministic-v1 is excluded from production RRF ranking unless enable_diagnostic_dense is True.
        - Inconsistent, mixed, or missing database vector metadata disables dense ranking safely.
        - Validated semantic models (e.g. transformer/ONNX) are enabled without code changes.
        """
        if self.dense_provider is None:
            return False, "Dense search provider not configured."

        is_semantic = getattr(self.dense_provider, "is_semantic", False)
        provider_model = getattr(self.dense_provider, "model_name", "unknown")
        provider_dim = getattr(self.dense_provider, "dimension", 0)

        # Inspect database vector store if accessible
        store = getattr(self.dense_provider, "store", None)
        if store is not None and hasattr(store, "get_store_metadata"):
            try:
                meta = store.get_store_metadata()
                if not meta.get("is_consistent", False):
                    return False, f"Dense search disabled: mixed or inconsistent store metadata: {meta}"

                stored_model = meta.get("model_name")
                stored_dim = meta.get("dimension")

                if stored_model != provider_model:
                    return False, f"Dense search disabled: provider model '{provider_model}' does not match stored model '{stored_model}'."
                if stored_dim != provider_dim:
                    return False, f"Dense search disabled: provider dimension {provider_dim} does not match stored dimension {stored_dim}."

                if stored_model == "local-deterministic-v1" and not self.enable_diagnostic_dense:
                    return False, "Dense search disabled: stored model 'local-deterministic-v1' is a non-semantic diagnostic hash model and is excluded from production ranking."
            except Exception as e:
                return False, f"Dense search disabled: error validating store metadata: {e}"

        if not is_semantic and not self.enable_diagnostic_dense:
            return False, f"Dense search disabled: provider '{provider_model}' is not a semantic neural model and diagnostic mode is not enabled."

        return True, f"Dense semantic search active with model '{provider_model}'."

    def retrieve(self, request: RetrievalRequest) -> RetrievalOutcome:
        """Execute full evidence retrieval pipeline."""
        t0 = time.perf_counter()
        diagnostics: Dict[str, Any] = {}

        # ------------------------------------------------------------------
        # Step 1: Applicability Resolution (Pre-search gating)
        # ------------------------------------------------------------------
        decision = request.applicability_decision
        if decision is None:
            ctx = request.match_context or MatchContext()
            decision = self.applicability_engine.resolve(ctx, self.repository)

        if decision.is_ambiguous or decision.clarification_needed:
            return RetrievalOutcome(
                status=RetrievalStatus.CLARIFICATION_REQUIRED,
                hits=[],
                applicable_document_ids=[],
                clarification_prompt=decision.clarification_needed,
                warnings=decision.assumptions or ["Applicability context ambiguous or clarification required."]
            )

        if not decision.selected_bundle:
            return RetrievalOutcome(
                status=RetrievalStatus.NO_APPLICABLE_SOURCES,
                hits=[],
                applicable_document_ids=[],
                warnings=["No applicable source documents found in bundle for requested context."]
            )

        candidate_docs = [
            d.id if hasattr(d, "id") else str(d)
            for d in decision.selected_bundle
        ]
        diagnostics["applicable_bundle"] = candidate_docs
        diagnostics["applicability_reasoning"] = decision.decision_trace

        # ------------------------------------------------------------------
        # Step 2: Exact Clause Lookup
        # ------------------------------------------------------------------
        t_exact_start = time.perf_counter()
        exact_results = self.exact_lookup.lookup(
            query=request.query,
            candidate_document_ids=candidate_docs
        )
        diagnostics["exact_lookup_ms"] = round((time.perf_counter() - t_exact_start) * 1000, 2)
        diagnostics["exact_hits_count"] = len(exact_results)

        # ------------------------------------------------------------------
        # Step 3: Sparse Lexical Search (FTS5 / BM25)
        # ------------------------------------------------------------------
        t_sparse_start = time.perf_counter()
        sparse_results = self.sparse_provider.search(
            query=request.query,
            candidate_document_ids=candidate_docs,
            top_k=request.top_k_sparse
        )
        diagnostics["sparse_search_ms"] = round((time.perf_counter() - t_sparse_start) * 1000, 2)
        diagnostics["sparse_hits_count"] = len(sparse_results)

        # ------------------------------------------------------------------
        # Step 4: Dense Semantic Search (if authorized)
        # ------------------------------------------------------------------
        dense_authorized, dense_status_reason = self.check_dense_channel_readiness()
        diagnostics["dense_channel_authorized"] = dense_authorized
        diagnostics["dense_channel_status"] = dense_status_reason

        dense_results = []
        if dense_authorized and self.dense_provider is not None:
            t_dense_start = time.perf_counter()
            try:
                dense_results = self.dense_provider.search(
                    query=request.query,
                    candidate_document_ids=candidate_docs,
                    top_k=request.top_k_dense
                )
                diagnostics["dense_search_ms"] = round((time.perf_counter() - t_dense_start) * 1000, 2)
                diagnostics["dense_hits_count"] = len(dense_results)
            except Exception as e:
                diagnostics["dense_search_error"] = str(e)
                diagnostics["dense_search_ms"] = 0.0
                diagnostics["dense_hits_count"] = 0
                dense_results = []
        else:
            diagnostics["dense_search_ms"] = 0.0
            diagnostics["dense_hits_count"] = 0

        # ------------------------------------------------------------------
        # Step 5: Reciprocal Rank Fusion (RRF)
        # ------------------------------------------------------------------
        t_fuse_start = time.perf_counter()
        fused_hits = self.rrf_engine.fuse(
            sparse_results=sparse_results,
            dense_results=dense_results,
            exact_results=exact_results,
            top_k=request.top_k_fused
        )
        diagnostics["fusion_ms"] = round((time.perf_counter() - t_fuse_start) * 1000, 2)

        if not fused_hits:
            return RetrievalOutcome(
                status=RetrievalStatus.NO_RESULTS,
                hits=[],
                applicable_document_ids=candidate_docs,
                query_diagnostics=diagnostics,
                warnings=["No matching rule clauses found in the applicable source bundle."]
            )

        # ------------------------------------------------------------------
        # Step 6: Evidence Graph Expansion (Parent + Cross-references)
        # ------------------------------------------------------------------
        t_expand_start = time.perf_counter()
        expanded_hits = self.expander.expand(
            primary_hits=fused_hits,
            candidate_document_ids=candidate_docs,
            include_parent_context=request.include_parent_context,
            include_related_evidence=request.include_related_evidence
        )
        diagnostics["expansion_ms"] = round((time.perf_counter() - t_expand_start) * 1000, 2)
        diagnostics["total_retrieval_ms"] = round((time.perf_counter() - t0) * 1000, 2)

        return RetrievalOutcome(
            status=RetrievalStatus.SUCCESS,
            hits=expanded_hits,
            applicable_document_ids=candidate_docs,
            query_diagnostics=diagnostics,
            warnings=[]
        )
