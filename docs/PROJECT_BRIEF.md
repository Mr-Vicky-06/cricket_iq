# Project Brief — CricketIQ

## 1. Product summary

CricketIQ is a natural-language cricket rules assistant. Users ask questions in everyday language; the system identifies the relevant match context, retrieves the applicable official Laws or playing conditions, and explains the answer with traceable citations.

**Product principle:** the LLM explains the evidence; it is not the authority on cricket regulations.

## 2. Problem

Cricket regulations are spread across MCC Laws, ICC format-specific playing conditions, competition rules, amendments, and historical editions. A rule may differ by format or competition, and a new edition may apply only to matches or series meeting a stated effective-date condition. Generic chatbots can produce plausible but outdated or contextually incorrect answers.

CricketIQ addresses this by combining a curated official-source corpus, structured rule metadata, applicability resolution, hybrid search, and citation-grounded generation.

## 3. Target users

- Cricket fans who want understandable explanations of rules.
- Players and coaches checking a rule or match scenario.
- Students and educators learning the Laws of Cricket.
- Umpires and officials using the system as a reference aid—not as a replacement for the official rulebook or on-field judgment.

## 4. Product goals

1. Answer common cricket-rule questions in clear, accessible language.
2. Retrieve the correct clause for the specified format and competition.
3. Distinguish MCC Laws from applicable ICC playing-condition modifications.
4. Preserve historical editions and resolve applicability by relevant dates and conditions.
5. Show verifiable document, clause, and page/source references.
6. Explain exceptions and related clauses when material.
7. Ask for missing context or abstain when an answer cannot be supported.
8. Make source updates auditable and regression-testable.

## 5. Initial scope

### In scope for the MVP

- Underlying MCC Laws relevant to international cricket.
- ICC men's and women's Test, ODI, and T20I playing conditions.
- Source/version metadata and historical document retention.
- Natural-language Q&A with citations.
- Context capture for format, category, competition, and match/series date when relevant.
- Keyword + semantic retrieval, reranking where justified, and evidence-grounded answer generation.
- A small evaluation set that grows toward a curated benchmark of approximately 300 questions.

### Deferred until the MVP is reliable

- Domestic and franchise competitions such as IPL, unless their official regulations are separately sourced and modeled.
- Ball-by-ball live match adjudication.
- Video/image recognition of on-field incidents.
- Automated umpire decisions or legal/disciplinary determinations.
- Multilingual answers, voice interface, mobile app, and broad cricket statistics.
- Fine-tuning a model on raw rulebook PDFs.

## 6. Core user journey

1. User asks a cricket rules question.
2. The system identifies likely intent and extracts known context.
3. It asks for missing context only when that context could change the answer.
4. It resolves candidate authoritative documents and applicable versions.
5. It retrieves exact and semantically related clauses, including exceptions and parent context.
6. It validates the evidence set.
7. The LLM generates a concise explanation supported by that evidence.
8. The UI displays the answer, source references, assumptions, and related clauses.

## 7. Product success measures

Treat the following as **proposed targets**, not achieved results:

- Relevant-clause Recall@5: at least 95% on a validated benchmark.
- Citation validity: at least 98% of displayed citations resolve to the correct source and clause.
- Expert-rated answer correctness: at least 95% on the benchmark, with separate reporting by format and question type.
- Unsupported-answer behaviour: the system abstains or asks clarification rather than inventing an answer when evidence/context is insufficient.
- Historical applicability: test cases select the correct edition for their defined match/series context.
- Maintainability: new source editions can be ingested without redesigning the chat application.

## 8. Product constraints and assumptions

- The official source corpus must be curated and checked for applicable terms, attribution, and redistribution restrictions.
- The system must not claim to provide an official ruling or replace umpires, match officials, or the source documents.
- The source hierarchy and applicability rules must be documented and tested. Do not assume every ICC document overrides every MCC provision; inspect the actual playing conditions and precedence language.
- Any date-specific rule statement must be based on the applicability wording in the relevant source.
- Proposed technology choices are provisional until the repository, team skills, hosting, cost, and licensing requirements are inspected.

## 9. MVP exit criteria

The MVP is ready for controlled demonstration when:

- The initial official source set is inventoried, versioned, and validated.
- Extracted clauses preserve source references and hierarchy.
- The applicability resolver has tests for format and effective-date scenarios.
- Hybrid retrieval returns the expected clauses for the initial benchmark.
- Answers cite the evidence actually retrieved.
- Unsupported and ambiguous questions are handled safely.
- Automated tests and a human-reviewed evaluation report are available.
