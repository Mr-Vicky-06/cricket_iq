# Phase 4 Pre-Implementation Audit — CricketIQ Grounded Answer API

**Document ID:** `CRICKIQ-AUDIT-PHASE4-001`  
**Date:** 2026-11-16  
**Auditor:** Principal Software Architect, Senior Backend Engineer, AI Safety & Verification Team  
**Status:** **GATE 0 COMPLETE — READY FOR REVIEW**  
**Repository Commit:** `336976d` (clean working tree on branch `master`)

---

## 1. Executive Summary

This pre-implementation audit establishes the technical baseline, architecture constraints, and execution requirements for **Phase 4: Grounded Answer API, Evidence-Bounded LLM Generation, Citation Validation & Abstention**.

In Phase 4, CricketIQ transitions from a retrieval subsystem into an end-to-end, version-aware rules intelligence assistant. The fundamental directive of Phase 4 is:
> **The Language Model is an explanation and synthesis component. It is NEVER the source of cricket law, and it must NEVER decide rule applicability or precedence independently of the deterministic engine.**

The mandatory execution sequence is strictly enforced:
$$\text{User Query} \longrightarrow \text{Request Validation} \longrightarrow \text{Context Extraction} \longrightarrow \text{ApplicabilityEngine} \longrightarrow \text{RetrievalService} \longrightarrow \text{Evidence Sufficiency} \longrightarrow \text{Evidence-Bounded LLM} \longrightarrow \text{Claim \& Citation Validation} \longrightarrow \text{Structured Response}$$

If applicability is ambiguous or missing material context, the system must halt and return a structured clarification request without running retrieval or generation. If evidence is incomplete, conflicting, or unverifiable, the system must abstain rather than inventing a ruling.

---

## 2. Current Baseline & Repository Inspection

### 2.1 Git and Runtime State
- **Repository Root:** `D:\Cricket_Rules_NLP_Chatbot`
- **Current Branch:** `master`
- **Active Commit:** `336976d` (`feat(corpus): acquire official MCC Laws of Cricket, extract 42 laws, normalize 12,522 clauses, and rebuild full database indexes`)
- **Working Tree:** Clean (zero uncommitted or untracked changes)
- **Python Runtime:** Python 3.14.10 / uv environment (`.venv`)
- **Test Suite Status:** **67 passed, 1 skipped (Postgres integration test when `TEST_POSTGRES_DSN` is unset), 0 failed** in 4.74s (`pytest -q`)
- **Active Database:** `data/cricketiq.db` (54,652,928 bytes) containing 11 registered source documents, 10 inter-document relationships, 9,454 indexed clauses in SQLite FTS5 (`rule_clauses_fts`), and 9,454 dense embeddings (dimension=384).

### 2.2 Installed Dependencies & License Audit
All installed packages in `pyproject.toml` and `.venv` have been audited for permissive open-source licensing:
- `fastapi` (0.115.x): MIT License (Web API framework)
- `uvicorn` (0.34.x): BSD-3-Clause (ASGI server)
- `pydantic` (2.10.x): MIT License (Data validation and serialization)
- `sqlalchemy` (2.0.x): MIT License (ORM and relational persistence)
- `alembic` (1.14.x): MIT License (Database schema migrations)
- `pymupdf` (1.25.x): AGPL-3.0 / Commercial (Local extraction tooling; runs in ingestion scripts only)
- `pdfplumber` (0.11.x): MIT License (Table extraction)
- `httpx` (0.28.x): BSD-3-Clause (Async/sync HTTP client for secure downloads and LLM provider calls)
- `numpy` (2.2.x): BSD-3-Clause (Vector similarity and dense search)
- `pytest` (8.3.x): MIT License (Automated test runner)

No non-permissive or viral licenses are imported into the runtime API path.

---

## 3. Architecture Audit & Call-Path Trace

### 3.1 Existing Component Interfaces
1. **`ApplicabilityEngine` (`cricketiq/backend/app/applicability/engine.py`):**
   - Inputs: `MatchContext(level, format, category, competition, series_start_date, match_date, raw_query)`
   - Outputs: `ApplicabilityDecision(status, candidate_documents, selected_bundle, precedence_chain, reason_codes, decision_trace, missing_fields, clarification_prompt)`
   - Behavior: Enforces strict boundary conditions (e.g. October 1, 2026 series start date transition), stops on unsupported domestic queries (IPL, BBL), and requires clarification when context changes the ruling.
2. **`RetrievalService` (`cricketiq/backend/app/retrieval/service.py`):**
   - Inputs: `RetrievalRequest(query, match_context, top_k, expand_evidence)`
   - Outputs: `RetrievalOutcome(request_id, status, decision, hits, expanded_hits, timing_diagnostics, warnings)`
   - Behavior: Automatically calls `ApplicabilityEngine.resolve()`. If applicability status is not `RESOLVED`, retrieval terminates immediately. If resolved, searches sparse FTS5 and dense vectors strictly confined to `selected_bundle`, combines via RRF ($k=60$), and expands parent/cross-reference clauses via `EvidenceExpander`.
3. **`CricketIQRepository` (`cricketiq/backend/app/database/repository.py`):**
   - Dual-mode SQLAlchemy repository supporting SQLite local development and PostgreSQL production.
   - Provides methods: `get_clause()`, `get_clauses_for_document()`, `get_source_document()`, `get_relationships_for_document()`, `upsert_clauses()`.

