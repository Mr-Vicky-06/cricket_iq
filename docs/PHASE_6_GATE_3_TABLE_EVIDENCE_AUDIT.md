# CricketIQ — Structured Table Evidence Audit & Representation Specification (Gate 3)

- **Date:** 2026-11-17
- **Document Version:** 1.0.0
- **Scope:** Phase 6 Gate 3 Pre-Implementation Audit
- **Data Asset:** `data/extracted/tables/*.json` (240 extracted tables across 11 documents)
- **Companion Specifications:** `docs/reviews/PHASE_6_GATE_3_PRE_IMPLEMENTATION_AUDIT.md`, `docs/SYSTEM_ARCHITECTURE.md`

---

## 1. Executive Summary

Official cricket regulations frequently articulate prescriptive numerical standards, variable conditions, and multi-dimensional matrices in tabular form rather than narrative prose:
1. **DRS Ball Tracking Zones (Appendix D):** Pitching Zone, Impact Zone, and Wicket Zone boundaries that determine whether an on-field LBW decision stands, is overturned, or reverts to Umpire's Call.
2. **Player Review Outcomes (Appendix D):** Deterministic rules mapping review outcome (Overturned, Umpire's Call, Unchanged) to review deduction or retention.
3. **Powerplay Calculations in Rain-Affected Matches (Clause 28.7):** Exact lookup tables calculating Powerplay 1, 2, and 3 overs when limited-overs innings are shortened to between 5 and 49 overs.
4. **Pitch and Crease Dimensions (Appendix C):** Exact imperial and metric specifications for popping crease length, return crease width, bowling crease distance, and stump heights.

When user queries demand exact numbers (e.g., *"How many overs of powerplay in a 12-over rain-reduced T20I?"* or *"What percentage of the ball must hit the wicket zone in DRS?"*), raw text retrieval often retrieves descriptive prose but misses the exact cell value from the official table.

This audit evaluates all 240 extracted tables in `data/extracted/tables/`, analyzes extraction fidelity and structural artifacts, and designs the typed `TableEvidence` contract for Gate 3 retrieval.

---

## 2. Table Extraction Inventory Across Documents

| Source Document ID | Table File | Extracted Table Count | Key Regulatory Tables Identified | Primary Structural Types | Validation Status |
| :--- | :--- | :---: | :--- | :--- | :---: |
| **`ICC_ODI_MEN_2026`** | `ICC_ODI_MEN_2026_tables.json` | 9 | - Clause 28.7 (pg 48): Shortened match Powerplay table (31x4)<br>- Appx D (pg 88): Third Umpire Non-DRS vs DRS jurisdiction (6x3)<br>- Appx D (pgs 93-95): Hawk-Eye Pitching, Impact, Wicket Zones (3x2)<br>- Appx D (pg 97): Player Review consequences (6x3) | Complex lookup matrix, multi-column comparison, binary outcome maps | **AUDITED** |
| **`ICC_ODI_WOMEN_2026`** | `ICC_ODI_WOMEN_2026_tables.json` | 9 | - Clause 28.7 (pg 48): Shortened match Powerplay table (31x4)<br>- Appx D: DRS jurisdiction, zones, review outcomes | Identical to Men's ODI with gender-specific crease markings | **AUDITED** |
| **`ICC_T20I_MEN_2026`** | `ICC_T20I_MEN_2026_tables.json` | 9 | - Clause 28.7 (pg 47): 5-19 over Powerplay restriction table (16x2)<br>- Appx D (pg 87): Third Umpire jurisdiction (6x3)<br>- Appx D (pgs 92-94): Hawk-Eye zones (3x2)<br>- Appx D (pg 96): Review outcomes (6x3) | Shortened over lookup, zone definitions | **AUDITED** |
| **`ICC_T20I_MEN_ADD_2026`** | `ICC_T20I_MEN_ADD_2026_tables.json` | 0 | None (Addendum is narrative textual amendments) | N/A | **VERIFIED EMPTY** |
| **`ICC_T20I_WOMEN_2026`** | `ICC_T20I_WOMEN_2026_tables.json` | 9 | - Clause 28.7 (pg 47): T20I Powerplay table (16x2)<br>- Appx D: DRS jurisdiction and ball-tracking zones | T20I matrices | **AUDITED** |
| **`ICC_TEST_MEN_2026`** | `ICC_TEST_MEN_2026_tables.json` | 6 | - Appx D (pg 89): Third Umpire jurisdiction (6x3)<br>- Appx D (pgs 94-96): Hawk-Eye Pitching/Impact/Wicket Zones (3x2)<br>- Appx D (pg 98): Player Review consequences (6x3) | DRS technical standards, Player Review matrix | **AUDITED** |
| **`ICC_TEST_WOMEN_2026`** | `ICC_TEST_WOMEN_2026_tables.json` | 6 | - Appx D: Test DRS protocols and ball tracking specifications | Identical to Men's Test PC | **AUDITED** |
| **`ICC_WTC_2025_2027_PC`** | `ICC_WTC_2025_2027_PC_tables.json` | 6 | - Competition specific DRS overlays and match points structure | Competition regulation matrices | **AUDITED** |
| **`MCC_CHANGES_EXPLAINED_2026`** | `MCC_CHANGES_EXPLAINED_2026_tables.json` | 0 | None (Narrative summary of rule changes) | N/A | **VERIFIED EMPTY** |
| **`MCC_LAWS_2022`** | `MCC_LAWS_2022_tables.json` | 192 | - Appendix B & C specifications for pitch, crease, ball, bat, stumps<br>- Historical extraction fragments from PDF layout | High volume of single-row dimensional fragments | **REQUIRES PRUNING** |
| **`MCC_LAWS_2026`** | `MCC_LAWS_2026_tables.json` | 0 | Layout parser emitted narrative clauses; tables formatted as ASCII text blocks inside rule clauses | Text-embedded tables | **AUDITED** |
| **TOTAL** | **11 JSON Files** | **240** | **45 Substantive Regulatory Tables; 195 Fragmentary/Legacy Tables** | — | — |

---

## 3. Deep-Dive Audit of Substantive Regulatory Tables

### Sample A: DRS Hawk-Eye Wicket Zone Specifications
- **Source Document:** `ICC_TEST_MEN_2026`
- **Page Locator:** Page 96 (Appendix D, Clause 3.3.3)
- **Shape:** 3 rows $\times$ 2 columns
- **Exact Extracted Cells:**
  - Row 1: `["Hitting", "The ball was hitting the wicket, and the centre of the ball was inside the Wicket Zone"]`
  - Row 2: `["Umpire's Call", "The ball was hitting the wicket, but the centre of the ball was inside the Margin"]`
  - Row 3: `["Missing", "No part of the ball was hitting the wicket, or the centre was outside the Margin"]`
- **Regulatory Function:** **PRESCRIPTIVE RULE**. Defines the quantitative threshold differentiating an overturned NOT OUT decision from an on-field UMPIRE'S CALL decision.
- **Extraction Quality:** Clean, complete textual fidelity, no OCR noise.

### Sample B: Player Review Outcome and Consequence Matrix
- **Source Document:** `ICC_TEST_MEN_2026`
- **Page Locator:** Page 98 (Appendix D, Table 1)
- **Shape:** 6 rows $\times$ 3 columns
- **Header:** `["Category of Player Review", "Outcome of Player Review", "Consequence of Player Review"]`
- **Sample Extracted Rows:**
  - `["Dismissal (LBW)", "Reversed (Out -> Not Out)", "Review Retained"]`
  - `["Dismissal (LBW)", "Umpire's Call (Stands)", "Review Retained"]`
  - `["Dismissal (LBW)", "Confirmed (Stands)", "Review Lost"]`
- **Regulatory Function:** **PRESCRIPTIVE RULE**. Dictates whether a team retains or forfeits one of their 3 allotted reviews per innings in Test matches.
- **Extraction Quality:** Excellent, structured column alignment.

### Sample C: Rain-Interrupted Innings Powerplay Restrictions
- **Source Document:** `ICC_T20I_MEN_2026`
- **Page Locator:** Page 47 (Clause 28.7.4, Table 1)
- **Shape:** 16 rows $\times$ 2 columns
- **Header:** `["Total overs in innings", "Number of overs for which fielding restrictions... apply"]`
- **Sample Extracted Data:**
  - `5-8 overs`: `1 over`
  - `9-11 overs`: `2 overs`
  - `12-14 overs`: `3 overs`
  - `15-18 overs`: `4 overs`
  - `19 overs`: `5 overs`
  - `20 overs`: `6 overs`
- **Regulatory Function:** **NUMERIC SPECIFICATION**. Crucial operational lookup for weather-delayed matches.
- **Extraction Quality:** Clean integer mappings, correct range boundaries.

### Sample D: Fragmentary / Degraded Extraction Artifacts
- **Source Document:** `MCC_LAWS_2022_tables.json`
- **Observation:** Contains ~180 1-row or 2-row fragments containing nulls or standalone dimension markers (e.g., `["17in/43.18cm", ""]`).
- **Remediation Policy for Gate 3:** Prune fragmentary/empty table artifacts. Only register validated, substantive multi-cell tables with verified page locators and captions.

---

## 4. Typed `TableEvidence` Contract for Gate 3 Retrieval

In Gate 3, substantive tables will be modeled as strongly typed structured evidence:

```python
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TableValidationStatus(str, Enum):
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    EXTRACTED_UNVALIDATED = "EXTRACTED_UNVALIDATED"
    DEPRECATED_FRAGMENT = "DEPRECATED_FRAGMENT"

class TableEvidence(BaseModel):
    table_id: str = Field(description="Unique stable identifier, e.g. ICC_TEST_MEN_2026:TBL_APP_D_ZONES")
    source_document_id: str = Field(description="Parent authoritative document ID")
    page_number: int = Field(description="1-based PDF page locator")
    caption: str = Field(description="Authoritative table title or figure caption")
    headers: List[str] = Field(description="Column header labels")
    rows: List[List[Optional[str]]] = Field(description="2D matrix of cell values as extracted from source")
    units: Optional[Dict[str, str]] = Field(default=None, description="Physical units per column, e.g. {'length': 'cm'}")
    footnotes: List[str] = Field(default_factory=list, description="Footnotes and explanatory caveats")
    linked_clause_ids: List[str] = Field(default_factory=list, description="Associated rule clauses, e.g. ['ICC_TEST_MEN_2026:28.7']")
    validation_status: TableValidationStatus = Field(default=TableValidationStatus.EXTRACTED_UNVALIDATED)

class TableEvidenceBundle(BaseModel):
    query_id: str
    matched_tables: List[TableEvidence]
    retrieval_method: str = "EXPLICIT_CLAUSE_LINK"
```

---

## 5. Table Evidence Retrieval Integration Plan

1. **Explicit Clause-Linked Retrieval (Primary Channel):**
   - When a retrieved clause (e.g., `ICC_T20I_MEN_2026:28.7.4`) lists an associated table in its `extracted_tables` metadata field, the `RetrievalService` automatically hydrates the corresponding `TableEvidence` record from the repository.
   - This guarantees that table evidence is **100% grounded in the applicable regulation context** and avoids cross-format leakage.
2. **Tabular Prompt Formatting for LLM:**
   - When table evidence is present, format it as clean Markdown tables with source citations in the LLM prompt context:
     ```markdown
     [OFFICIAL TABLE EVIDENCE: ICC_TEST_MEN_2026 Page 98 — Player Review Outcomes]
     | Category | Outcome | Consequence |
     | :--- | :--- | :--- |
     | LBW | Umpire's Call | Review Retained |
     | LBW | Reversed | Review Retained |
     ```
3. **No Unvalidated Cell Claims:**
   - Any table with status `EXTRACTED_UNVALIDATED` will include an internal confidence warning in the retrieval trace, and only `SOURCE_VERIFIED` tables will be presented as normative proof.
