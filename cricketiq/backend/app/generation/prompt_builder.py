"""Evidence-Bounded Prompt Builder for CricketIQ Answer Generation.

Formats user queries and authoritative retrieved clauses into strictly delimited
XML structures to enforce evidence boundaries and prevent prompt injection.
"""

from __future__ import annotations
import html
from typing import List, Optional
from cricketiq.backend.app.api.schemas.query import ResponsePreferences
from cricketiq.backend.app.database.models import MatchContext
from cricketiq.backend.app.retrieval.contracts import RetrievalHit


SYSTEM_PROMPT = """You are CricketIQ, the world's most authoritative and precise cricket rules intelligence assistant.
Your answers must be completely grounded in the retrieved official regulations provided in the <evidence_pack>.

STRICT OPERATIONAL RULES:
1. Grounding Invariant: Base every rule statement, penalty, condition, and exception ONLY on the verbatim text in <evidence_pack>. Never use outside knowledge or hallucinate provisions.
2. Citation Requirement: In `citations_used`, list the exact `id` of each clause in <evidence_pack> that supports your answer.
3. Claim Mapping: In `claim_mappings`, connect each substantive statement in your answer to the specific clause `id` that proves it.
4. Precedence: Playing Conditions (ICC) override fundamental Laws of Cricket (MCC). If both are present, explain the ICC playing condition as primary, noting any MCC baseline.
5. Neutrality: If evidence is ambiguous, incomplete, or discretionary (e.g. umpire discretion), state the exact wording and condition without guessing outcomes.
6. JSON Output: Output MUST be a valid JSON object matching the requested schema. No surrounding markdown code blocks, backticks, or extraneous commentary.
"""


class EvidenceBoundedPromptBuilder:
    """Builds prompt payloads enclosing retrieved evidence in XML boundaries."""

    def build_system_prompt(self, preferences: Optional[ResponsePreferences] = None) -> str:
        prompt = SYSTEM_PROMPT
        if preferences:
            prompt += f"\nDetail Level: {preferences.detail_level}.\n"
            if preferences.include_historical_comparison:
                prompt += "Include historical comparison between previous editions and current regulations if evidence is provided.\n"
        return prompt

    def build_user_prompt(
        self,
        query: str,
        context: MatchContext,
        evidence_hits: List[RetrievalHit],
        preferences: Optional[ResponsePreferences] = None,
    ) -> str:
        """Construct the prompt with XML tags enclosing context and evidence."""
        max_cits = preferences.max_citations if preferences else 5
        selected_hits = evidence_hits[:max_cits]

        # Sanitize text
        clean_query = query.replace("</user_question>", "").strip()

        lines: List[str] = []

        # Context block
        lines.append("<match_context>")
        lines.append(f"  <cricket_level>{context.cricket_level}</cricket_level>")
        if context.governing_body:
            lines.append(f"  <governing_body>{context.governing_body}</governing_body>")
        if context.format:
            lines.append(f"  <format>{context.format.value}</format>")
        if context.category:
            lines.append(f"  <category>{context.category.value}</category>")
        if context.competition:
            lines.append(f"  <competition>{context.competition}</competition>")
        if context.series_start_date:
            lines.append(f"  <series_start_date>{context.series_start_date}</series_start_date>")
        if context.match_date:
            lines.append(f"  <match_date>{context.match_date}</match_date>")
        lines.append("</match_context>\n")

        # Evidence Pack block
        lines.append("<evidence_pack>")
        for hit in selected_hits:
            clause_id = hit.clause_id
            doc_id = hit.document_id
            clause_num = hit.clause_number
            heading = html.escape(hit.heading or "")
            body_text = hit.original_text.strip()

            lines.append(
                f'  <clause id="{clause_id}" document="{doc_id}" clause_number="{clause_num}" heading="{heading}">'
            )
            lines.append(f"    {body_text}")
            lines.append("  </clause>")
        lines.append("</evidence_pack>\n")

        # User Question block
        lines.append("<user_question>")
        lines.append(f"  {clean_query}")
        lines.append("</user_question>\n")

        # Required JSON Output Instructions
        lines.append("""Format your JSON response exactly matching this schema:
{
  "summary": "Concise summary directly answering the question",
  "detailed_explanation": "Comprehensive explanation with exact clause citations",
  "key_points": ["Point 1", "Point 2"],
  "exceptions_and_edge_cases": ["Edge case or condition 1"],
  "historical_context": null or "Note on rule change / comparison if applicable",
  "citations_used": ["<exact clause id from evidence_pack>"],
  "claim_mappings": [
    {
      "claim_text": "Substantive claim statement",
      "supporting_clause_ids": ["<exact clause id>"]
    }
  ]
}
""")
        return "\n".join(lines)
