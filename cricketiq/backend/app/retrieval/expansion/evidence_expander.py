"""Bounded Evidence Graph Expansion for CricketIQ.

Recursively expands parent section context and cross-referenced clauses
(e.g. Clause 21.18.2 Free Hit -> 21.17 Dismissals from a No ball)
strictly within the applicable source bundle, with cycle protection and bounded depth.
"""

from __future__ import annotations
from typing import List, Set, Dict, Optional
from sqlalchemy import select

from cricketiq.backend.app.database.models import RuleClause
from cricketiq.backend.app.database.orm_models import RuleClauseEntity
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import RetrievalHit, EvidenceRole


class EvidenceExpander:
    """Expands retrieved primary clauses with parent sections and cross-references."""

    def __init__(self, repository: CricketIQRepository):
        self.repository = repository
        self.session = repository.session

    def expand(
        self,
        primary_hits: List[RetrievalHit],
        candidate_document_ids: Optional[List[str]] = None,
        include_parent_context: bool = True,
        include_related_evidence: bool = True,
        max_depth: int = 2
    ) -> List[RetrievalHit]:
        """Expand hits with parent and referenced clauses within candidate documents."""
        if not primary_hits:
            return []

        expanded_results: List[RetrievalHit] = list(primary_hits)
        seen_clause_ids: Set[str] = {h.clause_id for h in primary_hits}
        candidate_set = set(candidate_document_ids) if candidate_document_ids is not None else None

        for hit in primary_hits:
            primary_clause = self.repository.get_clause(hit.clause_id)
            if not primary_clause:
                continue

            # 1. Expand Parent Context
            if include_parent_context and primary_clause.parent_clause_id:
                curr_parent_id = primary_clause.parent_clause_id
                depth = 0
                while curr_parent_id and depth < max_depth:
                    if curr_parent_id not in seen_clause_ids:
                        parent_clause = self.repository.get_clause(curr_parent_id)
                        if parent_clause:
                            # Verify bundle confinement
                            if candidate_set is None or parent_clause.source_document_id in candidate_set:
                                parent_hit = RetrievalHit(
                                    clause_id=parent_clause.id,
                                    document_id=parent_clause.source_document_id,
                                    clause_number=parent_clause.clause_number,
                                    heading=parent_clause.heading,
                                    original_text=parent_clause.original_text,
                                    normalized_text=parent_clause.normalized_text or parent_clause.original_text.lower(),
                                    page_start=parent_clause.page_start,
                                    page_end=parent_clause.page_end,
                                    evidence_role=EvidenceRole.PARENT_CONTEXT,
                                    relationship_path=[parent_clause.id, hit.clause_id],
                                    applicability_reason=f"Parent context for Clause {hit.clause_number}"
                                )
                                expanded_results.append(parent_hit)
                                seen_clause_ids.add(curr_parent_id)
                                curr_parent_id = parent_clause.parent_clause_id
                            else:
                                break
                        else:
                            break
                    else:
                        break
                    depth += 1

            # 2. Expand Cross-Referenced Evidence (e.g. 21.18.2 -> 21.17)
            if include_related_evidence and primary_clause.cross_references:
                for ref_target in primary_clause.cross_references:
                    # Look up referenced clause by clause_number in candidate documents
                    stmt = select(RuleClauseEntity).where(RuleClauseEntity.clause_number == ref_target)
                    if candidate_set is not None:
                        stmt = stmt.where(RuleClauseEntity.source_document_id.in_(candidate_set))
                    else:
                        # Default to same source document
                        stmt = stmt.where(RuleClauseEntity.source_document_id == primary_clause.source_document_id)

                    ref_entities = self.session.scalars(stmt).all()
                    for ref_entity in ref_entities:
                        if ref_entity.id not in seen_clause_ids:
                            ref_clause = self.repository._entity_to_rule_clause(ref_entity)
                            rel_hit = RetrievalHit(
                                clause_id=ref_clause.id,
                                document_id=ref_clause.source_document_id,
                                clause_number=ref_clause.clause_number,
                                heading=ref_clause.heading,
                                original_text=ref_clause.original_text,
                                normalized_text=ref_clause.normalized_text or ref_clause.original_text.lower(),
                                page_start=ref_clause.page_start,
                                page_end=ref_clause.page_end,
                                evidence_role=EvidenceRole.RELATED_SUPPORT,
                                relationship_path=[hit.clause_id, ref_clause.id],
                                applicability_reason=f"Cross-referenced by Clause {hit.clause_number}"
                            )
                            expanded_results.append(rel_hit)
                            seen_clause_ids.add(ref_clause.id)

        return expanded_results
