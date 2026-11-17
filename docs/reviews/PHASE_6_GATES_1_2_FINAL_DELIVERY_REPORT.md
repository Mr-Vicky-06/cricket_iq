# CricketIQ — Phase 6 Gates 1 & 2 Final Delivery Report
**Authoritative Source Discovery, Applicability Repair & Safe Corpus Reconciliation**

- **Date:** 2026-11-17
- **Milestone:** Phase 6 Gates 1 & 2 (Complete)
- **Starting Commit:** `0975ba8456c942f2be0d6446fdc051c31138b025`
- **Branch:** `master`
- **Status:** Verified & Promoted

---

## 1. Executive Summary

This report documents the completion of **Phase 6 Gate 1 (Authoritative Source Discovery)** and **Gate 2 (Applicability Engine Repair & Safe Database Reconciliation)** in CricketIQ.

### Key Milestones Achieved:
1. **Gate 1 Evidence-Led Discovery:** Evaluated all 51 failure cases from Benchmark v2. Confirmed that 100% of governing clauses exist in the 11 registered active documents. Completed an evidence-based **NO-OP acquisition** to avoid corpus bloat. Verified `SecureDocumentDownloader` security controls.
2. **Gate 2A Normative Baseline Repair:** Resolved the critical bug where `MCC_CHANGES_EXPLAINED_2026` overwrote `MCC_LAWS_2026`. Introduced explicit `RegulatoryRole` enum. Implemented catalog-order determinism ($4! = 24$ permutations tested and verified invariant). Reconstructed precedence bundles and fixed MCC edition matching.
3. **Gate 2B/2C Safe Database Reconciliation:** Built and executed `scripts/reconcile_database.py`. Created immutable online SQLite backup. Initialized a clean staging database (`data/cricketiq_staging.db`) from canonical corpus JSON files. Deduplicated clause IDs by selecting substantive text over TOC lines, resulting in exactly **10,388 unique canonical clauses** across all 11 documents. Purged **1,864 stale rows** (831 Devanagari Hindi rows, 817 duplicate un-namespaced appendices, 216 stale legacy extraction rows). Verified staging integrity and atomically promoted to `data/cricketiq.db`.
4. **Empirical Improvement:**
   - **MCC Laws Target Recall:** Jumped from **0.0% to 100.0%** (8/8 queries find target clauses in top 5).
   - **Benchmark v2 Sparse-Only Recall@5:** Increased from **43.14% to 47.06%**; MRR increased from **0.3804 to 0.4065**.
   - **Exact Clause Lookup Accuracy:** **100.0%**.
   - **Regulatory Bundle Leakage:** **0.0%**.
   - **Test Suites:** 107 backend tests passed (1 skipped), 23 frontend tests passed.
   - **API OpenAPI Compatibility:** Zero breaking changes.

---

## 2. Commit and Working Tree State

- **Starting Baseline Commit:** `0975ba8456c942f2be0d6446fdc051c31138b025`
- **Git Branch:** `master`
- **Working Tree State:** Clean, verified, and staged for milestone commit.

### Files Created:
1. `docs/reviews/PHASE_6_GATES_1_2_BASELINE_REFRESH.md` — Gate 0 baseline audit refresh and verification ledger.
2. `docs/PHASE_6_SOURCE_GAP_ANALYSIS.md` — Exhaustive failure analysis and source gap classification.
3. `docs/PHASE_6_SOURCE_DISCOVERY_REGISTER.md` — Authoritative source discovery register.
4. `data/sources/manifests/phase6_candidate_sources.json` — Formal machine-readable candidate source manifest.
5. `docs/reviews/PHASE_6_GATE_1_DELIVERY_REPORT.md` — Formal delivery report for Gate 1.
6. `scripts/reconcile_database.py` — Safe, two-phase database reconciliation and atomic promotion CLI tool.
7. `data/backups/cricketiq_backup_20261117_052444.db` — Verified pre-staging online backup.
8. `data/backups/cricketiq_pre_promote_20261117_052849.db` — Verified pre-promotion active database backup.
9. `data/backups/staging_manifest_20261117_052444.json` — Cryptographic promotion manifest.
10. `docs/reviews/PHASE_6_GATES_1_2_FINAL_DELIVERY_REPORT.md` — This comprehensive delivery report.

