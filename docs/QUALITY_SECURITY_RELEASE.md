# Quality, Security, and Release — CricketIQ

## 1. Quality strategy

CricketIQ must be evaluated as a retrieval and decision-support system, not merely as a fluent chatbot. Separate retrieval quality, applicability correctness, answer correctness, citation integrity, and user experience.

## 2. Test layers

### Unit tests

Cover:
- PDF metadata and hash handling.
- Clause parsing and parent/child relationships.
- Table parsing and page mapping.
- Date and applicability boundary logic.
- Format/category/competition metadata filters.
- Result fusion and reranking helpers.
- Citation ID and source-locator validation.
- Prompt/evidence-pack serialization.

### Integration tests

Cover:
- Database migrations and repository operations.
- Full-text and vector retrieval against seeded records.
- Ingestion from a controlled fixture PDF.
- API validation, timeouts, and error responses.
- End-to-end query from user input to cited answer.

### Evaluation tests

Build a human-reviewed benchmark. A useful initial target is approximately 300 questions, distributed across:

| Category | Suggested count |
|---|---:|
| Basic rule questions | 60 |
| Complex interpretation | 50 |
| Format/category comparisons | 40 |
| Match scenarios | 50 |
| Exceptions and edge cases | 40 |
| Historical/version questions | 30 |
| Ambiguous or unanswerable questions | 30 |
| **Total** | **300** |

Each item should store the expected intent, required context, expected source/version, relevant clauses, expected conclusion or abstention, and reviewer status.

### UI tests

Verify:
- Desktop and narrow/mobile layouts.
- Loading and streaming states if used.
- No result / insufficient evidence state.
- Context selector defaults and correction.
- Source links and citation labels.
- Network/provider/database failure messaging.
- Keyboard navigation and basic accessibility.

## 3. Proposed evaluation metrics

These are acceptance targets to test—not measured claims:

| Metric | Proposed target | Definition |
|---|---:|---|
| Retrieval Recall@5 | ≥95% | Expected relevant evidence appears in top 5 |
| Citation validity | ≥98% | Citation resolves to the actual source and clause |
| Expert-rated answer correctness | ≥95% | Correct conclusion and material qualifications |
| Applicability accuracy | ≥98% | Correct source/version selected for benchmark context |
| Unsupported-answer handling | 100% of curated abstention cases | No invented definitive ruling for unanswerable cases |

Report metrics by format, category, intent, and historical/current context. An aggregate score can hide systematic failure in one format.

## 4. Required adversarial and edge-case tests

- User says “T20” but does not say whether the competition is T20I or domestic.
- Format is omitted and changes the answer.
- Match/series date falls on an effective-date boundary.
- A competition-specific document modifies a general playing condition.
- Two sources appear to conflict and precedence wording is unclear.
- Retrieved clause contains an exception in a neighboring clause.
- Retrieval finds a keyword match from an outdated edition.
- PDF extraction loses a table column, footnote, or “not” in a sentence.
- No relevant source is available.
- User asks the model to ignore its sources or invent a clause.
- Prompt-like text appears inside a retrieved PDF or user-uploaded file.
- LLM returns citations that were not in the evidence pack.

## 5. Security and privacy requirements

### Secrets and configuration

- Store provider keys and database credentials in environment variables or a secret manager.
- Commit only `.env.example` with placeholder values.
- Never print secrets in logs, traces, test snapshots, or agent reports.
- Rotate any credential accidentally committed or exposed.

### Input and document safety

