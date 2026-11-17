# CricketIQ — Phase 6 Gate 3 Hierarchy Migration & Dry-Run Report

- **Date:** 2026-11-17
- **Milestone:** Phase 6 — Gate 3 (Task 3.2 Hierarchy Depth & Relationship Repair)
- **Status:** **VERIFIED DRY-RUN COMPLETE** (Zero Invariant Breaches)
- **Script:** [`scripts/recompute_clause_depths.py`](file:///d:/Cricket_Rules_NLP_Chatbot/scripts/recompute_clause_depths.py)
- **Manifest Asset:** [`data/corpus/manifests/gate3_hierarchy_repairs.json`](file:///d:/Cricket_Rules_NLP_Chatbot/data/corpus/manifests/gate3_hierarchy_repairs.json)

---

## 1. Executive Summary

During the baseline audit, a critical parser legacy artifact was uncovered: in `data/corpus/clauses/` and `data/cricketiq.db`, all 10,388 canonical clauses possessed `hierarchy_depth: 1` regardless of actual nesting. Additionally, 357 parent links cited non-existent parent IDs in the same document due to omitted Law-level chapter headings and cross-document references.

`scripts/recompute_clause_depths.py` was executed in dry-run mode to calculate true tree depth and sanitize relationship links without altering canonical source records.

### Verified Invariants
- **Clause IDs:** **100% invariant** (10,388 unique IDs).
- **Original Text:** **100% invariant** (zero text changes).
- **ID Set SHA-256 Digest:** **100% invariant** (`8c85beb895d40d4379ecdc3d9829b924c176cdebc59289b33f2c408ef4968904`).
- **Graph Topology:** **0 cycles, 0 self-parents** (strictly acyclic directed forest).

---

## 2. Before vs After Depth Distribution Ledger

| Depth Level | Semantic Role in Cricket Regulations | Before Repair (Stored) | After Recalculation (True Depth) | Percentage of Corpus |
| :---: | :--- | :---: | :---: | :---: |
| **Depth 1** | Root Law / Section Headers (e.g. `Law 21 No ball`) | 10,388 | **720** | **6.93%** |
| **Depth 2** | Primary Substantive Rules (e.g. `21.5 Fair delivery - feet`) | 0 | **5,191** | **49.97%** |
| **Depth 3** | Granular Sub-clauses (e.g. `21.5.1 Back foot landing`) | 0 | **3,166** | **30.48%** |
| **Depth 4** | Operational Exceptions & Specific Conditions (e.g. `21.5.1.1`) | 0 | **1,311** | **12.62%** |
| **TOTAL** | — | **10,388** | **10,388** | **100.0%** |

---

## 3. Per-Document Hierarchy Recalculation Ledger

| Source Document ID | Total Unique Clauses | Depth 1 (Roots) | Depth 2 (Sections) | Depth 3 (Subclauses) | Depth 4 (Exceptions) | Repaired Records |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`ICC_ODI_MEN_2026`** | 1,197 | 76 | 556 | 390 | 175 | 1,152 |
| **`ICC_ODI_WOMEN_2026`** | 1,187 | 76 | 553 | 388 | 170 | 1,142 |
| **`ICC_T20I_MEN_2026`** | 1,201 | 77 | 559 | 397 | 168 | 1,156 |
| **`ICC_T20I_MEN_ADD_2026`** | 26 | 21 | 5 | 0 | 0 | 21 |
| **`ICC_T20I_WOMEN_2026`** | 1,206 | 77 | 558 | 397 | 174 | 1,161 |
| **`ICC_TEST_MEN_2026`** | 1,213 | 80 | 573 | 398 | 162 | 1,170 |
| **`ICC_TEST_WOMEN_2026`** | 1,216 | 80 | 577 | 397 | 162 | 1,173 |
| **`ICC_WTC_2025_2027_PC`** | 1,235 | 80 | 579 | 414 | 162 | 1,192 |
| **`MCC_CHANGES_EXPLAINED_2026`** | 173 | 75 | 83 | 15 | 0 | 172 |
| **`MCC_LAWS_2022`** | 832 | 5 | 827 | 0 | 0 | 827 |
| **`MCC_LAWS_2026`** | 902 | 73 | 321 | 370 | 138 | 859 |
| **TOTALS** | **10,388** | **720** | **5,191** | **3,166** | **1,311** | **10,245** |

---

## 4. Relationship Sanitization Details

1. **`MCC_CHANGES_EXPLAINED_2026` (74 Clauses):**
   - Previous state: `parent_clause_id` pointed to `MCC_CHANGES_EXPLAINED_2026:10.3` (which does not exist in the document).
   - Sanitized state: `parent_clause_id` set to `None`; statutory Law target `MCC_LAWS_2026:10.3` added to `cross_references`.
2. **`ICC_T20I_MEN_ADD_2026` (16 Clauses):**
   - Previous state: `parent_clause_id` pointed to `ICC_T20I_MEN_ADD_2026:2.1`.
   - Sanitized state: `parent_clause_id` set to `None`; base condition target `ICC_T20I_MEN_2026:2.1` added to `cross_references`.
3. **Absent Unnumbered Law Headings (267 Clauses):**
   - Parent IDs `:1`, `:7`, `:12`, `:24`, `:25`, `:42` represent Law titles with no legal body text.
   - Child clauses (`1.1`, `7.1`, `12.1`) now resolve as root Depth 1 in the relational clause tree, eliminating dangling foreign key/reference errors.
