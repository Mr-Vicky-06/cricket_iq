"""Clause Parser for CricketIQ.

Parses hierarchical clauses from page-extracted text of MCC Laws and ICC Playing Conditions,
preserving parent-child hierarchy, verbatim text, page locators, and cross-references.
"""

from __future__ import annotations
import re
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from cricketiq.backend.app.database.models import (
    RuleClause, ClauseType, ValidationStatus
)
from cricketiq.backend.app.ingestion.pdf_extractor import PageExtraction

# Regex patterns for cricket clause numbering
# Examples: "21. No Ball", "LAW 21 NO BALL", "21.18 Free Hit", "21.18.2 For any free hit..."
MAJOR_SECTION_RE = re.compile(
    r"^(?:LAW\s+)?([0-9]{1,2})\.?\s+([A-Z][A-Za-z0-9\s,\-–'\(\)]+)$",
    re.IGNORECASE
)
SUB_CLAUSE_HEADER_RE = re.compile(
    r"^([0-9]{1,2}\.[0-9]{1,2}(?:\.[0-9]{1,2}){0,2})\s+([A-Z][A-Za-z0-9\s,\-–'\(\)]+)$"
)
SUB_CLAUSE_INLINE_RE = re.compile(
    r"^([0-9]{1,2}\.[0-9]{1,2}(?:\.[0-9]{1,2}){0,2})\s+(.+)$"
)
STANDALONE_CLAUSE_RE = re.compile(
    r"^([0-9]{1,2}(?:\.[0-9]{1,2}){1,3})\s*$"
)
APPENDIX_HEADER_RE = re.compile(
    r"^APPENDIX\s+([A-Z])(?:\s*[:–\-]\s*.*)?$",
    re.IGNORECASE
)
CROSS_REF_RE = re.compile(
    r"(?:clause|law|clauses|laws)\s+([0-9]{1,2}(?:\.[0-9]{1,2}(?:\.[0-9]{1,2})?)?)",
    re.IGNORECASE
)
UNITS_RE = re.compile(
    r"^(?:ounces?|grams?|inches?|centimetres?|cm|mm|kg|g|m|yards?|yd|degrees?|deg|\%|percent)\b",
    re.IGNORECASE
)


