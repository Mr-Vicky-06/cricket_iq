"""Domain data models for CricketIQ — ICC & MCC Rules Intelligence Assistant.

These models define the core entities for source documents, rule clauses,
applicability rules, relationships, ingestion reports, match context, and decisions.
"""

from __future__ import annotations
from datetime import datetime, timezone, date
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator


class DocumentAuthority(str, Enum):
    MCC = "MCC"
    ICC = "ICC"
    BCCI = "BCCI"
    ECB = "ECB"
    CA = "CA"
    COMPETITION = "COMPETITION"


class DocumentType(str, Enum):
    LAW = "Law"
    PLAYING_CONDITIONS = "Playing Conditions"
    COMPETITION_REGULATIONS = "Competition Regulations"
    ADDENDUM = "Addendum"
    AMENDMENT = "Amendment"


class ScopeLevel(str, Enum):
    LAWS_BASELINE = "laws_baseline"
    FORMAT_PC = "format_pc"
    COMPETITION_PC = "competition_pc"
    ADDENDUM = "addendum"
    DOMESTIC = "domestic"


class RegulatoryRole(str, Enum):
    NORMATIVE_LAWS_BASELINE = "normative_laws_baseline"
    NORMATIVE_FORMAT_PC = "normative_format_pc"
    NORMATIVE_COMPETITION_REGULATION = "normative_competition_regulation"
    NORMATIVE_ADDENDUM = "normative_addendum"
    EXPLANATORY_GUIDANCE = "explanatory_guidance"
    ADMINISTRATIVE_REFERENCE = "administrative_reference"


class ApplicabilityBasis(str, Enum):
    SERIES_START_DATE = "series_start_date"
    MATCH_DATE = "match_date"
    COMPETITION_START_DATE = "competition_start_date"
    SEASON_EDITION = "season_edition"


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
    INCORPORATES = "incorporates"
    MODIFIES = "modifies"
    SUPPLEMENTS = "supplements"
    SUPERSEDES = "supersedes"
    CROSS_REFERENCES = "cross_references"


class MatchContext(BaseModel):
    """Domain representation of a match or query context."""
    cricket_level: str = Field(default="international", description="'international', 'domestic', or 'unspecified'")
    governing_body: Optional[str] = Field(default=None, description="ICC, MCC, BCCI, etc.")
    format: Optional[CricketFormat] = Field(default=None, description="Test, ODI, T20I")
    category: Optional[GenderCategory] = Field(default=None, description="Men's or Women's")
    competition: Optional[str] = Field(default=None, description="Tournament identifier, e.g. 'T20_WORLD_CUP_2026', 'WTC'")
    series_start_date: Optional[str] = Field(default=None, description="ISO date: YYYY-MM-DD")
    match_date: Optional[str] = Field(default=None, description="ISO date: YYYY-MM-DD")
    season: Optional[str] = Field(default=None, description="e.g. '2025-2027'")
    raw_query: Optional[str] = Field(default=None, description="Original user prompt")


class SourceDocument(BaseModel):
    """Authoritative source document (e.g. ICC Men's T20I Playing Conditions 2026)."""
    id: str = Field(..., description="Stable unique identifier, e.g. ICC_T20I_MEN_2026")
    publisher: DocumentAuthority = Field(..., description="MCC or ICC or competition authority")
    title: str = Field(..., description="Official title as printed on document")
    document_type: DocumentType = Field(..., description="Law, Playing Conditions, etc.")
    scope_level: ScopeLevel = Field(default=ScopeLevel.FORMAT_PC)
    regulatory_role: RegulatoryRole = Field(default=RegulatoryRole.ADMINISTRATIVE_REFERENCE, description="Normative legal role of the document")
    format: Optional[CricketFormat] = Field(default=None)
    category: Optional[GenderCategory] = Field(default=None)
    competition: Optional[str] = Field(default=None)
    edition: str = Field(..., description="Edition label, e.g. October 2026")
    addendum_id: Optional[str] = Field(default=None)
    published_at: Optional[str] = Field(default=None)
    effective_from: Optional[str] = Field(default=None)
    effective_until: Optional[str] = Field(default=None)
    applicability_basis: ApplicabilityBasis = Field(default=ApplicabilityBasis.SERIES_START_DATE)
    official_url: str = Field(..., description="Canonical URL from official publisher")
    retrieved_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sha256: str = Field(..., description="SHA-256 integrity hash of original immutable PDF")
    file_path: Optional[str] = Field(default=None)
    status: DocumentStatus = Field(default=DocumentStatus.CANDIDATE)
    terms_notes: str = Field(default="")

    @model_validator(mode="before")
    @classmethod
    def _resolve_regulatory_role(cls, values: Any) -> Any:
        if isinstance(values, dict):
            raw_role = values.get("regulatory_role")
            if raw_role:
                if isinstance(raw_role, RegulatoryRole):
                    values["regulatory_role"] = raw_role
                elif isinstance(raw_role, str) and raw_role in RegulatoryRole._value2member_map_:
                    values["regulatory_role"] = RegulatoryRole(raw_role)
                else:
                    # Unknown or unapproved role: classify as ADMINISTRATIVE_REFERENCE (never silently promote to normative)
                    values["regulatory_role"] = RegulatoryRole.ADMINISTRATIVE_REFERENCE
            else:
                doc_id = str(values.get("id", ""))
                scope = values.get("scope_level")
                doc_type = values.get("document_type")
                if "changes" in doc_id.lower() or doc_type in ("Amendment", DocumentType.AMENDMENT):
                    values["regulatory_role"] = RegulatoryRole.EXPLANATORY_GUIDANCE
                elif scope in (ScopeLevel.LAWS_BASELINE, "laws_baseline") or values.get("publisher") in (DocumentAuthority.MCC, "MCC"):
                    values["regulatory_role"] = RegulatoryRole.NORMATIVE_LAWS_BASELINE
                elif scope in (ScopeLevel.COMPETITION_PC, "competition_pc") or doc_type in (DocumentType.COMPETITION_REGULATIONS, "Competition Regulations"):
                    values["regulatory_role"] = RegulatoryRole.NORMATIVE_COMPETITION_REGULATION
                elif scope in (ScopeLevel.ADDENDUM, "addendum") or doc_type in (DocumentType.ADDENDUM, "Addendum"):
                    values["regulatory_role"] = RegulatoryRole.NORMATIVE_ADDENDUM
                elif scope in (ScopeLevel.FORMAT_PC, "format_pc") or doc_type in (DocumentType.PLAYING_CONDITIONS, "Playing Conditions"):
                    values["regulatory_role"] = RegulatoryRole.NORMATIVE_FORMAT_PC
                else:
                    values["regulatory_role"] = RegulatoryRole.ADMINISTRATIVE_REFERENCE
        return values


