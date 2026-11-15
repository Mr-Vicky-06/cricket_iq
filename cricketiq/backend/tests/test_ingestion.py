"""Comprehensive unit and integration tests for CricketIQ Single-Source Ingestion Slice."""

from pathlib import Path
import pytest

from cricketiq.backend.app.database.models import (
    DocumentAuthority, DocumentType, CricketFormat, GenderCategory,
    DocumentStatus, ClauseType, ValidationStatus
)
from cricketiq.backend.app.ingestion.document_registry import DocumentRegistry
from cricketiq.backend.app.ingestion.pdf_extractor import PDFExtractor
from cricketiq.backend.app.ingestion.clause_parser import ClauseParser
from cricketiq.backend.app.ingestion.validator import IngestionValidator
from cricketiq.backend.app.ingestion.pipeline import IngestionPipeline

FIXTURE_PDF = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "icc" / "icc_mens_t20i_pc_2026_sample.pdf"


def test_document_registry_official_url_validation(tmp_path):
    registry = DocumentRegistry(tmp_path / "registry.json")

    # Allowed official URLs
    assert registry.is_official_url("https://www.icc-cricket.com/about/rules")
    assert registry.is_official_url("https://resources.pulse.icc-cricket.com/document.pdf")
    assert registry.is_official_url("https://www.lords.org/mcc/laws")

    # Disallowed third-party / blog URLs
    assert not registry.is_official_url("https://espncricinfo.com/rules")
    assert not registry.is_official_url("https://randomcricketblog.org/law")
    assert not registry.is_official_url("http://localhost:8000/doc.pdf")


def test_document_registry_sha256_and_registration(tmp_path):
    assert FIXTURE_PDF.exists(), f"Fixture PDF missing: {FIXTURE_PDF}"
    registry = DocumentRegistry(tmp_path / "registry.json")

    actual_hash = registry.calculate_sha256(FIXTURE_PDF)
    assert len(actual_hash) == 64

    # Register successfully
    doc = registry.register_document(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        edition="October 2026",
        effective_from="2026-10-01",
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        file_path=FIXTURE_PDF,
        sha256=actual_hash
    )

    assert doc.id == "ICC_T20I_MEN_2026"
    assert doc.sha256 == actual_hash
    assert doc.status == DocumentStatus.CANDIDATE

    # Verify reload from disk
    registry_reloaded = DocumentRegistry(tmp_path / "registry.json")
    fetched = registry_reloaded.get("ICC_T20I_MEN_2026")
    assert fetched is not None
    assert fetched.title == doc.title


def test_pdf_extractor_pages_and_content():
    extractor = PDFExtractor()
    pages = extractor.extract_document(FIXTURE_PDF)

    assert len(pages) == 2
    assert not pages[0].is_empty
    assert not pages[0].is_garbled
    assert "21 NO BALL" in pages[0].text
    assert "21.18 Free Hit" in pages[1].text


def test_clause_parser_hierarchy_and_content():
    extractor = PDFExtractor()
    pages = extractor.extract_document(FIXTURE_PDF)

    parser = ClauseParser(document_id="ICC_T20I_MEN_2026")
    clauses = parser.parse_pages(pages)

    clause_map = {c.clause_number: c for c in clauses}

    # Verify major sections
    assert "21" in clause_map
    assert clause_map["21"].parent_clause_id is None
    assert "22" in clause_map
    assert clause_map["22"].parent_clause_id is None

    # Verify sub-clauses and parent-child hierarchy
    assert "21.18" in clause_map
    assert clause_map["21.18"].parent_clause_id == "ICC_T20I_MEN_2026:21"
    assert "21.18.2" in clause_map
    assert clause_map["21.18.2"].parent_clause_id == "ICC_T20I_MEN_2026:21.18"

    # Verify verbatim clause text
    free_hit_dismissals = clause_map["21.18.2"]
    assert "striker can be dismissed only under the circumstances" in free_hit_dismissals.original_text
    assert "Law 38 (Run out)" in free_hit_dismissals.original_text

    # Verify cross-reference extraction
    assert "38" in free_hit_dismissals.cross_references
    assert "34" in free_hit_dismissals.cross_references

    # Verify clause classification
    assert free_hit_dismissals.clause_type == ClauseType.EXCEPTION


def test_ingestion_validator_passed(tmp_path):
    from datetime import datetime, timezone
    extractor = PDFExtractor()
    pages = extractor.extract_document(FIXTURE_PDF)
    parser = ClauseParser(document_id="ICC_T20I_MEN_2026")
    clauses = parser.parse_pages(pages)

    validator = IngestionValidator(document_id="ICC_T20I_MEN_2026")
    report = validator.validate(clauses, pages, started_at=datetime.now(timezone.utc))

    assert report.status == "PASSED"
    assert report.clauses_found > 5
    assert len(report.errors) == 0


def test_end_to_end_ingestion_pipeline(tmp_path):
    pipeline = IngestionPipeline(data_dir=tmp_path)

    actual_hash = DocumentRegistry.calculate_sha256(FIXTURE_PDF)
    doc = pipeline.registry.register_document(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's Twenty20 International Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        edition="October 2026",
        effective_from="2026-10-01",
        official_url="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions",
        file_path=FIXTURE_PDF,
        sha256=actual_hash
    )

    clauses, report = pipeline.ingest_pdf(FIXTURE_PDF, doc)

    assert report.status == "PASSED"
    assert len(clauses) >= 6

    # Verify processed JSON file exists
    processed_json = tmp_path / "processed" / f"{doc.id}_clauses.json"
    assert processed_json.exists()

    # Verify document status updated to active
    updated_doc = pipeline.registry.get(doc.id)
    assert updated_doc.status == DocumentStatus.ACTIVE
