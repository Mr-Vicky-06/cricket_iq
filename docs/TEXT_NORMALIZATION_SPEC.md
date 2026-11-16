# Text Normalization Specification — CricketIQ

**Version:** 1.0.0  
**Effective Date:** 2026-11-16  
**Auditor:** CricketIQ Principal NLP / Information Retrieval Architect  
**Implementation Module:** `cricketiq.backend.app.nlp.normalizer.TextNormalizer`  

---

## 1. Multi-View Architecture Rationale

Cricket rules are authoritative legal texts. Applying a single destructively cleaned text view (such as lowercase, stop-word stripped, punctuation removed) destroys critical legal distinctions:
- **Negation & Exceptions:** *"The striker can be dismissed only under..."* vs *"neither batter can be out..."*
- **Modal Verbs:** *"The umpire shall signal..."* (mandatory) vs *"may signal..."* (discretionary)
- **Cricket Compounds:** *"no-ball"*, *"free-hit"*, *"wide-ball"*, *"run-out"*, *"full-pitched"*
- **Exact Identifiers:** *"Clause 21.18.2"*, *"Law 38"*, *"21.18.3.1"*

To satisfy legal accuracy and high-precision search simultaneously, CricketIQ generates seven distinct, immutable, versioned representations for every parsed clause:

| View Name | Target Subsystem | Transformation Rules | Legal & Linguistic Purpose |
| :--- | :--- | :--- | :--- |
| **`original_text`** | Audit & Storage | Verbatim extracted text. Completely immutable. | Preserves cryptographic and legal provenance. |
| **`normalized_text`** | Citation & Retrieval | Typographic clean (LF normalized, `\u202f` & `\xa0` replaced with ASCII space, whitespace collapsed). Retains all punctuation, hyphens, negation, and modal verbs. | Clean presentation without semantic loss. |
| **`lexical_text`** | SQLite FTS5 / BM25 | Compound expansion (e.g. `no-ball` -> `no-ball no ball`), explicit Law prefix tokens (`law 21`, `clause 21.18.2`). Retains stop words and negation. | Ensures both hyphenated and split colloquial queries match. |
| **`embedding_text`** | Dense Vector Model | Versioned template: `[{authority} {title} | {edition}] Clause {num} ({heading}): {normalized_body}` | Injects document hierarchy and format context into dense vectors. |
| **`sentence_segments`** | Evidence Extraction | Punctuation boundary detection protecting abbreviations (`e.g.`, `i.e.`, `no.`, `cl.`, `approx.`, `dr.`, `oz.`, `ft.`) and decimal clauses (`21.18.2`). | Enables sentence-level citation highlighting in future answers. |
| **`chunk_text`** | Semantic Search Chunks | Bounded contextual chunk incorporating parent clause context (`[Context: {parent_id}] {body}`). | Ensures child subclauses carry parent scope during vector retrieval. |
| **`display_text`** | User Presentation | Source-use compliant formatting appending official publisher attribution, clause, and page number. | Complies with copyright and fair citation requirements. |

---

## 2. Invariant Rules for Normalization

1. **Never mutate `original_text`:** Source PDF bytes and raw extracted characters remain immutable.
2. **Never delete stop words from authoritative text:** Words like `not`, `no`, `only`, `unless`, `except`, `neither`, `either`, `before`, `after`, `within`, `must`, `may`, `shall` dictate the outcome of a cricket rule.
3. **Compound Term Symmetry:** All cricket compound terms (`no-ball`, `free-hit`, `run-out`, `full-pitched`, `hit-wicket`, `leg-bye`, `wicket-keeper`) are indexed in both hyphenated and space-separated forms in `lexical_text`.
4. **Versioning:** Every transformed record carries `pipeline_version: "1.0.0"`, `normalization_version: "v1"`, and `source_text_hash` (SHA-256).
