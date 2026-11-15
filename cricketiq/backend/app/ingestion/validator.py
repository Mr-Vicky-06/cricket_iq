"""Ingestion Validator for CricketIQ.

Performs rigorous diagnostics on extracted clauses to ensure completeness,
integrity of hierarchy, preservation of verbatim text, and absence of garbled content.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Set
from pathlib import Path

from cricketiq.backend.app.database.models import (
    RuleClause, IngestionReport, ValidationStatus
)
from cricketiq.backend.app.ingestion.pdf_extractor import PageExtraction


class IngestionValidator:
    """Validates extracted clauses and generates audit reports."""

    def __init__(self, document_id: str):
        self.document_id = document_id

    def validate(
        self,
        clauses: List[RuleClause],
        pages: List[PageExtraction],
        started_at: datetime
    ) -> IngestionReport:
        warnings: List[str] = []
        errors: List[str] = []

        completed_at = datetime.now(timezone.utc)
        clause_ids: Set[str] = {c.id for c in clauses}

        if not pages:
            errors.append("No pages were extracted from the document.")

        if not clauses:
            errors.append("Zero clauses were parsed from the document.")

        # Check pages
        empty_pages = [p.page_number for p in pages if p.is_empty]
        if empty_pages:
            warnings.append(f"Pages detected as empty or below threshold: {empty_pages}")

        garbled_pages = [p.page_number for p in pages if p.is_garbled]
        if garbled_pages:
            errors.append(f"Pages detected with high non-printable/garbled content: {garbled_pages}")

        # Check clauses
        for clause in clauses:
            # Check empty text
            if not clause.original_text.strip():
                errors.append(f"Clause {clause.id} has empty original text.")
                clause.validation_status = ValidationStatus.REJECTED
                continue

            # Check parent integrity
            if clause.parent_clause_id and clause.parent_clause_id not in clause_ids:
                warnings.append(
                    f"Clause {clause.id} references parent {clause.parent_clause_id} which was not explicitly parsed as a separate clause."
                )

            # Check page numbers
            if clause.page_start < 1 or clause.page_end < clause.page_start:
                errors.append(f"Clause {clause.id} has invalid page range: {clause.page_start}-{clause.page_end}")
                clause.validation_status = ValidationStatus.REJECTED
                continue

            # Mark as validated if no critical errors
            clause.validation_status = ValidationStatus.VALIDATED

        status = "FAILED" if errors else ("WARNING" if warnings else "PASSED")

        total_tables = sum(len(p.tables) for p in pages)

        report = IngestionReport(
            id=f"REPORT_{self.document_id}_{int(started_at.timestamp())}",
            source_document_id=self.document_id,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            status=status,
            pages_extracted=len(pages),
            clauses_found=len(clauses),
            tables_found=total_tables,
            warnings=warnings,
            errors=errors,
            reviewer_notes="Automated extraction audit"
        )

        return report
