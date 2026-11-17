"""Unit and integration tests for QueryOrchestrator."""

import pytest
from sqlalchemy.orm import Session
from cricketiq.backend.app.api.schemas.query import QueryRequest, MatchContextInput
from cricketiq.backend.app.api.schemas.response import QueryStatus
from cricketiq.backend.app.application.query_orchestrator import QueryOrchestrator
from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.models import CricketFormat
from cricketiq.backend.app.database.repository import CricketIQRepository


@pytest.fixture
def repo():
    engine = create_db_engine("sqlite:///data/cricketiq.db")
    session = Session(bind=engine)
    return CricketIQRepository(session)


@pytest.fixture
def orchestrator(repo):
    return QueryOrchestrator(repository=repo)


def test_orchestrator_free_hit_t20i(orchestrator):
    """Test full pipeline execution on canonical T20I free hit query."""
    req = QueryRequest(
        query="What happens after a no ball in T20I? Is there a free hit?",
        context=MatchContextInput(format=CricketFormat.T20I),
    )
    resp = orchestrator.execute(req)

    assert resp.status == QueryStatus.ANSWERED
    assert resp.answer is not None
    assert len(resp.citations) >= 1
    assert any("21.18" in c.clause_number for c in resp.citations)
    assert resp.trace.retrieval_count > 0
    assert resp.trace.latency_ms > 0


def test_orchestrator_domestic_ipl_abstention(orchestrator):
    """Test strict abstention when query is about domestic IPL rules."""
    req = QueryRequest(query="What is the impact player rule in IPL?")
    resp = orchestrator.execute(req)

    assert resp.status == QueryStatus.UNSUPPORTED_COMPETITION
    assert resp.answer is None
    assert "IPL" in resp.abstention_reason
    assert len(resp.suggested_clarifications) > 0


def test_orchestrator_series_start_date_clarification(orchestrator):
    """Test clarification required when match date is post-transition but series start is missing."""
    req = QueryRequest(
        query="Can a bowler bowl bouncers in this match?",
        context=MatchContextInput(match_date="2026-10-15"),
    )
    resp = orchestrator.execute(req)

    assert resp.status == QueryStatus.CLARIFICATION_REQUIRED
    assert resp.answer is None
    assert "series" in resp.abstention_reason.lower()
