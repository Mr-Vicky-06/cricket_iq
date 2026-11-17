# CricketIQ — Phase 6 Gate 2 Remediation Pre-Implementation Audit

- **Date:** 2026-11-17
- **Starting Baseline Commit:** `d2bf845bec7c7481fa1c3243aad3a96d9c90b6a5` (`master`)
- **Workspace:** `D:\Cricket_Rules_NLP_Chatbot`
- **Environment:**
  - Python: 3.14.10 (AMD64)
  - SQLite: 3.53.1
  - SQLAlchemy: 2.1.8
  - Pydantic: 2.14.3
  - FastAPI: 0.163.0
  - Pytest: 9.2.0
  - Node.js: v26.13.0
  - npm: 11.20.0
- **Status:** Complete (Pre-Implementation Audit)

---

## 1. Baseline Environment & Test Suite Verification

### A. Git Repository State
- **Branch:** `master`
- **HEAD Commit:** `d2bf845bec7c7481fa1c3243aad3a96d9c90b6a5` (`feat(phase6): complete Gates 1 and 2 (source discovery, applicability repair, and safe corpus reconciliation)`)
- **Working Tree:** Pristine and clean. Zero unstaged or untracked changes.

### B. Pre-Modification Test Suite Results
1. **Backend Tests:**
   ```powershell
   .\.venv\Scripts\pytest cricketiq/backend/tests -q
   ```
   **Output:** `107 passed, 1 skipped, 1 warning in 3.81s` (0 failures).
   - Skipped: `test_persistence.py::TestPostgresPersistence::test_postgres_connection_and_table_creation` (PostgreSQL environment skip).
2. **Frontend Tests:**
   ```powershell
   npm --prefix frontend run test:run
   ```
   **Output:** `7 test files passed, 23 passed in 3.92s` (0 failures).

---

## 2. Active Database & Canonical Corpus Inspection Ledger

### A. Active Database (`data/cricketiq.db`)
- **Path:** `D:\Cricket_Rules_NLP_Chatbot\data\cricketiq.db`
- **Size:** 58,638,336 bytes (55.92 MB)
- **SHA-256 Digest:** `1b33cc43ccec8d132d2d3bbe5c9bfaa1b61cfec8d4b86c3440fea4d0cff66627`
- **Integrity Check:** `PRAGMA integrity_check` $\rightarrow$ `[('ok',)]`
- **Foreign Key Check:** `PRAGMA foreign_key_check` $\rightarrow$ `0` errors
- **Relational Clauses (`rule_clauses`):** 10,388 rows
- **FTS5 Search Rows (`rule_clauses_fts`):** 10,388 rows
- **Vector Embeddings (`clause_embeddings`):** 10,388 rows
- **Identifier Set Equivalence:**
  - `relational_ids == fts_ids`: **True** (Exact set equality)
  - `relational_ids == embedding_ids`: **True** (Exact set equality)
- **Vector Store Metadata:**
  - Model Name: `{'local-deterministic-v1'}`
  - Dimensions: `{384}`
  - Template Versions: `{'v1'}`
  - Readiness Classification: **Diagnostic Pseudo-Vectors** (MD5 word hash feature buckets, non-semantic)
- **Source Documents:** 11 registered active documents

### B. Canonical Normalized JSON Corpus (`data/corpus/clauses/`)
- **Total JSON Files:** 11 files
- **Total List Items Across All Files:** 11,008 items
- **Total Duplicate Entries in Source Files:** 620 entries (TOC entries, page headers, cross-reference headings)
- **Total Unique Canonical Clause IDs:** 10,388 unique IDs
- **Deduplication Policy:** Select entry with longest `original_text` to preserve substantive rule bodies over running headers/page markers.

#### Per-Document Corpus & Active Database Breakdown
| Document ID | Canonical File | Items in JSON | Unique IDs | Duplicate IDs | Active DB Rows | Relational/FTS/Vector Parity |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **ICC_ODI_MEN_2026** | `ICC_ODI_MEN_2026_clauses.json` | 1,221 | 1,197 | 24 | 1,197 | 100% Match |
| **ICC_ODI_WOMEN_2026** | `ICC_ODI_WOMEN_2026_clauses.json` | 1,213 | 1,187 | 26 | 1,187 | 100% Match |
| **ICC_T20I_MEN_2026** | `ICC_T20I_MEN_2026_clauses.json` | 1,234 | 1,201 | 33 | 1,201 | 100% Match |
| **ICC_T20I_MEN_ADD_2026** | `ICC_T20I_MEN_ADD_2026_clauses.json` | 26 | 26 | 0 | 26 | 100% Match |
| **ICC_T20I_WOMEN_2026** | `ICC_T20I_WOMEN_2026_clauses.json` | 1,239 | 1,206 | 33 | 1,206 | 100% Match |
| **ICC_TEST_MEN_2026** | `ICC_TEST_MEN_2026_clauses.json` | 1,241 | 1,213 | 28 | 1,213 | 100% Match |
| **ICC_TEST_WOMEN_2026** | `ICC_TEST_WOMEN_2026_clauses.json` | 1,243 | 1,216 | 27 | 1,216 | 100% Match |
| **ICC_WTC_2025_2027_PC** | `ICC_WTC_2025_2027_PC_clauses.json` | 1,263 | 1,235 | 28 | 1,235 | 100% Match |
| **MCC_CHANGES_EXPLAINED_2026** | `MCC_CHANGES_EXPLAINED_2026_clauses.json` | 182 | 173 | 9 | 173 | 100% Match |
| **MCC_LAWS_2022** | `MCC_LAWS_2022_clauses.json` | 1,197 | 832 | 365 | 832 | 100% Match |
| **MCC_LAWS_2026** | `MCC_LAWS_2026_clauses.json` | 949 | 902 | 47 | 902 | 100% Match |
| **TOTAL** | **11 Files** | **11,008** | **10,388** | **620** | **10,388** | **100% Exact Parity** |

