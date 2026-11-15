"""PDF Extractor for CricketIQ.

Extracts text, layout structure, page numbers, and tables from official PDF documents
using PyMuPDF (fitz) and pdfplumber with defensive error handling.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf  # PyMuPDF
import pdfplumber


@dataclass
class PageExtraction:
    page_number: int  # 1-indexed
    text: str
    tables: List[Dict[str, Any]] = field(default_factory=list)
    char_count: int = 0
    is_empty: bool = False
    is_garbled: bool = False


class PDFExtractor:
    """Extracts text and tables with exact page mappings from official PDFs."""

    def __init__(self, min_char_threshold: int = 20):
        self.min_char_threshold = min_char_threshold

    def extract_document(self, pdf_path: Path) -> List[PageExtraction]:
        """Extract all pages from a PDF file preserving page numbers and table data."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        extracted_pages: List[PageExtraction] = []

        # PyMuPDF pass for high-fidelity text extraction
        doc = pymupdf.open(str(pdf_path))
        num_pages = len(doc)

        for page_idx in range(num_pages):
            page = doc[page_idx]
            page_num = page_idx + 1
            text = page.get_text("text") or ""
            clean_text = text.strip()

            char_count = len(clean_text)
            is_empty = char_count < self.min_char_threshold
            # Basic check for garbled/binary text
            non_printable = sum(1 for c in clean_text if not (c.isprintable() or c.isspace()))
            is_garbled = (non_printable / max(1, char_count)) > 0.15

            extracted_pages.append(
                PageExtraction(
                    page_number=page_num,
                    text=clean_text,
                    char_count=char_count,
                    is_empty=is_empty,
                    is_garbled=is_garbled
                )
            )
        doc.close()

        # pdfplumber pass for structured table extraction
        try:
            with pdfplumber.open(str(pdf_path)) as plumber_pdf:
                for idx, page in enumerate(plumber_pdf.pages):
                    if idx < len(extracted_pages):
                        tables = page.extract_tables()
                        if tables:
                            extracted_pages[idx].tables = [
                                {"table_index": t_idx, "rows": table}
                                for t_idx, table in enumerate(tables)
                            ]
        except Exception:
            # Table extraction fallback if plumber encounters complex graphics
            pass

        return extracted_pages
