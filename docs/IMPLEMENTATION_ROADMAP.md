# Implementation Roadmap — CricketIQ

## Delivery strategy

Build a narrow but trustworthy end-to-end slice before expanding source coverage. The first usable milestone should answer a small set of questions from one validated source with exact citations. Scale document coverage only after the ingestion and applicability model are proven.

The order below is a dependency sequence, not a promise of calendar duration. Estimate tasks after repository discovery.

## Phase 0 — Repository discovery and project setup [STATUS: COMPLETED]

**Goal:** understand the starting point and establish reproducible development.

Tasks:
- [x] Inspect repository, Git status, runtimes, dependencies, and existing tests.
- [x] Confirm product scope, hosting constraints, API/model budget, and data-use requirements.
- [x] Decide initial source set and one representative format/category for the first vertical slice (ICC Men's T20I Playing Conditions 2026).
- [x] Define coding, environment, logging, and test conventions.
- [x] Create project skeleton (`cricketiq/`), virtual environment (`uv venv`), and lockfile.

Exit gate:
- [x] A documented baseline and approved first milestone exist.
- [x] No existing user work was overwritten.

## Phase 1 — Source registry and one-document ingestion [STATUS: COMPLETED (Single-Source Slice)]

**Goal:** reliably ingest and inspect a single official PDF.

Tasks:
- [x] Implement source-document metadata and file hashing (`SourceDocument`, `DocumentRegistry`).
- [x] Import verified official source (ICC Men's T20I Playing Conditions 2026 fixture sample).
- [x] Extract text and page mapping (`PDFExtractor` with PyMuPDF and pdfplumber).
- [x] Parse clause hierarchy, tables, and references (`ClauseParser`).
- [x] Produce a validation report for empty pages, garbled text, and missing numbering (`IngestionValidator`).
- [x] Keep original file immutable with SHA-256 integrity verification.
- [x] Comprehensive test suite (`cricketiq/backend/tests/test_ingestion.py` - 6 passed in 1.13s).

Exit gate:
- [x] A reviewer can navigate from a structured clause to the exact source page.
- [x] Duplicate detection, hash verification, and failed-ingestion handling work.

## Phase 2 — Structured rule store and applicability model [STATUS: COMPLETED]

**Goal:** represent rule text and its context without flattening away version differences.

Tasks:
- [x] Create source-document, rule-clause, and relationship models (`orm_models.py`, `models.py`).
- [x] Add format/category/competition/date applicability fields and `MatchContext`.
- [x] Implement explicit source status and amendment relationships (`incorporates`, `modifies`, `supplements`, `supersedes`).
- [x] Build deterministic applicability selection with reason codes and decision trace (`ApplicabilityEngine`).
- [x] Implement Alembic database migrations (`alembic.ini`, `migrations/`).
- [x] Build secure document downloader with SSRF and DNS rebinding protections (`secure_downloader.py`).
- [x] Add tests for known effective-date, series-start boundary, cross-clause evidence, and format differences (`test_applicability.py`, `test_persistence.py`, `test_security_downloader.py` - 29 passed, 1 skipped).

Exit gate:
- [x] Given a test scenario, the resolver returns expected candidate documents, precedence order, and explains why.
- [x] Ambiguous or unsupported scenarios (e.g. domestic IPL, missing series start date on transition boundaries) are surfaced safely with clarification requests.

## Phase 3 — Retrieval baseline [STATUS: COMPLETED]

**Goal:** retrieve exact and semantically relevant clauses within the applicable regulatory bundle with provenance.

Tasks:
- [x] Complete Pre-Implementation Audit and ADR 0002 (`docs/reviews/PHASE_3_PRE_IMPLEMENTATION_AUDIT.md`, `docs/adr/0002-hybrid-retrieval.md`).
- [x] Implement typed retrieval contracts (`RetrievalRequest`, `RetrievalHit`, `RetrievalOutcome`, `EvidenceRole`, `RetrievalStatus`).
- [x] Implement Exact Clause Lookup Engine (`ExactClauseLookupEngine`) with regular expression dotted-identifier matching.
- [x] Implement SQLite FTS5 sparse provider with BM25 column weighting, query sanitization, and index synchronization (`SQLiteFTSSearchProvider`).
- [x] Add PostgreSQL full-text search adapter (`PostgresFTSSearchProvider`).
- [x] Implement versioned embedding text construction (`v1`) and evaluate embedding candidates (`LocalDeterministicEmbeddingProvider`, `SentenceTransformerEmbeddingProvider`).
- [x] Implement persistent, versioned embedding store with atomic staging rebuilds and validation guards (`EmbeddingStore`).
- [x] Implement local NumPy dense semantic search (`SQLiteNumPyDenseSearchProvider`) and pgvector adapter (`PostgresPgVectorSearchProvider`).
- [x] Implement unweighted Reciprocal Rank Fusion ($k=60$) with rank provenance and deterministic tie-breaking (`RRFEngine`).
- [x] Implement bounded evidence graph expansion for parent headers and cross-referenced clauses (`EvidenceExpander`).
- [x] Build unified `RetrievalService` with pre-search applicability gating, timing diagnostics, and strict bundle confinement.
- [x] Construct 65-item labelled benchmark across 15 categories (`benchmark_v1.jsonl`, `benchmark_schema.json`).
- [x] Build automated benchmark evaluation harness (`evaluate_retrieval.py`) achieving Recall@5: 89.66%, MRR: 0.7477, Exact Acc: 100%, Supporting Recall: 100%, Leakage Rate: 0.0%, Latency: 7.26ms.
- [x] Unit, integration, and evaluation test suite: 55 passed, 1 skipped (0 failures).

Exit gate:
- [x] 65-query labelled benchmark retrieves expected evidence with inspectable provenance.
- [x] Zero cross-format or domestic regulatory leakage verified in tests (0.0%).

## Phase 4 — Grounded answer API

**Goal:** produce clear answers based only on retrieved evidence.

Tasks:
- Parse intent and structured context from the user question.
- Clarify missing material context.
- Build evidence-bounded prompts.
- Generate direct answer, explanation, exceptions, and citations.
- Validate citations against retrieved records.
- Implement abstention and safe provider-error handling.

Exit gate:
- Each benchmark answer is supported by source evidence or correctly abstains.

## Phase 5 — Minimal user interface

**Goal:** make the vertical slice usable.

Tasks:
- Create chat interface and match-context controls.
- Display answer, assumptions, sources, clauses, and page links.
- Add follow-up context handling and correction.
- Include empty, loading, timeout, and no-evidence states.

Exit gate:
- A user can ask, inspect, and challenge an answer without seeing internal implementation details.

## Phase 6 — Expand sources and evaluation

**Goal:** scale from one validated document to the MVP corpus.

Tasks:
- Add underlying MCC Laws and remaining in-scope ICC formats/categories.
- Add competition-specific documents only after separate source verification and schema support.
- Create and review a benchmark approaching 300 questions across rule definitions, edge cases, scenarios, comparisons, historical questions, and unanswerable questions.
- Measure retrieval, citation, answer, applicability, latency, and abstention performance.
- Conduct expert review of high-impact rule categories.

Exit gate:
- Metrics meet agreed acceptance targets or gaps are documented with mitigation plans.

## Phase 7 — Hardening and release

**Goal:** prepare a controlled deployment.

Tasks:
- Add authentication/authorization for administration if needed.
- Add secrets handling, backups, monitoring, rate limits, and data-retention controls.
- Containerize only the components needed for target hosting.
- Run full automated tests and security checks.
- Complete the release checklist.
- Document source update and rollback procedures.

Exit gate:
- Reproducible deployment, tested restore/rollback, known limitations, and owner for source maintenance.

## Suggested task template

For each task, record:

- **ID and title**
- **User/value outcome**
- **Scope and non-goals**
- **Prerequisites**
- **Likely files/modules**
- **Acceptance criteria**
- **Test cases and commands**
- **Risks/data migration impact**
- **Status:** not started / in progress / blocked / done
- **Evidence:** PR/commit, logs, test results, reviewer

## First vertical slice recommendation

Do not start by importing every MCC and ICC PDF. Choose one verified, representative source document and a small set of questions. Demonstrate the complete chain:

`official PDF → source registry → clause extraction → validation → structured storage → hybrid retrieval → grounded answer → verified citation → regression test`

Once that chain is reliable, expand coverage by adding documents—not by rewriting the architecture.
