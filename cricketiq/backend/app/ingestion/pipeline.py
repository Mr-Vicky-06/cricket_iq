"""Ingestion Pipeline for CricketIQ.

Coordinates document registration, secure extraction, hierarchical parsing, validation,
and transactional persistence into the structured relational repository.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List, Optional

from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, IngestionReport, DocumentStatus
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.ingestion.document_registry import DocumentRegistry
from cricketiq.backend.app.ingestion.pdf_extractor import PDFExtractor
from cricketiq.backend.app.ingestion.clause_parser import ClauseParser
from cricketiq.backend.app.ingestion.validator import IngestionValidator


class IngestionPipeline:
    """End-to-end ingestion pipeline for official cricket documents."""

    def __init__(self, data_dir: Optional[Path] = None, repository: Optional[CricketIQRepository] = None):
        if data_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.data_dir = self.base_dir / "cricketiq" / "data"
        else:
            self.data_dir = Path(data_dir)

        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.registry = DocumentRegistry(self.data_dir / "source_registry" / "registry.json")
        self.extractor = PDFExtractor()
        self.repository = repository

    def ingest_pdf(
        self,
        pdf_path: Path,
        source_doc: SourceDocument,
        force_reingest: bool = False
    ) -> Tuple[List[RuleClause], IngestionReport]:
        """Ingest an official PDF, parse clauses, validate, and persist transactionally."""
        started_at = datetime.now(timezone.utc)
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

        # 1. Verify file integrity hash
        computed_hash = DocumentRegistry.calculate_sha256(pdf_path)
        if source_doc.sha256.lower() != computed_hash.lower():
            raise ValueError(f"Integrity check failed: expected {source_doc.sha256}, got {computed_hash}")

        # 2. Idempotency Check in Repository
        if self.repository and not force_reingest:
            existing_doc = self.repository.get_document(source_doc.id)
            if existing_doc and existing_doc.sha256.lower() == computed_hash.lower():
                existing_clauses = self.repository.get_clauses_for_document(source_doc.id)
                if existing_clauses:
                    # Document already ingested idempotently
                    cached_report = IngestionReport(
                        id=f"CACHED_REPORT_{source_doc.id}",
                        source_document_id=source_doc.id,
                        started_at=started_at.isoformat(),
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        status="PASSED",
                        pages_extracted=existing_clauses[-1].page_end if existing_clauses else 0,
                        clauses_found=len(existing_clauses),
                        tables_found=0,
                        warnings=["Document already ingested and verified. Returned idempotently from repository."],
                        errors=[],
                        reviewer_notes="Idempotent repository retrieval"
                    )
                    return existing_clauses, cached_report
            elif existing_doc and existing_doc.sha256.lower() != computed_hash.lower():
                # Document hash has changed! Must create a reviewable version rather than silent overwrite
                source_doc.status = DocumentStatus.REVIEW
                source_doc.terms_notes += f" [HASH_CHANGED: Previous={existing_doc.sha256[:8]}, New={computed_hash[:8]}]"

        # 3. Extract pages and tables
        pages = self.extractor.extract_document(pdf_path)

        # 4. Parse hierarchical clauses
        parser = ClauseParser(document_id=source_doc.id)
        clauses = parser.parse_pages(pages)

        # 5. Validate integrity and hierarchy
        validator = IngestionValidator(document_id=source_doc.id)
        report = validator.validate(clauses, pages, started_at)

        # 6. Persist to disk files
        clauses_file = self.processed_dir / f"{source_doc.id}_clauses.json"
        with open(clauses_file, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in clauses], f, indent=2)

        report_file = self.processed_dir / f"{report.id}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        # 7. Update document status
        if report.status == "FAILED":
            source_doc.status = DocumentStatus.REJECTED
        elif report.status == "WARNING":
            source_doc.status = DocumentStatus.REVIEW
        else:
            source_doc.status = DocumentStatus.ACTIVE

        if source_doc.id not in self.registry._documents:
            self.registry._documents[source_doc.id] = source_doc
        self.registry.update_status(source_doc.id, source_doc.status)

        # 8. Transactional persistence into repository if configured
        if self.repository:
            if source_doc.status == DocumentStatus.ACTIVE:
                self.repository.upsert_source_document(source_doc)
                self.repository.upsert_clauses(clauses)
            else:
                # Do not expose failed or partial clauses as active in repository
                self.repository.upsert_source_document(source_doc)

        return clauses, report