class ClauseParser:
    """Parses hierarchical cricket rule clauses from extracted page text."""

    def __init__(self, document_id: str):
        self.document_id = document_id

    def parse_pages(self, pages: List[PageExtraction]) -> List[RuleClause]:
        """Parse structured RuleClause items from sequential pages."""
        clauses: List[RuleClause] = []

        current_major_num: Optional[str] = None
        current_major_heading: str = ""
        current_clause_num: Optional[str] = None
        current_heading: str = ""
        current_lines: List[str] = []
        current_page_start: int = 1
        current_page_end: int = 1
        current_appendix: Optional[str] = None

        def flush_current():
            nonlocal current_clause_num, current_heading, current_lines, current_page_start, current_page_end, current_appendix
            if current_clause_num and current_lines:
                full_text = "\n".join(current_lines).strip()
                if full_text:
                    if current_appendix:
                        eff_num = f"APP_{current_appendix}:{current_clause_num}"
                        clause_id = f"{self.document_id}:{eff_num}"
                        parent_id = f"{self.document_id}:APP_{current_appendix}"
                    else:
                        eff_num = current_clause_num
                        clause_id = f"{self.document_id}:{current_clause_num}"
                        parent_id = self._compute_parent_id(current_clause_num, current_major_num)

                    clause_type = self._classify_clause(current_heading, full_text)
                    cross_refs = self._extract_cross_refs(full_text)

                    clauses.append(
                        RuleClause(
                            id=clause_id,
                            source_document_id=self.document_id,
                            clause_number=eff_num,
                            parent_clause_id=parent_id,
                            heading=current_heading or current_major_heading or f"Clause {eff_num}",
                            original_text=full_text,
                            normalized_text=self._normalize_text(full_text),
                            page_start=current_page_start,
                            page_end=current_page_end,
                            clause_type=clause_type,
                            cross_references=cross_refs,
                            validation_status=ValidationStatus.UNCHECKED
                        )
                    )
            current_lines = []

        for page in pages:
            # Exclude back index in MCC_LAWS_2026 (pages 167-178 are the alphabetical Index)
            if self.document_id == "MCC_LAWS_2026" and page.page_number >= 167:
                continue

            raw_lines = [ln.strip() for ln in page.text.split("\n") if ln.strip()]

            for line in raw_lines:
                # Filter out Devanagari (Hindi) lines in MCC_LAWS_2022 Diglot edition
                if self.document_id == "MCC_LAWS_2022" and any("\u0900" <= c <= "\u097f" for c in line):
                    continue

                clean_line = line.replace("\u202f", " ").replace("\xa0", " ").strip()

                # Check for Appendix header, e.g. "APPENDIX A: DEFINITIONS" or "APPENDIX D: DECISION"
                app_match = APPENDIX_HEADER_RE.match(clean_line)
                if app_match:
                    flush_current()
                    current_appendix = app_match.group(1).upper()
                    current_major_num = None
                    current_major_heading = f"Appendix {current_appendix}"
                    app_parent_id = f"{self.document_id}:APP_{current_appendix}"
                    clauses.append(
                        RuleClause(
                            id=app_parent_id,
                            source_document_id=self.document_id,
                            clause_number=f"APP_{current_appendix}",
                            parent_clause_id=None,
                            heading=clean_line,
                            original_text=clean_line,
                            normalized_text=clean_line.lower(),
                            page_start=page.page_number,
                            page_end=page.page_number,
                            clause_type=ClauseType.RULE,
                            cross_references=[],
                            validation_status=ValidationStatus.UNCHECKED
                        )
                    )
                    continue

                # Check for major section / Law header, e.g. "21 No Ball" or "LAW 21 NO BALL"
                major_match = MAJOR_SECTION_RE.match(clean_line)
                if major_match and not ("." in major_match.group(1)) and not current_appendix:
                    major_val = int(major_match.group(1))
                    if 1 <= major_val <= 42:
                        flush_current()
                        current_major_num = major_match.group(1)
                        current_major_heading = major_match.group(2).strip()

                        # Register the major section as a parent clause itself
                        major_clause_id = f"{self.document_id}:{current_major_num}"
                        clauses.append(
                            RuleClause(
                                id=major_clause_id,
                                source_document_id=self.document_id,
                                clause_number=current_major_num,
                                parent_clause_id=None,
                                heading=current_major_heading,
                                original_text=f"{current_major_num}. {current_major_heading}",
                                normalized_text=current_major_heading.lower(),
                                page_start=page.page_number,
                                page_end=page.page_number,
                                clause_type=ClauseType.RULE,
                                cross_references=[],
                                validation_status=ValidationStatus.UNCHECKED
                            )
                        )
                        continue

                # Check for standalone clause number line, e.g. "5.1\t" or "21.18.3.1"
                standalone_match = STANDALONE_CLAUSE_RE.match(clean_line)
                if standalone_match and self._is_valid_clause_start(standalone_match.group(1)):
                    flush_current()
                    current_clause_num = standalone_match.group(1)
                    current_heading = f"Clause {current_clause_num}"
                    current_page_start = page.page_number
                    current_page_end = page.page_number
                    current_lines = [clean_line]
                    continue

                # Check for sub-clause header, e.g. "21.18 Free Hit"
                sub_header_match = SUB_CLAUSE_HEADER_RE.match(clean_line)
                if sub_header_match and self._is_valid_clause_start(sub_header_match.group(1), sub_header_match.group(2)):
                    flush_current()
                    current_clause_num = sub_header_match.group(1)
                    current_heading = sub_header_match.group(2).strip()
                    current_page_start = page.page_number
                    current_page_end = page.page_number
                    current_lines = [clean_line]
                    continue

                # Check for inline clause, e.g. "21.18.2 For any free hit, the striker can..."
                inline_match = SUB_CLAUSE_INLINE_RE.match(clean_line)
                if inline_match and self._is_valid_clause_start(inline_match.group(1), inline_match.group(2)):
                    flush_current()
                    current_clause_num = inline_match.group(1)
                    body_text = inline_match.group(2).strip()
                    current_heading = current_heading or f"Clause {current_clause_num}"
                    current_page_start = page.page_number
                    current_page_end = page.page_number
                    current_lines = [clean_line]
                    continue

                # If current_lines has only the standalone clause number, check if this line is a short heading
                if current_clause_num and len(current_lines) == 1 and current_lines[0] == current_clause_num:
                    if len(clean_line) < 60 and not clean_line.endswith("."):
                        current_heading = clean_line
                        current_lines.append(clean_line)
                        continue

                # Continuation line
                if current_clause_num:
                    current_lines.append(clean_line)
                    current_page_end = page.page_number

        flush_current()
        return clauses

    def _is_valid_clause_start(self, num_str: str, body_text: str = "") -> bool:
        parts = num_str.split(".")
        if not (all(p.isdigit() for p in parts) and len(parts) in (2, 3, 4)):
            return False
        # Major law number must be 1..42
        major = int(parts[0])
        if major < 1 or major > 42:
            return False
        # Reject lines where the following token is a measurement unit
        if body_text:
            tokens = body_text.strip().split()
            if tokens and UNITS_RE.match(tokens[0]):
                return False
        return True

    def _compute_parent_id(self, clause_num: str, major_num: Optional[str]) -> Optional[str]:
        parts = clause_num.split(".")
        if len(parts) == 4:
            return f"{self.document_id}:{parts[0]}.{parts[1]}.{parts[2]}"
        elif len(parts) == 3:
            return f"{self.document_id}:{parts[0]}.{parts[1]}"
        elif len(parts) == 2:
            return f"{self.document_id}:{parts[0]}"
        elif major_num and major_num != clause_num:
            return f"{self.document_id}:{major_num}"
        return None

    def _classify_clause(self, heading: str, text: str) -> ClauseType:
        combined = f"{heading} {text}".lower()
        if any(term in combined for term in ["penalty", "5 penalty runs", "penalty for a wide"]):
            return ClauseType.PENALTY
        if any(term in combined for term in ["exception", "saving that", "only under the circumstances", "shall not apply"]):
            return ClauseType.EXCEPTION
        if any(term in combined for term in ["is defined as", "means", "for the purpose of this clause"]):
            return ClauseType.DEFINITION
        if any(term in combined for term in ["procedure", "umpire shall signal", "consultation", "call and signal"]):
            return ClauseType.PROCEDURE
        return ClauseType.RULE

    def _extract_cross_refs(self, text: str) -> List[str]:
        matches = CROSS_REF_RE.findall(text)
        # Deduplicate and sort
        return sorted(list(set(matches)))

    def _normalize_text(self, text: str) -> str:
        # Lowercase, clean up extra spaces for search index
        clean = " ".join(text.split()).lower()
        return clean
