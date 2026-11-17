"""Unit tests for Bounded Hierarchy Traversal Engine (Phase 6 Gate 3 Task 3.3).
"""

import pytest
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus,
    ClauseType, CricketFormat, GenderCategory
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import EvidenceRole
from cricketiq.backend.app.retrieval.hierarchy.traversal_service import (
    HierarchyTraversalService, HierarchyTraversalRequest, HierarchyTraversalResult
)


@pytest.fixture
def traversal_repo():
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    # In-bundle document: ICC_T20I_MEN_2026
    doc1 = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="a" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc1)

    # Out-of-bundle document: MCC_LAWS_2026
    doc2 = SourceDocument(
        id="MCC_LAWS_2026",
        publisher=DocumentAuthority.MCC,
        title="MCC Laws of Cricket",
        document_type=DocumentType.LAW,
        edition="2026 Code",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://www.lords.org/mcc/laws.pdf",
        sha256="b" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc2)

    # Parent clause: 21.18
    p1 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc1.id,
        clause_number="21.18",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit for whichever batter is facing it.",
        normalized_text="the delivery following a no ball shall be a free hit for whichever batter is facing it",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )

    # Child clause 1: 21.18.1
    c1 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.1",
        source_document_id=doc1.id,
        clause_number="21.18.1",
        parent_clause_id=p1.id,
        hierarchy_depth=3,
        heading="Free Hit Delivery",
        original_text="If the delivery for the free hit is not a legitimate delivery, the run off it shall be scored.",
        normalized_text="if the delivery for the free hit is not a legitimate delivery the run off it shall be scored",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )

    # Child clause 2: 21.18.2 with cross-references to in-bundle 21.17 and out-of-bundle MCC_LAWS_2026:38.3
    c2 = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=doc1.id,
        clause_number="21.18.2",
        parent_clause_id=p1.id,
        hierarchy_depth=3,
        heading="Free Hit Dismissals",
        original_text="For any free hit, the striker can be dismissed only under the circumstances that apply for a No ball.",
        normalized_text="for any free hit the striker can be dismissed only under the circumstances that apply for a no ball",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1,
        cross_references=["ICC_T20I_MEN_2026:21.17", "MCC_LAWS_2026:38.3", "ICC_T20I_MEN_2026:99.99"]
    )

    # In-bundle referenced clause: 21.17
    xref_clause = RuleClause(
        id="ICC_T20I_MEN_2026:21.17",
        source_document_id=doc1.id,
        clause_number="21.17",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="No Ball Laws",
        original_text="Clauses governing no balls and exceptions.",
        normalized_text="clauses governing no balls and exceptions",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )

    # Out-of-bundle referenced clause: MCC_LAWS_2026:38.3
    out_clause = RuleClause(
        id="MCC_LAWS_2026:38.3",
        source_document_id=doc2.id,
        clause_number="38.3",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Non-striker leaving ground early",
        original_text="At any time from the moment the ball comes into play until the instant when the bowler would normally have been expected to release the ball.",
        normalized_text="at any time from the moment the ball comes into play",
        clause_type=ClauseType.RULE,
        page_start=10,
        page_end=10
    )

    # Upsert all clauses
    repo.upsert_clauses([p1, c1, c2, xref_clause, out_clause])

    return repo


def test_hierarchy_traversal_hop_up_parent(traversal_repo):
    service = HierarchyTraversalService(traversal_repo)
    req = HierarchyTraversalRequest(
        seed_clause_id="ICC_T20I_MEN_2026:21.18.1",
        candidate_document_ids=["ICC_T20I_MEN_2026"],
        include_parent=True,
        include_children=False,
        include_cross_references=False
    )
    res = service.traverse(req)

    assert res.seed_clause is not None
    assert res.seed_clause.id == "ICC_T20I_MEN_2026:21.18.1"
    assert res.parent_context is not None
    assert res.parent_context.id == "ICC_T20I_MEN_2026:21.18"

    roles = [node.evidence_role for node in res.assembled_nodes]
    assert roles == [EvidenceRole.DIRECT_EVIDENCE, EvidenceRole.PARENT_CONTEXT]
    assert res.assembled_nodes[1].hop_distance == 1


def test_hierarchy_traversal_hop_down_children(traversal_repo):
    service = HierarchyTraversalService(traversal_repo)
    req = HierarchyTraversalRequest(
        seed_clause_id="ICC_T20I_MEN_2026:21.18",
        candidate_document_ids=["ICC_T20I_MEN_2026"],
        include_parent=True,
        include_children=True,
        include_cross_references=False
    )
    res = service.traverse(req)

    assert res.seed_clause.id == "ICC_T20I_MEN_2026:21.18"
    assert res.parent_context is None
    assert len(res.operational_children) == 2
    child_ids = [c.id for c in res.operational_children]
    assert "ICC_T20I_MEN_2026:21.18.1" in child_ids
    assert "ICC_T20I_MEN_2026:21.18.2" in child_ids

    # Check evidence roles
    assert res.assembled_nodes[0].evidence_role == EvidenceRole.DIRECT_EVIDENCE
    assert all(n.evidence_role == EvidenceRole.OPERATIONAL_CHILD for n in res.assembled_nodes[1:])