### Files Modified:
1. `cricketiq/backend/app/database/models.py` — Introduced `RegulatoryRole` enum and `@model_validator` on `SourceDocument`.
2. `cricketiq/backend/app/core/applicability_engine.py` — Fixed baseline MCC Laws overwrite, sorted active documents deterministically, supported multiple addenda, assembled bundles by precedence.
3. `cricketiq/backend/tests/test_applicability.py` — Added 4 exhaustive test suites verifying catalog-order permutation invariance, historical selection, multiple addenda, and explanatory guide isolation.
4. `data/cricketiq.db` — Reconciled active database with 10,388 canonical clauses, FTS5, and vector embeddings.
5. `evaluation/retrieval/results/eval_report_v1.json` — Post-reconciliation Benchmark v1 evaluation report.
6. `evaluation/retrieval/results/eval_report_v2.json` — Post-reconciliation Benchmark v2 evaluation report.
7. `docs/IMPLEMENTATION_ROADMAP.md` — Updated roadmap to mark Gates 1 and 2 complete.
8. `docs/RETRIEVAL_ARCHITECTURE.md` — Updated architecture with `RegulatoryRole` and reconciled inventory.

---

## 3. Gate 1 — Source Gap Analysis & Candidate Discovery

### Gap Analysis Summary
All 51 failing queries in Benchmark v2 were categorized into root causes:
- **Missing Source:** 0 queries (0.0%). Every required governing clause already exists in the 11 active documents.
- **Wrong Applicability Bundle:** 8 queries (15.7%). `MCC_CHANGES_EXPLAINED_2026` overwriting `MCC_LAWS_2026`.
- **Vocabulary Mismatch (Colloquial Terms):** 28 queries (54.9%). E.g., *"freebie"*, *"beamer"*, *"timed out"*, *"retired hurt"*.
- **Semantic Ranking Noise (Pseudo-Embeddings):** 11 queries (21.6%). Unweighted RRF allowing random hash vector ranks to displace lexical hits.
- **Clause Hierarchy & Granularity:** 4 queries (7.8%). Query seeking operational leaf clause when parent section matched.

### Candidate Document Review & Acquisition Decision
| Candidate Document | Issuing Body | Format / Category | Decision | Justification |
| :--- | :--- | :--- | :--- | :--- |
| **ICC DLS Regulations 2026** | ICC | ODI / T20I (General) | **Not Acquired (Deferred)** | Clauses 11, 12, 13 and Appendix E in existing ICC PCs already contain the normative match provisions. |
| **ICC Champions Trophy 2025 PC** | ICC | Men's ODI Tournament | **Not Acquired (Deferred)** | Out of current scope; tournament regulations are covered by format PCs. |
| **ICC Women's T20 World Cup 2024 PC** | ICC | Women's T20I Tournament | **Not Acquired (Deferred)** | Core format PC `ICC_T20I_WOMEN_2026` already covers all governing tournament rules. |
| **MCC Laws of Cricket 2017 Code 2nd Ed** | MCC | Universal Historical | **Not Acquired (Deferred)** | Historical queries in benchmark specifically test the 2022 3rd Edition (`MCC_LAWS_2022`). |

**Conclusion:** Fully justified **NO-OP acquisition gate**. Zero unnecessary downloads; zero index bloat.

### Downloader Security Audit
Audited `cricketiq/backend/app/ingestion/secure_downloader.py`:
- Protocol: Strict HTTPS on port 443 only.
- Hostname Allowlist: `www.icc-cricket.com`, `resources.pulse.icc-cricket.com`, `www.lords.org`, `mcc.org`.
- Anti-SSRF / DNS Rebinding: Hostnames resolved to IPs; IPv4 loopback, private RFC 1918, link-local, carrier-grade NAT, and cloud metadata (169.254.169.254) strictly rejected.
- Size and Content Validation: 50MB maximum stream limit, `%PDF-` magic byte verification.
- Immutability: Source files written to UUID paths with cryptographic SHA-256 recording.

---

## 4. Gate 2A — Applicability Engine Normative Baseline Repair

### Root Cause of Baseline Overwrite Defect
In `cricketiq/backend/app/core/applicability_engine.py`, `ApplicabilityEngine.resolve()` iterated through `catalog.list_active_documents()` using an arbitrary dictionary iteration order.
When an MCC document was encountered, it assigned:
```python
selected_mcc_baseline_doc = doc
```
Because `MCC_CHANGES_EXPLAINED_2026` was classified as `ScopeLevel.LAWS_BASELINE`, it matched the baseline selection block and overwrote `MCC_LAWS_2026`. When a general MCC query was evaluated, the retrieval bundle contained `['MCC_CHANGES_EXPLAINED_2026']` instead of `MCC_LAWS_2026`, dropping MCC query recall to 0%.

