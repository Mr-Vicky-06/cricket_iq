# CricketIQ — Retrieval Architecture

## 1. Overview and Core Philosophy

CricketIQ's retrieval subsystem provides deterministic, evidence-grounded rule clause retrieval. Unlike generic RAG systems that query an unconstrained vector database, CricketIQ enforces a strict **Applicability-First** architectural invariant:

1. **Pre-Search Gating:** No lexical or semantic search is executed until the Phase 2 `ApplicabilityEngine` evaluates the query/match context and assembles an authoritative `selected_bundle`.
2. **Bundle Confinement:** Every retrieved hit, expanded parent section, and cross-referenced clause belongs exclusively to the candidate documents in the active source bundle.
3. **Exact Identifier Protection:** Technical clause numbers (e.g. `21.18.2`) are handled via a dedicated exact lookup path rather than relying solely on subword tokenizers or semantic embeddings.
4. **Hybrid Rank Fusion:** Sparse lexical search (SQLite FTS5 / BM25) and dense semantic search (NumPy / SentenceTransformers) are fused using unweighted Reciprocal Rank Fusion ($k=60$).
5. **Composite Regulatory Evidence:** Critical cricket rules cannot be answered from an isolated clause. Bounded evidence graph expansion automatically retrieves parent headers and cross-referenced clauses (such as Clause 21.18.2 referencing Clause 21.17 for Free Hit dismissal exceptions).

```
User Query + Match Context
          │
          ▼
Phase 2 Applicability Engine ──(If Ambiguous/Domestic)──► Return Clarification (Halt)
          │
          ▼ (Authoritative Source Bundle via RegulatoryRole Precedence)
Candidate Document Pre-Filter
          │
     ┌────┼──────────────────────────┐
     ▼    ▼                          ▼
Exact   Sparse Lexical Search      Dense Semantic Search
Lookup  (SQLite FTS5 / BM25)       (NumPy Cosine / pgvector)
(Regex)   │                          │
     │    └──────────────┬───────────┘
     └───────────────────┼───────────┐
                         ▼           │ (Exact matches top-priority)
          Reciprocal Rank Fusion (RRF)
          Score(d) = Σ [ 1 / (60 + rank_r(d)) ]
                         ▼
          Bounded Evidence Graph Expansion
          (Parent Section + Cross-References, depth ≤ 2)
                         ▼
             Ranked Structured Evidence Pack
```

### Precedence Hierarchy & Regulatory Role Model
As established in Phase 6 Gate 2, every document is tagged with an immutable `RegulatoryRole`:
- `NORMATIVE_COMPETITION_REGULATION`: Overlays all format conditions (e.g. WTC).
- `NORMATIVE_ADDENDUM`: Supplements primary format playing conditions (e.g. ICC T20I Addendum).
- `NORMATIVE_FORMAT_PC`: Format baseline (Test, ODI, T20I).
- `NORMATIVE_LAWS_BASELINE`: Universal underlying laws of cricket (`MCC_LAWS_2026`, historical `MCC_LAWS_2022`).
- `EXPLANATORY_GUIDANCE`: Non-normative supplemental explanations (`MCC_CHANGES_EXPLAINED_2026`), appended at lowest precedence and never permitted to replace normative baseline laws.

Bundles are assembled in strict precedence order:
$$\text{Competition Regulation} \rightarrow \text{Addenda} \rightarrow \text{Format PC} \rightarrow \text{Normative Baseline Laws} \rightarrow \text{Explanatory Guidance}$$

Catalog sorting is strictly deterministic by document identifier prior to resolution, guaranteeing complete catalog-order permutation invariance. All 10,388 unique canonical clauses across relational, FTS5, and vector tables map 1-to-1 with zero cross-bundle leakage (0.0%).

---

## 2. Exact Clause Number Lookup

Users, commentators, and umpires frequently search for specific clauses by dotted notation (e.g., *"What is clause 21.18.2?"* or *"Law 21.1"*).

### Detection Regular Expression
```python
EXACT_CLAUSE_PATTERN = re.compile(
    r"(?:(?:clause|law|rule|section)\s+)?\b([0-9]{1,2}(?:\.[0-9]{1,2}(?:\.[0-9]{1,2})?)?)\b",
    re.IGNORECASE
)
```

- Matches dotted clause numbers (`21.18.2`, `21.18`, `22.1`, `21.1`) and standalone law numbers when preceded by Law/Clause.
- Matches are queried directly against `rule_clauses.clause_number` scoped by `source_document_id IN (candidate_document_ids)`.
- Matching clauses receive top-rank confidence in fusion ($1.0$).

