"""Unit tests for EvidenceSufficiencyAuditor."""

import pytest
from cricketiq.backend.app.api.schemas.response import QueryStatus
from cricketiq.backend.app.application.evidence_sufficiency import EvidenceSufficiencyAuditor
from cricketiq.backend.app.database.models import MatchContext, CricketFormat
from cricketiq.backend.app.retrieval.contracts import (
    RetrievalOutcome,
    RetrievalStatus,
    RetrievalHit,
    EvidenceRole,
)


@pytest.fixture
def auditor():
    return EvidenceSufficiencyAuditor(min_primary_hits=1, min_hit_length=20)


def test_sufficiency_domestic_rejection(auditor):
    ctx = MatchContext(cricket_level="domestic", competition="IPL")
    outcome = RetrievalOutcome(status=RetrievalStatus.SUCCESS, hits=[])
    res = auditor.evaluate("Free hit in IPL", ctx, outcome)
    assert not res.is_sufficient
    assert res.status == QueryStatus.UNSUPPORTED_COMPETITION
    assert "IPL" in res.abstention_reason


def test_sufficiency_clarification_required(auditor):
    ctx = MatchContext()
    outcome = RetrievalOutcome(
        status=RetrievalStatus.CLARIFICATION_REQUIRED,
        clarification_prompt="Please specify format",
        hits=[],
    )
    res = auditor.evaluate("Wide ball rule", ctx, outcome)
    assert not res.is_sufficient
    assert res.status == QueryStatus.CLARIFICATION_REQUIRED
    assert "specify format" in res.abstention_reason


def test_sufficiency_empty_hits(auditor):
    ctx = MatchContext(format=CricketFormat.T20I)
    outcome = RetrievalOutcome(status=RetrievalStatus.NO_RESULTS, hits=[])
    res = auditor.evaluate("Random unknown rule xyz", ctx, outcome)
    assert not res.is_sufficient
    assert res.status == QueryStatus.INSUFFICIENT_EVIDENCE


def test_sufficiency_valid_hits(auditor):
    ctx = MatchContext(format=CricketFormat.T20I)
    hit = RetrievalHit(
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        document_id="ICC_T20I_MEN_2026",
        clause_number="21.18.2",
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit for whichever batter is facing.",
        normalized_text="delivery following no ball shall be free hit",
        evidence_role=EvidenceRole.PRIMARY,
        rrf_score=0.032,
    )
    outcome = RetrievalOutcome(status=RetrievalStatus.SUCCESS, hits=[hit])
    res = auditor.evaluate("Is there a free hit after a no ball?", ctx, outcome)
    assert res.is_sufficient
    assert res.status == QueryStatus.ANSWERED
    assert len(res.primary_hits) == 1
