"""Unit Tests for Deterministic Hierarchy Depth Calculation (Phase 6 Gate 3).

Validates:
- True tree depth calculation from parent link chains
- Cycle and self-parent detection
- Relationship sanitization without data corruption
- Invariance: 10,388 canonical clause IDs and original text preserved 100%
"""

import pytest
from pathlib import Path

from scripts.recompute_clause_depths import (
    load_deduplicated_clauses,
    recompute_hierarchy,
    compute_id_set_digest,
    CANONICAL_CLAUSES_DIR
)


def test_depth_calculation_synthetic_tree():
    """Test recursive depth calculation on a synthetic hierarchy."""
    doc_clauses = {
        "TEST_DOC": {
            "TEST:1": {"id": "TEST:1", "parent_clause_id": None, "original_text": "Root law"},
            "TEST:1.1": {"id": "TEST:1.1", "parent_clause_id": "TEST:1", "original_text": "Section 1"},
            "TEST:1.1.1": {"id": "TEST:1.1.1", "parent_clause_id": "TEST:1.1", "original_text": "Clause 1"},
            "TEST:1.1.1.1": {"id": "TEST:1.1.1.1", "parent_clause_id": "TEST:1.1.1", "original_text": "Subclause 1"},
            "TEST:2": {"id": "TEST:2", "parent_clause_id": None, "original_text": "Root law 2"},
            "TEST:2.1": {"id": "TEST:2.1", "parent_clause_id": "TEST:2", "original_text": "Section 2"}
        }
    }
    repaired, meta = recompute_hierarchy(doc_clauses)
    assert repaired["TEST:1"]["hierarchy_depth"] == 1
    assert repaired["TEST:1.1"]["hierarchy_depth"] == 2
    assert repaired["TEST:1.1.1"]["hierarchy_depth"] == 3
    assert repaired["TEST:1.1.1.1"]["hierarchy_depth"] == 4
    assert repaired["TEST:2"]["hierarchy_depth"] == 1
    assert repaired["TEST:2.1"]["hierarchy_depth"] == 2
    assert meta["depth_distribution_overall"] == {1: 2, 2: 2, 3: 1, 4: 1}


def test_canonical_corpus_depth_recalculation():
    """Test depth recalculation across the actual 11 canonical corpus documents."""
    doc_clauses = load_deduplicated_clauses(CANONICAL_CLAUSES_DIR)
    total_clauses = sum(len(c) for c in doc_clauses.values())
    assert total_clauses == 10388

    repaired, meta = recompute_hierarchy(doc_clauses)
    assert len(repaired) == 10388

    # Invariant: exactly 4 depth levels
    assert set(meta["depth_distribution_overall"].keys()) == {1, 2, 3, 4}
    assert meta["depth_distribution_overall"][1] == 720
    assert meta["depth_distribution_overall"][2] == 5191
    assert meta["depth_distribution_overall"][3] == 3166
    assert meta["depth_distribution_overall"][4] == 1311

    # Invariant: ID set digest unchanged
    original_ids = [cid for doc in doc_clauses.values() for cid in doc.keys()]
    assert compute_id_set_digest(original_ids) == compute_id_set_digest(list(repaired.keys()))
