# Product Requirements — CricketIQ

## 1. User-facing capabilities

### FR-01 — Natural-language questions

The user can ask a cricket rules question without knowing the official term or clause number.

**Acceptance:** representative paraphrases of the same question retrieve the same relevant clause family; the response remains grounded in the same official evidence.

### FR-02 — Context capture

The system can capture or infer, with confidence labels:

- Format: Test, ODI, or T20I.
- Category: men's or women's conditions where separate documents apply.
- Competition: general international conditions or a named competition.
- Match/series date or date range, when applicability depends on it.
- Relevant match circumstances supplied by the user.

**Acceptance:** the system asks one focused question when missing context materially changes the applicable rule. It does not silently turn “T20” into “T20I” when domestic rules may apply.

### FR-03 — Applicability resolution

Before retrieval, or as a retrieval constraint, the system identifies candidate sources and versions using explicit metadata and documented applicability/precedence rules.

**Acceptance:** historical and current test cases select the expected source version; ambiguous or unsupported competition contexts are surfaced rather than guessed.

### FR-04 — Hybrid retrieval

The system supports exact keyword/clause search and semantic retrieval. It can combine results and optionally rerank them.

**Acceptance:** retrieval returns relevant clauses, parent context, exceptions, and related provisions for benchmark cases. Search traces are available for debugging.

### FR-05 — Grounded response generation

The LLM explains the retrieved evidence in plain language, distinguishes rule text from explanation, and does not invent missing details.

**Acceptance:** each regulatory claim is supported by one or more retrieved clauses; insufficient evidence results in a qualified response or abstention.

### FR-06 — Citations

The answer displays, where available, publisher, document title, edition/version, clause number, page number, and a link or stable source locator.

**Acceptance:** citations resolve to the exact stored source and clause. The system never fabricates a page or clause reference.

### FR-07 — Rule comparison

The user can compare a rule across supported formats, categories, competitions, or editions.

**Acceptance:** comparisons show the scope and version of each source and clearly state when two documents are not directly comparable.

### FR-08 — Follow-up context

A conversation can retain explicitly established match context for follow-up questions.

**Acceptance:** context is visible or inspectable, can be corrected, and is not carried into a new match scenario without a clear signal.

### FR-09 — Source administration

Authorized maintainers can register, ingest, validate, activate, supersede, and archive official documents.

**Acceptance:** a document cannot become active in the authoritative corpus until required metadata and validation checks are complete.

### FR-10 — Feedback and evaluation

Users or reviewers can flag a wrong answer, bad citation, missing context, or retrieval failure. Maintainers can add reviewed examples to the evaluation dataset.

**Acceptance:** feedback is traceable to the question, retrieval set, source versions, and generated answer, with privacy-conscious retention.

## 2. System quality requirements

### NFR-01 — Correctness and traceability

The system prioritizes source correctness over answer fluency. Evidence IDs and source versions must be available for every generated answer.

### NFR-02 — Reliability

Handle extraction failures, provider timeouts, database failures, malformed input, and empty retrieval results with explicit user-safe errors.

### NFR-03 — Maintainability

Separate document ingestion, normalization, applicability resolution, retrieval, generation, API, and UI. Keep LLM/embedding providers replaceable through interfaces.

### NFR-04 — Performance

Establish a measured baseline before setting latency SLOs. Track extraction duration, query latency by stage, model latency, and total response latency.

### NFR-05 — Security and privacy

Validate inputs, protect credentials, restrict ingestion/admin actions, avoid unnecessary personal-data collection, and avoid logging secrets or sensitive user content.

### NFR-06 — Accessibility and usability

Answers must be readable on desktop and mobile, use clear headings, and expose source references without requiring specialist cricket knowledge.

### NFR-07 — Auditability

Store sufficient versioned metadata to reproduce which documents and clauses informed an answer. Avoid storing more user conversation data than needed.

## 3. Answer contract

For a normal answer, aim to include:

1. **Direct answer** — the conclusion supported by evidence.
2. **Explanation** — why the provision applies.
3. **Conditions/exceptions** — only those material to the question.
4. **Applicable context** — format, competition/category, and edition/date assumptions.
5. **Official references** — document, clause, page/source locator, and link when available.
6. **Limitation** — what remains uncertain or requires an umpire's judgment.

Do not force every field into a response when it would add noise; never omit a qualification that changes the answer.

## 4. Initial intents

- Rule definition.
- Rule interpretation.
- Dismissal and mode of dismissal.
- Delivery legality and penalty.
- Runs, extras, and boundary provisions.
- Fielding restrictions and over limits.
- Match interruption, bad weather, and resumption.
- Umpire signals and decision procedures.
- Format/competition comparison.
- Historical amendment comparison.
- Ambiguous or unanswerable question.

## 5. Out of scope for initial release

- Predicting what an umpire will decide in a live match.
- Treating video/image observations as conclusive evidence.
- Giving betting, fantasy, or match-outcome predictions.
- Reproducing large portions of copyrighted documents without checking the publisher's terms.
- Applying domestic competition rules that have not been added and validated as separate sources.
