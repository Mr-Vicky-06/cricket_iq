"""Multi-View Text Normalization and Segmentation Engine for CricketIQ.

Implements the multi-view text pipeline defined in Section 6 of the Pre-Phase 4 Master Directive:
1. original_text: Verbatim immutable extracted text.
2. normalized_text: Conservative typographic normalization preserving legal meaning and hyphens.
3. lexical_text: Prepared for FTS5/BM25 indexing, retaining compound variants and negation.
4. embedding_text: Versioned contextual template encoding regulatory authority and format hierarchy.
5. sentence_segments: Precise sentence-level boundaries respecting cricket abbreviations.
6. chunk_text: Structured retrieval chunk with parent context and role metadata.
7. display_text: Citation-compliant user-facing presentation.
"""

from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


PIPELINE_VERSION = "1.0.0"
NORMALIZATION_VERSION = "v1"
EMBEDDING_TEMPLATE_VERSION = "v1"

# Cricket hyphenated compound terms that must have both hyphenated and split forms in lexical search
CRICKET_COMPOUND_TERMS = [
    ("no-ball", "no ball"),
    ("free-hit", "free hit"),
    ("wide-ball", "wide ball"),
    ("dead-ball", "dead ball"),
    ("run-out", "run out"),
    ("short-pitch", "short pitch"),
    ("short-pitched", "short pitched"),
    ("full-pitch", "full pitch"),
    ("full-pitched", "full pitched"),
    ("hit-wicket", "hit wicket"),
    ("leg-bye", "leg bye"),
    ("power-play", "power play"),
    ("wicket-keeper", "wicket keeper"),
    ("wicket-keeping", "wicket keeping"),
    ("non-striker", "non striker"),
    ("over-rate", "over rate"),
]

# Common abbreviations to prevent false sentence boundaries
ABBREVIATIONS = {
    "e.g.", "i.e.", "no.", "cl.", "dr.", "mr.", "mrs.", "ms.",
    "etc.", "vs.", "v.", "approx.", "fig.", "ref.", "vol.", "oz.", "lb."
}


@dataclass
class SentenceSegment:
    sentence_index: int
    text: str
    char_start: int
    char_end: int


@dataclass
class ClauseChunk:
    chunk_id: str
    source_document_id: str
    clause_id: str
    parent_clause_id: Optional[str]
    role: str
    chunk_text: str
    token_count_estimate: int


@dataclass
class MultiViewTextRecord:
    clause_id: str
    source_document_id: str
    clause_number: str
    pipeline_version: str
    normalization_version: str
    source_text_hash: str
    original_text: str
    normalized_text: str
    lexical_text: str
    embedding_text: str
    sentence_segments: List[Dict[str, Any]]
    chunks: List[Dict[str, Any]]
    display_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clause_id": self.clause_id,
            "source_document_id": self.source_document_id,
            "clause_number": self.clause_number,
            "pipeline_version": self.pipeline_version,
            "normalization_version": self.normalization_version,
            "source_text_hash": self.source_text_hash,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "lexical_text": self.lexical_text,
            "embedding_text": self.embedding_text,
            "sentence_segments": self.sentence_segments,
            "chunks": self.chunks,
            "display_text": self.display_text,
        }


