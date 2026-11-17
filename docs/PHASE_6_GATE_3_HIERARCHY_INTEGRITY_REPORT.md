# CricketIQ — Canonical Clause Hierarchy & Relationship Integrity Report (Gate 3)

- **Date:** 2026-11-17
- **Document Version:** 1.0.0
- **Scope:** Phase 6 Gate 3 Pre-Implementation Audit
- **Data Asset:** `data/corpus/clauses/*_clauses.json` (10,388 unique canonical clauses across 11 documents)
- **Companion Specifications:** `docs/reviews/PHASE_6_GATE_3_PRE_IMPLEMENTATION_AUDIT.md`, `docs/SYSTEM_ARCHITECTURE.md`

---

## 1. Executive Summary

Cricket statutory codes are intrinsically hierarchical: a high-level Law or Playing Condition (e.g., *Law 21 No ball*) contains major structural subsections (e.g., *21.1 Mode of delivery*, *21.5 Fair delivery - the feet*), which in turn contain granular operational clauses (e.g., *21.5.1*, *21.5.2*). When an exact operational clause is retrieved, presenting it in isolation often strips essential definitions, exceptions, and umpire signals defined in its parent or sibling clauses.

This audit evaluates the structural integrity of the canonical clause hierarchy across all 11 active documents in `data/corpus/clauses/`.

### Key Findings
1. **Strictly Acyclic Forest (0 Cycles):** A cycle-detection traversal of all 10,388 clauses confirmed **zero cycles** across all 11 documents. Every populated parent link forms a valid directed tree rooted in a primary Law or Regulation header.
2. **Empirical Discovery — Uniform Depth-1 Anomaly:** Across all 11 canonical JSON files, `hierarchy_depth` is uniformly set to `1` for all 10,388 clauses. Even deeply nested clauses (such as `ICC_TEST_MEN_2026:21.5.1.1` or `MCC_LAWS_2026:41.3.2.1`) have `hierarchy_depth: 1` in the JSON corpus.
3. **Cross-Document Isolation:** Parent links are **100% intra-document**. No clause has a parent in another document.
4. **Cross-References:** 3,126 cross-references are documented in the corpus. They represent vital lateral citations (e.g., a Free Hit clause cross-referencing Law 34, 37, and 38 for dismissals) and must be resolved within the candidate document bundle at query time.

---

## 2. Per-Document Hierarchy Statistics Ledger

The following ledger details the empirical hierarchy metrics extracted directly from the canonical JSON files in `data/corpus/clauses/`:

| Document ID | Total Clauses | Root Clauses (`parent == None`) | Child Clauses (`parent != None`) | Missing Parent IDs | Cross-Doc Parent Links | Cycles Detected | Current Depth Distribution in JSON | Cross-References |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`ICC_ODI_MEN_2026`** | 1,221 | 51 | 1,170 | 31 | 0 | **0** | `{1: 1221}` | 358 |
| **`ICC_ODI_WOMEN_2026`** | 1,213 | 52 | 1,161 | 31 | 0 | **0** | `{1: 1213}` | 360 |
| **`ICC_T20I_MEN_2026`** | 1,234 | 50 | 1,184 | 33 | 0 | **0** | `{1: 1234}` | 358 |
| **`ICC_T20I_MEN_ADD_2026`** | 26 | 5 | 21 | 16 | 0 | **0** | `{1: 26}` | 21 |
| **`ICC_T20I_WOMEN_2026`** | 1,239 | 50 | 1,189 | 33 | 0 | **0** | `{1: 1239}` | 361 |
| **`ICC_TEST_MEN_2026`** | 1,241 | 51 | 1,190 | 37 | 0 | **0** | `{1: 1241}` | 370 |
| **`ICC_TEST_WOMEN_2026`** | 1,243 | 50 | 1,193 | 37 | 0 | **0** | `{1: 1243}` | 373 |
| **`ICC_WTC_2025_2027_PC`** | 1,263 | 51 | 1,212 | 37 | 0 | **0** | `{1: 1263}` | 374 |
| **`MCC_CHANGES_EXPLAINED_2026`** | 182 | 1 | 181 | 82 | 0 | **0** | `{1: 182}` | 50 |
| **`MCC_LAWS_2022`** | 1,197 | 9 | 1,188 | 0 | 0 | **0** | `{1: 1197}` | 282 |
| **`MCC_LAWS_2026`** | 949 | 50 | 899 | 32 | 0 | **0** | `{1: 949}` | 219 |
| **TOTALS** | **10,388** | **420** | **9,968** | **349** | **0** | **0** | **`{1: 10388}`** | **3,126** |

---

## 3. Root Cause Analysis: The Depth-1 Anomaly

### The Anomaly
In `cricketiq.db` and canonical JSON files, `hierarchy_depth` is uniformly set to `1` across all 10,388 clauses. For instance:
- `ICC_TEST_MEN_2026:21` (Major Law heading) $\rightarrow$ `depth: 1`
- `ICC_TEST_MEN_2026:21.5` (Section heading, parent is `21`) $\rightarrow$ `depth: 1`
- `ICC_TEST_MEN_2026:21.5.1` (Substantive rule, parent is `21.5`) $\rightarrow$ `depth: 1`

