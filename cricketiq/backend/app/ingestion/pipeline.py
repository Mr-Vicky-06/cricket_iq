"""Ingestion Pipeline for CricketIQ.

Coordinates document registration, extraction, hierarchical parsing, validation,
and persistence of structured rule clauses.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple, List, Optional

from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, IngestionReport, DocumentStatus
)
from cricketiq.backend.app.ingestion.document_registry import DocumentRegistry
from cricketiq.backend.app.ingestion.pdf_extractor import PDFExtractor
from cricketiq.backend.app.ingestion.clause_parser import ClauseParser
from cricketiq.backend.app.ingestion.validator import IngestionValidator


class IngestionPipeline:
    """End-to-end ingestion pipeline for an official cricket document."""

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            self.base_dir = Path(__file__).resolve().parent.parent.parent.parent
            self.data_dir = self.base_dir / "data"
        else:
            self.data_dir = Path(data_dir)

        self.processed_dir = self.data_dir / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.registry = DocumentRegistry(self.data_dir / "source_registry" / "registry.json")
        self.extractor = PDFExtractor()

    def ingest_pdf(
        self,
        pdf_path: Path,
        source_doc: SourceDocument
    ) -> Tuple[List[RuleClause], IngestionReport]:
        """Ingest an official PDF, parse clauses, validate, and persist."""
        started_at = datetime.now(timezone.utc)
        pdf_path = Path(pdf_path)

        # 1. Verify file hash against registered hash
        computed_hash = DocumentRegistry.calculate_sha256(pdf_path)
        if source_doc.sha256.lower() != computed_hash.lower():
            raise ValueError(f"Integrity check failed: expected {source_doc.sha256}, got {computed_hash}")

        # 2. Extract pages and tables
        pages = self.extractor.extract_document(pdf_path)

        # 3. Parse clauses
        parser = ClauseParser(document_id=source_doc.id)
        clauses = parser.parse_pages(pages)

        # 4. Validate
        validator = IngestionValidator(document_id=source_doc.id)
        report = validator.validate(clauses, pages, started_at)

        # 5. Persist processed clauses and report
        clauses_file = self.processed_dir / f"{source_doc.id}_clauses.json"
        with open(clauses_file, "w", encoding="utf-8") as f:
            json.dump([c.model_dump() for c in clauses], f, indent=2)

        report_file = self.processed_dir / f"{report.id}.json"
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)

        # 6. Update document status in registry
        if report.status == "FAILED":
            self.registry.update_status(source_doc.id, DocumentStatus.REJECTED)
        elif report.status == "WARNING":
            self.registry.update_status(source_doc.id, DocumentStatus.REVIEW)
        else:
            self.registry.update_status(source_doc.id, DocumentStatus.ACTIVE)

        return clauses, report