---

## 3. Systematic Review of Audit Claims & Findings

| Audit Dimension | Claimed Issue in Independent Review | Audit Finding | Classification | Remediation Plan |
| :--- | :--- | :--- | :--- | :--- |
| **2.1 Pseudo-Embedding Channel Safety** | `LocalDeterministicEmbeddingProvider` uses hash-based features and was allowed to participate in production RRF fusion. Dense ranks should not displace high-scoring lexical hits. | In `RetrievalService`, dense provider is initialized if provided. In production, unweighted RRF treated hash dense ranks equally with BM25. | **VERIFIED** | Enforce production retrieval to default to **exact + sparse lexical retrieval**. Exclude `local-deterministic-v1` from production RRF unless explicitly configured for diagnostic testing. Add tests for model metadata gating. |
| **2.2 Database Parity** | Set equality must be strictly verified across relational, FTS, vector, and canonical stores, not just count equality. Manifests must record sorted ID digests. | Active DB has exact ID set equality (`relational_ids == fts_ids == emb_ids == canonical_ids`), but manifest lacked cryptographic sorted ID set digest and FTS index config details. | **VERIFIED** | Upgrade `reconcile_database.py` to compute and record SHA-256 digests of sorted ID sets, per-document counts, and tokenizer settings in promotion manifests. |
| **2.3 Safe Promotion Protocol** | Active DB SHA before staging must match active DB SHA before promotion; staging must be revalidated immediately before swap; rollback copy must be retained until post-promotion checks pass. | Current `scripts/reconcile_database.py` created backup and swapped files, but did not assert active DB SHA remained unchanged during staging, nor did it enforce exclusive process locking or full rollback fault-injection tests. | **VERIFIED** | Implement pre-promotion active SHA invariant assertion, explicit exclusive lock (`reconcile.lock`), atomic swap error handling with Windows permission recovery, and comprehensive fault-injection test suite. |
| **2.4 Applicability Engine Multi-Document Selection** | Scalar selection for format PC and competition PC can silently overwrite if multiple candidates match; competition name matching was substring-based; role fallback defaulted to format PC. | `ApplicabilityEngine` resolves single format and competition doc. If multiple docs match, later sorted ID won silently. `context.competition` matching was simple string inclusion. Role fallback in validator defaulted to format PC. | **VERIFIED** | Add explicit cardinality & conflict detection: if multiple valid format or competition docs match without precedence rule, raise explicit ambiguous resolution / clarification. Validate canonical competition aliases. Reject/quarantine unknown regulatory roles. |
| **2.4 ORM Schema Column** | `source_documents` table in SQLite lacks `regulatory_role` column; Pydantic model infers it dynamically. | SQLite schema for `source_documents` has 20 columns; `regulatory_role` is present on Pydantic `SourceDocument` but not on ORM `SourceDocumentEntity`. | **VERIFIED** | Add `regulatory_role` column to `SourceDocumentEntity` and include migration / backward-compatible fallback in repository mapping. |

---

## 4. Remediation Implementation Strategy

1. **Phase 6 Gate 2 Remediation Scope:**
   - **Step 1:** Pseudo-Embedding Safety Gating in `RetrievalService` and provider factory.
   - **Step 2:** Database Parity & Manifest Integrity in `scripts/reconcile_database.py`.
   - **Step 3:** Promotion Protocol Hardening with Rollback & Lock Protection in `scripts/reconcile_database.py`.
   - **Step 4:** Applicability Engine Multi-Document Cardinality, Role Rejection & Canonical Competition Validation in `applicability_engine.py` and `models.py`.
   - **Step 5:** Comprehensive Unit & Fault-Injection Test Suite (`test_embedding_safety.py`, `test_reconciliation_protocol.py`, `test_applicability_remediation.py`).
2. **Phase 6 Gate 3 Pre-Implementation Audit Scope (Stage B):**
   - Audit `data/corpus/lexicon/cricket_lexicon.json` and create audit matrix.
   - Audit canonical hierarchy depth and cross-reference graph.
   - Audit table extraction assets in `data/extracted/`.
   - Design internal typed retrieval and table evidence contracts.
   - Author 5 Gate 3 design deliverables without modifying feature code.
