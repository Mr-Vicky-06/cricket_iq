# Implementation Roadmap — CricketIQ

## Delivery strategy

Build a narrow but trustworthy end-to-end slice before expanding source coverage. The first usable milestone should answer a small set of questions from one validated source with exact citations. Scale document coverage only after the ingestion and applicability model are proven.

The order below is a dependency sequence, not a promise of calendar duration. Estimate tasks after repository discovery.

## Phase 0 — Repository discovery and project setup

**Goal:** understand the starting point and establish reproducible development.

Tasks:
- Inspect repository, Git status, runtimes, dependencies, and existing tests.
- Confirm product scope, hosting constraints, API/model budget, and data-use requirements.
- Decide initial source set and one representative format/category for the first vertical slice.
- Define coding, environment, logging, and test conventions.
- Create only the missing project skeleton and local developer instructions.

Exit gate:
- A documented baseline and approved first milestone exist.
- No existing user work was overwritten.

## Phase 1 — Source registry and one-document ingestion

**Goal:** reliably ingest and inspect a single official PDF.

Tasks:
- Implement source-document metadata and file hashing.
- Download/import one verified official source.
- Extract text and page mapping.
- Parse clause hierarchy, tables, and references.
- Produce a validation report for empty pages, garbled text, and missing numbering.
- Keep original file immutable.

Exit gate:
- A reviewer can navigate from a structured clause to the exact source page.
- Duplicate detection and failed-ingestion handling work.

## Phase 2 — Structured rule store and applicability model

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
