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

## Pre-Phase 4 — Data Foundation, Corpus Engineering & NLP Readiness [STATUS: COMPLETED]

**Goal:** establish a validated, version-aware, cricket-aware rules corpus and supporting NLP/data assets before implementing Phase 4 answer-generation features.

Tasks:
- [x] **Gate 0:** Complete repository, test baseline, and physical storage audit (`docs/reviews/DATA_FOUNDATION_PRE_IMPLEMENTATION_AUDIT.md`).
- [x] **Gate 1:** Authoritative source discovery and corpus scope register across Tier 1 (Core ICC & MCC), Tier 2 (WTC & T20WC), and Tier 3 (Domestic out-of-scope) (`docs/DATA_SOURCE_INVENTORY.md`, `docs/CORPUS_SCOPE_AND_COVERAGE.md`, `docs/SOURCE_USE_AND_ATTRIBUTION_REGISTER.md`).
- [x] **Gate 2:** Secure acquisition of 8 Tier 1 ICC Playing Conditions PDFs via `secure_downloader.py`, resolution of ISP DNS sinkhole via direct SNI acquisition of 3 official MCC documents from Lord's (`MCC_LAWS_2026`, `MCC_LAWS_2022`, `MCC_CHANGES_EXPLAINED_2026`), and master raw manifest generation (`data/sources/manifests/raw_manifest.json`, `data/sources/manifests/acquisition_log.json`).
- [x] **Gate 3:** Full document extraction and clause parsing across all 11 documents, extracting 1,162 pages, 12,522 clauses, and 246 tables with zero garbled pages (`docs/DOCUMENT_EXTRACTION_SPEC.md`, `data/extracted/`).
- [x] **Gate 4:** Multi-view text normalization (7 views: `original_text`, `normalized_text`, `lexical_text`, `embedding_text`, `sentence_segments`, `chunks`, `display_text`) and tokenization evaluator module (`cricketiq/backend/app/nlp/normalizer.py`, `tokenization_evaluator.py`, `docs/TEXT_NORMALIZATION_SPEC.md`, `docs/TOKENIZATION_EVALUATION.md`, `test_text_normalization.py`, `test_cricket_tokenization.py`).
- [x] **Gate 5:** Cricket domain terminology lexicon and ontology dataset with non-equivalence mappings (`data/corpus/lexicon/cricket_lexicon.json`, `docs/CRICKET_DOMAIN_LEXICON_SPEC.md`, `test_lexicon.py`).
- [x] **Gate 6:** Corpus quality validation, atomic SQLite database and FTS5 index build, persistent vector store creation (9,454 indexed clauses, 384 dimensions, `data/cricketiq.db` 54.65 MB), and benchmark evaluation across 92 items (`benchmark_v2.jsonl`, `eval_report_v2.json`, `docs/CORPUS_QUALITY_REPORT.md`).
- [x] **Gate 7:** Final delivery report, test suite verification (67 passed, 1 skipped), and milestone stopping gate before Phase 4 (`docs/reviews/MCC_DATA_COLLECTION_AND_FINAL_DELIVERY_REPORT.md`).

Exit gate:
- [x] 100% of Tier 1 official sources acquired directly from official governing bodies, cryptographically verified, and ingested.
- [x] Multi-view representations generated for all 12,522 clauses with full provenance.
- [x] Persistent SQLite database, FTS5 virtual table, and vector store built with zero errors (9,454 indexed clauses).
- [x] Benchmark v1 regression verified with zero drop in accuracy (100% exact accuracy, 0.0% leakage).
- [x] **Explicit boundary confirmed: No Phase 4 answer generation, LLM prompts, API endpoints, or chat UI implemented.**

## Phase 4 — Grounded answer API [STATUS: COMPLETED]

**Goal:** produce clear answers based only on retrieved evidence, format-aware applicability resolution, deterministic citation verification, and strict abstention.

