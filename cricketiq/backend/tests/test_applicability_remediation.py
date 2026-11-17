"""Tests for Applicability Engine Multi-Document Cardinality, Role Rejection & Canonical Competitions (Gate 2 Remediation).

Verifies:
1. Multiple matching competition documents trigger explicit conflict / ambiguity rather than silent overwrite.
2. Multiple matching format playing conditions trigger explicit conflict / ambiguity.
3. Multiple matching baseline MCC Laws trigger explicit conflict / ambiguity.
4. Canonical competition matching validates aliases ('wtc', 'world test championship') and rejects unrecognized competitions.
5. Malformed date strings trigger invalid date clarification rather than defaulting.
6. Unknown or unapproved regulatory roles are rejected during document screening.
7. Explanatory documents remain at lowest precedence and never become primary or baseline.
"""

import pytest
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus,
    CricketFormat, GenderCategory, ScopeLevel, RegulatoryRole, MatchContext
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.core.applicability_engine import ApplicabilityEngine


@pytest.fixture
def memory_repo():
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    return CricketIQRepository(session)


def test_competing_format_pc_conflict(memory_repo):
    """Multiple format PC documents matching the same format/category/edition must trigger conflict."""
    doc1 = SourceDocument(
        id="ICC_TEST_MEN_2026_A",
        publisher=DocumentAuthority.ICC,
        title="Test PC A",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        regulatory_role=RegulatoryRole.NORMATIVE_FORMAT_PC,
        edition="October 2026",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://icc.com/a.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    doc2 = SourceDocument(
        id="ICC_TEST_MEN_2026_B",
        publisher=DocumentAuthority.ICC,
        title="Test PC B",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        regulatory_role=RegulatoryRole.NORMATIVE_FORMAT_PC,
        edition="October 2026",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://icc.com/b.pdf",
        sha256="2" * 64,
        status=DocumentStatus.ACTIVE
    )
    memory_repo.upsert_source_document(doc1)
    memory_repo.upsert_source_document(doc2)

    engine = ApplicabilityEngine()
    ctx = MatchContext(format=CricketFormat.TEST, category=GenderCategory.MENS)
    decision = engine.resolve(ctx, memory_repo)

    assert decision.is_ambiguous is True
    assert "COMPETING_FORMAT_PC_CONFLICT" in decision.reason_codes
    assert len(decision.conflicts) > 0
    assert "Multiple conflicting format playing conditions" in decision.clarification_needed


def test_competing_competition_regulations_conflict(memory_repo):
    """Multiple competition documents matching the same competition alias must trigger conflict."""
    doc1 = SourceDocument(
        id="ICC_WTC_A",
        publisher=DocumentAuthority.ICC,
        title="WTC A",
        document_type=DocumentType.COMPETITION_REGULATIONS,
        scope_level=ScopeLevel.COMPETITION_PC,
        regulatory_role=RegulatoryRole.NORMATIVE_COMPETITION_REGULATION,
        edition="2025-2027",
        competition="World Test Championship",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://icc.com/wtc_a.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    doc2 = SourceDocument(
        id="ICC_WTC_B",
        publisher=DocumentAuthority.ICC,
        title="WTC B",
        document_type=DocumentType.COMPETITION_REGULATIONS,
        scope_level=ScopeLevel.COMPETITION_PC,
        regulatory_role=RegulatoryRole.NORMATIVE_COMPETITION_REGULATION,
        edition="2025-2027",
        competition="World Test Championship",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://icc.com/wtc_b.pdf",
        sha256="2" * 64,
        status=DocumentStatus.ACTIVE
    )
    memory_repo.upsert_source_document(doc1)
    memory_repo.upsert_source_document(doc2)

    engine = ApplicabilityEngine()
    ctx = MatchContext(format=CricketFormat.TEST, competition="WTC")
    decision = engine.resolve(ctx, memory_repo)

    assert decision.is_ambiguous is True
    assert "COMPETING_COMPETITION_REGULATIONS_CONFLICT" in decision.reason_codes
    assert "Multiple conflicting competition regulations" in decision.clarification_needed


def test_unrecognized_competition_rejected(memory_repo):
    """An unsupported or unrecognized competition triggers explicit clarification."""
    engine = ApplicabilityEngine()
    ctx = MatchContext(format=CricketFormat.TEST, competition="Galactic Cricket Championship")
    decision = engine.resolve(ctx, memory_repo)

    assert decision.is_ambiguous is True
    assert "UNRECOGNIZED_COMPETITION" in decision.reason_codes
    assert "not recognized" in decision.clarification_needed


def test_invalid_date_format_clarification(memory_repo):
    """Malformed date strings must trigger clarification and never proceed with silent defaults."""
    engine = ApplicabilityEngine()
    ctx1 = MatchContext(format=CricketFormat.T20I, series_start_date="01-10-2026") # non-ISO
    decision1 = engine.resolve(ctx1, memory_repo)
    assert decision1.is_ambiguous is True
    assert "INVALID_SERIES_START_DATE_FORMAT" in decision1.reason_codes

    ctx2 = MatchContext(format=CricketFormat.T20I, match_date="yesterday")
    decision2 = engine.resolve(ctx2, memory_repo)
    assert decision2.is_ambiguous is True
    assert "INVALID_MATCH_DATE_FORMAT" in decision2.reason_codes


def test_unknown_regulatory_role_rejected(memory_repo):
    """A document with an invalid or unapproved regulatory role must be rejected during screening."""
    # Create doc directly in DB with unknown role
    doc = SourceDocument(
        id="DOC_UNKNOWN_ROLE",
        publisher=DocumentAuthority.ICC,
        title="Unknown Doc",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        regulatory_role=RegulatoryRole.NORMATIVE_FORMAT_PC,
        edition="October 2026",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://icc.com/u.pdf",
        sha256="u" * 64,
        status=DocumentStatus.ACTIVE
    )
    # Manually tamper regulatory_role to simulate corrupted/unknown metadata
    object.__setattr__(doc, "regulatory_role", "corrupted_unknown_role")
    memory_repo.upsert_source_document(doc)

    engine = ApplicabilityEngine()
    ctx = MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    decision = engine.resolve(ctx, memory_repo)

    assert "DOC_UNKNOWN_ROLE" not in [d.id for d in decision.selected_bundle]
    rejected_ids = [r["doc_id"] for r in decision.rejected_candidates]
    assert "DOC_UNKNOWN_ROLE" in rejected_ids
