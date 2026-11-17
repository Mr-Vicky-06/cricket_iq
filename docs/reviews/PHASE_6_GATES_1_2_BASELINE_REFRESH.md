# CricketIQ — Phase 6 Gates 1–2 Baseline Refresh & Pre-Execution Audit
## Audit Refresh: Environment, Active Database State, Test Suites & Benchmark Archive

**Document ID:** `CRICKETIQ-PHASE-6-REFRESH-001`  
**Date:** 2026-11-17  
**Status:** COMPLETE / VERIFIED  
**Author:** Principal Software Architect & QA Engineer  
**Workspace:** `D:\Cricket_Rules_NLP_Chatbot`  
**Git Baseline:** `0975ba8456c942f2be0d6446fdc051c31138b025` (`master`)  

---

## 1. Environment & Git Baseline Verification

The working environment and Git tracking state were verified prior to any code or data modifications:

```powershell
git status --short
git branch --show-current
git rev-parse HEAD
git log -5 --oneline
git remote -v
```

### Verified Properties:
- **Active Branch:** `master`
- **Current HEAD Commit:** `0975ba8456c942f2be0d6446fdc051c31138b025`
- **Remote:** `https://github.com/Mr-Vicky-06/cricket_iq.git` (tracked cleanly, 0 commits ahead/behind)
- **Working Tree:** Completely clean (zero untracked or unstaged user changes)
- **Runtime Environment:** Windows 11, PowerShell 5.1 / 7, Python 3.12.10 (`.venv`), Node.js v20.18.0, pnpm 9.15.4

---

## 2. Pre-Modification Test Suite Results

Both backend and frontend regression suites were executed against the unmodified baseline:

### 2.1 Backend Pytest Suite
- **Command:** `.\.venv\Scripts\pytest cricketiq/backend/tests -q`
- **Result:** **103 passed, 1 skipped**, 1 warning in 7.45s
- **Status:** PASS (100% success rate on active tests)

### 2.2 Frontend Vitest Suite
- **Command:** `pnpm --dir frontend test:run`
- **Result:** **23 passed across 7 test files** in 5.45s
  - `src/api/urlValidator.test.ts`: 8 passed
  - `src/api/client.test.ts`: 3 passed
  - `src/components/context/MatchContextPanel.test.tsx`: 2 passed
  - `src/components/answer/AnswerCard.test.tsx`: 1 passed
  - `src/components/answer/AbstentionCard.test.tsx`: 2 passed
  - `src/components/composer/QuestionInput.test.tsx`: 4 passed
  - `src/test/smoke.test.tsx`: 3 passed
- **Status:** PASS

---

## 3. Baseline Benchmark Archive Execution

The retrieval evaluator `evaluation/retrieval/evaluate_retrieval.py` was executed against both benchmark suites, and its complete execution logs and JSON reports were archived under `evaluation/retrieval/results/archive/phase6_gate0_refresh/`:

### 3.1 Benchmark v1 (In-Memory Baseline — 65 Queries)
- **Console Log:** `evaluation/retrieval/results/archive/phase6_gate0_refresh/benchmark_v1_console.txt`
- **Report JSON:** `evaluation/retrieval/results/archive/phase6_gate0_refresh/eval_report_v1.json`
- **Metrics Summary:**
  - Sparse-Only (FTS5): Recall@5 = **85.34%**, MRR = **0.7284**, Exact Acc = **100.0%**, Supp Recall = **100.0%**, Leakage = **0.0%**, Latency = **5.75 ms**
  - Dense-Only (Hash): Recall@5 = **87.07%**, MRR = **0.7511**, Exact Acc = **100.0%**, Supp Recall = **100.0%**, Leakage = **0.0%**, Latency = **5.84 ms**
  - Hybrid (RRF + Expansion): Recall@5 = **89.66%**, MRR = **0.7477**, Exact Acc = **100.0%**, Supp Recall = **100.0%**, Leakage = **0.0%**, Latency = **6.35 ms**

