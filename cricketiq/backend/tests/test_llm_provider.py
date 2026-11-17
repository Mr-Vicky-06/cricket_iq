"""Unit tests for LLM providers and provider factory."""

import pytest
from cricketiq.backend.app.generation.provider import FakeLLMProvider
from cricketiq.backend.app.generation.provider_factory import get_llm_provider
from cricketiq.backend.app.generation.contracts import StructuredDraftAnswer, ClaimMapping


def test_fake_llm_provider_default():
    provider = FakeLLMProvider()
    prompt = """
<evidence_pack>
  <clause id="ICC_T20I_MEN_2026:21.18.2" document="ICC_T20I_MEN_2026" clause_number="21.18.2" heading="Free Hit">
    The delivery following a No ball shall be a free hit.
  </clause>
</evidence_pack>
<user_question>Can a batter be out on a free hit?</user_question>
"""
    answer = provider.generate_answer(prompt)
    assert isinstance(answer, StructuredDraftAnswer)
    assert len(answer.citations_used) == 1
    assert answer.citations_used[0] == "ICC_T20I_MEN_2026:21.18.2"
    assert len(answer.claim_mappings) == 1
    assert provider.call_count == 1


def test_fake_llm_provider_forced_hallucination():
    provider = FakeLLMProvider(force_hallucinated_clause="ICC_TEST_MEN_2026:99.99")
    answer = provider.generate_answer("test prompt")
    assert answer.citations_used == ["ICC_TEST_MEN_2026:99.99"]


def test_provider_factory_fallback():
    provider = get_llm_provider()
    assert isinstance(provider, FakeLLMProvider)