### Architectural Solution
1. **Domain Model Upgrade (`models.py`):**
   Introduced `RegulatoryRole(str, Enum)`:
   - `NORMATIVE_LAWS_BASELINE` (e.g., `MCC_LAWS_2026`, `MCC_LAWS_2022`)
   - `NORMATIVE_FORMAT_PC` (e.g., `ICC_TEST_MEN_2026`, `ICC_ODI_MEN_2026`, `ICC_T20I_MEN_2026`)
   - `NORMATIVE_COMPETITION_REGULATION` (e.g., `ICC_WTC_2025_2027_PC`)
   - `NORMATIVE_ADDENDUM` (e.g., `ICC_T20I_MEN_ADD_2026`)
   - `EXPLANATORY_GUIDANCE` (e.g., `MCC_CHANGES_EXPLAINED_2026`)
   - `ADMINISTRATIVE_REFERENCE`
   Added `regulatory_role` field to `SourceDocument` with backwards-compatible `@model_validator(mode="before")`.

2. **Resolver Invariants (`applicability_engine.py`):**
   - **Catalog-Order Invariance:** `active_docs = sorted(catalog.list_active_documents(), key=lambda d: d.id)`. Resolves identically regardless of catalog iteration order.
   - **Normative Baseline Exclusivity:** `selected_mcc_baseline_doc` only accepts documents with `regulatory_role == RegulatoryRole.NORMATIVE_LAWS_BASELINE`. Explanatory documents are tracked separately in `selected_explanatory_docs`.
   - **Multiple Addenda Support:** Multiple applicable addenda are collected into `selected_addenda_docs` and sorted deterministically by ID.
   - **Historical MCC Matching:** Refined `mcc_edition_matches` to prevent `"2017"` in `"2017 Code 4th Edition (2026)"` from incorrectly matching pre-2026 historical queries.
   - **Deterministic Precedence Assembly:** Bundles are assembled in strict legal precedence:
     $$\text{Competition Regulation} \rightarrow \text{Addenda} \rightarrow \text{Format PC} \rightarrow \text{Normative Baseline Laws} \rightarrow \text{Explanatory Guidance}$$

3. **Permutation Invariance Verification (`test_applicability.py`):**
   Added `test_catalog_order_permutation_invariance` testing all $4! = 24$ permutations of catalog document order (`MCC_LAWS_2026`, `MCC_CHANGES_EXPLAINED_2026`, `ICC_T20I_MEN_2026`, `ICC_T20I_MEN_ADD_2026`). All 24 permutations yielded 100% identical source bundles and deterministic decision traces.

---

## 5. Gate 2B/2C — Safe Database Reconciliation & Atomic Promotion

### Reconciliation Safety Architecture
Broad `DELETE` operations against the active database were strictly prohibited. Reconciliation followed a two-phase staging rebuild and atomic file swap:
1. **Immutable Online Backup:** Taken via SQLite's Online Backup API (`src_conn.backup(dst_conn)`) to ensure complete consistency even under concurrent read access.
2. **Staging Construction:** Built `data/cricketiq_staging.db` cleanly from canonical JSON files in `data/corpus/clauses/`.
3. **Substantive Clause Deduplication:** The 11 JSON files contained 11,008 list entries but 10,388 unique clause IDs due to 620 duplicate table-of-contents or running header items. Deduplication selected the entry with the longest `original_text`, ensuring substantive rule text was retained.
4. **Index Rebuilding:** Rebuilt SQLite FTS5 virtual table and deterministic 384-dimensional vector embeddings (`LocalDeterministicEmbeddingProvider`).
5. **Staging Validation:** Verified `PRAGMA integrity_check = ok`, 0 foreign key errors, exactly 10,388 rows across relational, FTS5, and vector tables, and 0 foreign language rows.
6. **Atomic Swap & Rollback Safety:** Swapped staging into active path on the same filesystem. Preserved pre-promotion active database in `data/backups/`.

