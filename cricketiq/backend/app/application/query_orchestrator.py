"""Query Orchestrator for CricketIQ.

Coordinates the end-to-end evidence-bounded rule answering pipeline:
Query -> ContextExtractor -> ApplicabilityEngine -> RetrievalService ->
EvidenceSufficiencyAuditor -> AnswerGenerator -> CitationValidator -> QueryResponse.
"""

from __future__ import annotations
import time
import uuid
import logging
from typing import Optional

from cricketiq.backend.app.api.schemas.query import QueryRequest
from cricketiq.backend.app.api.schemas.response import (
    QueryResponse,
    QueryStatus,
    AnswerPayload,
    QueryTrace,
)
from cricketiq.backend.app.application.context_extractor import ContextExtractor
from cricketiq.backend.app.application.evidence_sufficiency import EvidenceSufficiencyAuditor
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.generation.answer_generator import AnswerGenerator
from cricketiq.backend.app.generation.citation_validator import CitationValidator
from cricketiq.backend.app.generation.provider_factory import get_llm_provider
from cricketiq.backend.app.generation.contracts import LLMProvider
from cricketiq.backend.app.retrieval.contracts import RetrievalRequest
from cricketiq.backend.app.retrieval.service import RetrievalService

logger = logging.getLogger(__name__)


class QueryOrchestrator:
    """Master orchestrator for grounded cricket rules queries."""

    def __init__(
        self,
        repository: CricketIQRepository,
        retrieval_service: Optional[RetrievalService] = None,
        context_extractor: Optional[ContextExtractor] = None,
        sufficiency_auditor: Optional[EvidenceSufficiencyAuditor] = None,
        llm_provider: Optional[LLMProvider] = None,
        answer_generator: Optional[AnswerGenerator] = None,
        citation_validator: Optional[CitationValidator] = None,
    ):
        self.repository = repository
        self.retrieval_service = retrieval_service or RetrievalService(repository)
        self.context_extractor = context_extractor or ContextExtractor()
        self.sufficiency_auditor = sufficiency_auditor or EvidenceSufficiencyAuditor()
        self.llm_provider = llm_provider or get_llm_provider()
        self.answer_generator = answer_generator or AnswerGenerator(self.llm_provider)
        self.citation_validator = citation_validator or CitationValidator(repository)

    def execute(self, request: QueryRequest) -> QueryResponse:
        """Execute the full pipeline deterministically with timing and tracing."""
        t_start = time.perf_counter()
        query_id = f"q-{uuid.uuid4().hex[:12]}"

        # 1. Context Extraction & Harmonization
        match_context, provenance = self.context_extractor.extract(
            query=request.query,
            explicit_input=request.context,
        )

        # 2. Check for Unsupported Domestic Competitions
        if match_context.cricket_level == "domestic":
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryResponse(
                status=QueryStatus.UNSUPPORTED_COMPETITION,
                abstention_reason=(
                    f"Domestic competitions like {match_context.competition or 'the specified league'} "
                    "operate under local board playing conditions. CricketIQ covers official ICC international "
                    "playing conditions and MCC Laws. Please specify an international format (Test, ODI, T20I)."
                ),
                suggested_clarifications=[
                    "Would you like the rule according to official ICC T20I Playing Conditions instead?",
                    "Would you like the baseline MCC Law?"
                ],
                trace=QueryTrace(
                    query_id=query_id,
                    latency_ms=latency_ms,
                    retrieval_count=0,
                    applicable_documents=[],
                    model_used="none",
                ),
            )

        # 3. Evidence Retrieval (incorporates Applicability Resolution pre-search)
        max_cits = request.preferences.max_citations if request.preferences else 5
        ret_req = RetrievalRequest(
            query=request.query,
            match_context=match_context,
            top_k_fused=max_cits,
            include_parent_context=request.preferences.include_cross_references if request.preferences else True,
            include_related_evidence=request.preferences.include_cross_references if request.preferences else True,
        )
        ret_outcome = self.retrieval_service.retrieve(ret_req)

        # 4. Check for Clarification Required at Applicability Level
        if ret_outcome.clarification_prompt:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryResponse(
                status=QueryStatus.CLARIFICATION_REQUIRED,
                abstention_reason=ret_outcome.clarification_prompt,
                suggested_clarifications=[ret_outcome.clarification_prompt],
                trace=QueryTrace(
                    query_id=query_id,
                    latency_ms=latency_ms,
                    retrieval_count=0,
                    applicable_documents=ret_outcome.applicable_document_ids,
                    model_used="none",
                ),
            )

        # 5. Evidence Sufficiency Pre-Generation Gate
        sufficiency = self.sufficiency_auditor.evaluate(
            query=request.query,
            context=match_context,
            outcome=ret_outcome,
        )

        if not sufficiency.is_sufficient:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryResponse(
                status=sufficiency.status,
                abstention_reason=sufficiency.abstention_reason,
                suggested_clarifications=sufficiency.suggested_clarifications,
                trace=QueryTrace(
                    query_id=query_id,
                    latency_ms=latency_ms,
                    retrieval_count=len(ret_outcome.hits),
                    applicable_documents=ret_outcome.applicable_document_ids,
                    model_used="none",
                ),
            )

        # 6. Evidence-Bounded LLM Generation
        all_hits = sufficiency.primary_hits + sufficiency.context_hits
        draft = self.answer_generator.generate(
            query=request.query,
            context=match_context,
            evidence_hits=all_hits,
            preferences=request.preferences,
        )

        # 7. Deterministic Citation Validation & Database Hydration
        citations, claims, is_valid = self.citation_validator.validate_and_hydrate(
            draft=draft,
            evidence_hits=all_hits,
        )

        # 8. Strict Validation Invariant: Must have at least 1 validated citation
        if not is_valid or not citations:
            latency_ms = (time.perf_counter() - t_start) * 1000.0
            return QueryResponse(
                status=QueryStatus.INSUFFICIENT_EVIDENCE,
                abstention_reason="The generated explanation could not be verified against authoritative citations in the evidence pack.",
                suggested_clarifications=["Please rephrase the query or specify an exact clause."],
                trace=QueryTrace(
                    query_id=query_id,
                    latency_ms=latency_ms,
                    retrieval_count=len(all_hits),
                    applicable_documents=ret_outcome.applicable_document_ids,
                    model_used=getattr(self.llm_provider, "model_name", "FakeLLMProvider"),
                ),
            )

        # 9. Assemble Final Grounded Response
        answer_payload = AnswerPayload(
            summary=draft.summary,
            detailed_explanation=draft.detailed_explanation,
            key_points=draft.key_points,
            exceptions_and_edge_cases=draft.exceptions_and_edge_cases,
            historical_context=draft.historical_context,
        )

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        model_name = getattr(self.llm_provider, "model_name", "FakeLLMProvider")

        # Determine precedence note
        precedence_note = None
        doc_ids = ret_outcome.applicable_document_ids
        if any(d.startswith("ICC") for d in doc_ids) and any(d.startswith("MCC") for d in doc_ids):
            precedence_note = "ICC Playing Conditions take precedence over baseline MCC Laws"

        return QueryResponse(
            status=QueryStatus.ANSWERED,
            answer=answer_payload,
            citations=citations,
            claims=claims,
            trace=QueryTrace(
                query_id=query_id,
                latency_ms=latency_ms,
                retrieval_count=len(all_hits),
                applicable_documents=ret_outcome.applicable_document_ids,
                precedence_applied=precedence_note,
                model_used=model_name,
            ),
        )