class RuleClause(BaseModel):
    """Hierarchical clause or rule section within a source document."""
    id: str = Field(..., description="Unique ID, e.g. ICC_T20I_MEN_2026:21.18.2")
    source_document_id: str = Field(..., description="Foreign key to SourceDocument.id")
    clause_number: str = Field(..., description="Original clause number, e.g. '21.18.2' or 'Law 21.1'")
    parent_clause_id: Optional[str] = Field(default=None)
    hierarchy_depth: int = Field(default=1)
    heading: str = Field(..., description="Original heading text, e.g. 'Free Hit'")
    original_text: str = Field(..., description="Verbatim text from official source")
    normalized_text: str = Field(default="", description="Search-normalized text")
    page_start: int = Field(..., description="Starting printed page / 1-indexed PDF page")
    page_end: int = Field(..., description="Ending printed page")
    pdf_page_index: int = Field(default=0, description="Zero-based PDF index")
    printed_page_number: Optional[str] = Field(default=None)
    source_locator: str = Field(default="")
    clause_type: ClauseType = Field(default=ClauseType.RULE)
    cross_references: List[str] = Field(default_factory=list)
    validation_status: ValidationStatus = Field(default=ValidationStatus.UNCHECKED)
    extracted_tables: Optional[List[Dict[str, Any]]] = Field(default=None)


class ClauseStructureNode(BaseModel):
    """Non-citable structural hierarchy node (e.g. unnumbered chapter heading).

    Requirements (Phase 6 Gate 3):
    - Structural nodes are not RuleClause legal text.
    - They receive no fabricated clause number, citation identity, FTS row, vector, or independent answer claim.
    - Child clauses may refer to the structural node as their parent for navigation/context.
    - The node retains document ID, heading title, source locator/page and source provenance.
    - Retrieval labels it as structural context, not direct legal evidence.
    """
    id: str = Field(..., description="Unique structural ID, e.g. ICC_ODI_MEN_2026:STRUCT_LAW_1")
    source_document_id: str = Field(..., description="Foreign key to SourceDocument.id")
    heading_title: str = Field(..., description="Official structural heading title from source")
    source_locator: str = Field(default="", description="Source locator e.g. 'Law 1 Heading'")
    page_start: int = Field(..., description="Page locator where heading appears")
    page_end: int = Field(..., description="Ending page locator")
    source_provenance: str = Field(default="ICC Playing Conditions Structural Heading", description="Audit provenance")



class DocumentRelationship(BaseModel):
    """Explicit relationship between documents or clauses."""
    id: str
    source_doc_id: str
    target_doc_id: str
    relationship_type: RelationshipType
    description: str
    supporting_clause_id: Optional[str] = None
    review_status: str = "validated"


class ApplicabilityDecision(BaseModel):
    """Deterministic result of rule applicability resolution."""
    context: MatchContext
    selected_bundle: List[SourceDocument] = Field(default_factory=list)
    primary_document: Optional[SourceDocument] = None
    baseline_document: Optional[SourceDocument] = None
    relationships_applied: List[DocumentRelationship] = Field(default_factory=list)
    rejected_candidates: List[Dict[str, str]] = Field(default_factory=list)
    effective_date_basis_used: Dict[str, str] = Field(default_factory=dict)
    reason_codes: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    unresolved_conditions: List[str] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    is_ambiguous: bool = False
    clarification_needed: Optional[str] = None
    decision_trace: List[str] = Field(default_factory=list)
    engine_version: str = "2.0.0"


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
