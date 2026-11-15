# ADR 0002: Sparse + Dense Hybrid Retrieval, Reciprocal Rank Fusion (RRF), and Evidence Expansion

- **Status:** Accepted
- **Date:** 2026-11-15
- **Deciders:** CricketIQ Architecture, Information Retrieval, and NLP Team
- **Context:** Antigravity Phase 3 Implementation

---

## 1. Context and Problem Statement

Cricket regulations present distinct information retrieval challenges:
1. **Exact Identifier Queries:** Users and umpires often ask directly about clause numbers (e.g., *"What is clause 21.18.2?"* or *"Law 38"*). Dense semantic embeddings frequently fail on granular numerical identifiers.
2. **Domain Vocabulary Overlap:** Terms like "No ball", "Free hit", "Wide", and "Dead ball" require exact lexical matching to avoid false positives with neighboring rules.
3. **Paraphrased Queries:** Lay users ask questions without knowing official terminology (e.g., *"Can a batsman be out after a front-foot no-ball free delivery?"*). Dense semantic retrieval is necessary to bridge the vocabulary gap.
4. **Composite Evidence:** Crucial cricket rules cannot be understood from a single isolated clause. For example, ICC T20I Clause 21.18.2 states dismissals on a Free Hit are restricted to those permitted for a No ball, but the actual list of permitted dismissals (Run out, Hit the ball twice, Obstructing the field) is specified in Clause 21.17.
5. **Regulatory Applicability Invariant:** Searching the entire rulebook globally leads to severe errors (such as returning Test match conditions for T20I questions or superseded 2024 editions for 2026 matches).

---

## 2. Decision

We establish an evidence-grounded, hybrid retrieval architecture structured as follows:

```
User Query + Match Context
          │
          ▼
Phase 2 Applicability Engine ──(If Unresolved)──► Return Clarification (Do Not Search)
          │
          ▼ (Applicable Source Bundle)
Candidate Document Pre-Filter
          │
     ┌────┴──────────────────────────┐
     ▼                               ▼
Sparse Lexical Search       Dense Semantic Search
(SQLite FTS5 / BM25)        (Dense Embeddings + Cosine)
     │                               │
     └──────────────┬────────────────┘
                    ▼
     Reciprocal Rank Fusion (RRF)
     Score(d) = Σ [ 1 / (60 + rank(d)) ]
                    ▼
     Bounded Evidence Graph Expansion
     (Parent Section + Cross-Referenced Clauses)
                    ▼
     Ranked Structured Evidence Pack
```

### 2.1 Applicability-First Invariant
Retrieval is strictly downstream of the Phase 2 `ApplicabilityEngine`.
- If the applicability engine returns `UNRESOLVED` or `CLARIFICATION_NEEDED`, the retrieval engine halts and returns status `CLARIFICATION_REQUIRED` without executing database searches.
- Candidate clauses are strictly pre-filtered to `candidate_document_ids` belonging to `ApplicabilityDecision.selected_bundle`. Clauses from superseded or non-candidate editions are impossible to retrieve.

### 2.2 Exact Clause Lookup & Sparse Search
- Dotted clause identifiers (`^\d{1,2}(\.\d{1,2}(\.\d{1,2})?)?$`) are detected by regular expression and matched directly against `RuleClause.clause_number`.
- Sparse lexical search utilizes SQLite FTS5 for local execution and PostgreSQL `tsvector` with GIN indexing for production.
- Token overlap across headings and original text is weighted with log-damped term frequency.

### 2.3 Dense Semantic Search & Embedding Strategy
- A pluggable `EmbeddingProvider` protocol defines text and batch embedding generation.
- Production candidate: `all-MiniLM-L6-v2` (SentenceTransformers, 384 dimensions, Apache 2.0).
- Local deterministic fallback: `LocalDeterministicEmbeddingProvider` produces 384-dimensional normalized vectors via subword n-gram hashing, enabling deterministic testing without network downloads.
- Vectors are stored alongside metadata (model name, dimension, text hash) and compared using cosine similarity.

### 2.4 Unweighted Reciprocal Rank Fusion (RRF)
To combine sparse and dense ranked candidate lists without calibrating incompatible raw score distributions:
$$RRF(d) = \sum_{m \in \{\text{sparse}, \text{dense}\}} \frac{1}{k + \text{rank}_m(d)}$$
where $k = 60$ (configurable constant). Deduplication occurs on stable `clause_id`, preserving sparse and dense ranks for auditability.

### 2.5 Bounded Evidence Graph Expansion
For the top-ranked primary clauses:
1. **Parent Context:** If `clause.parent_clause_id` exists, the parent clause (e.g. `21.18 Free Hit` header) is included as `PARENT_CONTEXT`.
2. **Cross-Clause Evidence:** If `clause.cross_references` exists (e.g. `21.18.2` referencing `21.17`), the referenced clauses within the source bundle are included as `RELATED_SUPPORT`.
3. Traversal depth is bounded ($\le 2$ hops) and cycle-protected to prevent runaway expansion.

---

## 3. Consequences

### Positive
- High Recall on both technical clause numbers and colloquial lay queries.
- Zero risk of cross-format rule leakage or historical edition confusion.
- Complete composite evidence: answers regarding free hits will always include the underlying dismissal exceptions from Clause 21.17.
- Local reproducibility: unit tests run in $<2$ seconds on local SQLite without network calls.

### Trade-offs
- Two-stage retrieval and fusion requires slightly more compute than single-pass vector search.
- Indexing must maintain both FTS text tables and vector embeddings.