class TextNormalizer:
    """Produces the 7 canonical text views for a rule clause."""

    def __init__(self, normalization_version: str = NORMALIZATION_VERSION):
        self.normalization_version = normalization_version

    def build_views(
        self,
        clause_id: str,
        source_document_id: str,
        clause_number: str,
        heading: str,
        original_text: str,
        authority: str = "ICC",
        document_title: str = "Playing Conditions",
        edition: str = "October 2026",
        page_start: int = 1,
        parent_clause_id: Optional[str] = None,
        parent_clause_text: Optional[str] = None,
        clause_type: str = "RULE"
    ) -> MultiViewTextRecord:
        """Construct all seven representations from raw extracted text."""
        # 1. Original text (immutable)
        raw_text = original_text

        # 2. Source text hash
        source_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

        # 3. Normalized text (conservative typographic cleanup)
        norm_text = self.normalize_text(raw_text)

        # 4. Lexical text (for FTS5 / BM25 search)
        lex_text = self.build_lexical_text(norm_text, clause_number, heading)

        # 5. Embedding text (contextualized for dense retrieval)
        emb_text = self.build_embedding_text(
            authority=authority,
            document_title=document_title,
            edition=edition,
            clause_number=clause_number,
            heading=heading,
            normalized_body=norm_text
        )

        # 6. Sentence segments
        sentences = self.segment_sentences(norm_text)
        sentence_dicts = [
            {
                "sentence_index": s.sentence_index,
                "text": s.text,
                "char_start": s.char_start,
                "char_end": s.char_end,
            }
            for s in sentences
        ]

        # 7. Chunk representation
        chunks = self.build_chunks(
            clause_id=clause_id,
            source_document_id=source_document_id,
            clause_number=clause_number,
            heading=heading,
            normalized_body=norm_text,
            parent_clause_id=parent_clause_id,
            parent_clause_text=parent_clause_text,
            clause_type=clause_type
        )
        chunk_dicts = [
            {
                "chunk_id": c.chunk_id,
                "parent_clause_id": c.parent_clause_id,
                "role": c.role,
                "chunk_text": c.chunk_text,
                "token_count_estimate": c.token_count_estimate,
            }
            for c in chunks
        ]

        # 8. Display text (citation-compliant output)
        disp_text = self.build_display_text(
            original_text=raw_text,
            authority=authority,
            document_title=document_title,
            clause_number=clause_number,
            page_start=page_start
        )

        return MultiViewTextRecord(
            clause_id=clause_id,
            source_document_id=source_document_id,
            clause_number=clause_number,
            pipeline_version=PIPELINE_VERSION,
            normalization_version=self.normalization_version,
            source_text_hash=source_hash,
            original_text=raw_text,
            normalized_text=norm_text,
            lexical_text=lex_text,
            embedding_text=emb_text,
            sentence_segments=sentence_dicts,
            chunks=chunk_dicts,
            display_text=disp_text
        )

    def normalize_text(self, text: str) -> str:
        """Conservative normalization preserving legal modal verbs, negation, and hyphens."""
        if not text:
            return ""

        # Normalize line endings
        t = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace non-breaking spaces with standard spaces
        t = t.replace("\u202f", " ").replace("\xa0", " ")

        # Normalize multiple spaces per line while preserving single newlines
        lines = []
        for line in t.split("\n"):
            clean_line = " ".join(line.split())
            if clean_line:
                lines.append(clean_line)

        return "\n".join(lines).strip()

    def build_lexical_text(self, normalized_text: str, clause_number: str, heading: str) -> str:
        """Create search-ready lexical text expanding compound terms without losing negation."""
        lower_text = normalized_text.lower()

        # Add explicit clause and Law search tokens
        prefix_tokens = [f"clause {clause_number}", clause_number]
        if "." in clause_number:
            major_num = clause_number.split(".")[0]
            prefix_tokens.append(f"law {major_num}")

        # Expand compound cricket terms
        expanded_body = lower_text
        for hyp_term, space_term in CRICKET_COMPOUND_TERMS:
            if hyp_term in expanded_body and space_term not in expanded_body:
                expanded_body = expanded_body.replace(hyp_term, f"{hyp_term} {space_term}")
            elif space_term in expanded_body and hyp_term not in expanded_body:
                expanded_body = expanded_body.replace(space_term, f"{space_term} {hyp_term}")

        combined = f"{' '.join(prefix_tokens)} {heading.lower()} {expanded_body}"
        return " ".join(combined.split())

    def build_embedding_text(
        self,
        authority: str,
        document_title: str,
        edition: str,
        clause_number: str,
        heading: str,
        normalized_body: str
    ) -> str:
        """Versioned embedding input template encoding document hierarchy and clause identity."""
        # Clean heading
        clean_heading = heading.strip()
        if not clean_heading or clean_heading == f"Clause {clause_number}":
            header_part = f"Clause {clause_number}"
        else:
            header_part = f"Clause {clause_number} ({clean_heading})"

        return f"[{authority} {document_title} | {edition}] {header_part}: {normalized_body}"

    def segment_sentences(self, text: str) -> List[SentenceSegment]:
        """Precise sentence boundary detection respecting cricket abbreviations."""
        if not text:
            return []

        segments: List[SentenceSegment] = []
        # Pattern for candidate sentence endings: period, question mark, or exclamation mark followed by space or newline
        sentence_end_re = re.compile(r'([\.\?!])(\s+|$)')

        start = 0
        current_idx = 0

        for match in sentence_end_re.finditer(text):
            punct_pos = match.start(1)
            end_pos = match.end()

            # Inspect preceding word to check if it's an abbreviation
            preceding_text = text[start:punct_pos + 1].strip()
            last_word = preceding_text.split()[-1].lower() if preceding_text.split() else ""

            if last_word in ABBREVIATIONS:
                # Do not split on known abbreviations
                continue

            # Check if this period is part of a decimal or clause number (e.g. "21.18.2")
            if punct_pos > 0 and punct_pos + 1 < len(text):
                if text[punct_pos - 1].isdigit() and text[punct_pos + 1].isdigit():
                    continue

            sentence_text = text[start:punct_pos + 1].strip()
            if sentence_text:
                segments.append(
                    SentenceSegment(
                        sentence_index=current_idx,
                        text=sentence_text,
                        char_start=start,
                        char_end=punct_pos + 1
                    )
                )
                current_idx += 1
            start = end_pos

        # Remaining trailing text
        if start < len(text):
            trailing = text[start:].strip()
            if trailing:
                segments.append(
                    SentenceSegment(
                        sentence_index=current_idx,
                        text=trailing,
                        char_start=start,
                        char_end=len(text)
                    )
                )

        return segments

    def build_chunks(
        self,
        clause_id: str,
        source_document_id: str,
        clause_number: str,
        heading: str,
        normalized_body: str,
        parent_clause_id: Optional[str] = None,
        parent_clause_text: Optional[str] = None,
        clause_type: str = "RULE"
    ) -> List[ClauseChunk]:
        """Build retrieval chunk incorporating bounded parent context."""
        chunks: List[ClauseChunk] = []

        if parent_clause_text and len(parent_clause_text.strip()) > 0:
            combined_chunk = f"[Context: {parent_clause_id}] {normalized_body}"
            role = f"CHILD_{clause_type}"
        else:
            combined_chunk = normalized_body
            role = clause_type

        # Estimate tokens roughly at 1.3 words per token
        word_count = len(combined_chunk.split())
        token_estimate = int(word_count * 1.3)

        chunk = ClauseChunk(
            chunk_id=f"{clause_id}#c0",
            source_document_id=source_document_id,
            clause_id=clause_id,
            parent_clause_id=parent_clause_id,
            role=role,
            chunk_text=combined_chunk,
            token_count_estimate=token_estimate
        )
        chunks.append(chunk)
        return chunks

    def build_display_text(
        self,
        original_text: str,
        authority: str,
        document_title: str,
        clause_number: str,
        page_start: int
    ) -> str:
        """Create citation-compliant user-facing display text."""
        return (
            f"{original_text}\n\n"
            f"— Source: {document_title}, Clause {clause_number} (Page {page_start}), "
            f"published by {authority}."
        )