### Root Cause
1. During Phase 2 ingestion, the PDF parser successfully extracted dot-separated clause identifiers and inferred `parent_clause_id` by stripping trailing sub-numbers (e.g., `21.5.1` $\rightarrow$ parent `21.5`).
2. However, the serialization step populated the Pydantic schema default (`hierarchy_depth: int = 1`) without recursively traversing parent chains to compute true mathematical tree depth.
3. Consequently, relational SQL queries filtering by `hierarchy_depth > 1` return zero rows, and hierarchy-based context expansion cannot rely on the `hierarchy_depth` column in its current state.

### Missing Parents Analysis (349 instances)
- In the ICC Playing Conditions, ~31-37 clauses per document list a parent ID (e.g., `ICC_TEST_MEN_2026:12`) that corresponds to an unnumbered chapter title or appendix heading that was not emitted as an independent clause record during initial PDF extraction.
- In `MCC_CHANGES_EXPLAINED_2026`, 82 clauses list parents corresponding to MCC Laws (e.g., `MCC_LAWS_2026:41.3`) because the explanatory document references the Law it modifies.
- **Remedy:** Missing parent links will be sanitized in Gate 3 by:
  1. Synthesizing explicit structural section header nodes where missing.
  2. For explanatory guidance, recording Law references as `cross_references` rather than broken `parent_clause_id` links.

---

## 4. Deterministic Hierarchy Traversal Design for Gate 3

To enrich retrieved rule evidence without exploding the context window or diluting retrieval precision, Gate 3 will introduce a deterministic **Hierarchy Evidence Traversal Engine**:

```mermaid
graph TD
    Parent["Parent Clause (e.g., 21.5 Fair Delivery - Feet)<br>[Role: DEFINITIONAL_CONTEXT]"]
    Seed["Primary Retrieved Hit (e.g., 21.5.1 Back Foot Landing)<br>[Role: DIRECT_ANSWER]"]
    Child["Leaf Child (e.g., 21.5.1.1 Exceptions)<br>[Role: OPERATIONAL_EXCEPTION]"]
    XRef["Cross-Referenced Clause (e.g., Law 21.18 Free Hit)<br>[Role: STATUTORY_CROSS_REFERENCE]"]

    Seed -->|Hop Up (Max 1)| Parent
    Seed -->|Hop Down (Max 1)| Child
    Seed -->|Follow Reference (Max 1, Confined to Bundle)| XRef
```

### Traversal Invariants & Guardrails

1. **Candidate-Document Confinement:**
   - Traversal must **NEVER cross document boundaries** outside the active candidate bundle resolved by `ApplicabilityEngine`.
   - If an ICC Men's Test query retrieves `ICC_TEST_MEN_2026:21.5`, traversal can expand to `ICC_TEST_MEN_2026:21` (parent) or `MCC_LAWS_2026:21` (if incorporated), but NEVER to `ICC_T20I_MEN_2026` or domestic rules.
2. **Strict Bounded Hops:**
   - **Child-to-Parent (Upward):** Maximum **1 hop**. Retrieves immediate parent heading/scope to supply context.
   - **Parent-to-Child (Downward):** Maximum **1 hop**. Retrieves operational leaf clauses if the query hits a broad section header.
   - **Lateral Cross-References:** Maximum **1 hop**, bounded to explicit clause identifiers in `cross_references`.
3. **Evidence Role Assignment:**
   - Every retrieved snippet is tagged with an immutable evidence role:
     - `DIRECT_EVIDENCE`: Primary search hit from exact lookup or FTS5 BM25.
     - `PARENT_CONTEXT`: Ancestor clause supplying definition or title.
     - `OPERATIONAL_CHILD`: Child sub-clause specifying granular rules or exceptions.
     - `CROSS_REFERENCE`: Explicit statutory cross-citation.
4. **Strict Token & Snippet Budgets:**
   - Maximum total evidence snippets per query: $M \le 5$.
   - Maximum evidence tokens fed to LLM generation: $T \le 1,200$ tokens.
   - Truncate lowest-scoring context snippets if budget is exceeded; never truncate `DIRECT_EVIDENCE`.

---

## 5. Gate 3 Hierarchy Migration & Remediation Plan

Per master guidelines, **no database modifications are executed in this audit turn**. The following migration protocol will execute during Gate 3 implementation:

1. **Dry-Run Tree Depth Calculator:**
   - Implement `scripts/recompute_clause_depths.py --dry-run`.
   - Compute tree depth deterministically:
     $$\text{depth}(c) = \begin{cases} 1 & \text{if } \text{parent}(c) \text{ is None} \\ \text{depth}(\text{parent}(c)) + 1 & \text{otherwise} \end{cases}$$
   - Verify maximum depth across corpus (expected range: 1 to 5).
2. **Parent Link Sanitization:**
   - Resolve the 349 missing parent links using a verified manual mapping table.
   - Move cross-document parent links in `MCC_CHANGES_EXPLAINED_2026` to `cross_references`.
3. **Safe Two-Phase Migration:**
   - Execute depth update through `scripts/reconcile_database.py --build-staging`.
   - Validate 4-way ID parity and verify that clause IDs and original text remain 100% byte-identical.
   - Verify all tests pass before atomic promotion.
