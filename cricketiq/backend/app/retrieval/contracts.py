"""Typed Domain Contracts for CricketIQ Retrieval Subsystem.

Defines request options, evidence hits, ranking diagnostics, and retrieval outcomes.
"""

from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from cricketiq.backend.app.database.models import (
    MatchContext, ApplicabilityDecision, RuleClause
)


class EvidenceRole(str, Enum):
    PRIMARY = "PRIMARY"
    DIRECT_EVIDENCE = "DIRECT_EVIDENCE"
    PARENT_CONTEXT = "PARENT_CONTEXT"
    OPERATIONAL_CHILD = "OPERATIONAL_CHILD"
    STATUTORY_CROSS_REFERENCE = "STATUTORY_CROSS_REFERENCE"
    RELATED_SUPPORT = "RELATED_SUPPORT"
    DEFINITION = "DEFINITION"
    TABLE_SPECIFICATION = "TABLE_SPECIFICATION"
    STRUCTURAL_CONTEXT = "STRUCTURAL_CONTEXT"


class RetrievalStatus(str, Enum):
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    NO_APPLICABLE_SOURCES = "NO_APPLICABLE_SOURCES"
    RETRIEVAL_UNAVAILABLE = "RETRIEVAL_UNAVAILABLE"
    PARTIAL_RESULTS = "PARTIAL_RESULTS"


class RetrievalRequest(BaseModel):
    """Specification of a retrieval query with optional match context or resolved decision."""
    query: str = Field(..., description="User query or rule inquiry")
    match_context: Optional[MatchContext] = Field(default=None, description="Optional match metadata")
    applicability_decision: Optional[ApplicabilityDecision] = Field(default=None, description="Pre-computed applicability")
    top_k_sparse: int = Field(default=15, description="Number of sparse candidates to retrieve")
    top_k_dense: int = Field(default=15, description="Number of dense candidates to retrieve")
    top_k_fused: int = Field(default=5, description="Number of fused primary matches to return")
    include_parent_context: bool = Field(default=True, description="Expand parent section context")
    include_related_evidence: bool = Field(default=True, description="Expand cross-referenced clauses")


class RetrievalHit(BaseModel):
    """A single retrieved and grounded clause with ranking provenance and evidence role."""
    clause_id: str
    document_id: str
    clause_number: str
    heading: Optional[str] = None
    original_text: str
    normalized_text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    source_url: Optional[str] = None
    sparse_rank: Optional[int] = None
    dense_rank: Optional[int] = None
    rrf_score: float = 0.0
    evidence_role: EvidenceRole = EvidenceRole.PRIMARY
    relationship_path: List[str] = Field(default_factory=list)
    applicability_reason: Optional[str] = None


class RetrievalObservabilityTrace(BaseModel):
    """Internal diagnostic trace for Gate 3 retrieval observability.
    
    Privacy & Correctness Guardrails (Phase 6 Gate 3):
    - Raw query is omitted by default from traces and persisted logs to preserve privacy.
    - Deterministic normalized query hash and correlation ID provide auditability.
    - Aggregate token usage is reported as token_estimate based on conservative tokenization.
    """
    correlation_id: str
    normalized_query_hash: str
    lexicon_version: Optional[str] = None
    lexicon_hash: Optional[str] = None
    candidate_source_bundle: List[str] = Field(default_factory=list)
    original_sparse_query: Optional[str] = None  # Redacted by default; populated only under dev opt-in
    expansion_variants: List[str] = Field(default_factory=list)
    exact_hit_count: int = 0
    original_sparse_hit_count: int = 0
    expansion_only_hit_count: int = 0
    hierarchy_nodes_visited: int = 0
    hierarchy_nodes_included: Dict[str, int] = Field(default_factory=dict)
    blocked_cross_references: List[str] = Field(default_factory=list)
    unresolved_cross_references: List[str] = Field(default_factory=list)
    table_ids_hydrated: List[str] = Field(default_factory=list)
    table_ids_excluded: List[str] = Field(default_factory=list)
    included_evidence_ids: List[str] = Field(default_factory=list)
    pruned_evidence_ids: List[str] = Field(default_factory=list)
    blocked_evidence_ids: List[str] = Field(default_factory=list)
    unresolved_evidence_ids: List[str] = Field(default_factory=list)
    over_budget_evidence_ids: List[str] = Field(default_factory=list)
    stage_latencies_ms: Dict[str, float] = Field(default_factory=dict)
    total_latency_ms: float = 0.0
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    token_budget: int = 1200
    token_estimate: int = 0
    budget_overflow: bool = False


class RetrievalOutcome(BaseModel):
    """Complete, structured response from the retrieval subsystem."""
    status: RetrievalStatus
    hits: List[RetrievalHit] = Field(default_factory=list)
    applicable_document_ids: List[str] = Field(default_factory=list)
    query_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    clarification_prompt: Optional[str] = None
