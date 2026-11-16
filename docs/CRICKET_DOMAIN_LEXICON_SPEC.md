# Cricket Domain Lexicon and Ontology Specification — CricketIQ

**Version:** 1.0.0  
**Effective Date:** 2026-11-16  
**Auditor:** CricketIQ Cricket Rules Knowledge Engineer & IR Architect  
**Data Asset Path:** `data/corpus/lexicon/cricket_lexicon.json`  

---

## 1. Executive Summary & Purpose

Cricket regulations contain nuanced, domain-specific terminology that differs fundamentally from general English:
- **Colloquial Queries vs Official Terms:** Users ask about *"mankading"*, *"beamer"*, or *"overstepping"*, but the official regulations govern *"Law 38.3 non-striker leaving ground early"*, *"Clause 21.5 high full-pitched delivery"*, and *"Clause 21.1 mode of delivery"*.
- **Crucial Non-Equivalences:** Certain terms sound similar to casual fans but represent legally distinct events under MCC/ICC rules:
  - `Retired hurt` (not a dismissal; batsman can resume) vs `Retired out` (dismissal without consent; batter cannot return).
  - `Wide ball` (Law 22; ball out of reach) vs `No ball` (Law 21; illegal bowler action, crease overstep, or waist-high delivery).
  - `Run out` (Law 38; attempting a run or out of crease) vs `Stumped` (Law 39; striker out of crease without attempting run off a legal delivery).
  - `Bye` (Law 23; ball misses bat and person) vs `Leg bye` (Law 23; ball strikes batter's person after playing a stroke or evading).

---

## 2. Terminology Taxonomy & Schema

Every lexicon record adheres to the following strict schema:

```json
{
  "term_id": "CRIC_DELIV_NO_BALL",
  "preferred_term": "No ball",
  "surface_forms": ["No ball", "no-ball", "no ball", "No-ball"],
  "abbreviations": ["NB"],
  "spelling_variants": ["no ball", "no-ball"],
  "colloquial_query_forms": ["noball", "overstepping", "front foot fault"],
  "definition": "An unlawful delivery penalized under Law 21...",
  "term_type": "DELIVERY_LEGALITY",
  "related_terms": ["free hit", "front foot crease"],
  "distinct_from": ["Wide ball", "Dead ball"],
  "source_refs": ["MCC Law 21", "ICC Clause 21"],
  "review_status": "APPROVED"
}
```

---

## 3. Disambiguation Mapping Table

| Colloquial Query Term | Official Regulatory Designation | Governing Authority & Law | Semantic Distinction / Legal Consequence |
| :--- | :--- | :--- | :--- |
| **"Mankad" / "Mankading"** | Non-striker leaving their ground early | **MCC Law 38.3 / ICC Clause 38.3** | Fully legitimate Run out dismissal. Moved in 2022 from Law 41 (Unfair Play) to Law 38 (Run Out). |
| **"Beamer"** | High full-pitched delivery above waist height | **MCC Law 41.7 / ICC Clause 21.5** | Automatic No ball + first and final warning to the bowler before removal from bowling. |
| **"Free Hit Out"** | Dismissal exceptions on Free Hit delivery | **ICC Playing Conditions Clause 21.18.2** | Striker can ONLY be dismissed under Law 34 (Hit ball twice), Law 37 (Obstructing field), or Law 38 (Run out). |
| **"Timed Out"** | Incoming batter time limit | **MCC Law 31 / ICC Clause 31.1** | 3 minutes under MCC Laws; 2 minutes under international ODI and T20I Playing Conditions. |
| **"Double Bounce"** | Ball bouncing more than once | **MCC Law 21.5** | Automatic No ball if the ball bounces more than once before reaching the popping crease. |
| **"Retired Out"** | Unconsented retirement | **MCC Law 25.4** | Recorded as a dismissal; batter cannot resume innings. |
| **"Retired Hurt"** | Injury / illness retirement | **MCC Law 25.4** | Not a dismissal; batter may resume innings at the fall of a subsequent wicket. |
