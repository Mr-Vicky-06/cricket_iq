"""SQLAlchemy ORM Entities for CricketIQ.

Maps relational tables for source documents, rule clauses, document relationships,
and applicability rules.
"""

from __future__ import annotations
import json
from typing import List, Optional
from sqlalchemy import (
    Column, String, Text, Integer, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from cricketiq.backend.app.database.connection import Base


class SourceDocumentEntity(Base):
    __tablename__ = "source_documents"

    id = Column(String(64), primary_key=True)
    publisher = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False)
    document_type = Column(String(64), nullable=False)
    scope_level = Column(String(32), nullable=False, default="format_pc")
    format = Column(String(32), nullable=True, index=True)
    category = Column(String(32), nullable=True, index=True)
    competition = Column(String(64), nullable=True, index=True)
    edition = Column(String(64), nullable=False)
    addendum_id = Column(String(64), nullable=True)
    published_at = Column(String(32), nullable=True)
    effective_from = Column(String(32), nullable=True, index=True)
    effective_until = Column(String(32), nullable=True, index=True)
    applicability_basis = Column(String(32), nullable=False, default="series_start_date")
    official_url = Column(Text, nullable=False)
    retrieved_at = Column(String(32), nullable=False)
    sha256 = Column(String(64), nullable=False)
    file_path = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="candidate", index=True)
    terms_notes = Column(Text, nullable=False, default="")
    regulatory_role = Column(String(64), nullable=True, default=None)

    clauses = relationship("RuleClauseEntity", back_populates="document", cascade="all, delete-orphan")
    applicability_rules = relationship("ApplicabilityRuleEntity", back_populates="document", cascade="all, delete-orphan")


class RuleClauseEntity(Base):
    __tablename__ = "rule_clauses"

    id = Column(String(128), primary_key=True)  # e.g. ICC_T20I_MEN_2026:21.18.2
    source_document_id = Column(String(64), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_number = Column(String(32), nullable=False, index=True)
    parent_clause_id = Column(String(128), nullable=True, index=True)
    hierarchy_depth = Column(Integer, nullable=False, default=1)
    heading = Column(Text, nullable=False)
    original_text = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    page_start = Column(Integer, nullable=False)
    page_end = Column(Integer, nullable=False)
    pdf_page_index = Column(Integer, nullable=False, default=0)
    printed_page_number = Column(String(32), nullable=True)
    source_locator = Column(Text, nullable=False, default="")
    clause_type = Column(String(32), nullable=False, default="rule", index=True)
    cross_references = Column(Text, nullable=False, default="[]")  # JSON encoded list
    validation_status = Column(String(32), nullable=False, default="unchecked")

    document = relationship("SourceDocumentEntity", back_populates="clauses")

    __table_args__ = (
        Index("ix_clause_lookup", "source_document_id", "clause_number"),
        UniqueConstraint("source_document_id", "clause_number", name="uq_doc_clause_number"),
    )

    def get_cross_references(self) -> List[str]:
        try:
            return json.loads(self.cross_references)
        except Exception:
            return []

    def set_cross_references(self, refs: List[str]) -> None:
        self.cross_references = json.dumps(refs)


class DocumentRelationshipEntity(Base):
    __tablename__ = "document_relationships"

    id = Column(String(128), primary_key=True)
    source_doc_id = Column(String(64), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    target_doc_id = Column(String(64), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(String(32), nullable=False)  # incorporates, modifies, supplements, supersedes
    description = Column(Text, nullable=False)
    supporting_clause_id = Column(String(128), nullable=True)
    review_status = Column(String(32), nullable=False, default="validated")


class ApplicabilityRuleEntity(Base):
    __tablename__ = "applicability_rules"

    id = Column(String(128), primary_key=True)
    source_document_id = Column(String(64), ForeignKey("source_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    format = Column(String(32), nullable=True, index=True)  # Test, ODI, T20I, General
    category = Column(String(32), nullable=True, index=True)  # Men's, Women's, Universal
    competition = Column(String(64), nullable=True, index=True)
    effective_start = Column(String(32), nullable=True)
    effective_until = Column(String(32), nullable=True)
    precedence_rank = Column(Integer, nullable=False, default=100)  # 1: Competition, 2: Format PC, 3: MCC Laws
    notes = Column(Text, nullable=False, default="")

    document = relationship("SourceDocumentEntity", back_populates="applicability_rules")
