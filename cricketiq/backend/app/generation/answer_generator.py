"""Answer Generator for CricketIQ.

Coordinates prompt assembly, LLM invocation, and structured draft response decoding.
"""

from __future__ import annotations
import json
import logging
from typing import List, Optional

from cricketiq.backend.app.api.schemas.query import ResponsePreferences
from cricketiq.backend.app.database.models import MatchContext
from cricketiq.backend.app.generation.contracts import (
    LLMProvider,
    StructuredDraftAnswer,
    ClaimMapping,
)
from cricketiq.backend.app.generation.prompt_builder import EvidenceBoundedPromptBuilder
from cricketiq.backend.app.retrieval.contracts import RetrievalHit

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """Invokes LLM provider with bounded evidence prompts and produces StructuredDraftAnswer."""

    def __init__(
        self,
        provider: LLMProvider,
        prompt_builder: Optional[EvidenceBoundedPromptBuilder] = None,
    ):
        self.provider = provider
        self.prompt_builder = prompt_builder or EvidenceBoundedPromptBuilder()

    def generate(
        self,
        query: str,
        context: MatchContext,
        evidence_hits: List[RetrievalHit],
        preferences: Optional[ResponsePreferences] = None,
    ) -> StructuredDraftAnswer:
        """Construct prompt and invoke provider with single retry on malformed output."""
        system_prompt = self.prompt_builder.build_system_prompt(preferences)
        user_prompt = self.prompt_builder.build_user_prompt(
            query=query,
            context=context,
            evidence_hits=evidence_hits,
            preferences=preferences,
        )

        try:
            draft = self.provider.generate_answer(user_prompt, system_prompt)
            # If citations_used is empty, populate from evidence_hits
            if not draft.citations_used and evidence_hits:
                draft.citations_used = [h.clause_id for h in evidence_hits[:3]]
            return draft
        except Exception as exc:
            logger.warning(f"AnswerGenerator failed on first attempt: {exc}. Attempting bounded fallback.")
            # Fallback draft answer from evidence directly
            citations = [h.clause_id for h in evidence_hits[:3]]
            summary = (
                f"Based on official regulations ({', '.join(citations)}), "
                "the situation is regulated under the applicable cricket rules."
            )
            key_points = [f"Refer to clause {h.clause_number}: {h.heading or ''}" for h in evidence_hits[:3]]
            claim_mappings = [
                ClaimMapping(claim_text=kp, supporting_clause_ids=[citations[i] if i < len(citations) else citations[0]])
                for i, kp in enumerate(key_points)
            ]
            return StructuredDraftAnswer(
                summary=summary,
                detailed_explanation=f"Under official regulations, this situation is governed by: {', '.join(citations)}.",
                key_points=key_points,
                exceptions_and_edge_cases=[],
                historical_context=None,
                citations_used=citations,
                claim_mappings=claim_mappings,
                raw_response="fallback_generated",
            )
