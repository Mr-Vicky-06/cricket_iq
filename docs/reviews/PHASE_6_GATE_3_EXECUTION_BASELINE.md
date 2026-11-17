# CricketIQ — Phase 6 Gate 3 Execution Baseline Verification

- **Date:** 2026-11-17
- **Milestone:** Phase 6 — Gate 3 (Baseline State Audit)
- **Starting Git Commit:** `475baa01b704c0bb561f2a1a51840839afea1f35` (`master`)
- **Working Tree State:** Clean (0 untracked, 0 unstaged changes)
- **Environment:**
  - Python: `3.14.10 (MSC v.1944 64-bit AMD64)`
  - Operating System: `Windows-11-10.0.26300-SP0`
  - Virtual Environment: `D:\Cricket_Rules_NLP_Chatbot\.venv`
  - SQLite: `3.53.1`
  - Node.js: `v26.13.0`
  - npm: `11.20.0`
- **Active Database Path:** `data/cricketiq.db`
- **Database Size:** 58,638,336 bytes (55.92 MB)
- **Database SHA-256:** `7720a9444cfbd91f94649fbfa1021eb41cf859d89c7ffa005b980776d0fa179a`

---

## 1. Baseline Test Suite Verification

### A. Backend Pytest Suite
```powershell
.\.venv\Scripts\pytest cricketiq/backend/tests -v
```
- **Total Tests Collected:** 128
- **Passed:** **127**
- **Skipped:** 1 (`test_persistence.py::TestPostgresPersistence::test_postgres_connection_and_table_creation` — skipped due to absence of local PostgreSQL server)
- **Failed:** 0
- **Duration:** 10.06s
- **Status:** 100% passing across all unit, security, applicability, sparse FTS, dense safety, and reconciliation fault-injection suites.

### B. Frontend Vitest Suite
```powershell
npm --prefix frontend run test:run
```
- **Test Files:** 7 passed across 7 files
- **Total Tests:** **23 passed**
- **Failed:** 0
- **Duration:** 6.03s
- **Status:** 100% passing across UI components, API client, URL allowlist validators, and smoke tests.

---

## 2. Benchmark v2 Production-Safe Baseline (92 Queries)

Evaluated with `evaluate_retrieval.py` against active SQLite database `data/cricketiq.db`:

```powershell
.\.venv\Scripts\python.exe evaluation/retrieval/evaluate_retrieval.py evaluation/retrieval/benchmark_v2.jsonl
```

### Official Baseline Performance Metrics

| Metric | Sparse-Only (SQLite FTS5) [Production-Safe] | Dense-Only (NumPy Hash) [Diagnostic] | Hybrid (RRF Fusion) [Diagnostic] |
| :--- | :---: | :---: | :---: |
| **Recall@1** | 35.37% | 29.88% | 32.93% |
| **Recall@3** | 42.07% | 32.32% | 40.24% |
| **Recall@5** | **47.06%** | 34.12% | 41.18% |
| **Recall@10** | 47.06% | 34.12% | 41.18% |
| **MRR** | **0.4065** | 0.3257 | 0.3745 |
| **nDCG@5** | 0.5781 | 0.4645 | 0.5316 |
| **nDCG@10** | 0.5781 | 0.4645 | 0.5316 |
| **Exact Clause Accuracy** | **100.0%** | 100.0% | 100.0% |
| **Supporting Clause Recall** | 54.35% | 56.52% | 58.70% |
| **Regulatory Leakage Rate** | **0.0%** | 0.0% | 0.0% |
| **p50 Latency (Median)** | **35.99 ms** | 63.06 ms | 80.34 ms |
| **p95 Latency** | **47.63 ms** | 70.68 ms | 101.82 ms |
| **p99 Latency** | 58.41 ms | 90.89 ms | 111.40 ms |
| **Mean Latency** | 34.76 ms | 61.22 ms | 80.95 ms |

### Dense Channel Safety Invariant Assertion
- Stored Embedding Model: `local-deterministic-v1` (Dimension: 384, Template: v1)
- Provider `is_semantic` flag: `False`
- `RetrievalService` default `enable_diagnostic_dense`: `False`
- Readiness Probe: `(False, "Dense search disabled: stored model 'local-deterministic-v1' is a non-semantic diagnostic hash model and is excluded from production ranking.")`
- **Proof:** Production ranking strictly isolates to Exact Clause Lookup + Sparse FTS5 BM25. Diagnostic pseudo-vectors cannot displace high-scoring lexical hits.

---

## 3. Public API Contract & OpenAPI Snapshot

- **Route:** `POST /v1/rules/query`
- **OpenAPI Schema SHA-256:** `0e4bd7a38cc46501d7a0e82bec0b5fb9441e74b1554555bb6019cf10ee48a3da`
- **Frozen Contract Check:** All Gate 3 extensions must remain internal to retrieval pipeline; zero alterations to `/v1/rules/query` schema are permitted.

---

## 4. Cryptographic Asset Ledger

