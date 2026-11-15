"""Unit and Integration tests for Retrieval Scope and Leakage Prevention (Gate 5).
"""

import pytest
from datetime import date
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus,
    ClauseType, MatchContext, CricketFormat, GenderCategory
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.core.applicability_engine import ApplicabilityEngine
from cricketiq.backend.app.retrieval.contracts import RetrievalRequest, RetrievalStatus
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.service import RetrievalService


@pytest.fixture
def multi_format_repo() -> CricketIQRepository:
    """Setup repository with both Test and T20I Playing Conditions."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    t20_doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    test_doc = SourceDocument(
        id="ICC_TEST_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Test Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/test-2026.pdf",
        sha256="2" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(t20_doc)
    repo.upsert_source_document(test_doc)

    c_t20 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=t20_doc.id,
        clause_number="21.18",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit.",
        normalized_text="the delivery following a no ball shall be a free hit",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    c_test = RuleClause(
        id="ICC_TEST_MEN_2026:21.1",
        source_document_id=test_doc.id,
        clause_number="21.1",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Mode of delivery",
        original_text="The umpire shall ascertain whether the bowler intends to bowl right-handed or left-handed.",
        normalized_text="the umpire shall ascertain whether the bowler intends to bowl right handed or left handed",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    repo.upsert_clauses([c_t20, c_test])

    fts = SQLiteFTSSearchProvider(repo)
    fts.rebuild_index()

    return repo


def test_format_isolation_test_does_not_leak_t20i(multi_format_repo):
    """Verify that a Test query never returns T20I-only clauses."""
    repo = multi_format_repo
    service = RetrievalService(repository=repo)

    ctx = MatchContext(
        cricket_level="international",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        series_start_date="2026-10-05",
        match_date="2026-10-06"
    )

    req = RetrievalRequest(
        query="What happens after a no ball?",
        match_context=ctx
    )

    outcome = service.retrieve(req)
    assert outcome.status in (RetrievalStatus.SUCCESS, RetrievalStatus.NO_RESULTS)

    for hit in outcome.hits:
        # Crucial invariant: No T20I Free Hit clause may leak into Test context
        assert hit.document_id == "ICC_TEST_MEN_2026"
        assert hit.clause_number != "21.18"


def test_domestic_query_blocks_search_with_clarification(multi_format_repo):
    """Verify that a query referencing a domestic league stops at applicability gating."""
    repo = multi_format_repo
    service = RetrievalService(repository=repo)

    ctx = MatchContext(
        cricket_level="domestic",
        competition="IPL"
    )

    req = RetrievalRequest(
        query="What are the free hit rules in IPL?",
        match_context=ctx
    )

    outcome = service.retrieve(req)
    # Must reject or require clarification before search
    assert outcome.status == RetrievalStatus.CLARIFICATION_REQUIRED
    assert outcome.clarification_prompt is not None
    assert "domestic" in outcome.clarification_prompt.lower()
    assert len(outcome.hits) == 0
