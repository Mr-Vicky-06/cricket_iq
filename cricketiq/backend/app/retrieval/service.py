"""Unified Retrieval Service for CricketIQ (Phase 6 Gate 3).

Coordinates:
1. Applicability Resolution (Pre-search gating)
2. Exact Clause Lookup
3. Sparse Lexical Search (FTS5 / BM25)
4. Controlled Domain Lexicon Expansion (Feature-flagged)
5. Dense Semantic Search (Diagnostic / Neural if authorized)
6. Reciprocal Rank Fusion (RRF)
7. Bounded Clause Hierarchy Traversal (Feature-flagged)
8. Structured Table Evidence Hydration (Feature-flagged)
9. Internal Observability Tracing
"""

from __future__ import annotations
import time
import hashlib
from typing import Optional, List, Dict, Any, Tuple, Set

from cricketiq.backend.app.database.models import MatchContext, ApplicabilityDecision, RuleClause
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.core.applicability_engine import ApplicabilityEngine
from cricketiq.backend.app.retrieval.contracts import (
    RetrievalRequest, RetrievalOutcome, RetrievalStatus, RetrievalHit,
    EvidenceRole, RetrievalObservabilityTrace
)
from cricketiq.backend.app.retrieval.exact_clause_lookup import ExactClauseLookupEngine
from cricketiq.backend.app.retrieval.sparse.base import SparseSearchProvider
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.dense.base import DenseSearchProvider
from cricketiq.backend.app.retrieval.fusion.rrf import RRFEngine
from cricketiq.backend.app.retrieval.expansion.evidence_expander import EvidenceExpander

# Gate 3 Modules
from cricketiq.backend.app.retrieval.nlp.lexicon_service import (
    LexiconExpansionService, NormalizedQueryView, LexiconExpansionTrace
)
from cricketiq.backend.app.retrieval.hierarchy.traversal_service import (
    HierarchyTraversalService, HierarchyTraversalRequest
)
from cricketiq.backend.app.retrieval.tables.table_service import (
    TableEvidenceService, TableValidationStatus
)


