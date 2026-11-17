"""Unit tests for Phase 4 API Pydantic Schemas."""

import pytest
from pydantic import ValidationError

from cricketiq.backend.app.api.schemas.query import (
    MatchContextInput,
    ResponsePreferences,
    QueryRequest,
)
from cricketiq.backend.app.api.schemas.response import (
    QueryStatus,
    CitationItem,
    ClaimSupportItem,
    AnswerPayload,
    QueryTrace,
    QueryResponse,
)
from cricketiq.backend.app.database.models import (
    CricketFormat,
    GenderCategory,
    DocumentAuthority,
)


def test_query_request_valid():
    """Test valid query request instantiation."""
    req = QueryRequest(
        query="Can a batter be out on a free hit in T20I?",
        context=MatchContextInput(
            format=CricketFormat.T20I,
            category=GenderCategory.MENS,
            series_start_date="2026-10-01",
        ),
        preferences=ResponsePreferences(
            detail_level="detailed",
            max_citations=3,
        ),
    )
    assert req.query == "Can a batter be out on a free hit in T20I?"
    assert req.context.format == CricketFormat.T20I
    assert req.preferences.max_citations == 3


def test_query_request_min_length_validation():
    """Test min_length validation on query."""
    with pytest.raises(ValidationError):
        QueryRequest(query="hi")


def test_query_request_max_length_validation():
    """Test max_length validation on query."""
    with pytest.raises(ValidationError):
        QueryRequest(query="a" * 1001)


def test_response_preferences_constraints():
    """Test constraints on max_citations (1-10) and detail_level."""
    with pytest.raises(ValidationError):
        ResponsePreferences(max_citations=0)

    with pytest.raises(ValidationError):
        ResponsePreferences(max_citations=11)

    with pytest.raises(ValidationError):
        ResponsePreferences(detail_level="ultra")


def test_query_response_schema():
    """Test valid QueryResponse schema serialization."""
    trace = QueryTrace(
        query_id="trace-1234",
        latency_ms=125.4,
        retrieval_count=3,
        applicable_documents=["ICC_T20I_MEN_2026", "MCC_LAWS_2026"],
        precedence_applied="ICC Playing Conditions override MCC Laws",
        model_used="FakeLLMProvider",
    )
    cit = CitationItem(
        citation_id="cit-1",
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        clause_number="21.18.2",
        document_id="ICC_T20I_MEN_2026",
        document_title="ICC Men's T20I Playing Conditions",
        document_version="October 2026",
        authority="ICC",
        page_start=45,
        page_end=45,
        exact_quote="The delivery following a No ball shall be a free hit.",
        confidence=0.98,
    )
    claim = ClaimSupportItem(
        claim_text="A batter can only be run out on a free hit delivery.",
        supporting_citation_ids=["cit-1"],
        is_verified=True,
    )
    answer = AnswerPayload(
        summary="A batter cannot be out caught or bowled on a free hit, but can be run out.",
        detailed_explanation="Under Clause 21.18.2...",
        key_points=["Free hit follows any No ball", "Run out is permitted"],
        exceptions_and_edge_cases=["Illegal fielding change before the free hit delivery"],
    )

    resp = QueryResponse(
        status=QueryStatus.ANSWERED,
        answer=answer,
        citations=[cit],
        claims=[claim],
        trace=trace,
    )

    assert resp.status == QueryStatus.ANSWERED
    assert len(resp.citations) == 1
    assert resp.citations[0].clause_number == "21.18.2"
    assert resp.claims[0].is_verified is True
    assert resp.trace.retrieval_count == 3


def test_query_response_abstention():
    """Test QueryResponse when system abstains or requires clarification."""
    trace = QueryTrace(
        query_id="trace-5678",
        latency_ms=22.1,
        retrieval_count=0,
        applicable_documents=[],
        model_used="none",
    )
    resp = QueryResponse(
        status=QueryStatus.CLARIFICATION_REQUIRED,
        abstention_reason="Question does not specify whether Test or T20I rules apply.",
        suggested_clarifications=["Are you referring to Test matches or T20 Internationals?"],
        trace=trace,
    )
    assert resp.status == QueryStatus.CLARIFICATION_REQUIRED
    assert resp.answer is None
    assert len(resp.suggested_clarifications) == 1
