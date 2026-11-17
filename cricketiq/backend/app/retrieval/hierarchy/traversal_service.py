"""Bounded Hierarchy Traversal Engine for CricketIQ (Phase 6 Gate 3).

Provides bundle-confined traversal over the canonical clause tree:
- Hops up to immediate parent clause for definitional context (EvidenceRole.PARENT_CONTEXT)
- Hops down to immediate leaf children for operational rules/exceptions (EvidenceRole.OPERATIONAL_CHILD)
- Resolves lateral statutory cross-references within the active candidate bundle (EvidenceRole.STATUTORY_CROSS_REFERENCE)
- Enforces strict candidate bundle confinement: never widens the applicability scope
- Enforces maximum 1-hop limit, 5-snippet limit, and token budgets
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple, Any, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select

from cricketiq.backend.app.database.models import RuleClause, ClauseStructureNode
from cricketiq.backend.app.database.orm_models import RuleClauseEntity
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import EvidenceRole
from cricketiq.backend.app.retrieval.hierarchy.structure_store import ClauseStructureNodeStore


class TraversedNode(BaseModel):
    clause: Optional[RuleClause] = None
    structural_node: Optional[ClauseStructureNode] = None
    evidence_role: EvidenceRole
    hop_distance: int
    traversal_path: List[str] = Field(default_factory=list)


class HierarchyTraversalRequest(BaseModel):
    seed_clause_id: str
    candidate_document_ids: List[str]
    include_parent: bool = True
    include_children: bool = True
    include_cross_references: bool = True
    max_hops: int = 1
    max_evidence_count: int = 5
    token_budget: int = 1200


class HierarchyTraversalResult(BaseModel):
    seed_clause_id: str
    seed_clause: Optional[RuleClause] = None
    parent_context: Optional[RuleClause] = None
    structural_context: Optional[ClauseStructureNode] = None
    operational_children: List[RuleClause] = Field(default_factory=list)
    resolved_cross_references: List[RuleClause] = Field(default_factory=list)
    blocked_out_of_bundle_targets: List[str] = Field(default_factory=list)
    unresolved_targets: List[str] = Field(default_factory=list)
    assembled_nodes: List[TraversedNode] = Field(default_factory=list)
    token_count_estimate: int = 0
    budget_overflow: bool = False


class HierarchyTraversalService:
    """Bounded, bundle-confined traversal service for regulatory clause trees."""

    def __init__(
        self,
        repository: CricketIQRepository,
        structure_store: Optional[ClauseStructureNodeStore] = None
    ):
        self.repository = repository
        self.session = repository.session
        self.structure_store = structure_store or ClauseStructureNodeStore()

    def _get_clause_by_number(self, doc_id: str, clause_number: str) -> Optional[RuleClause]:
        full_id = f"{doc_id}:{clause_number}"
        direct = self.repository.get_clause(full_id)
        if direct:
            return direct
        stmt = select(RuleClauseEntity).where(
            RuleClauseEntity.source_document_id == doc_id,
            RuleClauseEntity.clause_number == clause_number
        )
        entity = self.session.scalars(stmt).first()
        if entity:
            return self.repository._entity_to_rule_clause(entity)
        return None

    def traverse(self, request: HierarchyTraversalRequest) -> HierarchyTraversalResult:
        result = HierarchyTraversalResult(seed_clause_id=request.seed_clause_id)
        visited_ids: Set[str] = set()

        # 1. Fetch seed clause
        seed_clause = self.repository.get_clause(request.seed_clause_id)
        if not seed_clause:
            result.unresolved_targets.append(request.seed_clause_id)
            return result

        # Verify seed belongs to candidate bundle
        if seed_clause.source_document_id not in request.candidate_document_ids:
            result.blocked_out_of_bundle_targets.append(request.seed_clause_id)
            return result

        result.seed_clause = seed_clause
        visited_ids.add(seed_clause.id)

        # Direct evidence is priority #1
        assembled: List[TraversedNode] = [
            TraversedNode(
                clause=seed_clause,
                evidence_role=EvidenceRole.DIRECT_EVIDENCE,
                hop_distance=0,
                traversal_path=[seed_clause.id]
            )
        ]

        # 2. Hop Up: Parent Context (Max 1 hop)
        if request.include_parent and request.max_hops >= 1:
            pid = seed_clause.parent_clause_id
            if pid and pid not in visited_ids:
                parent_clause = self.repository.get_clause(pid)
                if parent_clause:
                    if parent_clause.source_document_id in request.candidate_document_ids:
                        result.parent_context = parent_clause
                        visited_ids.add(parent_clause.id)
                        assembled.append(
                            TraversedNode(
                                clause=parent_clause,
                                evidence_role=EvidenceRole.PARENT_CONTEXT,
                                hop_distance=1,
                                traversal_path=[seed_clause.id, parent_clause.id]
                            )
                        )
                    else:
                        result.blocked_out_of_bundle_targets.append(pid)
                else:
                    # Check if pid refers to a structural node
                    struct_node = self.structure_store.get_node(pid)
                    if struct_node:
                        if struct_node.source_document_id in request.candidate_document_ids:
                            result.structural_context = struct_node
                            visited_ids.add(struct_node.id)
                            assembled.append(
                                TraversedNode(
                                    structural_node=struct_node,
                                    evidence_role=EvidenceRole.STRUCTURAL_CONTEXT,
                                    hop_distance=1,
                                    traversal_path=[seed_clause.id, struct_node.id]
                                )
                            )
                        else:
                            result.blocked_out_of_bundle_targets.append(pid)
                    else:
                        result.unresolved_targets.append(pid)
            elif not pid and self.structure_store:
                # Resolve absent unnumbered chapter heading as structural context
                struct_node = self.structure_store.get_structural_parent(seed_clause.id)
                if struct_node and struct_node.id not in visited_ids:
                    if struct_node.source_document_id in request.candidate_document_ids:
                        result.structural_context = struct_node
                        visited_ids.add(struct_node.id)
                        assembled.append(
                            TraversedNode(
                                structural_node=struct_node,
                                evidence_role=EvidenceRole.STRUCTURAL_CONTEXT,
                                hop_distance=1,
                                traversal_path=[seed_clause.id, struct_node.id]
                            )
                        )
                    else:
                        result.blocked_out_of_bundle_targets.append(struct_node.id)

        # 3. Hop Down: Operational Children (Max 1 hop)
        if request.include_children and request.max_hops >= 1:
            stmt = (
                select(RuleClauseEntity)
                .where(
                    RuleClauseEntity.parent_clause_id == seed_clause.id,
                    RuleClauseEntity.source_document_id.in_(request.candidate_document_ids)
                )
                .order_by(RuleClauseEntity.clause_number)
            )
            child_entities = self.session.scalars(stmt).all()
            for entity in child_entities:
                if len(assembled) >= request.max_evidence_count:
                    break
                if entity.id not in visited_ids:
                    child_clause = self.repository._entity_to_rule_clause(entity)
                    result.operational_children.append(child_clause)
                    visited_ids.add(child_clause.id)
                    assembled.append(
                        TraversedNode(
                            clause=child_clause,
                            evidence_role=EvidenceRole.OPERATIONAL_CHILD,
                            hop_distance=1,
                            traversal_path=[seed_clause.id, child_clause.id]
                        )
                    )

        # 4. Hop Lateral: Statutory Cross-References (Max 1 hop)
        if request.include_cross_references and seed_clause.cross_references and request.max_hops >= 1:
            for xref in seed_clause.cross_references:
                if len(assembled) >= request.max_evidence_count:
                    break
                
                resolved_clause: Optional[RuleClause] = None
                
                # If xref is full ID e.g. DOC:1.2.3
                if ":" in xref:
                    doc_part, num_part = xref.split(":", 1)
                    if doc_part in request.candidate_document_ids:
                        resolved_clause = self.repository.get_clause(xref)
                    else:
                        result.blocked_out_of_bundle_targets.append(xref)
                        continue
                else:
                    # Look up by clause_number in same document first
                    cand = self._get_clause_by_number(seed_clause.source_document_id, xref)
                    if cand and cand.source_document_id in request.candidate_document_ids:
                        resolved_clause = cand
                    else:
                        # Search across candidate documents in bundle
                        for c_doc in request.candidate_document_ids:
                            cand = self._get_clause_by_number(c_doc, xref)
                            if cand:
                                resolved_clause = cand
                                break

                if resolved_clause:
                    if resolved_clause.id not in visited_ids:
                        result.resolved_cross_references.append(resolved_clause)
                        visited_ids.add(resolved_clause.id)
                        assembled.append(
                            TraversedNode(
                                clause=resolved_clause,
                                evidence_role=EvidenceRole.STATUTORY_CROSS_REFERENCE,
                                hop_distance=1,
                                traversal_path=[seed_clause.id, resolved_clause.id]
                            )
                        )
                else:
                    result.unresolved_targets.append(xref)

        # 5. Token budget accounting
        def _node_text(n: TraversedNode) -> str:
            if n.clause:
                return n.clause.original_text or ""
            if n.structural_node:
                return f"Chapter: {n.structural_node.heading_title}"
            return ""

        total_tokens = sum(len(_node_text(n).split()) for n in assembled)
        result.token_count_estimate = total_tokens

        # Check if direct evidence alone exceeds budget
        seed_tokens = len((seed_clause.original_text or "").split())
        if seed_tokens > request.token_budget:
            result.budget_overflow = True
            # Never truncate direct evidence
            result.assembled_nodes = [assembled[0]]
            return result

        # Prune lowest-priority context snippets if token budget exceeded
        while len(assembled) > 1 and total_tokens > request.token_budget:
            result.budget_overflow = True
            removed = assembled.pop()  # Pop lowest-priority (cross-ref or child)
            total_tokens -= len(_node_text(removed).split())

        result.assembled_nodes = assembled[:request.max_evidence_count]
        result.token_count_estimate = total_tokens
        return result
