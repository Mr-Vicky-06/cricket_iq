"""Unit tests for EvidenceBoundedPromptBuilder."""

import pytest
from cricketiq.backend.app.api.schemas.query import ResponsePreferences
from cricketiq.backend.app.database.models import MatchContext, CricketFormat
from cricketiq.backend.app.generation.prompt_builder import EvidenceBoundedPromptBuilder
from cricketiq.backend.app.retrieval.contracts import RetrievalHit, EvidenceRole


@pytest.fixture
def builder():
    return EvidenceBoundedPromptBuilder()


def test_build_system_prompt(builder):
    sp = builder.build_system_prompt()
    assert "CricketIQ" in sp
    assert "evidence_pack" in sp
    assert "JSON" in sp


def test_build_user_prompt_xml_enclosure(builder):
    ctx = MatchContext(format=CricketFormat.T20I, competition="T20_WORLD_CUP")
    hit = RetrievalHit(
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        document_id="ICC_T20I_MEN_2026",
        clause_number="21.18.2",
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit.",
        normalized_text="delivery following no ball shall be free hit",
        evidence_role=EvidenceRole.PRIMARY,
    )
    prefs = ResponsePreferences(max_citations=3)
    user_prompt = builder.build_user_prompt(
        query="Can a batter be caught on a free hit?",
        context=ctx,
        evidence_hits=[hit],
        preferences=prefs,
    )

    assert "<match_context>" in user_prompt
    assert "<evidence_pack>" in user_prompt
    assert '<clause id="ICC_T20I_MEN_2026:21.18.2"' in user_prompt
    assert "<user_question>" in user_prompt
    assert "Can a batter be caught on a free hit?" in user_prompt
