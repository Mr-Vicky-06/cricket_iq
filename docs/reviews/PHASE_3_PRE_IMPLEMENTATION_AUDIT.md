# Phase 3 Pre-Implementation Audit — CricketIQ

**Date:** 2026-11-15  
**Auditor:** CricketIQ Principal Architecture & IR Engineering Team  
**Milestone:** Phase 3 — Hybrid Retrieval Baseline  
**Repository:** `D:\Cricket_Rules_NLP_Chatbot`  

---

## 1. Verified Repository State & Test Baseline

- **Runtime & Environment:** Python 3.12.10 (Windows x86_64), `uv` virtual environment at `.venv`.
- **Database Engine:** SQLite 3 with runtime `FTS5` capability confirmed via `check_sqlite_fts5_support()` and pragma compilation options.
- **ORM & Migrations:** SQLAlchemy 2.0+ declarative models mapped in `orm_models.py` with Alembic initial migration `f1b6b37e1116_initial_schema.py` applied.
- **Test Baseline:** Exactly 29 tests passing, 1 PostgreSQL integration test skipped cleanly (when no `TEST_POSTGRES_DSN` is configured). Run duration: 1.83s.
- **Git State:** Commit `3913395` (`feat(phase-2): structured rule store, alembic migrations, deterministic applicability engine, and security hardening`). Working tree clean before Phase 3 edits.

---

## 2. Existing Interfaces & Reuse Plan

The retrieval subsystem directly consumes the following existing contracts:
1. `RuleCatalog` Protocol (`cricketiq/backend/app/database/repository.py`):
   - `get_document(doc_id: str) -> Optional[SourceDocument]`
   - `list_active_documents() -> List[SourceDocument]`
   - `get_relationships(doc_id: str) -> List[DocumentRelationship]`
   - `get_clause(clause_id: str) -> Optional[RuleClause]`
   - `get_clauses_for_document(doc_id: str) -> List[RuleClause]`
   - `get_clause_hierarchy(clause_id: str) -> Dict[str, Any]`
2. `ApplicabilityEngine` (`cricketiq/backend/app/core/applicability_engine.py`):
   - Pure domain service contract: `resolve(context: MatchContext, catalog: RuleCatalog) -> ApplicabilityDecision`.
   - Returns candidate documents in `decision.selected_bundle` (e.g. `['ICC_T20I_MEN_2026', 'MCC_LAWS_2026']`).
3. Domain Models (`cricketiq/backend/app/database/models.py`):
   - `RuleClause`: Contains `id`, `source_document_id`, `clause_number`, `parent_clause_id`, `hierarchy_depth`, `heading`, `original_text`, `normalized_text`, `clause_type`, `cross_references`.

---

## 3. Reconciliation of Source Bundle Hierarchy & Addenda

### Inconsistency Identified
- ADR 0001 Section 2.2 presented the source bundle as:
  $$\text{Competition} \rightarrow \text{Format PC} \rightarrow \text{Addenda} \rightarrow \text{MCC Baseline}$$
- The Phase 2 Delivery Report presented:
  $$\text{Competition} \rightarrow \text{Addenda} \rightarrow \text{Format PC} \rightarrow \text{MCC Baseline}$$

### Formal Domain Resolution
In official cricket regulation governance (ICC/MCC):
An **Addendum** is not an independent tournament layer; it is an official amendment issued by the ICC governing authority to amend or supplement a *specific parent document* (e.g. "Addendum to ICC Men's T20I Playing Conditions").
Therefore:
1. An addendum binds to its specific parent document (`parent_doc_id`).
2. Within that document's scope, clauses published in the addendum override or supplement the parent document's unamended clauses.
3. The overall governing precedence hierarchy is:
   $$\text{Competition Regulations} \rightarrow \text{Competition Addenda} \rightarrow \text{Standard Format PC} \rightarrow \text{Format Addenda} \rightarrow \text{Underlying MCC Laws Baseline}$$
4. This relationship is formally modeled as a directed edge in `DocumentRelationshipEntity` with `relationship_type = MODIFIES` or `SUPPLEMENTS`. The retrieval and applicability layers evaluate these explicit edges rather than guessing global document ranks.

---

## 4. Source Corpus Coverage & Gaps

- **Currently Ingested & Verified:**
  - `ICC_T20I_MEN_2026`: ICC Men's T20I Playing Conditions (October 2026 Edition) covering Laws 21 (No Ball) & 22 (Wide Ball) including Free Hit rules (Clause 21.18).
- **Pending Full Corpus (Phase 6):**
  - Full MCC Laws of Cricket (2017 Code 4th Edition 2026, 3rd Edition 2022).
  - ICC Men's Test & ODI Playing Conditions (October 2026 & October 2024 editions).
  - ICC Women's Test, ODI, and T20I Playing Conditions.
  - ICC Men's T20 World Cup 2026 Playing Conditions.
- **Handling in Phase 3:**
  - Retrieval unit tests and benchmark datasets operate strictly on verified source documents and controlled fixtures with authentic rule wording. No synthetic or invented clause numbers will be used.

---

## 5. Embedding Model Evaluation & Selection Strategy

To satisfy Gate 3 without requiring multi-gigabyte internet downloads during tests:
1. **Candidate 1: `all-MiniLM-L6-v2` (SentenceTransformers)**
   - Dimension: 384
   - License: Apache 2.0
   - Strengths: Fast CPU inference, widely adopted, strong semantic sentence similarity.
2. **Candidate 2: `bge-small-en-v1.5` (BAAI)**
   - Dimension: 384
   - License: MIT
   - Strengths: State-of-the-art dense retrieval on MTEB, optimized for search queries.
3. **Deterministic Local Fallback: `LocalDeterministicEmbeddingProvider`**
   - Dimension: 384
   - Footprint: Zero network download, pure NumPy character/word n-gram hash projection into normalized hypersphere.
   - Purpose: Ensures 100% test reproducibility and offline execution on any developer machine without network dependencies.

---

## 6. Phase 3 Architecture & Plan (Gates 1–6)

- **Gate 1:** Retrieval Contracts (`RetrievalRequest`, `RetrievalHit`, `RetrievalOutcome`) and `ExactClauseLookupEngine`.
- **Gate 2:** Sparse Lexical Retrieval (`SQLiteFTSSearchProvider` with FTS5 virtual table synchronization and PostgreSQL GIN adapter).
- **Gate 3:** Embedding Provider abstraction and versioned vector persistence (`EmbeddingStore`).
- **Gate 4:** Dense Semantic Search (`DenseVectorSearchProvider` with NumPy cosine similarity and pgvector production path).
- **Gate 5:** Reciprocal Rank Fusion (`RRFEngine` with $k=60$) and bounded `EvidenceExpander` (recursively gathering parent context and cross-referenced clauses such as Clause 21.17 for Free Hit).
- **Gate 6:** Retrieval evaluation benchmark (versioned JSONL dataset), latency measurements, and documentation updates.
