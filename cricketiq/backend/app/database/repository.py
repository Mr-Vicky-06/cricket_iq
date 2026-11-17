"""Relational Repository and Rule Catalog for CricketIQ.

Handles persistence, transactional writes, lookup, and relational graph queries for
Source Documents, Rule Clauses, Relationships, and Applicability Rules.
"""

from __future__ import annotations
import json
from typing import List, Optional, Dict, Any, Protocol
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType,
    ScopeLevel, ApplicabilityBasis, CricketFormat, GenderCategory,
    DocumentStatus, ClauseType, ValidationStatus, DocumentRelationship,
    RelationshipType, RegulatoryRole
)
from cricketiq.backend.app.database.orm_models import (
    SourceDocumentEntity, RuleClauseEntity, DocumentRelationshipEntity,
    ApplicabilityRuleEntity
)


class RuleCatalog(Protocol):
    """Protocol defining read access to authoritative cricket documents and rules."""
    def get_document(self, doc_id: str) -> Optional[SourceDocument]: ...
    def list_active_documents(self) -> List[SourceDocument]: ...
    def get_relationships(self, doc_id: str) -> List[DocumentRelationship]: ...
    def get_clause(self, clause_id: str) -> Optional[RuleClause]: ...
    def get_clauses_for_document(self, doc_id: str) -> List[RuleClause]: ...


