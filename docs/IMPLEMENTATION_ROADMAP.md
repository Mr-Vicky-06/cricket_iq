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

## Phase 2 — Structured rule store and applicability model [STATUS: READY TO IMPLEMENT]

**Goal:** represent rule text and its context without flattening away version differences.

Tasks:
- Create source-document, rule-clause, and relationship models.
- Add format/category/competition/date applicability fields.
- Implement explicit source status and amendment relationships.
- Build deterministic applicability selection with reason codes.
- Add tests for known effective-date and format differences from verified sources.

Exit gate:
- Given a test scenario, the resolver returns expected candidate documents and explains why.
- Ambiguous or unsupported scenarios are not silently resolved.

## Phase 3 — Retrieval baseline

**Goal:** retrieve exact and semantically relevant clauses.

Tasks:
- Add PostgreSQL full-text search.
- Evaluate an embedding model and store versioned embeddings.
- Add pgvector search with metadata filters.
- Fuse keyword and vector candidates; add a reranker only if benchmark results justify it.
- Retrieve parent clauses, exceptions, and cross-references.
- Add retrieval traces for debugging.

Exit gate:
- A small reviewed query set retrieves the expected evidence with inspectable provenance.

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
