# CricketIQ — Phase 6 Gate 3 Pre-Implementation Audit Synthesis

- **Date:** 2026-11-17
- **Baseline Git Commit:** `d2bf845bec7c7481fa1c3243aad3a96d9c90b6a5` (`master`)
- **Remediation Status:** Gate 2 Remediation Fully Complete (`GATE 2 CLOSED — GATE 3 DESIGN READY`)
- **Workspace:** `D:\Cricket_Rules_NLP_Chatbot`
- **Authors:** CricketIQ Senior Knowledge Engineer & Information Retrieval Architect

---

## 1. Executive Summary & Audit Context

Phase 6 Gate 2 established the core regulatory safety foundations for CricketIQ:
1. **Pseudo-Embedding Channel Safety:** Clarified that `local-deterministic-v1` (384-dimensional MD5 feature vectors) is a non-semantic diagnostic channel used solely for vector store schema validation and pipeline plumbing. By default, `RetrievalService` isolates production ranking to exact clause lookup + SQLite FTS5 BM25 search. Diagnostic dense search requires explicit opt-in (`enable_diagnostic_dense=True`) and never displaces high-scoring lexical hits.
2. **Database Parity & Promotion Safety:** Standardized 4-way cryptographic identifier set parity across Canonical JSON, SQLite Relational, FTS5 Virtual Table, and Vector Embedding stores (`8c85beb895d40d4379ecdc3d9829b924c176cdebc59289b33f2c408ef4968904`, 10,388 unique clauses). Hardened `scripts/reconcile_database.py` with an exclusive process lock (`reconcile.lock`), active database SHA-256 invariance assertion before promotion, atomic filesystem swap recovery, and permanent retention of pre-promotion rollback snapshots. Added 10 automated fault-injection tests in `cricketiq/backend/tests/test_reconciliation_protocol.py`.
3. **Applicability Conflict Resolution:** Upgraded `ApplicabilityEngine` to detect competing format PCs or competition overlays, replacing silent scalar overwrite with explicit ambiguity resolution. Added canonical alias mapping for competition identifiers and rejected unknown or non-normative regulatory roles.
4. **Verification State:** Full backend suite passes (`127 passed, 1 skipped`), frontend suite passes (`23 passed across 7 files`), and Benchmark v2 demonstrates **100.0% Exact Clause Accuracy**, **0.0% Regulatory Leakage**, and **47.06% Sparse-Only Recall@5** across 92 queries.

Having closed Gate 2, this audit package executes the pre-implementation analysis for **Gate 3: Cricket Domain Intelligence & Structured Regulatory Retrieval**. Per master instructions, **no Gate 3 implementation code is introduced in this milestone**. This document synthesizes findings across the four core Gate 3 domains:
- **Cricket Domain Lexicon & Controlled Query Expansion**
- **Canonical Clause Hierarchy & Cross-Reference Integrity**
- **Structured Table Evidence & Extraction Quality**
- **Typed Internal Retrieval Contracts & Observability**

---

## 2. Gate 3 Pre-Implementation Audit Synthesis Matrix

| Subsystem Audit | Key Findings & Empirical Evidence | Identified Risks & Failure Modes | Proposed Gate 3 Architectural Remedy | Companion Deliverable |
| :--- | :--- | :--- | :--- | :--- |
| **Cricket Domain Lexicon** (`3.1`) | - 20 terms currently cataloged in `cricket_lexicon.json`.<br>- 10 hard non-equivalences identified (`retired hurt` vs `retired out`, `wide` vs `no-ball`, `run out` vs `stumped`, `beamer` vs general `no-ball`, `Mankad` alias).<br>- Maps to 27 Benchmark v2 queries directly. | - Recursive or uncontrolled synonym expansion.<br>- Cross-concept leakage across `distinct_from` boundaries.<br>- Dilution of FTS5 BM25 scores through query inflation.<br>- Rewriting legal citations or statutory phrasing. | - Strict query immutability (original query untouched).<br>- Token-level controlled expansion with provenance tracing.<br>- Hard negative gating: never expand across `distinct_from` boundaries unless contrast is explicit.<br>- Lexicon schema validation and status lifecycle (`APPROVED`, `DRAFT`, `DEPRECATED`). | `docs/PHASE_6_GATE_3_LEXICON_AUDIT.md` |
| **Hierarchy & Relationships** (`3.2`) | - 10,388 clauses audited across 11 documents.<br>- **0 cycles found:** Parent graph is strictly acyclic directed forest.<br>- **Empirical Discovery:** `hierarchy_depth` is uniformly hardcoded to `1` across all 10,388 canonical clauses despite populated parent IDs.<br>- 3,126 cross-references mapped across corpus. | - Bulk parent/depth rewriting without review could alter clause numbering semantics.<br>- Cross-bundle parent traversal could leak inapplicable regulations.<br>- Exponential graph traversal explosion during evidence expansion. | - Retain dry-run verification before any hierarchy migration.<br>- Recompute exact depth (`depth = parent.depth + 1`, roots = 1) from parent links.<br>- Strictly bound hierarchy hops (max 1 hop up to parent, 1 hop down to leaf children).<br>- Confine cross-references strictly within the active candidate document bundle. | `docs/PHASE_6_GATE_3_HIERARCHY_INTEGRITY_REPORT.md` |
| **Structured Table Evidence** (`3.3`) | - 240 extracted tables audited in `data/extracted/tables/`.<br>- Rich substantive tables identified: DRS comparison tables (Appx D, pg 89), Hawk-Eye Pitching/Impact/Wicket zones (pgs 94-96), Player Review outcomes (pg 98).<br>- Empty/sparse tables detected in addenda and explanatory docs. | - Presenting unverified or OCR-degraded table cells as authoritative statutory rules.<br>- Tables detached from parent clauses or missing page locators.<br>- Misinterpreting illustrative tables as prescriptive regulatory mandates. | - Design typed `TableEvidence` model preserving exact PDF page locators, captions, headers, units, and verification state.<br>- Establish manual verification checklist for tables.<br>- Ground table retrieval via explicit clause cross-links (`extracted_tables` field in `RuleClause`). | `docs/PHASE_6_GATE_3_TABLE_EVIDENCE_AUDIT.md` |
| **Retrieval Contracts & API Compatibility** (`3.4`) | - `POST /v1/rules/query` public schema and answer format must remain 100% frozen.<br>- Internal retrieval models require rich typing for multi-stage evidence aggregation. | - Breaking frontend assumption regarding answer or citation shape.<br>- PII or unrestrained logging in retrieval traces.<br>- Non-deterministic evidence ordering across API calls. | - Keep all Gate 3 extensions internal to `cricketiq.backend.app.retrieval`.<br>- Define typed contracts: `NormalizedQueryView`, `LexiconExpansionTrace`, `HierarchyContextBundle`, `TableEvidenceBundle`.<br>- Structured, privacy-safe observability with per-stage latency tracking. | `docs/PHASE_6_GATE_3_IMPLEMENTATION_PLAN.md` |

