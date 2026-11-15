# ADR 0001: Structured Rule Store, Relational Model, and Deterministic Applicability Engine

- **Status:** Accepted
- **Date:** 2026-11-15
- **Deciders:** CricketIQ Architecture & Engineering Team
- **Context:** Antigravity Phase 2 Implementation

---

## 1. Context and Problem Statement

CricketIQ must answer cricket regulations questions strictly based on authoritative evidence from Marylebone Cricket Club (MCC) Laws of Cricket and International Cricket Council (ICC) Playing Conditions.

In cricket regulations:
1. **MCC Laws** define the baseline rules of the game.
2. **ICC Playing Conditions** incorporate the Laws of Cricket and introduce format-specific modifications, overrides, and additions for international cricket (e.g., Free Hit on No balls in T20I/ODI, boundary-catch interpretations, DRS protocols).
3. **Competition Regulations** (e.g., ICC Men's T20 World Cup, World Test Championship Final) may further overlay standard ICC Playing Conditions.
4. **Transition Rules (Crucial October 2026 ICC Transition):** ICC announced that its October 2026 playing conditions take effect for international series *starting on or after 1 October 2026*. Matches in an ongoing series that started before 1 October 2026 continue under predecessor regulations. Therefore, `match_date` alone is insufficient to resolve the governing regulation.

A naive RAG implementation that performs similarity search over a flat vector index of PDFs will inevitably retrieve incorrect rules, cite superseded clauses, or apply T20I rules to Test cricket.

This ADR establishes:
1. A structured, relational domain model for source documents, rule clauses, document relationships, and match contexts.
2. A dual-mode database repository (SQLite for zero-external-service local development and testing, PostgreSQL + pgvector for production).
3. A deterministic Applicability Engine that resolves governing source bundles without LLM hallucination.
4. A formal audit of dependency licensing (specifically PyMuPDF AGPL v3).

---

## 2. Decision & Architecture Details

### 2.1 Multi-Level Date & Applicability Semantics
We distinguish six distinct temporal attributes:
1. `published_at`: Date the official document was published by MCC/ICC.
2. `legal_effective_from`: Date stated in the document when it legally takes force.
3. `series_start_date`: First match date of the bilateral/multilateral series. For ICC transitions, this governs whether a series is ongoing or under the new edition.
4. `match_date`: Specific day a match or delivery takes place.
5. `competition_start_date`: Start date of a tournament.
6. `applicability_basis`: Explicit trigger enum:
   - `SERIES_START_DATE` (Standard ICC Playing Conditions)
   - `MATCH_DATE` (Immediate-effect amendments / specific playing conditions)
   - `COMPETITION_START_DATE` (Tournaments)
   - `SEASON_EDITION` (General MCC Laws)

#### ICC 1 October 2026 Transition Rule
```
IF series_start_date is known:
    IF series_start_date >= 2026-10-01:
        -> Select October 2026 Edition
    ELSE (series started before 2026-10-01):
        -> Select Predecessor Edition (even if match_date >= 2026-10-01)
ELSE IF series_start_date is unknown:
    IF match_date is known and match_date >= 2026-10-01:
        -> Return UNRESOLVED / CLARIFICATION_NEEDED:
           Cannot determine whether the match is part of an ongoing series started before Oct 1.
    ELSE IF match_date < 2026-10-01:
        -> Select Predecessor Edition
    ELSE (no dates provided):
        -> Default to Current Active Edition with explicit audit assumption logged.
```

### 2.2 Source Hierarchy & Source Bundles
CricketIQ models the governing rules as a **Source Bundle**, not a single winning PDF.
A source bundle contains:
1. **Event / Competition Regulations** (highest precedence if competition specified, e.g. T20 World Cup).
2. **ICC Format Playing Conditions** (modifies / supplements MCC Laws for Test, ODI, or T20I).
3. **Official Addenda** (if active and in scope for the format/competition).
4. **Underlying MCC Laws Baseline** (incorporated for all provisions not modified by playing conditions).

### 2.3 Explicit Clause-Level Relationships
Precedence is modeled as a directed graph of relationships:
- `INCORPORATES`: e.g. ICC T20I PC incorporates MCC Laws of Cricket.
- `MODIFIES`: e.g. ICC T20I Clause 21.18 modifies MCC Law 21 (No ball) by granting a Free Hit.
- `SUPPLEMENTS`: e.g. ICC T20I Clause 21.18.2 specifies dismissals permitted on a Free Hit.
- `SUPERSEDES`: e.g. ICC T20I October 2026 edition supersedes October 2024 edition for series starting $\ge$ 2026-10-01.

**Cross-Clause Evidence Preservation Example (Free Hit):**
- Clause 21.18.2 states: *"For any free hit, the striker can be dismissed only under the circumstances that apply for a No ball..."*
- Clause 21.17 states: *"When a No ball has been called, neither batter can be out to that delivery except under Law 34 (Hit the ball twice), Law 37 (Obstructing the field) or Law 38 (Run out)."*
- The relationship graph links `21.18.2` $\rightarrow$ `21.17`. When answering a free-hit question, both clauses are retrieved as composite evidence.

### 2.4 Dual-Mode Storage Architecture
- **Development & Test:** SQLite with SQLAlchemy 2.0. SQLite FTS5 capability is detected at startup (`PRAGMA compile_options`). Vector similarity fallback uses NumPy cosine similarity without external daemon services.
- **Production:** PostgreSQL 16 with `pgvector` for vector index and `tsvector`/GIN for full-text search.
- **Migrations:** Alembic is used for schema versioning and database migrations.

### 2.5 Security Hardening for Remote Document Ingestion
- Remote fetching requires HTTPS.
- Strict hostname allowlist: `icc-cricket.com`, `www.icc-cricket.com`, `resources.pulse.icc-cricket.com`, `images.icc-cricket.com`, `lords.org`, `www.lords.org`.
- DNS resolution validation: Pre-flight check rejects loopback (`127.0.0.0/8`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and multicast to prevent SSRF and DNS rebinding attacks.
- Magic-byte validation (`%PDF-`) and strict size limits (max 50MB) before parsing.

### 2.6 Dependency & Licensing Audit (PyMuPDF)
- **PyMuPDF (`fitz`):** Licensed under GNU AGPL v3 (and commercial license from Artifex).
  - *Implication:* If CricketIQ is deployed as a networked software service, AGPL v3 requires offering the complete corresponding source code of the service to users interacting with it over the network.
  - *CricketIQ Decision:* CricketIQ is being developed as an open-source, fully auditable reference assistant. In Phase 2, PyMuPDF is used for high-fidelity extraction in compliance with AGPL v3 terms. For commercial distributions where proprietary encapsulation is required, CricketIQ provides a pluggable extractor interface that can switch to Apache-2.0 / MIT extractors (`pdfplumber` / `pypdfium2`).
- **pdfplumber:** Licensed under MIT License.
- **SQLAlchemy & Pydantic:** Licensed under MIT License.

---

## 3. Consequences

### Positive
- Strict regulatory correctness: no more guessing editions or applying T20I rules to Test matches.
- Transparent audit trail: Every resolution returns reason codes, assumptions, and precedence levels.
- Zero external daemon required for developer onboarding or unit tests.
- Robust security preventing SSRF and malicious PDF injections.

### Trade-offs
- More upfront modeling complexity than simple vector-similarity chunking.
- Requires maintaining explicit document relationship edges when new tournaments or addenda are released.
