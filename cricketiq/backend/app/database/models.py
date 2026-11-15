"""Domain data models for CricketIQ — ICC & MCC Rules Intelligence Assistant.

These models define the core entities for source documents, rule clauses,
applicability rules, relationships, ingestion reports, and evaluation benchmarks.
"""

from __future__ import annotations
from datetime import datetime, timezone, date
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentAuthority(str, Enum):
    MCC = "MCC"
    ICC = "ICC"
    COMPETITION = "COMPETITION"


class DocumentType(str, Enum):
    LAW = "Law"
    PLAYING_CONDITIONS = "Playing Conditions"
    COMPETITION_REGULATIONS = "Competition Regulations"
    AMENDMENT = "Amendment"


class CricketFormat(str, Enum):
    TEST = "Test"
    ODI = "ODI"
    T20I = "T20I"
    GENERAL = "General"


class GenderCategory(str, Enum):
    MENS = "Men's"
    WOMENS = "Women's"
    UNIVERSAL = "Universal"


class DocumentStatus(str, Enum):
    CANDIDATE = "candidate"
    PROCESSING = "processing"
    REVIEW = "review"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class ClauseType(str, Enum):
    RULE = "rule"
    DEFINITION = "definition"
    EXCEPTION = "exception"
    PROCEDURE = "procedure"
    PENALTY = "penalty"
    TABLE = "table"
    NOTE = "note"


class ValidationStatus(str, Enum):
    UNCHECKED = "unchecked"
    VALIDATED = "validated"
    CORRECTED = "corrected"
    REJECTED = "rejected"


class RelationshipType(str, Enum):
    SUPPLEMENTS = "supplements"
    MODIFIES = "modifies"
    SUPERSEDES = "supersedes"
    INCORPORATES = "incorporates"


class SourceDocument(BaseModel):
    """Authoritative source document (e.g. ICC Men's T20I Playing Conditions 2026)."""
    id: str = Field(..., description="Stable unique identifier, e.g. ICC_T20I_MEN_2026")
    publisher: DocumentAuthority = Field(..., description="MCC or ICC or competition authority")
    title: str = Field(..., description="Official title as printed on document")
    document_type: DocumentType = Field(..., description="Law, Playing Conditions, etc.")
    format: CricketFormat = Field(default=CricketFormat.GENERAL, description="Test, ODI, T20I or General")
    category: GenderCategory = Field(default=GenderCategory.UNIVERSAL, description="Men's, Women's, or Universal")
    competition: Optional[str] = Field(default=None, description="e.g. WTC, CWC, or None for general international")
    edition: str = Field(..., description="Edition label, e.g. October 2026")
    published_at: Optional[str] = Field(default=None, description="Publication date if stated (ISO format)")
    effective_from: Optional[str] = Field(default=None, description="Date from which conditions apply (ISO format)")
    effective_until: Optional[str] = Field(default=None, description="Date until which conditions apply if expired")
    official_url: str = Field(..., description="Canonical URL from official publisher")
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Timestamp of retrieval")
    sha256: str = Field(..., description="SHA-256 integrity hash of original immutable PDF")
    file_path: Optional[str] = Field(default=None, description="Local path to stored immutable PDF file")
    status: DocumentStatus = Field(default=DocumentStatus.CANDIDATE, description="Lifecycle status")
    terms_notes: str = Field(default="", description="Licensing and attribution notes")


class RuleClause(BaseModel):
    """Hierarchical clause or rule section within a source document."""
    id: str = Field(..., description="Unique ID, e.g. ICC_T20I_MEN_2026:21.18.2")
    source_document_id: str = Field(..., description="Foreign key to SourceDocument.id")
    clause_number: str = Field(..., description="Original clause number, e.g. '21.18.2' or 'Law 21.1'")
    parent_clause_id: Optional[str] = Field(default=None, description="Parent clause ID, e.g. ICC_T20I_MEN_2026:21.18")
    heading: str = Field(..., description="Original heading text, e.g. 'Free Hit'")
    original_text: str = Field(..., description="Exact verbatim extracted text from official source")
    normalized_text: str = Field(default="", description="Search-normalized text without alterations to meaning")
    page_start: int = Field(..., description="Starting page in PDF document (1-indexed)")
    page_end: int = Field(..., description="Ending page in PDF document (1-indexed)")
    source_locator: str = Field(default="", description="Fragment or official URL reference")
    clause_type: ClauseType = Field(default=ClauseType.RULE, description="rule, definition, exception, etc.")
    cross_references: List[str] = Field(default_factory=list, description="Referenced clause numbers, e.g. ['21.17', '21.13']")
    validation_status: ValidationStatus = Field(default=ValidationStatus.UNCHECKED)
    extracted_tables: Optional[List[Dict[str, Any]]] = Field(default=None, description="Extracted table data if present")


class DocumentRelationship(BaseModel):
    """Relationship between documents (e.g. ICC Playing Conditions modifying MCC Law)."""
    id: str
    source_doc_id: str
    target_doc_id: str
    relationship_type: RelationshipType
    description: str
    supporting_clause_id: Optional[str] = None


class IngestionReport(BaseModel):
    """Audit report generated following PDF extraction and validation."""
    id: str
    source_document_id: str
    started_at: str
    completed_at: str
    status: str
    pages_extracted: int
    clauses_found: int
    tables_found: int
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    reviewer_notes: Optional[str] = None