---

## 3. Subsystem Audit Highlights

### 3.1 Lexicon & Controlled Expansion Highlights
- **Scope & Coverage:** The existing lexicon provides strong coverage for core delivery legality, dismissal methods, and technical systems (DRS, DLS).
- **Hard Semantic Invariants:** The audit identified 10 critical distinctions that must be programmatically enforced:
  1. `CRIC_DISMISS_RETIRED_HURT` $\neq$ `CRIC_DISMISS_RETIRED_OUT` (Retirement due to illness/injury is not a dismissal; player may resume).
  2. `CRIC_DELIV_WIDE_BALL` $\neq$ `CRIC_DELIV_NO_BALL` (Law 22 vs Law 21; distinct conditions and scoring).
  3. `CRIC_DISMISS_RUN_OUT` $\neq$ `CRIC_DISMISS_STUMPED` (Law 38 vs Law 39; distinction based on delivery legality and attempting a run).
  4. `CRIC_DELIV_BEAMER` $\subset$ `CRIC_DELIV_NO_BALL` (A beamer is a specific high full-pitched delivery above waist height; never expand general "no ball" to beamer).
  5. `Mankad` $\rightarrow$ Alias for `CRIC_NON_STRIKER_RUN_OUT` (Law 38.3; strictly colloquial synonym, never presented as a separate legal code).
- **Expansion Architecture:** Query expansion will operate at the lexical view generation stage. The raw query is preserved verbatim. Expansions are appended as scored disjunctions (`OR` clauses) with capped expansion counts ($K \le 3$ synonyms per identified term).

### 3.2 Hierarchy Integrity Highlights
- **Integrity Validation:** Across 11 canonical documents (10,388 unique clauses), zero cycles were found. All parent links point to ancestor nodes within the same source document.
- **The Depth-1 Anomaly:** A significant parser legacy was uncovered: in `data/corpus/clauses/*_clauses.json`, all clauses possess `hierarchy_depth: 1`, regardless of whether `parent_clause_id` is populated or null. For example, `ICC_TEST_MEN_2026:9.1.2` has `parent_clause_id: "ICC_TEST_MEN_2026:9.1"` but lists `hierarchy_depth: 1`.
- **Remediation Strategy:** A deterministic depth calculation script will be developed in Gate 3 to recompute depths based on parent link chains (`root = 1`, `child = parent.depth + 1`). This migration will be accompanied by dry-run validation and will preserve existing clause IDs and text immutably.

### 3.3 Table Evidence Highlights
- **Corpus Table Assets:** 240 tables exist in `data/extracted/tables/`. 192 are in `MCC_LAWS_2022`, 9 each in ODI and T20I Playing Conditions, and 6 each in Test Playing Conditions and WTC Regulations.
- **Substantive vs Illustrative:** Tables in Playing Conditions Appendix D govern the exact technical specifications for DRS (Hawk-Eye Pitching Zone $\ge 50\%$, Impact Zone, Wicket Zone, Player Review consequences). These are normative technical rules and must be exposed as first-class structured evidence.
- **Typed Representation:** A `TableEvidence` schema was designed, encapsulating `table_id`, `source_document_id`, `page_number`, `caption`, `headers`, `rows`, `footnotes`, and `verification_status`.

---

## 4. Verification and Decision

### Verified Checklist
- [x] Baseline Git state clean and recorded.
- [x] Gate 2 remediations fully verified in code, DB, and tests.
- [x] Pseudo-embedding safety asserted: non-semantic vectors isolated from production RRF.
- [x] Database parity verified: exact 4-way ID digest equality proven across 10,388 clauses.
- [x] Reconcile protocol hardened with exclusive locking and atomic rollback recovery.
- [x] Full backend test suite passes: `127 passed, 1 skipped` (100% pass rate).
- [x] Full frontend test suite passes: `23 passed across 7 files`.
- [x] Benchmark v2 evaluation verified: Exact Clause Acc 100.0%, Regulatory Leakage 0.0%, Sparse Recall@5 47.06%.
- [x] Comprehensive pre-implementation audits executed for Lexicon, Hierarchy, Tables, and Contracts.
- [x] Zero Gate 3 feature code introduced in this milestone.

### Milestone Decision
**`GATE 2 CLOSED — GATE 3 DESIGN READY`**

Proceed to authoring the four detailed companion audit reports and implementation plan under `docs/`.
