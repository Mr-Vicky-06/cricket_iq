"""Evidence Sufficiency Evaluator for CricketIQ.

Deterministic pre-generation gate that assesses whether retrieved hits provide
adequate, authoritative, and format-valid evidence before invoking the LLM.
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

from cricketiq.backend.app.api.schemas.response import QueryStatus
from cricketiq.backend.app.database.models import MatchContext
from cricketiq.backend.app.retrieval.contracts import (
    RetrievalOutcome,
    RetrievalStatus,
    RetrievalHit,
    EvidenceRole,
)


class SufficiencyEvaluation(BaseModel):
    """Result of evidence sufficiency analysis."""
    is_sufficient: bool = Field(..., description="True if evidence is adequate for synthesis")
    status: QueryStatus = Field(..., description="Determined query resolution status")
    abstention_reason: Optional[str] = Field(default=None, description="Reason if system must abstain")
    suggested_clarifications: List[str] = Field(default_factory=list, description="Follow-up clarification questions")
    primary_hits: List[RetrievalHit] = Field(default_factory=list, description="Primary direct evidence hits")
    context_hits: List[RetrievalHit] = Field(default_factory=list, description="Supporting context hits")
    max_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class EvidenceSufficiencyAuditor:
    """Evaluates evidence sufficiency to prevent hallucination on weak or missing data."""

    def __init__(self, min_primary_hits: int = 1, min_hit_length: int = 20):
        self.min_primary_hits = min_primary_hits
        self.min_hit_length = min_hit_length

    def evaluate(
        self,
        query: str,
        context: MatchContext,
        outcome: RetrievalOutcome,
    ) -> SufficiencyEvaluation:
        """Audit retrieval outcome for completeness and authoritative grounding."""
        # 1. Domestic competition check
        if context.cricket_level == "domestic":
            return SufficiencyEvaluation(
                is_sufficient=False,
                status=QueryStatus.UNSUPPORTED_COMPETITION,
                abstention_reason=(
                    f"Domestic and franchise competitions ({context.competition or 'domestic league'}) "
                    "operate under board-specific tournament regulations outside the official ICC/MCC international corpus."
                ),
                suggested_clarifications=[
                    "Please specify an international format (Test, ODI, or T20I) to query official ICC/MCC regulations."
                ],
            )

        # 2. Check for clarification required at retrieval / applicability level
        if outcome.status == RetrievalStatus.CLARIFICATION_REQUIRED:
            prompt = outcome.clarification_prompt or "Clarification required regarding match context or series start date."
            return SufficiencyEvaluation(
                is_sufficient=False,
                status=QueryStatus.CLARIFICATION_REQUIRED,
                abstention_reason=prompt,
                suggested_clarifications=[prompt],
            )

        # 3. Check for alien non-cricket subjects / sports cross-over concepts
        alien_subjects = {
            "touchdown", "hockey", "basketball", "soccer", "baseball",
            "tennis", "volleyball", "rugby", "quarterback", "puck",
            "slapshot", "slam dunk"
        }
        q_lower = query.lower()
        if any(w in q_lower for w in alien_subjects):
            return SufficiencyEvaluation(
                is_sufficient=False,
                status=QueryStatus.INSUFFICIENT_EVIDENCE,
                abstention_reason=(
                    f"The inquiry references terms or concepts from outside cricket regulations ('{query}'). "
                    "Official ICC and MCC rules do not contain provisions for these concepts."
                ),
                suggested_clarifications=[
                    "Please ensure the inquiry pertains to official Laws of Cricket or ICC Playing Conditions."
                ],
            )

        # 4. Check for empty results or unavailable sources
        if outcome.status in [RetrievalStatus.NO_RESULTS, RetrievalStatus.NO_APPLICABLE_SOURCES] or not outcome.hits:
            return SufficiencyEvaluation(
                is_sufficient=False,
                status=QueryStatus.INSUFFICIENT_EVIDENCE,
                abstention_reason=(
                    "No authoritative clauses could be retrieved from the applicable cricket regulations "
                    f"matching the inquiry: '{query}'."
                ),
                suggested_clarifications=[
                    "Would you like to search under general MCC Laws instead of specific Playing Conditions?",
                    "Please check if the terminology or rule number is specified in official regulations."
                ],
            )

        # 4. Partition hits by evidence role
        primary_hits: List[RetrievalHit] = []
        context_hits: List[RetrievalHit] = []

        for hit in outcome.hits:
            if hit.evidence_role == EvidenceRole.PRIMARY:
                # Ensure hit text has non-trivial length
                if len(hit.original_text.strip()) >= self.min_hit_length:
                    primary_hits.append(hit)
            else:
                context_hits.append(hit)

        # 5. Evaluate if primary evidence is sufficient
        if len(primary_hits) < self.min_primary_hits:
            # Check if any context hits can serve as fallback
            if not context_hits:
                return SufficiencyEvaluation(
                    is_sufficient=False,
                    status=QueryStatus.INSUFFICIENT_EVIDENCE,
                    abstention_reason=(
                        "Retrieved clauses contained insufficient substantive rule text to provide an authoritative ruling."
                    ),
                    suggested_clarifications=[
                        "Please rephrase the question or specify the specific Law or Playing Condition clause number."
                    ],
                )
            # If we only have context hits, check if the best one has adequate text
            primary_hits = context_hits[:1]
            context_hits = context_hits[1:]

        # Calculate max score
        scores = [h.rrf_score for h in primary_hits if h.rrf_score > 0]
        max_score = max(scores) if scores else 1.0

        return SufficiencyEvaluation(
            is_sufficient=True,
            status=QueryStatus.ANSWERED,
            primary_hits=primary_hits,
            context_hits=context_hits,
            max_confidence=min(1.0, max_score * 50.0) if max_score < 1.0 else 1.0,
        )
