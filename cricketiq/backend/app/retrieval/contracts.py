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
    PARENT_CONTEXT = "PARENT_CONTEXT"
    RELATED_SUPPORT = "RELATED_SUPPORT"
    DEFINITION = "DEFINITION"


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


class RetrievalOutcome(BaseModel):
    """Complete, structured response from the retrieval subsystem."""
    status: RetrievalStatus
    hits: List[RetrievalHit] = Field(default_factory=list)
    applicable_document_ids: List[str] = Field(default_factory=list)
    query_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    clarification_prompt: Optional[str] = None