Tasks:
- [x] **Gate 0:** Pre-implementation architecture and data readiness audit (`docs/reviews/PHASE_4_PRE_IMPLEMENTATION_AUDIT.md`, `docs/reviews/PHASE_4_DATA_READINESS_AUDIT.md`, `docs/adr/0003-grounded-answer-api.md`, `docs/reviews/PHASE_4_COMPONENT_IMPLEMENTATION_PLAN.md`).
- [x] **Gate 0 Remediation:** Elimination of primary key collision in `clause_parser.py` via appendix namespacing (`APP_<X>:<num>`), back index exclusion for `MCC_LAWS_2026`, and Devanagari filtering for `MCC_LAWS_2022`, bringing non-colliding corpus to 11,008 unique clauses across all 11 documents.
- [x] **Gate 1:** Pydantic request/response schemas, FastAPI application skeleton, CORS, correlation ID middleware, liveness/readiness probes (`cricketiq/backend/app/api/schemas/`, `health.py`, `main.py`, `test_api_schemas.py`, `test_health_routes.py`).
- [x] **Gate 2:** Natural-language match context extractor and end-to-end pipeline orchestrator (`context_extractor.py`, `query_orchestrator.py`, `test_context_extractor.py`, `test_query_orchestrator.py`).
- [x] **Gate 3:** Pre-generation evidence sufficiency auditor, LLM provider protocol, deterministic offline fake provider, and Gemini provider adapter (`evidence_sufficiency.py`, `contracts.py`, `provider.py`, `provider_factory.py`, `test_evidence_sufficiency.py`, `test_llm_provider.py`).
- [x] **Gate 4:** Evidence-bounded XML prompt builder and answer generator (`prompt_builder.py`, `answer_generator.py`, `test_prompt_builder.py`).
- [x] **Gate 5:** Deterministic citation validator, DB metadata hydration, and claim support verification (`citation_validator.py`, `test_citation_validator.py`).
- [x] **Gate 6:** End-to-end API route `POST /v1/rules/query`, golden benchmark of 50 curated Q&A cases (`evaluation/answers/grounded_answer_benchmark_v1.jsonl`), evaluation runner (`evaluate_answers.py`), security/abuse hardening tests (`test_rules_query_api.py`, `test_security_abuse.py`), and comprehensive final delivery report (`docs/reviews/PHASE_4_FINAL_DELIVERY_REPORT.md`).

Exit gate:
- [x] 100% of benchmark answers supported by source evidence or correctly abstain (50/50 test cases, 100% status accuracy).
- [x] Citation identity validity: 100.0% (117/117 citations verified in database).
- [x] Claim citation coverage: 100.0% (117/117 claims substantiated).
- [x] Regulatory leakage rate: 0.0% (0 cross-bundle citations).
- [x] Appropriate abstention rate: 100.0% (11/11 domestic, ambiguous, and out-of-scope inquiries).
- [x] Latency: Mean 138.6ms, p50 140.7ms, p95 268.9ms.
- [x] Full test suite: 103 passed, 1 skipped (Postgres integration), 0 failed.
- [x] Strict boundary preserved: No frontend UI, chat widgets, client apps, or unvalidated streaming.

## Phase 5 — Minimal user interface [STATUS: COMPLETED]

**Goal:** make the vertical slice usable with an authoritative, responsive, and verifiable user interface.

Tasks:
- [x] **Gate 0:** Pre-implementation frontend architecture audit, API contract mapping, and ADR 0004 (`docs/reviews/PHASE_5_PRE_IMPLEMENTATION_AUDIT.md`, `docs/PHASE_5_API_CONTRACT_MAP.md`, `docs/adr/0004-frontend-architecture.md`).
- [x] **Gate 1:** Project bootstrap (React 19, TypeScript 5.7, Vite 6, Tailwind CSS 3.4, Lucide Icons, Vitest) in `frontend/`.
- [x] **Gate 2:** Typed API client with 30s timeout, abort controller, error handling, and strict URL domain allowlist (`frontend/src/api/`).
- [x] **Gate 3:** Design system tokens & accessible styles based on cricket editorial aesthetic (`frontend/tailwind.config.js`, `frontend/src/styles/index.css`).
- [x] **Gate 4:** Interactive components: Header with live corpus status probe, Footer, QuestionInput composer, ExampleQueries benchmark chips, MatchContextPanel controls, AnswerCard, AbstentionCard, CitationCard, CitationDrawer slide-over, and TraceSummary telemetry.
- [x] **Gate 5:** Unit and component test suites (20 tests passed across 6 test files, strict `tsc --noEmit` typecheck, production build verified).
- [x] **Gate 6:** End-to-end browser journey verification via Playwright & Chrome DevTools (free hit answered ruling, citation drawer inspection, domestic IPL abstention, clarification flow, mobile 375x667 viewport, and clean console with 0 errors / 0 warnings).
- [x] **Gate 7:** Comprehensive documentation and delivery report (`frontend/README.md`, `docs/reviews/PHASE_5_FINAL_DELIVERY_REPORT.md`).

Exit gate:
- [x] A user can ask questions naturally and receive grounded rulings with exact official clause citations.
- [x] Interactive citation drawer displays verbatim regulatory text with verified links to official governing bodies.
- [x] Clarification requests and domestic screening abstentions are presented gracefully with clickable alternatives.
- [x] Zero hallucinated UI elements, strict HTTPS URL allowlist for governing bodies (`icc-cricket.com`, `lords.org`).
- [x] Full responsive mobile support (375px+) and clean browser console (0 errors, 0 warnings).

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
