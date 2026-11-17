"""Unit and Integration tests for Unified RetrievalService Gate 3 Capabilities (Phase 6 Gate 3 Task 3.5).
"""

import pytest
from sqlalchemy.orm import Session

from cricketiq.backend.app.database.connection import create_db_engine
from cricketiq.backend.app.database.orm_models import Base
from cricketiq.backend.app.database.models import (
    SourceDocument, RuleClause, DocumentAuthority, DocumentType, DocumentStatus,
    ClauseType, CricketFormat, GenderCategory, MatchContext
)
from cricketiq.backend.app.database.repository import CricketIQRepository
from cricketiq.backend.app.retrieval.contracts import (
    RetrievalRequest, RetrievalOutcome, RetrievalStatus, EvidenceRole
)
from cricketiq.backend.app.retrieval.sparse.sqlite_fts import SQLiteFTSSearchProvider
from cricketiq.backend.app.retrieval.service import RetrievalService
from cricketiq.backend.app.retrieval.nlp.lexicon_service import LexiconExpansionService
from cricketiq.backend.app.retrieval.hierarchy.traversal_service import HierarchyTraversalService
from cricketiq.backend.app.retrieval.tables.table_service import TableEvidenceService, TableEvidence, TableValidationStatus


@pytest.fixture
def gate3_repo():
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    repo = CricketIQRepository(session)

    # ICC T20I Men 2026
    doc_t20 = SourceDocument(
        id="ICC_T20I_MEN_2026",
        publisher=DocumentAuthority.ICC,
        title="ICC Men's T20I Playing Conditions",
        document_type=DocumentType.PLAYING_CONDITIONS,
        edition="October 2026",
        format=CricketFormat.T20I,
        category=GenderCategory.MENS,
        official_url="https://www.icc-cricket.com/t20i-2026.pdf",
        sha256="1" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc_t20)

    # MCC Laws 2026
    doc_mcc = SourceDocument(
        id="MCC_LAWS_2026",
        publisher=DocumentAuthority.MCC,
        title="MCC Laws of Cricket",
        document_type=DocumentType.LAW,
        edition="2026 Code",
        format=CricketFormat.TEST,
        category=GenderCategory.MENS,
        official_url="https://www.lords.org/mcc/laws.pdf",
        sha256="2" * 64,
        status=DocumentStatus.ACTIVE
    )
    repo.upsert_source_document(doc_mcc)

    # Clauses
    c_fh_parent = RuleClause(
        id="ICC_T20I_MEN_2026:21.18",
        source_document_id=doc_t20.id,
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
    c_fh_child = RuleClause(
        id="ICC_T20I_MEN_2026:21.18.2",
        source_document_id=doc_t20.id,
        clause_number="21.18.2",
        parent_clause_id=c_fh_parent.id,
        hierarchy_depth=3,
        heading="Free Hit Dismissals",
        original_text="For any free hit, the striker can be dismissed only under the circumstances that apply for a No ball.",
        normalized_text="for any free hit the striker can be dismissed only under the circumstances that apply for a no ball",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1,
        cross_references=["ICC_T20I_MEN_2026:21.17"]
    )
    c_nb = RuleClause(
        id="ICC_T20I_MEN_2026:21.17",
        source_document_id=doc_t20.id,
        clause_number="21.17",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="No Ball Laws",
        original_text="Clauses governing no ball penalties and beamers.",
        normalized_text="clauses governing no ball penalties and beamers",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )
    c_mankad = RuleClause(
        id="MCC_LAWS_2026:38.3",
        source_document_id=doc_mcc.id,
        clause_number="38.3",
        parent_clause_id=None,
        hierarchy_depth=2,
        heading="Non-striker leaving ground early",
        original_text="At any time from the moment the ball comes into play until the instant when the bowler would normally have been expected to release the ball, the non-striker is liable to be run out.",
        normalized_text="at any time from the moment the ball comes into play until the instant when the bowler would normally have been expected to release the ball the non-striker is liable to be run out",
        clause_type=ClauseType.RULE,
        page_start=10,
        page_end=10
    )

    repo.upsert_clauses([c_fh_parent, c_fh_child, c_nb, c_mankad])

    # Rebuild FTS
    fts = SQLiteFTSSearchProvider(repo)
    fts.rebuild_index()

    return repo


def test_retrieval_baseline_mode_flags_disabled(gate3_repo):
    """When all Gate 3 flags are False, behaves as Gate 2 baseline."""
    service = RetrievalService(
        repository=gate3_repo,
        enable_lexicon_expansion=False,
        enable_hierarchy_traversal=False,
        enable_table_evidence=False
    )
    req = RetrievalRequest(
        query="Free hit dismissals",
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    res = service.retrieve(req)

    assert res.status == RetrievalStatus.SUCCESS
    assert len(res.hits) > 0
    trace = res.query_diagnostics.get("observability_trace", {})
    assert trace.get("feature_flags", {}).get("enable_lexicon_expansion") is False
    assert trace.get("feature_flags", {}).get("enable_hierarchy_traversal") is False
    assert trace.get("feature_flags", {}).get("enable_table_evidence") is False
    # Privacy verification: raw query must be absent/None by default in production trace
    assert trace.get("original_sparse_query") is None
    assert trace.get("normalized_query_hash") is not None
    assert len(trace.get("expansion_variants", [])) == 0


def test_retrieval_lexicon_expansion_colloquial_term(gate3_repo):
    """When enable_lexicon_expansion is True, colloquial queries expand and rank relevant rules."""
    service = RetrievalService(
        repository=gate3_repo,
        enable_lexicon_expansion=True,
        enable_hierarchy_traversal=False,
        enable_table_evidence=False
    )
    # Query with colloquial term 'mankad'
    req = RetrievalRequest(
        query="mankad dismissal",
        match_context=MatchContext(format=CricketFormat.TEST, category=GenderCategory.MENS)
    )
    res = service.retrieve(req)

    assert res.status == RetrievalStatus.SUCCESS
    trace = res.query_diagnostics.get("observability_trace", {})
    assert len(trace.get("expansion_variants", [])) >= 1
    # Check that 38.3 was retrieved
    retrieved_cids = [h.clause_id for h in res.hits]
    assert "MCC_LAWS_2026:38.3" in retrieved_cids


def test_retrieval_hierarchy_traversal_integration(gate3_repo):
    """When enable_hierarchy_traversal is True, hops up to parent and lateral cross-refs."""
    service = RetrievalService(
        repository=gate3_repo,
        enable_lexicon_expansion=False,
        enable_hierarchy_traversal=True,
        enable_table_evidence=False
    )
    req = RetrievalRequest(
        query="21.18.2",  # Exact child clause lookup
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    res = service.retrieve(req)

    assert res.status == RetrievalStatus.SUCCESS
    roles = [h.evidence_role for h in res.hits]
    assert EvidenceRole.DIRECT_EVIDENCE in roles or EvidenceRole.PRIMARY in roles
    assert EvidenceRole.PARENT_CONTEXT in roles

    # Parent 21.18 should be present
    hit_cids = [h.clause_id for h in res.hits]
    assert "ICC_T20I_MEN_2026:21.18" in hit_cids


def test_retrieval_table_evidence_hydration(gate3_repo):
    """When enable_table_evidence is True, hydrates verified linked tables."""
    # Create TableEvidenceService with a registered table linked to 21.18
    tbl_service = TableEvidenceService(auto_load=False, repository=gate3_repo)
    tbl = TableEvidence(
        table_id="ICC_T20I_MEN_2026:TBL_P1_0",
        source_document_id="ICC_T20I_MEN_2026",
        page_number=1,
        headers=["No Ball Type", "Free Hit Permitted"],
        rows=[["Front foot", "Yes"], ["Beamer", "Yes"]],
        shape=(2, 2),
        linked_clause_ids=["ICC_T20I_MEN_2026:21.18"],
        validation_status=TableValidationStatus.SOURCE_VERIFIED
    )
    tbl_service.register_table(tbl)

    service = RetrievalService(
        repository=gate3_repo,
        enable_lexicon_expansion=False,
        enable_hierarchy_traversal=False,
        enable_table_evidence=True,
        table_service=tbl_service
    )
    req = RetrievalRequest(
        query="21.18",
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    res = service.retrieve(req)

    assert res.status == RetrievalStatus.SUCCESS
    table_hits = [h for h in res.hits if h.evidence_role == EvidenceRole.TABLE_SPECIFICATION]
    assert len(table_hits) == 1
    assert table_hits[0].clause_id == "ICC_T20I_MEN_2026:TBL_P1_0"
    assert "| Front foot | Yes |" in table_hits[0].original_text

    trace = res.query_diagnostics.get("observability_trace", {})
    assert "ICC_T20I_MEN_2026:TBL_P1_0" in trace.get("table_ids_hydrated", [])


def test_retrieval_all_gate3_features_active(gate3_repo):
    """All Gate 3 features active concurrently."""
    tbl_service = TableEvidenceService(auto_load=False, repository=gate3_repo)
    tbl = TableEvidence(
        table_id="ICC_T20I_MEN_2026:TBL_P1_0",
        source_document_id="ICC_T20I_MEN_2026",
        page_number=1,
        headers=["ColA", "ColB"],
        rows=[["Val1", "Val2"]],
        shape=(1, 2),
        linked_clause_ids=["ICC_T20I_MEN_2026:21.18"],
        validation_status=TableValidationStatus.SOURCE_VERIFIED
    )
    tbl_service.register_table(tbl)

    service = RetrievalService(
        repository=gate3_repo,
        enable_lexicon_expansion=True,
        enable_hierarchy_traversal=True,
        enable_table_evidence=True,
        table_service=tbl_service
    )
    req = RetrievalRequest(
        query="free hit rule",
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    res = service.retrieve(req)

    assert res.status == RetrievalStatus.SUCCESS
    assert len(res.hits) >= 1
    trace = res.query_diagnostics.get("observability_trace", {})
    assert trace["correlation_id"] is not None
    assert trace["feature_flags"]["enable_lexicon_expansion"] is True
    assert trace["feature_flags"]["enable_hierarchy_traversal"] is True
    assert trace["feature_flags"]["enable_table_evidence"] is True


def test_retrieval_query_wide_evidence_budget_cap(gate3_repo):
    """Verify query-wide budget: supporting snippets capped at <= 5 and token_estimate reported."""
    service = RetrievalService(
        repository=gate3_repo,
        enable_hierarchy_traversal=True,
        enable_table_evidence=True
    )
    req = RetrievalRequest(
        query="no ball call and procedure",
        match_context=MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    )
    res = service.retrieve(req)

    assert res.status == RetrievalStatus.SUCCESS
    primary_hits = [h for h in res.hits if h.evidence_role in (EvidenceRole.PRIMARY, EvidenceRole.DIRECT_EVIDENCE)]
    supporting_hits = [h for h in res.hits if h not in primary_hits]

    # Query-wide supporting evidence cap
    assert len(supporting_hits) <= 5

    trace = res.query_diagnostics.get("observability_trace", {})
    assert "token_estimate" in trace
    assert trace["token_estimate"] > 0
    assert "included_evidence_ids" in trace
    assert len(trace["included_evidence_ids"]) == len(res.hits)


def test_retrieval_dev_opt_in_privacy(gate3_repo):
    """Verify development-only opt-in populates original_sparse_query, while default omits it."""
    ctx = MatchContext(format=CricketFormat.T20I, category=GenderCategory.MENS)
    # Default: omitted
    s_default = RetrievalService(repository=gate3_repo)
    res_def = s_default.retrieve(RetrievalRequest(query="dead ball rule", match_context=ctx))
    assert res_def.status == RetrievalStatus.SUCCESS
    trace_def = res_def.query_diagnostics.get("observability_trace", {})
    assert trace_def.get("original_sparse_query") is None

    # Opt-in: present
    s_opt_in = RetrievalService(repository=gate3_repo, include_raw_query_in_diagnostics=True)
    res_opt = s_opt_in.retrieve(RetrievalRequest(query="dead ball rule", match_context=ctx))
    assert res_opt.status == RetrievalStatus.SUCCESS
    trace_opt = res_opt.query_diagnostics.get("observability_trace", {})
    assert trace_opt.get("original_sparse_query") == "dead ball rule"

