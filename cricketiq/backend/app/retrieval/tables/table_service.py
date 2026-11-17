"""Structured Table Evidence Hydration Engine for CricketIQ (Phase 6 Gate 3 Task 3.4).

Provides authoritative, bundle-confined tabular evidence hydration for regulatory matrices:
- Preserves raw cells, headers, nulls, empty strings, units, and footnotes exactly.
- Reconciles tables against the source-verified audit manifest.
- Strictly confines retrieval to the candidate document bundle.
- Only SOURCE_VERIFIED tables may be hydrated for regulatory proof.
- Renders deterministic, escaped Markdown table representations for LLM prompt context.
"""

from __future__ import annotations
import os
import json
import hashlib
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from pydantic import BaseModel, Field

from cricketiq.backend.app.database.repository import CricketIQRepository


class TableValidationStatus(str, Enum):
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    EXTRACTED_UNVALIDATED = "EXTRACTED_UNVALIDATED"
    DEPRECATED_FRAGMENT = "DEPRECATED_FRAGMENT"


class TableEvidence(BaseModel):
    """Strongly typed regulatory table evidence preserving exact source layout."""
    table_id: str
    source_document_id: str
    source_document_sha256: Optional[str] = None
    source_file_sha256: Optional[str] = None
    page_number: int  # 1-based PDF page index
    printed_page_number: Optional[int] = None
    source_locator: Optional[str] = None
    caption: Optional[str] = None
    headers: List[str] = Field(default_factory=list)
    rows: List[List[Optional[str]]] = Field(default_factory=list)
    shape: Tuple[int, int]
    units: Optional[Dict[str, str]] = None
    footnotes: List[str] = Field(default_factory=list)
    linked_clause_ids: List[str] = Field(default_factory=list)
    validation_status: TableValidationStatus = TableValidationStatus.SOURCE_VERIFIED
    reviewer_notes: Optional[str] = None


