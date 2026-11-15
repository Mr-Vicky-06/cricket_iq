"""Comprehensive tests for Database Persistence, Repository, and Cross-Clause Evidence in CricketIQ."""

import pytest
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from cricketiq.backend.app.database.connection import (
    Base, create_db_engine, check_sqlite_fts5_support
)
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentRelationship, DocumentAuthority,
    DocumentType, ScopeLevel, ApplicabilityBasis, CricketFormat,
    GenderCategory, DocumentStatus, ClauseType, ValidationStatus,
    RelationshipType
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.ingestion.pipeline import IngestionPipeline

FIXTURE_PDF = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "icc" / "icc_mens_t20i_pc_2026_sample.pdf"


@pytest.fixture
def db_session() -> Session:
    """Provide a fresh in-memory SQLite database session for each test."""
    eng = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=eng)
    session = Session(bind=eng)
    try:
        yield session
    finally:
        session.close()


def test_sqlite_fts5_capability_detected(db_session):
    eng = db_session.get_bind()
    fts5_ok = check_sqlite_fts5_support(eng)
    assert fts5_ok is True


def test_repository_source_document_crud(db_session):
    repo = CricketIQRepository(db_session)
    doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        edition="October 2026",
        effective_from="2026-10-01",
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        sha256="1234567890abcdef" * 4,
        status=DocumentStatus.ACTIVE
    )

    saved = repo.upsert_source_document(doc)
    assert saved.id == doc.id
    assert saved.title == doc.title

    fetched = repo.get_document(doc.id)
    assert fetched is not None
    assert fetched.edition == "October 2026"

    active_docs = repo.list_active_documents()
    assert len(active_docs) == 1
    assert active_docs[0].id == doc.id


def test_repository_clauses_crud_and_hierarchy(db_session):
    repo = CricketIQRepository(db_session)

    # 1. Create parent doc
    doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        sha256="a" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc)

    # 2. Major Section 21
    sec_21 = RuleClause(
        id="ICC_T20I_MEN_2026:21",
        source_document_id=doc.id,
        clause_number="21",
        parent_clause_id=None,
        hierarchy_depth=1,
        heading="No Ball",
        original_text="21 NO BALL",
        page_start=1,
        page_end=1,
        clause_type=ClauseType.RULE,
        validation_status=ValidationStatus.VALIDATED
    )

    # 3. Clause 21.17 No-ball dismissals
    clause_21_17 = RuleClause(
        id="ICC_T20I_MEN_2026:21.17",
        source_document_id=doc.id,
        clause_number="21.17",
        parent_clause_id="ICC_T20I_MEN_2026:21",
        hierarchy_depth=2,
        heading="Out from a No ball",
        original_text="When a No ball has been called, neither batter can be out to that delivery except under Law 34 (Hit the ball twice), Law 37 (Obstructing the field) or Law 38 (Run out).",
        page_start=2,
        page_end=2,
        clause_type=ClauseType.EXCEPTION,
        cross_references=["34", "37", "38"],
        validation_status=ValidationStatus.VALIDATED
    )

    # 4. Clause 21.18 Free Hit Header
    clause_21_18 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc.id,
        clause_number="21.18",
        parent_clause_id="ICC_T20I_MEN_2026:21",
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="21.18 Free Hit",
        page_start=2,
        page_end=2,
        clause_type=ClauseType.RULE,
        validation_status=ValidationStatus.VALIDATED
    )

    # 5. Clause 21.18.2 Free Hit Dismissals
    clause_21_18_2 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=doc.id,
        clause_number="21.18.2",
        parent_clause_id="ICC_T20I_MEN_2026:21.18",
        hierarchy_depth=3,
        heading="Dismissal on Free Hit",
        original_text="For any free hit, the striker can be dismissed only under the circumstances that apply for a No ball, even if the delivery for the free hit is called Wide ball.",
        page_start=2,
        page_end=2,
        clause_type=ClauseType.EXCEPTION,
        cross_references=["21.17", "38"],
        validation_status=ValidationStatus.VALIDATED
    )

    clauses_to_save = [sec_21, clause_21_17, clause_21_18, clause_21_18_2]
    saved_count = repo.upsert_clauses(clauses_to_save)
    assert saved_count == 4

    # Test hierarchy retrieval for 21.18.2
    hierarchy = repo.get_clause_hierarchy("ICC_T20I_MEN_2026:21.18.2")
    assert hierarchy["clause"].clause_number == "21.18.2"
    assert hierarchy["parent"].clause_number == "21.18"

    # Cross-clause evidence regression test:
    # Verify that Clause 21.18.2 cross-references Clause 21.17, which contains the No-ball exceptions
    cross_refs = hierarchy["cross_references"]
    ref_nums = [c.clause_number for c in cross_refs]
    assert "21.17" in ref_nums

    evidence_21_17 = next(c for c in cross_refs if c.clause_number == "21.17")
    assert "Law 38 (Run out)" in evidence_21_17.original_text


def test_repository_transaction_rollback(db_session):
    repo = CricketIQRepository(db_session)
    # Attempting to insert a clause referencing a nonexistent document must fail foreign key constraint
    invalid_clause = RuleClause(
        id="NONEXISTENT:99",
        source_document_id="NONEXISTENT_DOC",
        clause_number="99",
        heading="Orphan",
        original_text="Orphan clause",
        page_start=1,
        page_end=1
    )

    with pytest.raises(Exception):
        repo.upsert_clauses([invalid_clause])

    # Ensure transaction was rolled back and session remains usable
    assert repo.get_clause("NONEXISTENT:99") is None


def test_idempotent_ingestion_with_repository(tmp_path, db_session):
    repo = CricketIQRepository(db_session)
    pipeline = IngestionPipeline(data_dir=tmp_path, repository=repo)

    actual_hash = pipeline.registry.calculate_sha256(FIXTURE_PDF)
    doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        scope_level=ScopeLevel.FORMAT_PC,
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        edition="October 2026",
        effective_from="2026-10-01",
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        file_path=str(FIXTURE_PDF),
        sha256=actual_hash,
        status=DocumentStatus.CANDIDATE
    )

    # First ingestion
    clauses1, report1 = pipeline.ingest_pdf(FIXTURE_PDF, doc)
    assert report1.status == "PASSED"
    initial_clause_count = len(repo.get_clauses_for_document(doc.id))
    assert initial_clause_count >= 6

    # Second ingestion (idempotent test)
    clauses2, report2 = pipeline.ingest_pdf(FIXTURE_PDF, doc)
    assert "idempotently" in report2.warnings[0].lower()
    second_clause_count = len(repo.get_clauses_for_document(doc.id))

    # Clause count must NOT double!
    assert second_clause_count == initial_clause_count