### Inventory Ledger & Parity Table
| Document ID | Canonical Unique Clauses | Relational Rows (`rule_clauses`) | FTS5 Rows (`rule_clauses_fts`) | Vector Rows (`clause_embeddings`) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ICC_TEST_MEN_2026** | 1,213 | 1,213 | 1,213 | 1,213 | 100% Match |
| **ICC_ODI_MEN_2026** | 1,197 | 1,197 | 1,197 | 1,197 | 100% Match |
| **ICC_T20I_MEN_2026** | 1,201 | 1,201 | 1,201 | 1,201 | 100% Match |
| **ICC_T20I_MEN_ADD_2026** | 26 | 26 | 26 | 26 | 100% Match |
| **ICC_TEST_WOMEN_2026** | 1,216 | 1,216 | 1,216 | 1,216 | 100% Match |
| **ICC_ODI_WOMEN_2026** | 1,187 | 1,187 | 1,187 | 1,187 | 100% Match |
| **ICC_T20I_WOMEN_2026** | 1,206 | 1,206 | 1,206 | 1,206 | 100% Match |
| **ICC_WTC_2025_2027_PC** | 1,235 | 1,235 | 1,235 | 1,235 | 100% Match |
| **MCC_LAWS_2026** | 902 | 902 | 902 | 902 | 100% Match |
| **MCC_LAWS_2022** | 832 | 832 | 832 | 832 | 100% Match |
| **MCC_CHANGES_EXPLAINED_2026** | 173 | 173 | 173 | 173 | 100% Match |
| **TOTAL** | **10,388** | **10,388** | **10,388** | **10,388** | **100% Parity** |

### Rows Purged During Reconciliation (1,864 Rows Total):
1. **831 Stale Devanagari Hindi Rows:** Resided in `MCC_LAWS_2022` from an obsolete multilingual extraction. Completely removed.
2. **817 Stale Un-namespaced Appendix Rows:** Legacy un-prefixed appendix rows in ICC Playing Conditions. Completely replaced by canonical `APP_<X>:<num>` clauses.
3. **216 Stale Legacy Extraction Rows:** Inactive duplicate rows from previous parser revisions.

---

## 6. Cryptographic Backups & Integrity Verification

All backups are stored permanently in `data/backups/`:

| Backup File | Timestamp (UTC) | Size | SHA-256 Digest | Verification |
| :--- | :--- | :--- | :--- | :--- |
| `cricketiq_backup_20261117_052444.db` | 2026-11-17 05:24:44 | 70,643,712 bytes | `88173c0e1c87768c3777b00b1d65a6049a3e57f729ffecbba8729d9c6bfcfc46` | Online backup, integrity ok, 0 FK errors |
| `cricketiq_pre_promote_20261117_052849.db` | 2026-11-17 05:28:49 | 70,643,712 bytes | `0e60c453eddbea7a5fab6a47e8136b6dc544f852c6638680a03f321bdac34472` | Pre-promotion snapshot, integrity ok |
| **Promoted Active DB (`cricketiq.db`)** | 2026-11-17 05:28:49 | 58,638,336 bytes | `1b33cc43ccec8d132d2d3bbe5c9bfaa1b61cfec8d4b86c3440fea4d0cff66627` | Active reconciled DB, integrity ok, 0 FK errors |

Promotion manifest saved at `data/backups/staging_manifest_20261117_052444.json`.

---

## 7. Verification Evidence & Test Results

### 1. Backend Test Suite
```powershell
.\.venv\Scripts\pytest cricketiq/backend/tests -q
```
**Result:** `107 passed, 1 skipped in 6.83s` (0 failures).
- `test_applicability.py`: 14 passed (includes all new permutation invariance and historical selection tests).
- `test_rules_query_api.py`: 10 passed.
- `test_citation_validator.py`: 5 passed.
- `test_query_orchestrator.py`: 12 passed.
- `test_prompt_builder.py`: 8 passed.
- `test_llm_provider.py`: 11 passed.
- `test_persistence.py`: 1 passed, 1 skipped (Postgres integration).

### 2. Frontend Test Suite
```powershell
npm --prefix frontend run test:run
```
**Result:** `7 test files passed, 23 tests passed in 6.72s` (0 failures).
- `src/api/urlValidator.test.ts`: 8 passed.
- `src/api/client.test.ts`: 3 passed.
- `src/components/context/MatchContextPanel.test.tsx`: 2 passed.
- `src/components/answer/AnswerCard.test.tsx`: 1 passed.
- `src/components/answer/AbstentionCard.test.tsx`: 2 passed.
- `src/components/composer/QuestionInput.test.tsx`: 4 passed.
- `src/test/smoke.test.tsx`: 3 passed.

### 3. Retrieval Benchmark v2 (92 Queries — Persistent Database)
```powershell
.\.venv\Scripts\python evaluation/retrieval/evaluate_retrieval.py evaluation/retrieval/benchmark_v2.jsonl
```
| Metric | Baseline (Gate 0 Refresh) | Post-Gate 2 Reconciled Active DB | Delta / Status |
| :--- | :---: | :---: | :---: |
| **Sparse-Only (FTS5) Recall@5** | 43.14% | **47.06%** | **+3.92% improvement** |
| **Sparse-Only (FTS5) MRR** | 0.3804 | **0.4065** | **+0.0261 improvement** |
| **Exact Clause Lookup Accuracy** | 100.0% | **100.0%** | Maintained invariant |
| **Regulatory Bundle Leakage** | 0.0% | **0.0%** | Maintained invariant |
| **Supporting Clause Recall** | 54.35% | **54.35%** | Maintained |
| **MCC Laws Queries Recall@5 (8 queries)** | 0.0% (0/8) | **100.0% (8/8)** | **100% resolved** |

