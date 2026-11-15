"""Unit tests for Bounded Evidence Graph Expansion (Gate 5).
"""

import pytest
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus, ClauseType
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import RetrievalHit, EvidenceRole
from cricketiq.backend.app.retrieval.expansion.evidence_expander import EvidenceExpander


@pytest.fixture
def repo_with_hierarchy_and_references() -> CricketIQRepository:
    """Setup repository with parent-child hierarchy and cross-reference edges."""
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    doc = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format="T20I",
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc)

    # 21.18 Free Hit (Parent)
    c_parent = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc.id,
        clause_number="21.18",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Free Hit",
        original_text="The delivery following a No ball shall be a free hit.",
        normalized_text="the delivery following a no ball shall be a free hit",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    # 21.18.2 Free Hit Dismissals (Child, references 21.17)
    c_child = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=doc.id,
        clause_number="21.18.2",
        parent_clause_id=c_parent.id,
        hierarchy_depth=3,
        heading="Free Hit Dismissals",
        original_text="The striker can be dismissed only under circumstances of a No ball.",
        normalized_text="the striker can be dismissed only under circumstances of a no ball",
        clause_type=ClauseType.EXCEPTION,
        cross_references=["21.17"],
        page_start=1,
        page_end=1
    )
    # 21.17 Dismissals from a No ball (Target of cross-reference)
    c_ref = RuleClause(
        id="ICC_T20I_MEN_2026:21.17",
        source_document_id=doc.id,
        clause_number="21.17",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Dismissals from a No ball",
        original_text="Neither batter shall be out off that delivery except for Run out, Hit the ball twice, Obstructing the field.",
        normalized_text="neither batter shall be out off that delivery except for run out hit the ball twice obstructing the field",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    repo.upsert_clauses([c_parent, c_child, c_ref])
    return repo


def test_evidence_expansion_composite_retrieval(repo_with_hierarchy_and_references):
    """Verify that retrieving 21.18.2 automatically brings parent 21.18 and cross-ref 21.17."""
    repo = repo_with_hierarchy_and_references
    expander = EvidenceExpander(repo)

    primary_hit = RetrievalHit(
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        document_id="ICC_T20I_MEN_2026",
        clause_number="21.18.2",
        heading="Free Hit Dismissals",
        original_text="The striker can be dismissed only under circumstances of a No ball.",
        normalized_text="the striker can be dismissed only under circumstances of a no ball",
        evidence_role=EvidenceRole.PRIMARY,
        relationship_path=["ICC_T20I_MEN_2026:21.18.2"]
    )

    expanded = expander.expand(
        primary_hits=[primary_hit],
        candidate_document_ids=["ICC_T20I_MEN_2026"],
        include_parent_context=True,
        include_related_evidence=True
    )

    # Must contain 3 hits: primary 21.18.2, parent 21.18, and related 21.17
    assert len(expanded) == 3

    roles = {h.clause_number: h.evidence_role for h in expanded}
    assert roles["21.18.2"] == EvidenceRole.PRIMARY
    assert roles["21.18"] == EvidenceRole.PARENT_CONTEXT
    assert roles["21.17"] == EvidenceRole.RELATED_SUPPORT

    # Check reason strings
    parent_hit = next(h for h in expanded if h.clause_number == "21.18")
    assert "Parent context" in parent_hit.applicability_reason

    rel_hit = next(h for h in expanded if h.clause_number == "21.17")
    assert "Cross-referenced by Clause 21.18.2" in rel_hit.applicability_reason


def test_evidence_expansion_bundle_confinement(repo_with_hierarchy_and_references):
    """Verify expansion never brings in clauses outside candidate documents."""
    repo = repo_with_hierarchy_and_references
    expander = EvidenceExpander(repo)

    primary_hit = RetrievalHit(
        clause_id="ICC_T20I_MEN_2026:21.18.2",
        document_id="ICC_T20I_MEN_2026",
        clause_number="21.18.2",
        heading="Free Hit Dismissals",
        original_text="The striker can be dismissed only under circumstances of a No ball.",
        normalized_text="the striker can be dismissed only under circumstances of a no ball",
        evidence_role=EvidenceRole.PRIMARY,
        relationship_path=["ICC_T20I_MEN_2026:21.18.2"]
    )

    # Restrict to an unrelated document where these clauses are NOT valid
    expanded = expander.expand(
        primary_hits=[primary_hit],
        candidate_document_ids=["OTHER_DOC_ID"],
        include_parent_context=True,
        include_related_evidence=True
    )

    # Only primary hit remains, no out-of-scope clauses added
    assert len(expanded) == 1
    assert expanded[0].clause_id == "ICC_T20I_MEN_2026:21.18.2"