### 3.2 Gaps Identified for Phase 4
1. **Missing Natural Language Question Understanding & Context Extraction:**
   - User questions arrive in raw natural language (e.g. *"Can a batter be run out on a free hit in a T20 international?"*).
   - We need a robust `ContextExtractor` that identifies explicit tokens (e.g. `T20I`, `men's`, `series starting in November 2026`) versus ambiguous phrasing (`"in a T20 match"` -> could be domestic IPL or international T20I), builds a validated `MatchContext`, and tracks `explicit_fields` vs `inferred_fields`.
2. **Missing Evidence Sufficiency & Conflict Evaluation:**
   - Between retrieval and generation, the system must verify whether the retrieved evidence pack actually contains the necessary parent clauses, definitions, and exceptions required to answer the specific question.
   - If an unresolvable regulatory conflict or missing critical exception exists, generation must abstain.
3. **Missing Pluggable LLM Provider Abstraction:**
   - Domain and application services must not directly invoke third-party SDKs or specific vendor APIs.
   - A typed `LLMProvider` protocol is required with:
     - `FakeLLMProvider` (deterministic, canned or fixture-based responses for 100% offline unit/integration tests).
     - Production provider adapter supporting Gemini API (via modern httpx JSON structured mode or SDK), configurable via environment variables (`GEMINI_API_KEY`).
4. **Missing Evidence-Bounded Prompt Builder:**
   - Prompts must present retrieved source clauses as **untrusted data**, wrapped in defensive delimiters (e.g. `<evidence_clause id="...">...</evidence_clause>`).
   - The prompt must forbid following instructions embedded in source text and instruct the model to cite only allowed `citation_id` keys.
5. **Missing Citation & Claim Validation Engine:**
   - The LLM's structured output must return distinct factual claims with associated citation IDs.
   - The validation engine must verify that every citation ID maps to a genuine clause in the per-request evidence pack, matching the trusted database metadata (`document_id`, `clause_number`, `page_start`, `official_url`).
   - Any hallucinated or out-of-pack citation must cause immediate rejection, safe single repair, or abstention.
6. **Missing Public API Endpoints:**
   - Need FastAPI application factory, routing `POST /v1/rules/query`, `GET /health/live`, `GET /health/ready`, with structured error handling and request correlation IDs.

---

## 4. LLM Provider Decision & Budget Analysis

Per Section 4.4 of the Master Prompt, the LLM provider evaluation table is documented below:

| Provider / Model | Structured JSON Output | Context Window | Latency (avg) | Privacy & Terms | Cost / 1k Tokens | Offline Test Support | Evaluation Verdict |
| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :--- |
| **`FakeLLMProvider` (Local)** | 100% (Native) | $\infty$ | $<1$ ms | 100% local, 0 data transfer | \$0.00 | **YES (Primary)** | **MANDATORY for all automated test suites.** |
| **Gemini 2.5 Flash** | Excellent (`response_schema`) | 1M+ tokens | ~400–800 ms | Enterprise privacy; no training on API data | ~\$0.00015 | No (requires network) | **RECOMMENDED production live provider** (Fast, cheap, highly reliable structured JSON). |
| **Claude 3.5 Sonnet** | Excellent (Tool use) | 200k tokens | ~1.2–2.0 s | Strong privacy terms | ~\$0.003 | No (requires network) | Viable fallback production provider. |
| **Local Ollama / Llama 3.3** | Variable | 8k–128k tokens | Hardware-dependent | 100% local | Hardware cost only | Partial (requires local daemon) | Viable for air-gapped deployments. |

### Decision:
1. All unit tests, integration tests, and CI/CD pipelines will use `FakeLLMProvider`, ensuring zero cost, zero network flakiness, and deterministic verification.
2. The live production adapter will support the Google Gemini API (`gemini-2.5-flash`), configured via `GEMINI_API_KEY`.
3. If no API key is provided, the application starts safely in `safe_mode`, returning `PROVIDER_NOT_CONFIGURED` on live queries rather than crashing or faking real live answers.

---

## 5. Architectural Guardrails & Invariants

1. **Applicability-First Sequence:** `ApplicabilityEngine.resolve()` must run and succeed before any retrieval or generation call.
2. **Strict Bundle Confinement:** No clause outside `ApplicabilityDecision.selected_bundle` may enter the prompt evidence pack.
3. **No LLM Precedence:** Precedence between ICC Playing Conditions and baseline MCC Laws is determined strictly by deterministic relationships (`INCORPORATES`, `MODIFIES`, `SUPPLEMENTS`, `SUPERSEDES`), never by model opinion.
4. **No Premature Streaming:** Live streaming is disabled to ensure claim and citation validation runs completely before output leaves the API boundary.
5. **No Hallucinated Citations:** Citation metadata (page numbers, URLs, titles) is injected exclusively from trusted repository records, never from model output.

---

## 6. Audit Conclusion & Gate 0 Verdict

The existing repository architecture is robust, typed, and well-structured. The integration path is clean and requires no redesign of Phase 1–3 subsystems. The project is cleared to proceed with the Gate 0 Data Readiness Audit and ADR 0003.