#### MCC Laws Queries Target Clause Verification:
- `mcc_law_001` (Appeals / Law 31.1): **Found (Rank 1)**
- `mcc_law_002` (Run Out / Law 38.3): **Found (Rank 1)**
- `mcc_law_003` (Hit the Ball Twice / Law 34.1): **Found (Rank 2)**
- `mcc_law_004` (Dead Ball / Law 20.1): **Found (Rank 1)**
- `mcc_law_005` (Boundaries / Law 19.5): **Found (Rank 3)**
- `mcc_law_006` (Deliberate Short Running / Law 18.5): **Found (Rank 1)**
- `mcc_law_007` (Fielder Position / Law 28.4): **Found (Rank 1)**
- `mcc_law_008` (No Ball Mode of Delivery / Law 21.2): **Found (Rank 1)**

### 4. Retrieval Benchmark v1 (65 Queries — Baseline Harness)
```powershell
.\.venv\Scripts\python evaluation/retrieval/evaluate_retrieval.py evaluation/retrieval/benchmark_v1.jsonl
```
- Sparse Recall@5: **85.34%** | MRR: **0.7284**
- Dense Recall@5: **87.07%** | MRR: **0.7511**
- Hybrid Recall@5: **89.66%** | MRR: **0.7477**
- Exact Clause Accuracy: **100.0%** | Leakage: **0.0%**

---

## 8. API Compatibility & Smoke Test Verification

### OpenAPI Schema Invariance
Extracted OpenAPI schema from live running backend (`http://127.0.0.1:8000/openapi.json`):
- Available Endpoints: `['/health/live', '/health/ready', '/v1/rules/query']`.
- Operation ID: `query_rules_v1_rules_query_post`.
- Request / Response Schemas: 100% backward compatible. Zero fields removed or altered.

### Live End-to-End Query Smoke Test
Sent live query to `POST /v1/rules/query`:
```json
{
  "query": "Can an umpire change a decision after signalling out?",
  "match_context": {
    "format": "general",
    "gender": "universal"
  }
}
```
**Response:** HTTP 200 OK, `status: answered`, grounded summary generated with verified citations.

---

## 9. Known Gaps & Readiness for Next Gates

1. **Vocabulary Mismatch (Colloquial Queries):**
   - Pure lexical search still misses queries containing informal slang (*"beamer"*, *"freebie"*, *"timed out"*, *"retired hurt"*).
   - *Next Action (Gate 3):* Implement `CricketDomainNormalizer` with query expansion using `cricket_lexicon.json`.
2. **Dense Search Pseudo-Embeddings:**
   - Vector search currently uses hash-based embeddings (`local-deterministic-v1`), contributing noise when fused.
   - *Next Action (Gate 4):* Integrate ONNX runtime with real transformer embeddings (`all-MiniLM-L6-v2` or `bge-small-en-v1.5`).
3. **Reciprocal Rank Fusion Weighting:**
   - Current RRF is unweighted ($k=60$).
   - *Next Action (Gate 5):* Implement weighted RRF with adaptive gating and cross-encoder reranking.

---

## 10. Conclusion & Gate Exit Sign-Off

All Gate 1 and Gate 2 exit criteria defined in the Phase 6 mandate have been rigorously satisfied:
- [x] Evidence-led source discovery complete and documented.
- [x] Zero unneeded documents acquired.
- [x] ApplicabilityEngine baseline overwrite defect resolved with explicit `RegulatoryRole`.
- [x] Catalog-order permutation invariance mathematically verified across all 24 permutations.
- [x] Reconciled staging database built from canonical corpus with verified immutable backups.
- [x] Database cleanly promoted to active path with 100% parity across relational, FTS5, and vector tables (10,388 rows).
- [x] All 107 backend tests and 23 frontend tests passing.
- [x] Zero breaking API contract changes.
- [x] 0.0% regulatory leakage and 100.0% exact clause lookup accuracy maintained.
- [x] Benchmark v2 MCC Laws target recall increased from 0% to 100%.

Phase 6 Gates 1 and 2 are formally **CLOSED**. The repository is in a pristine state and ready for **Gate 3**.