class RetrievalService:
    """End-to-end evidence retrieval service with Gate 3 multi-stage intelligence."""

    def __init__(
        self,
        repository: CricketIQRepository,
        applicability_engine: Optional[ApplicabilityEngine] = None,
        exact_lookup: Optional[ExactClauseLookupEngine] = None,
        sparse_provider: Optional[SparseSearchProvider] = None,
        dense_provider: Optional[DenseSearchProvider] = None,
        rrf_engine: Optional[RRFEngine] = None,
        expander: Optional[EvidenceExpander] = None,
        enable_diagnostic_dense: bool = False,
        enable_lexicon_expansion: bool = False,
        enable_hierarchy_traversal: bool = False,
        enable_table_evidence: bool = False,
        lexicon_service: Optional[LexiconExpansionService] = None,
        hierarchy_service: Optional[HierarchyTraversalService] = None,
        table_service: Optional[TableEvidenceService] = None
    ):
        self.repository = repository
        self.applicability_engine = applicability_engine or ApplicabilityEngine()
        self.exact_lookup = exact_lookup or ExactClauseLookupEngine(repository)
        self.sparse_provider = sparse_provider or SQLiteFTSSearchProvider(repository)
        self.dense_provider = dense_provider
        self.rrf_engine = rrf_engine or RRFEngine(k=60)
        self.expander = expander or EvidenceExpander(repository)
        self.enable_diagnostic_dense = enable_diagnostic_dense

        # Feature Flags
        self.enable_lexicon_expansion = enable_lexicon_expansion
        self.enable_hierarchy_traversal = enable_hierarchy_traversal
        self.enable_table_evidence = enable_table_evidence

        # Lazy-load Gate 3 Services if enabled and not injected
        self.lexicon_service = lexicon_service
        if self.enable_lexicon_expansion and self.lexicon_service is None:
            self.lexicon_service = LexiconExpansionService()

        self.hierarchy_service = hierarchy_service
        if self.enable_hierarchy_traversal and self.hierarchy_service is None:
            self.hierarchy_service = HierarchyTraversalService(repository)

        self.table_service = table_service
        if self.enable_table_evidence and self.table_service is None:
            self.table_service = TableEvidenceService(repository=repository)

    def check_dense_channel_readiness(self) -> Tuple[bool, str]:
        """Evaluate whether dense semantic search is authorized to participate in RRF ranking."""
        if self.dense_provider is None:
            return False, "Dense search provider not configured."

        is_semantic = getattr(self.dense_provider, "is_semantic", False)
        provider_model = getattr(self.dense_provider, "model_name", "unknown")
        provider_dim = getattr(self.dense_provider, "dimension", 0)

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
        """Execute full evidence retrieval pipeline adhering strictly to Gate 3 execution order."""
        t0 = time.perf_counter()
        stage_latencies: Dict[str, float] = {}
        diagnostics: Dict[str, Any] = {}

        # Correlation ID & Hashed Query for Observability
        corr_id = hashlib.sha256(f"{request.query}:{time.time_ns()}".encode()).hexdigest()[:16]
        query_hash = hashlib.sha256(request.query.strip().lower().encode()).hexdigest()[:16]

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
        # Step 2: Preserve Raw Query & Exact Clause Lookup
        # ------------------------------------------------------------------
        raw_query = request.query
        t_exact_start = time.perf_counter()
        exact_results = self.exact_lookup.lookup(
            query=raw_query,
            candidate_document_ids=candidate_docs
        )
        exact_ms = round((time.perf_counter() - t_exact_start) * 1000, 2)
        stage_latencies["exact_lookup_ms"] = exact_ms
        diagnostics["exact_lookup_ms"] = exact_ms
        diagnostics["exact_hits_count"] = len(exact_results)

        # ------------------------------------------------------------------
        # Step 3: Sparse Lexical Search on Original Query
        # ------------------------------------------------------------------
        t_sparse_start = time.perf_counter()
        sparse_results = self.sparse_provider.search(
            query=raw_query,
            candidate_document_ids=candidate_docs,
            top_k=request.top_k_sparse
        )
        sparse_ms = round((time.perf_counter() - t_sparse_start) * 1000, 2)
        stage_latencies["original_sparse_ms"] = sparse_ms
        diagnostics["sparse_search_ms"] = sparse_ms
        diagnostics["sparse_hits_count"] = len(sparse_results)

        # ------------------------------------------------------------------
        # Step 4: Controlled Lexicon Expansion (Feature-Flagged)
        # ------------------------------------------------------------------
        expansion_variants: List[str] = []
        expansion_only_hits_count = 0
        lexicon_version = None
        lexicon_hash = None

        if self.enable_lexicon_expansion and self.lexicon_service:
            t_lex_start = time.perf_counter()
            view = self.lexicon_service.expand_query(raw_query)
            lexicon_version = view.lexicon_version
            lexicon_hash = view.lexicon_hash

            if view.expansions:
                combined_clauses: Dict[str, Tuple[float, RuleClause, float, str]] = {}
                for rank_idx, (clause, score) in enumerate(sparse_results):
                    combined_clauses[clause.id] = (rank_idx + 1.0, clause, score, "original_sparse")

                for exp in view.expansions:
                    # Filter out phrases that are just punctuation/spacing variants of the matched token
                    matched_norm = exp.matched_token.lower().replace("-", "").replace(" ", "")
                    meaningful_phrases = [
                        p for p in exp.expansion_phrases
                        if p.lower().replace("-", "").replace(" ", "") != matched_norm
                    ]

                    for phrase in meaningful_phrases:
                        if phrase not in expansion_variants:
                            expansion_variants.append(phrase)
                            exp_sparse_results = self.sparse_provider.search(
                                query=phrase,
                                candidate_document_ids=candidate_docs,
                                top_k=request.top_k_sparse
                            )
                            for rank_idx, (clause, score) in enumerate(exp_sparse_results):
                                cid = clause.id
                                # Expansion-only hits placed fairly without displacing high-confidence direct matches
                                exp_rank = (rank_idx + 1.0) + 1.0
                                if cid in combined_clauses:
                                    orig_rank, orig_clause, orig_score, _ = combined_clauses[cid]
                                    if (rank_idx + 1.0) < orig_rank:
                                        combined_clauses[cid] = (rank_idx + 1.0, clause, score, "both")
                                else:
                                    combined_clauses[cid] = (exp_rank, clause, score, "lexicon_expansion")
                                    expansion_only_hits_count += 1

                sorted_items = sorted(combined_clauses.values(), key=lambda x: x[0])
                sparse_results = [(item[1], item[2]) for item in sorted_items[:request.top_k_sparse * 2]]

            stage_latencies["lexicon_expansion_ms"] = round((time.perf_counter() - t_lex_start) * 1000, 2)

        diagnostics["expansion_variants"] = expansion_variants
        diagnostics["expansion_only_hits_count"] = expansion_only_hits_count

        # ------------------------------------------------------------------
        # Step 5: Dense Semantic Search (if authorized)
        # ------------------------------------------------------------------
        dense_authorized, dense_status_reason = self.check_dense_channel_readiness()
        diagnostics["dense_channel_authorized"] = dense_authorized
        diagnostics["dense_channel_status"] = dense_status_reason

        dense_results = []
        if dense_authorized and self.dense_provider is not None:
            t_dense_start = time.perf_counter()
            try:
                dense_results = self.dense_provider.search(
                    query=raw_query,
                    candidate_document_ids=candidate_docs,
                    top_k=request.top_k_dense
                )
                dense_ms = round((time.perf_counter() - t_dense_start) * 1000, 2)
                stage_latencies["dense_ms"] = dense_ms
                diagnostics["dense_search_ms"] = dense_ms
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
        # Step 6: Reciprocal Rank Fusion (RRF)
        # ------------------------------------------------------------------
        t_fuse_start = time.perf_counter()
        fused_hits = self.rrf_engine.fuse(
            sparse_results=sparse_results,
            dense_results=dense_results,
            exact_results=exact_results,
            top_k=request.top_k_fused
        )
        fuse_ms = round((time.perf_counter() - t_fuse_start) * 1000, 2)
        stage_latencies["fusion_ms"] = fuse_ms
        diagnostics["fusion_ms"] = fuse_ms

        if not fused_hits:
            return RetrievalOutcome(
                status=RetrievalStatus.NO_RESULTS,
                hits=[],
                applicable_document_ids=candidate_docs,
                query_diagnostics=diagnostics,
                warnings=["No matching rule clauses found in the applicable source bundle."]
            )

        # ------------------------------------------------------------------
        # Step 7: Bounded Hierarchy Traversal vs Evidence Expansion
        # ------------------------------------------------------------------
        t_hier_start = time.perf_counter()
        expanded_hits: List[RetrievalHit] = []
        visited_clause_ids: Set[str] = set()
        hierarchy_visited_count = 0
        hierarchy_included_counts: Dict[str, int] = {}
        blocked_xrefs: List[str] = []
        unresolved_xrefs: List[str] = []
        budget_overflow = False

        if self.enable_hierarchy_traversal and self.hierarchy_service:
            # 1. Retain all primary fused hits first
            expanded_hits = list(fused_hits)
            visited_clause_ids = {h.clause_id for h in fused_hits}

            # 2. Append bounded hierarchy context snippets
            for hit in fused_hits:
                trav_req = HierarchyTraversalRequest(
                    seed_clause_id=hit.clause_id,
                    candidate_document_ids=candidate_docs,
                    include_parent=request.include_parent_context,
                    include_children=True,
                    include_cross_references=request.include_related_evidence,
                    max_hops=1,
                    max_evidence_count=5,
                    token_budget=1200
                )
                trav_res = self.hierarchy_service.traverse(trav_req)
                hierarchy_visited_count += len(trav_res.assembled_nodes)
                blocked_xrefs.extend(trav_res.blocked_out_of_bundle_targets)
                unresolved_xrefs.extend(trav_res.unresolved_targets)
                if trav_res.budget_overflow:
                    budget_overflow = True

                for node in trav_res.assembled_nodes:
                    role_str = node.evidence_role.value
                    hierarchy_included_counts[role_str] = hierarchy_included_counts.get(role_str, 0) + 1
                    
                    if node.clause.id not in visited_clause_ids:
                        visited_clause_ids.add(node.clause.id)
                        expanded_hits.append(
                            RetrievalHit(
                                clause_id=node.clause.id,
                                document_id=node.clause.source_document_id,
                                clause_number=node.clause.clause_number,
                                heading=node.clause.heading,
                                original_text=node.clause.original_text,
                                normalized_text=node.clause.normalized_text,
                                page_start=node.clause.page_start,
                                page_end=node.clause.page_end,
                                evidence_role=node.evidence_role,
                                relationship_path=node.traversal_path,
                                applicability_reason=f"Hierarchy {role_str} for {hit.clause_id}"
                            )
                        )
            stage_latencies["hierarchy_traversal_ms"] = round((time.perf_counter() - t_hier_start) * 1000, 2)
            diagnostics["expansion_ms"] = stage_latencies["hierarchy_traversal_ms"]
        else:
            expanded_hits = self.expander.expand(
                primary_hits=fused_hits,
                candidate_document_ids=candidate_docs,
                include_parent_context=request.include_parent_context,
                include_related_evidence=request.include_related_evidence
            )
            exp_ms = round((time.perf_counter() - t_hier_start) * 1000, 2)
            stage_latencies["expansion_ms"] = exp_ms
            diagnostics["expansion_ms"] = exp_ms

        # ------------------------------------------------------------------
        # Step 8: Structured Table Evidence Hydration (Feature-Flagged)
        # ------------------------------------------------------------------
        table_ids_hydrated: List[str] = []
        table_ids_excluded: List[str] = []

        if self.enable_table_evidence and self.table_service:
            t_tbl_start = time.perf_counter()
            table_hits: List[RetrievalHit] = []
            hydrated_tables_set: Set[str] = set()

            for hit in list(expanded_hits):
                tables = self.table_service.get_table_evidence_for_clause(
                    clause_id=hit.clause_id,
                    candidate_document_ids=candidate_docs
                )
                for tbl in tables:
                    if tbl.table_id not in hydrated_tables_set:
                        hydrated_tables_set.add(tbl.table_id)
                        table_ids_hydrated.append(tbl.table_id)
                        md_table = self.table_service.render_markdown(tbl)
                        table_hits.append(
                            RetrievalHit(
                                clause_id=tbl.table_id,
                                document_id=tbl.source_document_id,
                                clause_number=f"TBL_P{tbl.page_number}",
                                heading=tbl.caption or f"Table {tbl.table_id}",
                                original_text=md_table,
                                normalized_text=md_table.lower(),
                                page_start=tbl.page_number,
                                page_end=tbl.page_number,
                                evidence_role=EvidenceRole.TABLE_SPECIFICATION,
                                relationship_path=[hit.clause_id, tbl.table_id],
                                applicability_reason=f"Authoritative table specification linked to {hit.clause_id}"
                            )
                        )
            expanded_hits.extend(table_hits)
            stage_latencies["table_hydration_ms"] = round((time.perf_counter() - t_tbl_start) * 1000, 2)

        # ------------------------------------------------------------------
        # Step 9: Observability Trace Assembly
        # ------------------------------------------------------------------
        total_retrieval_ms = round((time.perf_counter() - t0) * 1000, 2)
        stage_latencies["total_ms"] = total_retrieval_ms
        diagnostics["total_retrieval_ms"] = total_retrieval_ms

        trace = RetrievalObservabilityTrace(
            correlation_id=corr_id,
            normalized_query_hash=query_hash,
            lexicon_version=lexicon_version,
            lexicon_hash=lexicon_hash,
            candidate_source_bundle=candidate_docs,
            original_sparse_query=raw_query,
            expansion_variants=expansion_variants,
            exact_hit_count=len(exact_results),
            original_sparse_hit_count=len(sparse_results),
            expansion_only_hit_count=expansion_only_hits_count,
            hierarchy_nodes_visited=hierarchy_visited_count,
            hierarchy_nodes_included=hierarchy_included_counts,
            blocked_cross_references=blocked_xrefs,
            unresolved_cross_references=unresolved_xrefs,
            table_ids_hydrated=table_ids_hydrated,
            table_ids_excluded=table_ids_excluded,
            stage_latencies_ms=stage_latencies,
            total_latency_ms=total_retrieval_ms,
            feature_flags={
                "enable_lexicon_expansion": self.enable_lexicon_expansion,
                "enable_hierarchy_traversal": self.enable_hierarchy_traversal,
                "enable_table_evidence": self.enable_table_evidence,
                "enable_diagnostic_dense": self.enable_diagnostic_dense
            },
            token_budget=1200,
            budget_overflow=budget_overflow
        )
        diagnostics["observability_trace"] = trace.model_dump()

        return RetrievalOutcome(
            status=RetrievalStatus.SUCCESS,
            hits=expanded_hits,
            applicable_document_ids=candidate_docs,
            query_diagnostics=diagnostics,
            warnings=[]
        )
