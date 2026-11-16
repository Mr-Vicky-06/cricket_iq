#!/usr/bin/env python3
"""Full Corpus Document Extraction & Clause Parsing Pipeline for CricketIQ.

Processes all documents registered in data/sources/manifests/raw_manifest.json:
- Extracts page text via PyMuPDF
- Extracts structured tables via pdfplumber
- Parses hierarchical RuleClauses
- Audits extraction quality via IngestionValidator
- Writes page_text, layout_json, tables, extraction_reports, and clauses
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from cricketiq.backend.app.ingestion.pdf_extractor import PDFExtractor
from cricketiq.backend.app.ingestion.clause_parser import ClauseParser
from cricketiq.backend.app.ingestion.validator import IngestionValidator

def main():
    manifest_path = root_dir / "data" / "sources" / "manifests" / "raw_manifest.json"
    if not manifest_path.exists():
        print(f"Error: manifest not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Ensure output directories exist
    pages_dir = root_dir / "data" / "extracted" / "page_text"
    layout_dir = root_dir / "data" / "extracted" / "layout_json"
    tables_dir = root_dir / "data" / "extracted" / "tables"
    reports_dir = root_dir / "data" / "extracted" / "extraction_reports"
    clauses_dir = root_dir / "data" / "corpus" / "clauses"

    for d in [pages_dir, layout_dir, tables_dir, reports_dir, clauses_dir]:
        d.mkdir(parents=True, exist_ok=True)

    extractor = PDFExtractor()
    summary = []

    print(f"Starting extraction for {len(manifest)} documents...\n")

    for item in manifest:
        doc_id = item["source_document_id"]
        pdf_path = root_dir / item["relative_path"]
        print(f"Processing {doc_id} ({pdf_path.name})...")

        if not pdf_path.exists():
            print(f"  -> ERROR: File not found: {pdf_path}")
            continue

        started_at = datetime.now(timezone.utc)

        # 1. Page & Table Extraction
        pages = extractor.extract_document(pdf_path)

        # Save page text JSON
        pages_payload = [
            {
                "page_number": p.page_number,
                "char_count": p.char_count,
                "is_empty": p.is_empty,
                "is_garbled": p.is_garbled,
                "text": p.text
            }
            for p in pages
        ]
        with open(pages_dir / f"{doc_id}_pages.json", "w", encoding="utf-8") as f:
            json.dump(pages_payload, f, indent=2)

        # Save layout JSON
        layout_payload = {
            "source_document_id": doc_id,
            "total_pages": len(pages),
            "pages": [
                {
                    "page_number": p.page_number,
                    "char_count": p.char_count,
                    "table_count": len(p.tables),
                    "status": "garbled" if p.is_garbled else ("empty" if p.is_empty else "valid")
                }
                for p in pages
            ]
        }
        with open(layout_dir / f"{doc_id}_layout.json", "w", encoding="utf-8") as f:
            json.dump(layout_payload, f, indent=2)

        # Save tables JSON
        all_tables = []
        for p in pages:
            for t in p.tables:
                all_tables.append({
                    "page_number": p.page_number,
                    "table_index": t.get("table_index", 0),
                    "rows": t.get("rows", [])
                })
        with open(tables_dir / f"{doc_id}_tables.json", "w", encoding="utf-8") as f:
            json.dump(all_tables, f, indent=2)

        # 2. Clause Parsing
        parser = ClauseParser(document_id=doc_id)
        clauses = parser.parse_pages(pages)

        # Save clauses JSON
        clauses_payload = [c.model_dump(mode="json") for c in clauses]
        with open(clauses_dir / f"{doc_id}_clauses.json", "w", encoding="utf-8") as f:
            json.dump(clauses_payload, f, indent=2)

        # 3. Validation & Quality Report
        validator = IngestionValidator(document_id=doc_id)
        report = validator.validate(clauses, pages, started_at=started_at)

        report_payload = {
            "report_id": report.id,
            "source_document_id": doc_id,
            "status": report.status,
            "started_at": report.started_at,
            "completed_at": report.completed_at,
            "pages_extracted": report.pages_extracted,
            "clauses_found": report.clauses_found,
            "tables_found": report.tables_found,
            "warnings_count": len(report.warnings),
            "errors_count": len(report.errors),
            "warnings": report.warnings,
            "errors": report.errors
        }
        with open(reports_dir / f"{doc_id}_report.json", "w", encoding="utf-8") as f:
            json.dump(report_payload, f, indent=2)

        summary.append({
            "source_document_id": doc_id,
            "pages": len(pages),
            "clauses": len(clauses),
            "tables": len(all_tables),
            "status": report.status,
            "warnings": len(report.warnings),
            "errors": len(report.errors)
        })

        print(f"  -> DONE: {len(pages)} pages, {len(clauses)} clauses, {len(all_tables)} tables. Status: {report.status}")

    # Write unified extraction summary
    with open(root_dir / "data" / "extracted" / "extraction_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nAll {len(summary)} documents processed successfully!")

if __name__ == "__main__":
    main()
