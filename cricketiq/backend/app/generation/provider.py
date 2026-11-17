"""LLM Providers for CricketIQ Answer Generation.

Includes:
- FakeLLMProvider: 100% offline, deterministic mock provider for testing and CI.
- GeminiLLMProvider: Production provider calling Google Gemini API with JSON schema enforcement.
"""

from __future__ import annotations
import json
import os
import re
from typing import Optional, List, Dict, Any, Callable

from cricketiq.backend.app.generation.contracts import (
    LLMProvider,
    StructuredDraftAnswer,
    ClaimMapping,
)


class FakeLLMProvider:
    """Deterministic offline mock provider for unit tests, CI, and benchmarks."""

    def __init__(
        self,
        custom_responder: Optional[Callable[[str, Optional[str]], StructuredDraftAnswer]] = None,
        force_malformed_json: bool = False,
        force_hallucinated_clause: Optional[str] = None,
        force_empty_citations: bool = False,
    ):
        self.custom_responder = custom_responder
        self.force_malformed_json = force_malformed_json
        self.force_hallucinated_clause = force_hallucinated_clause
        self.force_empty_citations = force_empty_citations
        self.call_count = 0
        self.last_prompt = ""
        self.last_system_prompt = ""

    def generate_answer(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> StructuredDraftAnswer:
        """Generate deterministic structured response grounded in prompt evidence."""
        self.call_count += 1
        self.last_prompt = prompt
        self.last_system_prompt = system_prompt or ""

        if self.custom_responder:
            return self.custom_responder(prompt, system_prompt)

        if self.force_malformed_json:
            return StructuredDraftAnswer(
                summary="Malformed",
                detailed_explanation="Invalid JSON test",
                key_points=[],
                exceptions_and_edge_cases=[],
                citations_used=[],
                claim_mappings=[],
                raw_response="{not valid json:",
            )

        # Extract available clause IDs from prompt XML delimiters <clause id="...">
        clause_ids = re.findall(r'<clause\s+id="([^"]+)"', prompt)

        if self.force_hallucinated_clause:
            citations = [self.force_hallucinated_clause]
        elif self.force_empty_citations:
            citations = []
        else:
            citations = clause_ids[:3] if clause_ids else []

        # Derive title / topic from prompt
        summary = "Based on authoritative cricket regulations, the applicable rules govern this situation."
        detailed_explanation = (
            f"According to the official regulations ({', '.join(citations) if citations else 'applicable rules'}), "
            "the match situation is strictly regulated under the playing conditions."
        )
        key_points = [
            f"Governed under clause {c}" for c in citations
        ] if citations else ["Applicable under official playing conditions."]

        exceptions = ["Subject to umpire consultation and conditions of play."]

        claim_mappings = [
            ClaimMapping(
                claim_text=f"The situation is governed by official clause {c}.",
                supporting_clause_ids=[c],
            )
            for c in citations
        ]

        payload = {
            "summary": summary,
            "detailed_explanation": detailed_explanation,
            "key_points": key_points,
            "exceptions_and_edge_cases": exceptions,
            "historical_context": None,
            "citations_used": citations,
            "claim_mappings": [m.model_dump() for m in claim_mappings],
        }

        return StructuredDraftAnswer(
            summary=summary,
            detailed_explanation=detailed_explanation,
            key_points=key_points,
            exceptions_and_edge_cases=exceptions,
            historical_context=None,
            citations_used=citations,
            claim_mappings=claim_mappings,
            raw_response=json.dumps(payload),
        )


class GeminiLLMProvider:
    """Production provider integrating Google Gemini models via official SDK or REST."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash",
        temperature: float = 0.0,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model_name = model_name
        self.temperature = temperature
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY environment variable is required for GeminiLLMProvider.")
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                import google.generativeai as gai
                gai.configure(api_key=self.api_key)
                self._client = gai
        return self._client

    def generate_answer(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> StructuredDraftAnswer:
        """Call Gemini model with system instruction and structured JSON output."""
        client = self._get_client()

        # Check if google-genai SDK
        if hasattr(client, "models"):
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={
                    "system_instruction": system_prompt,
                    "temperature": self.temperature,
                    "response_mime_type": "application/json",
                },
            )
            raw_text = response.text
        else:
            # Legacy google-generativeai fallback
            model = client.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_prompt,
                generation_config={"temperature": self.temperature, "response_mime_type": "application/json"},
            )
            response = model.generate_content(prompt)
            raw_text = response.text

        # Parse JSON
        parsed = json.loads(raw_text)
        claim_mappings = [
            ClaimMapping(**m) for m in parsed.get("claim_mappings", [])
        ]

        return StructuredDraftAnswer(
            summary=parsed.get("summary", ""),
            detailed_explanation=parsed.get("detailed_explanation", ""),
            key_points=parsed.get("key_points", []),
            exceptions_and_edge_cases=parsed.get("exceptions_and_edge_cases", []),
            historical_context=parsed.get("historical_context"),
            citations_used=parsed.get("citations_used", []),
            claim_mappings=claim_mappings,
            raw_response=raw_text,
        )