- Validate question length, file type, file size, and upload count.
- Treat imported files and extracted text as untrusted input.
- Do not execute content, links, embedded scripts, or instructions found in PDFs.
- Restrict admin ingestion and source activation to authorized users.
- Apply rate limits and timeouts to costly model and parsing endpoints.
- Remote PDF ingestion security (Implemented in Phase 2):
  - Strictly enforce HTTPS and port 443. Reject userinfo, IP literals, and nonstandard ports.
  - Domain allowlist verification (`icc-cricket.com`, `resources.pulse.icc-cricket.com`, `images.icc-cricket.com`, `lords.org`).
  - Pre-flight DNS resolution and IP validation rejecting loopback (`127.0.0.0/8`, `::1`), private (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local/cloud metadata (`169.254.0.0/16`), and multicast to prevent SSRF and DNS rebinding.
  - Streaming size limits (50MB) and PDF magic-byte validation (`%PDF-`).
  - Server-generated safe filenames (`uuid.uuid4().hex + '.pdf'`) preventing path traversal.

### Data handling

- Collect only user data needed for the feature.
- Define retention for chat history, telemetry, and feedback before production.
- Redact secrets and unnecessary personal content from logs.
- Use access controls and encrypted transport for hosted services.
- Back up the database and original source files; test restoration.

### Retrieval subsystem security and quality controls (Implemented in Phase 3)

- **SQL Parameterization & FTS Sanitization:**
  - Full-text queries are constructed using structured parameter binding (`:match_query`, `:doc_0`, ...).
  - User query text is never interpolated into raw SQL.
  - Punctuation, unclosed quotes, and hostile tokens (`***)))(((;;;'''''"""`, `NEAR`, `NOT`) are safely tokenized or stripped to prevent syntax injection or FTS parse exceptions.
- **Atomic Vector Rebuild & Safe Serialization:**
  - Embedding tables use `float32` byte arrays (`BLOB`) instead of untrusted pickle serialization.
  - Rebuilding embeddings utilizes staging tables (`clause_embeddings_staging`) swapped in an atomic transaction; index corruption cannot occur on mid-build failure.
  - Vectors are validated for expected dimension (384), finiteness (rejecting NaN and Inf), and non-zero magnitude before persistence.
- **Pre-Search Applicability Gating & Regulatory Leakage Prevention:**
  - No database search occurs if the query context is ambiguous or targets unsupported competitions (e.g., domestic leagues).
  - Search candidates are strictly pre-filtered to the resolved `selected_bundle`.
  - Zero regulatory leakage invariant (0.0% measured across all benchmark runs).
- **Evidence Graph Traversal Bounds:**
  - Parent section and cross-clause graph expansion is strictly depth-bounded ($\le 2$ hops).
  - Visited clause tracking prevents infinite cyclic reference loops.
  - Expanded clauses are strictly confined to the active candidate bundle.

## 6. Copyright and source-use review

Before loading or displaying official MCC/ICC materials:

- Review the current publisher terms and copyright notices.
- Distinguish internal indexing from public redistribution.
- Do not assume that a publicly accessible PDF is free to republish.
- Store only the amount of source text permitted for the intended use.
- Prefer short attributed excerpts and links to official source documents where appropriate.
- Record the reviewer, date, and outcome of the usage review.

## 7. Observability

For each request, capture a privacy-conscious trace with:

- Trace/request ID and timestamp.
- Parsed intent and context fields, with inferred vs explicit values distinguished.
- Applicability resolver result and reason codes.
- Source document IDs/versions considered.
- Retrieved clause IDs, ranks, and retrieval strategy.
- Model/provider and prompt-template version (not secret credentials).
- Citation validation outcome.
- Latency by stage and error category.

Avoid logging full personal conversation content by default. Define access and retention controls for any diagnostic payloads.

## 8. Release checklist

### Before release

- [ ] Scope and known limitations are documented.
- [ ] Active official source inventory is reviewed and current.
- [ ] Source terms/attribution review is recorded.
- [ ] Document versions, effective dates, and amendment relationships are validated.
- [ ] Database migrations are tested against a clean database and an upgrade path.
- [ ] Unit, integration, and evaluation tests are run.
- [ ] Critical citation and applicability tests pass.
- [ ] No secrets or private data are committed.
- [ ] Authentication and admin authorization are verified where applicable.
- [ ] Error handling, rate limits, backups, and monitoring are configured.
- [ ] UI source links and empty/error states are checked.
- [ ] Deployment and rollback steps are documented.
- [ ] A human reviewer approves release readiness.

### After release

- [ ] Smoke-test a small set of known questions.
- [ ] Verify source citations resolve correctly.
- [ ] Monitor retrieval failures, abstention, latency, and provider errors.
- [ ] Confirm backup completion.
- [ ] Record release version and active source-index version.

## 9. Incident response for wrong rule answers

1. Capture the trace ID, question context, source versions, evidence pack, and answer.
2. Classify the failure: source/version, applicability, extraction, retrieval, reranking, generation, citation, or UI.
3. If a material rule error is confirmed, disable or qualify the affected answer path/source version as needed.
4. Correct the source data or logic with a regression test.
5. Re-run the relevant benchmark slice and full regression suite when appropriate.
6. Document the cause, correction, and user-facing impact.

Never silently patch an answer string without correcting the underlying source or system failure.