---

## 3. Sparse Lexical Search

### SQLite FTS5 Implementation
SQLite FTS5 provides fast, full-text indexing without external search daemons.

#### Virtual Table Schema
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS rule_clauses_fts USING fts5(
    clause_id UNINDEXED,
    source_document_id UNINDEXED,
    clause_number,
    heading,
    content,
    tokenize=porter
);
```

#### BM25 Column Weighting
Relevance is weighted across fields:
- `clause_number`: Weight $10.0$
- `heading`: Weight $5.0$
- `content`: Weight $1.0$

```sql
SELECT clause_id, bm25(rule_clauses_fts, 10.0, 5.0, 1.0) AS rank
FROM rule_clauses_fts
WHERE rule_clauses_fts MATCH :match_query
  AND source_document_id IN (:doc_0, :doc_1, ...)
ORDER BY rank ASC
LIMIT :limit;
```

#### Query Sanitization & Cricket Punctuation
- Hyphenated domain terms (`no-ball`, `free-hit`, `wide-ball`) and key multi-word phrases are preserved as quoted phrases (`"no ball"`, `"free hit"`).
- Special characters that could break FTS5 parser (`*`, `(`, `)`, `"`, `;`) are stripped or wrapped safely.
- All parameters are bound via prepared statements; user text is never directly concatenated into SQL.

---

## 4. Dense Semantic Search & Vector Store

### Pseudo-Embedding Channel Safety (Gate 2 Remediation Invariant)
In the initial baseline, `LocalDeterministicEmbeddingProvider` generated 384-dimensional MD5 feature buckets for vector schema testing. In Phase 6 Gate 2, the channel safety contract was formalized:
- `EmbeddingProvider.is_semantic`: Boolean flag indicating whether the provider outputs genuine semantic representations (`True`) or diagnostic structural pseudo-vectors (`False`).
- `LocalDeterministicEmbeddingProvider.is_semantic = False`.
- In `RetrievalService`, dense participation in production Reciprocal Rank Fusion is **gated by semantic readiness**. By default (`enable_diagnostic_dense=False`), `local-deterministic-v1` vectors are excluded from production RRF ranking, ensuring that pseudo-vector artifacts cannot displace high-scoring BM25 lexical hits.
- Genuine semantic embeddings (`all-MiniLM-L6-v2` / `bge-small-en-v1.5`) will be introduced in Gate 4.

### Versioned Embedding Text Template (`v1`)
Embedding text incorporates regulatory context without modifying the stored `original_text`:

```python
def build_clause_embedding_text(clause: RuleClause, doc: Optional[SourceDocument] = None) -> str:
    context_prefix = ""
    if doc:
        pub = doc.publisher.value if hasattr(doc.publisher, "value") else str(doc.publisher)
        fmt = f" {doc.format.value if hasattr(doc.format, 'value') else str(doc.format)}" if doc.format else ""
        ed = f" {doc.edition}" if doc.edition else ""
        context_prefix = f"[{pub}{fmt}{ed}] "

    heading_part = f" - {clause.heading}" if clause.heading else ""
    return f"{context_prefix}Clause {clause.clause_number}{heading_part}: {clause.original_text.strip()}"
```

### Embedding Storage Schema
Vectors are stored in SQLite as binary float arrays (`float32` BLOBs) alongside metadata:
```sql
CREATE TABLE IF NOT EXISTS clause_embeddings (
    clause_id VARCHAR(128) PRIMARY KEY,
    document_id VARCHAR(128) NOT NULL,
    model_name VARCHAR(64) NOT NULL,
    dimension INTEGER NOT NULL,
    template_version VARCHAR(16) NOT NULL,
    input_hash VARCHAR(64) NOT NULL,
    vector_blob BLOB NOT NULL,
    created_at VARCHAR(32) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_embeddings_doc ON clause_embeddings(document_id);
```

### Atomic Rebuild via Staging Table
Rebuilding the vector index uses `clause_embeddings_staging`. The entire corpus is embedded and validated before an atomic table swap is performed in a transaction. If encoding fails or produces invalid vectors (e.g. NaN or dimension mismatch), the existing index remains completely undamaged.

### Similarity Calculation
- Local execution calculates cosine similarity using NumPy vector operations:
  $$\text{sim}(\vec{q}, \vec{c}) = \frac{\vec{q} \cdot \vec{c}}{\|\vec{q}\|_2 \|\vec{c}\|_2}$$
- Candidate vectors are filtered by `candidate_document_ids` prior to dot-product calculations.

---

