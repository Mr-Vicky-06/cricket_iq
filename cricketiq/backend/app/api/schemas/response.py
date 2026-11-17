"""Response schemas for CricketIQ Query API."""

from __future__ import annotations
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class QueryStatus(str, Enum):
    """Execution status for rule query processing."""
    ANSWERED = "answered"
    CLARIFICATION_REQUIRED = "clarification_required"
    UNSUPPORTED_COMPETITION = "unsupported_competition"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    ERROR = "error"


class CitationItem(BaseModel):
    """Authoritative citation grounded in database source documents."""
    citation_id: str = Field(..., description="Unique citation identifier, e.g. 'cit-1'")
    clause_id: str = Field(..., description="Corpus clause identifier, e.g. 'ICC_T20I_MEN_2026:21.18.2'")
    clause_number: str = Field(..., description="Official clause number, e.g. '21.18.2'")
    document_id: str = Field(..., description="Source document identifier")
    document_title: str = Field(..., description="Official publication title")
    document_version: str = Field(..., description="Document edition / publication version")
    authority: str = Field(..., description="Governing authority (ICC, MCC, etc.)")
    official_url: Optional[str] = Field(default=None, description="Official publisher URL")
    page_start: Optional[int] = Field(default=None, description="Starting printed/PDF page")
    page_end: Optional[int] = Field(default=None, description="Ending printed/PDF page")
    exact_quote: str = Field(..., description="Verbatim or authoritative excerpt from source clause")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Retrieval / relevance confidence score")


class ClaimSupportItem(BaseModel):
    """Verification mapping connecting an answer claim to supporting citations."""
    claim_text: str = Field(..., description="Specific substantive claim made in the answer")
    supporting_citation_ids: List[str] = Field(
        default_factory=list,
        description="IDs of citations supporting this claim"
    )
    is_verified: bool = Field(
        default=True,
        description="True if claim is substantiated by at least one citation"
    )


class AnswerPayload(BaseModel):
    """Structured synthesized answer grounded in retrieved evidence."""
    summary: str = Field(..., description="Concise high-level answer to user query")
    detailed_explanation: str = Field(..., description="Detailed regulatory explanation with clause citations")
    key_points: List[str] = Field(default_factory=list, description="Core bullet-point takeaways")
    exceptions_and_edge_cases: List[str] = Field(
        default_factory=list,
        description="Applicable exceptions, conditions, or umpire discretions"
    )
    historical_context: Optional[str] = Field(
        default=None,
        description="Comparison to previous editions or note of recent rule changes"
    )


class QueryTrace(BaseModel):
    """Audit and telemetry trace of the query resolution pipeline."""
    query_id: str = Field(..., description="UUID for query transaction")
    latency_ms: float = Field(..., description="Total pipeline latency in milliseconds")
    retrieval_count: int = Field(default=0, description="Number of evidence clauses retrieved")
    applicable_documents: List[str] = Field(
        default_factory=list,
        description="IDs of documents resolved as applicable"
    )
    precedence_applied: Optional[str] = Field(
        default=None,
        description="Description of precedence rule applied (e.g. 'Playing Conditions override MCC Laws')"
    )
    model_used: str = Field(default="none", description="LLM model or provider used for synthesis")


class QueryResponse(BaseModel):
    """Top-level response payload for POST /v1/rules/query."""
    status: QueryStatus = Field(..., description="Resolution status")
    answer: Optional[AnswerPayload] = Field(
        default=None,
        description="Synthesized answer (present when status is ANSWERED)"
    )
    citations: List[CitationItem] = Field(
        default_factory=list,
        description="Authoritative citations backing the answer"
    )
    claims: List[ClaimSupportItem] = Field(
        default_factory=list,
        description="Clause-level support mapping for each substantive statement"
    )
    abstention_reason: Optional[str] = Field(
        default=None,
        description="Explanation when assistant must abstain from answering"
    )
    suggested_clarifications: List[str] = Field(
        default_factory=list,
        description="Targeted follow-up questions to resolve ambiguity"
    )
    trace: QueryTrace = Field(..., description="Execution trace and telemetry")
