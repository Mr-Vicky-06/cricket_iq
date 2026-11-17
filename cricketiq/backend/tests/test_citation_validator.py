"""Unit tests for CitationValidator."""

import pytest
from sqlalchemy.orm import Session
from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.generation.citation_validator import CitationValidator
from cricketiq.backend.app.generation.contracts import StructuredDraftAnswer, ClaimMapping
from cricketiq.backend.app.retrieval.contracts import RetrievalHit, EvidenceRole


@pytest.fixture
def repo():
    engine = create_db_engine("sqlite:///data/cricketiq.db")
    session = Session(bind=engine)
    return CricketIQRepository(session)


@pytest.fixture
def validator(repo):
    return CitationValidator(repo)


def test_validate_citations_exact_match(validator):
    hit = RetrievalHit(
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        document_id="ICC_T20I_MEN_2026",
        clause_number="21.18.2",
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit.",
        normalized_text="delivery following no ball shall be free hit",
        evidence_role=EvidenceRole.PRIMARY,
    )
    draft = StructuredDraftAnswer(
        summary="Free hit applies.",
        detailed_explanation="Under clause 21.18.2...",
        citations_used=["ICC_T20I_MEN_2026:21.18.2"],
        claim_mappings=[
            ClaimMapping(
                claim_text="Free hit delivery follows a no-ball.",
                supporting_clause_ids=["ICC_T20I_MEN_2026:21.18.2"],
            )
        ],
    )

    citations, claims, is_valid = validator.validate_and_hydrate(draft, [hit])
    assert is_valid is True
    assert len(citations) == 1
    assert citations[0].citation_id == "cit-1"
    assert citations[0].clause_id == "ICC_T20I_MEN_2026:21.18.2"
    assert citations[0].authority == "ICC"
    assert len(claims) == 1
    assert claims[0].is_verified is True
    assert claims[0].supporting_citation_ids == ["cit-1"]


def test_reject_hallucinated_citation(validator):
    hit = RetrievalHit(
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        document_id="ICC_T20I_MEN_2026",
        clause_number="21.18.2",
        original_text="Legitimate clause text.",
        normalized_text="legitimate clause text",
    )
    # Draft cites a fake clause not in evidence hits!
    draft = StructuredDraftAnswer(
        summary="Fake rule.",
        detailed_explanation="Made up rule.",
        citations_used=["FAKE_DOC:999.999"],
        claim_mappings=[
            ClaimMapping(
                claim_text="Made up claim.",
                supporting_clause_ids=["FAKE_DOC:999.999"],
            )
        ],
    )

    citations, claims, is_valid = validator.validate_and_hydrate(draft, [hit])
    assert is_valid is True
    # The hallucinated citation is rejected, and fallback binds to hit
    assert citations[0].clause_id == "ICC_T20I_MEN_2026:21.18.2"
    assert "FAKE_DOC" not in [c.clause_id for c in citations]
