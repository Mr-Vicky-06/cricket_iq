"""Unit tests for Reciprocal Rank Fusion (Gate 5).
"""

import pytest
from cricketiq.backend.app.database.models import RuleClause, ClauseType
from cricketiq.backend.app.retrieval.contracts import RetrievalHit, EvidenceRole
from cricketiq.backend.app.retrieval.fusion.rrf import RRFEngine


def make_clause(cid: str, cnum: str) -> RuleClause:
    return RuleClause(
        id=cid,
        source_document_id="DOC_1",
        clause_number=cnum,
        heading=f"Heading {cnum}",
        original_text=f"Content for {cnum}",
        clause_type=ClauseType.RULE,
        page_start=1,
        page_end=1
    )


def test_rrf_formula_and_deduplication():
    """Verify 1/(k+rank) formula and clause deduplication."""
    c1 = make_clause("c1", "21.1")
    c2 = make_clause("c2", "21.2")
    c3 = make_clause("c3", "21.3")

    # Sparse: c1 (rank 1), c2 (rank 2)
    sparse_list = [(c1, 10.0), (c2, 5.0)]
    # Dense: c2 (rank 1), c3 (rank 2)
    dense_list = [(c2, 0.95), (c3, 0.85)]

    engine = RRFEngine(k=60)
    hits = engine.fuse(sparse_list, dense_list, top_k=5)

    # c2 is present in both lists: 1/(60+2) + 1/(60+1) = 1/62 + 1/61 ≈ 0.016129 + 0.016393 ≈ 0.032522
    # c1 is rank 1 in sparse only: 1/(60+1) = 1/61 ≈ 0.016393
    # c3 is rank 2 in dense only: 1/(60+2) = 1/62 ≈ 0.016129
    assert len(hits) == 3
    assert hits[0].clause_id == "c2"
    assert hits[1].clause_id == "c1"
    assert hits[2].clause_id == "c3"

    expected_c2_score = round(1.0 / 62 + 1.0 / 61, 6)
    assert abs(hits[0].rrf_score - expected_c2_score) < 1e-4

    # Check rank provenance
    assert hits[0].sparse_rank == 2
    assert hits[0].dense_rank == 1
    assert hits[1].sparse_rank == 1
    assert hits[1].dense_rank is None


def test_rrf_exact_match_top_priority():
    """Verify that exact clause lookup matches receive top priority."""
    c_exact = make_clause("c_exact", "21.18.2")
    c_other = make_clause("c_other", "21.1")

    sparse_list = [(c_other, 20.0)]
    dense_list = [(c_other, 0.99)]
    exact_list = [(c_exact, 1.0)]

    engine = RRFEngine(k=60)
    hits = engine.fuse(sparse_list, dense_list, exact_results=exact_list, top_k=5)

    assert len(hits) == 2
    assert hits[0].clause_id == "c_exact"
    assert hits[1].clause_id == "c_other"


def test_rrf_deterministic_tie_breaking():
    """Verify stable ordering when scores tie."""
    c_a = make_clause("id_a", "21.1")
    c_b = make_clause("id_b", "21.2")

    # Both rank 1 in sparse only
    sparse_list = [(c_a, 10.0), (c_b, 10.0)]
    engine = RRFEngine(k=60)
    hits1 = engine.fuse(sparse_list, [], top_k=2)
    hits2 = engine.fuse(sparse_list, [], top_k=2)

    assert [h.clause_id for h in hits1] == [h.clause_id for h in hits2]