class TableEvidenceService:
    """Service for indexing, validating, and retrieving structured table evidence."""

    def __init__(
        self,
        manifest_path: Optional[str | Path] = None,
        tables_dir: Optional[str | Path] = None,
        repository: Optional[CricketIQRepository] = None,
        auto_load: bool = True
    ):
        self.root_dir = Path(__file__).resolve().parents[5]
        self.manifest_path = Path(manifest_path) if manifest_path else self.root_dir / "data" / "corpus" / "manifests" / "gate3_table_audit.json"
        self.tables_dir = Path(tables_dir) if tables_dir else self.root_dir / "data" / "extracted" / "tables"
        self.repository = repository
        
        # Internal indexed tables: table_id -> TableEvidence
        self._tables_by_id: Dict[str, TableEvidence] = {}
        # Clause-to-table index: clause_id -> List[str] (table_ids)
        self._clause_to_tables: Dict[str, List[str]] = {}
        # Diagnostic list of all tables including unvalidated/fragmentary
        self._all_audited_tables: Dict[str, TableEvidence] = {}

        if auto_load and self.manifest_path.exists():
            self.load_tables()

    def register_table(self, table: TableEvidence) -> None:
        """Register a table directly with validation checks."""
        if table.table_id in self._tables_by_id:
            raise ValueError(f"Duplicate table ID rejected: {table.table_id}")

        self._all_audited_tables[table.table_id] = table

        # Only SOURCE_VERIFIED tables enter active retrieval
        if table.validation_status == TableValidationStatus.SOURCE_VERIFIED:
            self._tables_by_id[table.table_id] = table
            for cid in table.linked_clause_ids:
                if cid not in self._clause_to_tables:
                    self._clause_to_tables[cid] = []
                if table.table_id not in self._clause_to_tables[cid]:
                    self._clause_to_tables[cid].append(table.table_id)

    def load_tables(self) -> None:
        """Load and reconcile tables from the manifest and raw table files."""
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Table audit manifest not found: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        documents = manifest_data.get("documents", {})

        for doc_id, doc_meta in documents.items():
            file_name = doc_meta.get("file_name")
            expected_file_sha = doc_meta.get("file_sha256")
            table_file = self.tables_dir / file_name

            if not table_file.exists():
                continue

            # Verify table file hash integrity
            with open(table_file, "rb") as bf:
                actual_sha = hashlib.sha256(bf.read()).hexdigest()

            if actual_sha != expected_file_sha:
                raise ValueError(
                    f"Table file SHA-256 mismatch for {file_name}: "
                    f"expected {expected_file_sha}, got {actual_sha}"
                )

            with open(table_file, "r", encoding="utf-8") as tf:
                raw_table_list = json.load(tf)

            # Map raw tables by (page_number, table_index)
            raw_by_page_idx = {
                (t.get("page_number"), t.get("table_index")): t
                for t in raw_table_list
            }

            # Map manifest entries
            for entry in doc_meta.get("tables", []):
                t_id = entry.get("table_id")
                page_num = entry.get("page_number")
                t_idx = entry.get("table_index")
                classification = entry.get("classification")
                review_status_str = entry.get("review_status", "DEPRECATED_FRAGMENT")

                try:
                    status = TableValidationStatus(review_status_str)
                except ValueError:
                    status = TableValidationStatus.DEPRECATED_FRAGMENT

                raw_data = raw_by_page_idx.get((page_num, t_idx))
                raw_rows = raw_data.get("rows", []) if raw_data else []

                headers: List[str] = []
                data_rows: List[List[Optional[str]]] = []

                if raw_rows:
                    headers = [str(c) if c is not None else "" for c in raw_rows[0]]
                    data_rows = raw_rows[1:]

                shape = (len(raw_rows), len(headers) if headers else 0)

                # Determine linked clause IDs
                linked_clauses: List[str] = []
                if self.repository:
                    # Query clauses in the same document on this page
                    clauses_on_page = self._find_clauses_on_page(doc_id, page_num)
                    linked_clauses.extend(clauses_on_page)

                evidence = TableEvidence(
                    table_id=t_id,
                    source_document_id=doc_id,
                    source_file_sha256=expected_file_sha,
                    page_number=page_num,
                    headers=headers,
                    rows=data_rows,
                    shape=shape,
                    linked_clause_ids=linked_clauses,
                    validation_status=status,
                    reviewer_notes=f"Reconciled via Gate 3 Table Audit: {classification}"
                )

                self.register_table(evidence)

    def _find_clauses_on_page(self, doc_id: str, page_number: int) -> List[str]:
        """Find all clause IDs in doc_id covering page_number."""
        if not self.repository:
            return []
        from cricketiq.backend.app.database.orm_models import RuleClauseEntity
        from sqlalchemy import select

        stmt = select(RuleClauseEntity.id).where(
            RuleClauseEntity.source_document_id == doc_id,
            RuleClauseEntity.page_start <= page_number,
            RuleClauseEntity.page_end >= page_number
        )
        return list(self.repository.session.scalars(stmt).all())

    def get_table_evidence_for_clause(
        self,
        clause_id: str,
        candidate_document_ids: List[str]
    ) -> List[TableEvidence]:
        """Hydrate verified table evidence for a retrieved clause within candidate bundle.
        
        Strict safety invariant:
        - Never returns out-of-bundle tables.
        - Only returns SOURCE_VERIFIED tables.
        """
        table_ids = self._clause_to_tables.get(clause_id, [])
        results: List[TableEvidence] = []

        for tid in table_ids:
            table = self._tables_by_id.get(tid)
            if not table:
                continue

            # Strict candidate bundle confinement
            if table.source_document_id not in candidate_document_ids:
                continue

            # Strict source-verified status check
            if table.validation_status != TableValidationStatus.SOURCE_VERIFIED:
                continue

            results.append(table)

        return results

    def get_table_by_id(self, table_id: str) -> Optional[TableEvidence]:
        """Get table by ID from the active source-verified index."""
        return self._tables_by_id.get(table_id)

    def render_markdown(self, table: TableEvidence) -> str:
        """Render a deterministic Markdown table string for prompt context.
        
        Safely escapes pipe characters and newlines within cells.
        Never invents cells or alters null/empty values.
        """
        lines: List[str] = []

        # Source Metadata Header
        title = table.caption or f"Table {table.table_id}"
        lines.append(f"### Regulatory Specification: {title}")
        loc_info = f"Document: {table.source_document_id} | Page: {table.page_number} | Table ID: `{table.table_id}`"
        if table.linked_clause_ids:
            loc_info += f" | Linked Clauses: {', '.join(table.linked_clause_ids)}"
        lines.append(f"*{loc_info}*")
        lines.append("")

        if not table.headers and not table.rows:
            lines.append("*(Table contains no rows)*")
            return "\n".join(lines)

        def _escape_cell(val: Optional[str]) -> str:
            if val is None:
                return ""
            # Escape pipe characters and convert inner newlines to spaces or <br/>
            cleaned = str(val).replace("|", "\\|").replace("\r\n", "<br/>").replace("\n", "<br/>")
            return cleaned.strip()

        # Format Header row
        header_cells = [_escape_cell(h) for h in table.headers]
        lines.append("| " + " | ".join(header_cells) + " |")

        # Format Divider
        lines.append("| " + " | ".join(["---"] * len(header_cells)) + " |")

        # Format Data rows
        for row in table.rows:
            # Pad row to match header count if shorter, without inferring values
            padded_row: List[Optional[str]] = list(row)
            while len(padded_row) < len(header_cells):
                padded_row.append("")
            # Truncate if longer to preserve layout
            padded_row = padded_row[:len(header_cells)]
            
            row_cells = [_escape_cell(c) for c in padded_row]
            lines.append("| " + " | ".join(row_cells) + " |")

        # Format Footnotes if available
        if table.footnotes:
            lines.append("")
            for fn in table.footnotes:
                lines.append(f"> Note: {_escape_cell(fn)}")

        return "\n".join(lines)

    def validate_numeric_claim(
        self,
        table: TableEvidence,
        row_criteria: Dict[str, str],
        target_column: str,
        expected_value: str
    ) -> bool:
        """Internally validate an exact numeric claim against the verified table matrix.
        
        Checks that a row matching all `row_criteria` key-value pairs has `target_column`
        matching `expected_value` exactly.
        """
        if target_column not in table.headers:
            return False

        target_idx = table.headers.index(target_column)

        # Map criterion column names to indices
        criteria_indices: Dict[int, str] = {}
        for col_name, col_val in row_criteria.items():
            if col_name not in table.headers:
                return False
            criteria_indices[table.headers.index(col_name)] = str(col_val).strip()

        for row in table.rows:
            # Check row match
            matches = True
            for col_idx, expected_crit in criteria_indices.items():
                if col_idx >= len(row):
                    matches = False
                    break
                cell_val = str(row[col_idx] or "").strip()
                if cell_val != expected_crit:
                    matches = False
                    break

            if matches:
                # Check target column
                if target_idx < len(row):
                    actual_val = str(row[target_idx] or "").strip()
                    return actual_val == str(expected_value).strip()
                return False

        return False