### A. Authoritative Source Database
- Path: `data/cricketiq.db`
- SHA-256: `7720a9444cfbd91f94649fbfa1021eb41cf859d89c7ffa005b980776d0fa179a`
- PRAGMA `integrity_check`: `ok`
- PRAGMA `foreign_key_check`: `0 errors`
- Relational Clauses: 10,388
- FTS5 Rows: 10,388
- Embeddings: 10,388
- Source Documents: 11

### B. Cricket Domain Lexicon
- Path: `data/corpus/lexicon/cricket_lexicon.json`
- SHA-256: `04714a3a4bfcfc99a1e6cd7fb4ccfeea78e1b4823a5293076e766422a25bab45`

### C. Canonical Corpus Clauses (`data/corpus/clauses/`)
| File Name | SHA-256 Digest |
| :--- | :--- |
| `ICC_ODI_MEN_2026_clauses.json` | `80fe7816c2c64766a996f5bd6b01dccfb06e6019b61683d14a3ec1d915606ad9` |
| `ICC_ODI_WOMEN_2026_clauses.json` | `7737c4d0a7c2cff636fb3ba74a634ebb9be651cef25ef081e084692de588badd` |
| `ICC_T20I_MEN_2026_clauses.json` | `56f2872934e9b5d40e3ab46ad7c529b2e04eb6509aead0f2c3d2e987db2f908c` |
| `ICC_T20I_MEN_ADD_2026_clauses.json` | `f15325e642fccb76dd99b62495a9e0bfa611e93ee2269cdd4a91f180960d804e` |
| `ICC_T20I_WOMEN_2026_clauses.json` | `ea70d0d8e9047779af09d56ff996d402b8228b2b1fe2fab72a28d08c88944b5f` |
| `ICC_TEST_MEN_2026_clauses.json` | `a93cef140bc34fb1c6d9dab742663e7dd32ec4fc1532e5755b9b3ee91414cc43` |
| `ICC_TEST_WOMEN_2026_clauses.json` | `ee45a6846b05334da91ebd30ab2a8a1d143d07d060104ae6b9ee2b88e67affd5` |
| `ICC_WTC_2025_2027_PC_clauses.json` | `a2fd2dc1673271e48244c9a01e4b9da84e6e023677a681762ea57f7bb5d482cc` |
| `MCC_CHANGES_EXPLAINED_2026_clauses.json` | `eef2c93e6ae4982a3223342ce845b7519d7b5436fdd35d3ce353ef73fd9fb58b` |
| `MCC_LAWS_2022_clauses.json` | `582b249a99b634a58632ffba48c3fd477902f0c97f9d45ecd177e53b415985bd` |
| `MCC_LAWS_2026_clauses.json` | `210ce9cef79b27e7e6cb1cf3d1c73af9da7ddd68e0dc5bcdd41518777aead396` |

### D. Extracted Tables (`data/extracted/tables/`)
| File Name | SHA-256 Digest |
| :--- | :--- |
| `ICC_ODI_MEN_2026_tables.json` | `257bf3cc07c5d949086715c4daacbacc079e14c862964cb0f061116a7365c866` |
| `ICC_ODI_WOMEN_2026_tables.json` | `5fa13e3a7e2f0feff34d1dba686a16c54fec75c9a5cd1853a625eddd6a7d41cd` |
| `ICC_T20I_MEN_2026_tables.json` | `f8b1af55ca28490c726e518e459443b4b6d81d4b31582a91556efb324b8091f6` |
| `ICC_T20I_MEN_ADD_2026_tables.json` | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `ICC_T20I_WOMEN_2026_tables.json` | `20e793b93ed7b94257ddf073343a5716b240522e90be9ac4327e03f5eb178e8f` |
| `ICC_TEST_MEN_2026_tables.json` | `829790ae10d89d2d1c9667fa81d0f2afd95598b1b5b72d7268d918faeb2432a8` |
| `ICC_TEST_WOMEN_2026_tables.json` | `b7a9abea5a7596fc9baf7c7051dab0f78cb1a122be10d82bc8d15320b6d0d19d` |
| `ICC_WTC_2025_2027_PC_tables.json` | `1cfe12f8ecd4241e760c55c2b3c0caed67acdf2dd74ec6b9e5b2dab869615cfa` |
| `MCC_CHANGES_EXPLAINED_2026_tables.json` | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| `MCC_LAWS_2022_tables.json` | `c7987e7b6978fcbc2c11794d57eb826de87719e22e6b8bd8345d6425d21ffddd` |
| `MCC_LAWS_2026_tables.json` | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |

---

## 5. Gate 0 Exit Sign-Off

- **Baseline Working Tree:** Clean. Commit `475baa01b704c0bb561f2a1a51840839afea1f35`.
- **Test Integrity:** All 127 backend and 23 frontend tests pass.
- **Benchmark v2 Baseline Recorded:** Exact Acc = 100.0%, Leakage = 0.0%, Sparse-Only Recall@5 = 47.06%, p50 = 35.99 ms, p95 = 47.63 ms.
- **API & Frontend Freeze:** OpenAPI schema hashed and preserved.
- **Gate 0 Status:** **PASSED**. Proceeding to Gate 1 (Inventory Reconciliation).