## 5. Reciprocal Rank Fusion (RRF)

To combine sparse BM25 scores and dense cosine similarities without calibrating incompatible distributions:

$$RRF(d) = \sum_{r \in \{\text{sparse}, \text{dense}\}} \frac{1}{k + \text{rank}_r(d)}$$

- Default constant: $k = 60$.
- Missing from a ranked list contributes $0$.
- Deduplicated on stable `clause_id`.
- Deterministic tie-breaking: `(-rrf_score, best_rank, clause_number, clause_id)`.
- Full rank provenance (`sparse_rank`, `dense_rank`, `rrf_score`) is recorded in `RetrievalHit`.

---

## 6. Bounded Evidence Graph Expansion

Cricket rules require composite evidence to be legally actionable. For example:
- ICC T20I Clause 21.18.2 states: *"the striker can be dismissed only under the circumstances that apply for a No ball"*.
- The list of permitted dismissals (Run out, Hit the ball twice, Obstructing the field) is specified in **Clause 21.17**.

### Expansion Rules
1. **Parent Context:** If `primary_clause.parent_clause_id` exists, the parent section (e.g. `21.18 Free Hit` header) is added with `evidence_role = EvidenceRole.PARENT_CONTEXT`.
2. **Cross-Clause Relationships:** For each entry in `primary_clause.cross_references`, matching clauses within candidate documents are added with `evidence_role = EvidenceRole.RELATED_SUPPORT`.
3. **Boundaries:**
   - Traversal depth is capped at $\le 2$ hops.
   - Visited clause IDs are tracked to guarantee cycle termination.
   - Inapplicable documents or superseded editions are strictly excluded.

---

## 7. Gate 3 Intelligence & Evidence Hydration (Implemented)

Phase 6 Gate 3 introduces domain NLP intelligence, structural clause hierarchy traversal, and structured table evidence hydration while maintaining the frozen public API contract:

1. **Controlled Lexicon Query Expansion (`LexiconExpansionService`):**
   - Grounded in `data/corpus/lexicon/cricket_lexicon.json` (20 approved terms validated by `LexiconValidator`).
   - Enforces hard non-equivalence boundaries (`retired hurt` $\neq$ `retired out`, `wide` $\neq$ `no ball`, `run out` $\neq$ `stumped`).
   - Bounded expansion ($K \le 2$ phrases per term, max 3 terms per query) prevents FTS query inflation.
   - Preserves raw query immutability; emits `NormalizedQueryView` and substitutes colloquial slang (`mankad`, `beamer`, `chucking`) with statutory legal phrasing.
   - Suppresses redundant expansions when user already used canonical terms (e.g. `no-ball` / `no ball`).

2. **Deterministic Hierarchy Traversal (`HierarchyTraversalService`):**
   - True tree depths (Depths 1 through 4) calculated via `scripts/recompute_clause_depths.py`, resolving the legacy depth-1 anomaly with zero cycles across 10,388 unique clauses.
   - Traversal is strictly confined to the active candidate document bundle (`candidate_document_ids`).
   - Maximum 1 hop upward (`PARENT_CONTEXT`) and 1 hop downward (`OPERATIONAL_CHILD`).
   - Resolves statutory cross-references within bundle (`STATUTORY_CROSS_REFERENCE`) while blocking out-of-bundle references.
   - Enforces maximum 5-snippet budget and 1,200 token budget with direct evidence protection.

3. **Structured Table Evidence Hydration (`TableEvidenceService`):**
   - Exposes quantitative regulatory specifications (DRS Hawk-Eye pitching, impact, and wicket zones, review consequences, and Powerplay overs matrices) via typed `TableEvidence` models.
   - Reconciles 246 total tables, restricting active retrieval strictly to 39 `SOURCE_VERIFIED` tables in active Playing Conditions while isolating 84 historical MCC 2022 tables as `EXTRACTED_UNVALIDATED`.
   - Deterministic Markdown prompt rendering with pipe escaping (`\|`), line-break conversion, source document metadata, and numeric claim validation (`validate_numeric_claim`).

4. **Internal Typed Contracts & Observability:**
   - Independent feature flags in `RetrievalService`: `enable_lexicon_expansion`, `enable_hierarchy_traversal`, `enable_table_evidence` (all default `False`).
   - Granular per-stage latency diagnostics, correlation ID, query hash, expansion provenance, traversed nodes by role, and hydrated table IDs recorded in `RetrievalObservabilityTrace`.
   - Public API `POST /v1/rules/query` request/response schemas and OpenAPI specification remain 100% byte-identical.