class CricketIQRepository:
    """Repository providing typed, transactional access to CricketIQ persistence layer."""

    def __init__(self, session: Session):
        self.session = session

    # --- Source Document Operations ---

    def upsert_source_document(self, doc: SourceDocument) -> SourceDocument:
        try:
            entity = self.session.get(SourceDocumentEntity, doc.id)
            role_val = doc.regulatory_role.value if hasattr(doc.regulatory_role, "value") else (str(doc.regulatory_role) if doc.regulatory_role else None)
            if not entity:
                entity = SourceDocumentEntity(
                    id=doc.id,
                    publisher=doc.publisher.value,
                    title=doc.title,
                    document_type=doc.document_type.value,
                    scope_level=doc.scope_level.value,
                    regulatory_role=role_val,
                    format=doc.format.value if doc.format else None,
                    category=doc.category.value if doc.category else None,
                    competition=doc.competition,
                    edition=doc.edition,
                    addendum_id=doc.addendum_id,
                    published_at=doc.published_at,
                    effective_from=doc.effective_from,
                    effective_until=doc.effective_until,
                    applicability_basis=doc.applicability_basis.value,
                    official_url=doc.official_url,
                    retrieved_at=doc.retrieved_at,
                    sha256=doc.sha256,
                    file_path=doc.file_path,
                    status=doc.status.value,
                    terms_notes=doc.terms_notes
                )
                self.session.add(entity)
            else:
                entity.title = doc.title
                entity.edition = doc.edition
                entity.scope_level = doc.scope_level.value
                entity.regulatory_role = role_val
                entity.published_at = doc.published_at
                entity.effective_from = doc.effective_from
                entity.effective_until = doc.effective_until
                entity.applicability_basis = doc.applicability_basis.value
                entity.status = doc.status.value
                entity.sha256 = doc.sha256
                entity.file_path = doc.file_path
                entity.terms_notes = doc.terms_notes

            self.session.commit()
            return self._entity_to_source_doc(entity)
        except Exception:
            self.session.rollback()
            raise

    def get_document(self, doc_id: str) -> Optional[SourceDocument]:
        entity = self.session.get(SourceDocumentEntity, doc_id)
        if not entity:
            return None
        return self._entity_to_source_doc(entity)

    def list_active_documents(self) -> List[SourceDocument]:
        return self.list_source_documents(status=DocumentStatus.ACTIVE)

    def list_source_documents(self, status: Optional[DocumentStatus] = None) -> List[SourceDocument]:
        stmt = select(SourceDocumentEntity)
        if status:
            stmt = stmt.where(SourceDocumentEntity.status == status.value)
        results = self.session.scalars(stmt).all()
        return [self._entity_to_source_doc(e) for e in results]

    # --- Rule Clause Operations ---

    def upsert_clauses(self, clauses: List[RuleClause]) -> int:
        try:
            count = 0
            for clause in clauses:
                entity = self.session.get(RuleClauseEntity, clause.id)
                if not entity:
                    entity = RuleClauseEntity(
                        id=clause.id,
                        source_document_id=clause.source_document_id,
                        clause_number=clause.clause_number,
                        parent_clause_id=clause.parent_clause_id,
                        hierarchy_depth=clause.hierarchy_depth,
                        heading=clause.heading,
                        original_text=clause.original_text,
                        normalized_text=clause.normalized_text,
                        page_start=clause.page_start,
                        page_end=clause.page_end,
                        pdf_page_index=clause.pdf_page_index,
                        printed_page_number=clause.printed_page_number,
                        source_locator=clause.source_locator,
                        clause_type=clause.clause_type.value,
                        cross_references=json.dumps(clause.cross_references),
                        validation_status=clause.validation_status.value
                    )
                    self.session.add(entity)
                else:
                    entity.heading = clause.heading
                    entity.original_text = clause.original_text
                    entity.normalized_text = clause.normalized_text
                    entity.page_start = clause.page_start
                    entity.page_end = clause.page_end
                    entity.pdf_page_index = clause.pdf_page_index
                    entity.printed_page_number = clause.printed_page_number
                    entity.clause_type = clause.clause_type.value
                    entity.cross_references = json.dumps(clause.cross_references)
                    entity.validation_status = clause.validation_status.value
                count += 1
            self.session.commit()
            return count
        except Exception:
            self.session.rollback()
            raise

    def get_clause(self, clause_id: str) -> Optional[RuleClause]:
        entity = self.session.get(RuleClauseEntity, clause_id)
        if not entity:
            return None
        return self._entity_to_rule_clause(entity)

    def get_clauses_for_document(self, doc_id: str) -> List[RuleClause]:
        stmt = select(RuleClauseEntity).where(RuleClauseEntity.source_document_id == doc_id).order_by(RuleClauseEntity.clause_number)
        results = self.session.scalars(stmt).all()
        return [self._entity_to_rule_clause(e) for e in results]

    def get_clause_hierarchy(self, clause_id: str) -> Dict[str, Any]:
        """Retrieve clause together with parent, children subclauses, and cross-references."""
        target = self.get_clause(clause_id)
        if not target:
            return {}

        parent = None
        if target.parent_clause_id:
            parent = self.get_clause(target.parent_clause_id)

        children_stmt = select(RuleClauseEntity).where(RuleClauseEntity.parent_clause_id == clause_id).order_by(RuleClauseEntity.clause_number)
        children = [self._entity_to_rule_clause(e) for e in self.session.scalars(children_stmt).all()]

        cross_refs = []
        for ref_num in target.cross_references:
            ref_id = f"{target.source_document_id}:{ref_num}"
            ref_clause = self.get_clause(ref_id)
            if ref_clause:
                cross_refs.append(ref_clause)

        return {
            "clause": target,
            "parent": parent,
            "children": children,
            "cross_references": cross_refs
        }

    # --- Document Relationships ---

    def add_relationship(self, rel: DocumentRelationship) -> DocumentRelationship:
        try:
            entity = DocumentRelationshipEntity(
                id=rel.id,
                source_doc_id=rel.source_doc_id,
                target_doc_id=rel.target_doc_id,
                relationship_type=rel.relationship_type.value,
                description=rel.description,
                supporting_clause_id=rel.supporting_clause_id,
                review_status=rel.review_status
            )
            self.session.merge(entity)
            self.session.commit()
            return rel
        except Exception:
            self.session.rollback()
            raise

    def get_relationships(self, doc_id: str) -> List[DocumentRelationship]:
        return self.get_relationships_for_document(doc_id)

    def get_relationships_for_document(self, doc_id: str) -> List[DocumentRelationship]:
        stmt = select(DocumentRelationshipEntity).where(
            or_(
                DocumentRelationshipEntity.source_doc_id == doc_id,
                DocumentRelationshipEntity.target_doc_id == doc_id
            )
        )
        results = self.session.scalars(stmt).all()
        return [
            DocumentRelationship(
                id=e.id,
                source_doc_id=e.source_doc_id,
                target_doc_id=e.target_doc_id,
                relationship_type=RelationshipType(e.relationship_type),
                description=e.description,
                supporting_clause_id=e.supporting_clause_id,
                review_status=e.review_status
            )
            for e in results
        ]

    # --- Mapping Helpers ---

    def _entity_to_source_doc(self, entity: SourceDocumentEntity) -> SourceDocument:
        role_val = getattr(entity, "regulatory_role", None)
        if role_val:
            role = RegulatoryRole(role_val) if role_val in RegulatoryRole._value2member_map_ else RegulatoryRole.ADMINISTRATIVE_REFERENCE
        else:
            role = None
        return SourceDocument(
            id=entity.id,
            publisher=DocumentAuthority(entity.publisher),
            title=entity.title,
            document_type=DocumentType(entity.document_type),
            scope_level=ScopeLevel(entity.scope_level) if entity.scope_level else ScopeLevel.FORMAT_PC,
            regulatory_role=role,
            format=CricketFormat(entity.format) if entity.format else None,
            category=GenderCategory(entity.category) if entity.category else None,
            competition=entity.competition,
            edition=entity.edition,
            addendum_id=entity.addendum_id,
            published_at=entity.published_at,
            effective_from=entity.effective_from,
            effective_until=entity.effective_until,
            applicability_basis=ApplicabilityBasis(entity.applicability_basis) if entity.applicability_basis else ApplicabilityBasis.SERIES_START_DATE,
            official_url=entity.official_url,
            retrieved_at=entity.retrieved_at,
            sha256=entity.sha256,
            file_path=entity.file_path,
            status=DocumentStatus(entity.status),
            terms_notes=entity.terms_notes
        )

    def _entity_to_rule_clause(self, entity: RuleClauseEntity) -> RuleClause:
        return RuleClause(
            id=entity.id,
            source_document_id=entity.source_document_id,
            clause_number=entity.clause_number,
            parent_clause_id=entity.parent_clause_id,
            hierarchy_depth=entity.hierarchy_depth,
            heading=entity.heading,
            original_text=entity.original_text,
            normalized_text=entity.normalized_text,
            page_start=entity.page_start,
            page_end=entity.page_end,
            pdf_page_index=entity.pdf_page_index,
            printed_page_number=entity.printed_page_number,
            source_locator=entity.source_locator,
            clause_type=ClauseType(entity.clause_type),
            cross_references=json.loads(entity.cross_references) if entity.cross_references else [],
            validation_status=ValidationStatus(entity.validation_status)
        )