def test_hierarchy_traversal_statutory_cross_references_and_bundle_confinement(traversal_repo):
    service = HierarchyTraversalService(traversal_repo)
    req = HierarchyTraversalRequest(
        seed_clause_id="ICC_T20I_MEN_2026:21.18.2",
        candidate_document_ids=["ICC_T20I_MEN_2026"],
        include_parent=False,
        include_children=False,
        include_cross_references=True
    )
    res = service.traverse(req)

    # In-bundle cross-ref resolved
    resolved_ids = [c.id for c in res.resolved_cross_references]
    assert "ICC_T20I_MEN_2026:21.17" in resolved_ids

    # Out-of-bundle cross-ref blocked
    assert "MCC_LAWS_2026:38.3" in res.blocked_out_of_bundle_targets

    # Non-existent target unresolved
    assert "ICC_T20I_MEN_2026:99.99" in res.unresolved_targets


def test_hierarchy_traversal_token_budget_pruning(traversal_repo):
    service = HierarchyTraversalService(traversal_repo)
    # Give a very tight token budget: sufficient for seed, but not seed + parent + children + xref
    req = HierarchyTraversalRequest(
        seed_clause_id="ICC_T20I_MEN_2026:21.18.2",
        candidate_document_ids=["ICC_T20I_MEN_2026"],
        include_parent=True,
        include_children=True,
        include_cross_references=True,
        token_budget=25  # seed has 19 words, parent has 15 words
    )
    res = service.traverse(req)

    assert res.budget_overflow is True
    # Seed must be preserved regardless of budget overflow
    assert len(res.assembled_nodes) >= 1
    assert res.assembled_nodes[0].evidence_role == EvidenceRole.DIRECT_EVIDENCE
    assert res.assembled_nodes[0].clause.id == "ICC_T20I_MEN_2026:21.18.2"
    # Ensure total tokens within or equal to seed if pruned
    assert res.token_count_estimate <= 25


def test_hierarchy_traversal_seed_blocked_if_out_of_bundle(traversal_repo):
    service = HierarchyTraversalService(traversal_repo)
    # Seed is in MCC_LAWS_2026, but candidate_document_ids only has ICC_T20I_MEN_2026
    req = HierarchyTraversalRequest(
        seed_clause_id="MCC_LAWS_2026:38.3",
        candidate_document_ids=["ICC_T20I_MEN_2026"]
    )
    res = service.traverse(req)

    assert res.seed_clause is None
    assert "MCC_LAWS_2026:38.3" in res.blocked_out_of_bundle_targets
    assert len(res.assembled_nodes) == 0


def test_hierarchy_traversal_structural_node_resolution(traversal_repo):
    from cricketiq.backend.app.retrieval.hierarchy.structure_store import ClauseStructureNodeStore
    store = ClauseStructureNodeStore()
    assert store.total_nodes == 46
    assert store.total_mapped_children == 267

    # Ensure source document exists for foreign key integrity
    doc_odi = SourceDocument(
        id="ICC_ODI_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's ODI Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format=CricketFormat.ODI,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/odi-2026.pdf",
        sha256="c" * 64,
        status=DocumentStatus.ACTIVE
    )
    traversal_repo.upsert_source_document(doc_odi)

    # Insert a child clause whose parent in the source is the unnumbered Law 1 heading
    child = RuleClause(
        id="ICC_ODI_MEN_2026:1.1",
        source_document_id="ICC_ODI_MEN_2026",
        clause_number="1.1",
        parent_clause_id=None,
        hierarchy_depth=1,
        heading="Number of players",
        original_text="A match is played between two sides of eleven players each.",
        page_start=4,
        page_end=4
    )
    traversal_repo.upsert_clauses([child])

    service = HierarchyTraversalService(traversal_repo, structure_store=store)
    req = HierarchyTraversalRequest(
        seed_clause_id="ICC_ODI_MEN_2026:1.1",
        candidate_document_ids=["ICC_ODI_MEN_2026"],
        include_parent=True
    )
    res = service.traverse(req)

    assert res.structural_context is not None
    assert res.structural_context.id == "ICC_ODI_MEN_2026:STRUCT_LAW_1"
    assert res.structural_context.heading_title == "THE PLAYERS"
    assert any(n.evidence_role == EvidenceRole.STRUCTURAL_CONTEXT for n in res.assembled_nodes)