### 3.2 Benchmark v2 (Full Database — 92 Queries)
- **Console Log:** `evaluation/retrieval/results/archive/phase6_gate0_refresh/benchmark_v2_console.txt`
- **Report JSON:** `evaluation/retrieval/results/archive/phase6_gate0_refresh/eval_report_v2.json`
- **Metrics Summary:**
  - Sparse-Only (FTS5): Recall@5 = **44.71%**, MRR = **0.3749**, Exact Acc = **100.0%**, Supp Recall = **54.35%**, Leakage = **0.0%**, Latency = **64.17 ms**
  - Dense-Only (Hash): Recall@5 = **33.53%**, MRR = **0.2955**, Exact Acc = **100.0%**, Supp Recall = **47.83%**, Leakage = **0.0%**, Latency = **54.45 ms**
  - Hybrid (RRF + Expansion): Recall@5 = **38.82%**, MRR = **0.3373**, Exact Acc = **100.0%**, Supp Recall = **54.35%**, Leakage = **0.0%**, Latency = **70.92 ms**

---

## 4. Active Database State vs. Canonical Corpus Inventory

Direct database reflection queries were run against `data/cricketiq.db` to capture its exact state:

### 4.1 Database Properties
- **File Path:** `D:\Cricket_Rules_NLP_Chatbot\data\cricketiq.db`
- **File Size:** `70,643,712 bytes` (67.37 MB)
- **SHA-256 Digest:** `0e60c453eddbea7a5fab6a47e8136b6dc544f852c6638680a03f321bdac34472`
- **PRAGMA integrity_check:** `ok`
- **PRAGMA foreign_key_check:** `[]` (0 foreign key violations)
- **PRAGMA schema_version:** `35`
- **Total Relational Clauses (`rule_clauses`):** **12,252**
- **Total FTS5 Entries (`rule_clauses_fts`):** **12,252**
- **Total Vector Embeddings (`clause_embeddings`):** **12,252** (`local-deterministic-v1`, dimension 384, template `v1`)
- **Stale Devanagari Hindi Rows (`MCC_LAWS_2022`):** **831 rows** containing Devanagari Unicode characters (`[ऀ-ॿ]`)

### 4.2 Document-by-Document Inventory Comparison

| Source Document ID | Active Database Rows | Canonical JSON Clauses | Delta | Primary Cause of Discrepancy |
| :--- | :---: | :---: | :---: | :--- |
| `ICC_ODI_MEN_2026` | 1,342 | 1,221 | +121 | Stale un-namespaced duplicate appendix clauses |
| `ICC_ODI_WOMEN_2026` | 1,333 | 1,213 | +120 | Stale un-namespaced duplicate appendix clauses |
| `ICC_T20I_MEN_2026` | 1,344 | 1,234 | +110 | Stale un-namespaced duplicate appendix clauses |
| `ICC_T20I_MEN_ADD_2026` | 26 | 26 | 0 | Perfect Match |
| `ICC_T20I_WOMEN_2026` | 1,348 | 1,239 | +109 | Stale un-namespaced duplicate appendix clauses |
| `ICC_TEST_MEN_2026` | 1,349 | 1,241 | +108 | Stale un-namespaced duplicate appendix clauses |
| `ICC_TEST_WOMEN_2026` | 1,355 | 1,243 | +112 | Stale un-namespaced duplicate appendix clauses |
| `ICC_WTC_2025_2027_PC` | 1,369 | 1,263 | +106 | Stale un-namespaced duplicate appendix clauses |
| `MCC_CHANGES_EXPLAINED_2026` | 173 | 182 | -9 | 9 appendix/table entries present in updated canonical JSON |
| `MCC_LAWS_2022` | 1,709 | 1,197 | +512 | Stale Devanagari Hindi rows present in DB |
| `MCC_LAWS_2026` | 904 | 949 | -45 | Additional definitions/appendix entries in canonical JSON |
| **TOTAL** | **12,252** | **11,008** | **+1,244** | **1,244 Net Contaminated / Stale Rows** |

---

## 5. Audit Confirmation & Go-Ahead for Gates 1–2

1. **Working Tree and Commit:** Confirmed clean at commit `0975ba8`.
2. **Safety & Backup:** Database SHA-256 recorded. Full staging and promotion protocol ready.
3. **No Breaking Changes:** Zero contract changes to FastAPI or React frontend.
4. **Authorization:** Audit refresh is complete and verified. Authorized to proceed immediately with **Gate 1** (Authoritative Source Discovery & Targeted Corpus Enrichment) and **Gate 2** (Applicability Repair & Safe Corpus Reconciliation).
