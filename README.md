# CricketIQ — Antigravity Vibe-Coding Starter Pack

**Eight project documents for building CricketIQ with Google Antigravity.**

CricketIQ is an evidence-grounded natural-language assistant for understanding cricket Laws and playing conditions. The project is designed around official-source ingestion, version-aware rule applicability, hybrid retrieval, and cited answers—not an LLM that guesses from general cricket knowledge.

## 1. Contents (8 essential documents)

| # | File | Purpose |
|---:|---|---|
| 1 | `README.md` | Setup, usage, and first Antigravity prompts |
| 2 | `AGENTS.md` | Persistent workspace instructions for the coding agent |
| 3 | `docs/PROJECT_BRIEF.md` | Product vision, scope, users, and success criteria |
| 4 | `docs/PRODUCT_REQUIREMENTS.md` | Functional and non-functional requirements |
| 5 | `docs/SYSTEM_ARCHITECTURE.md` | Components, data flow, technology choices, and boundaries |
| 6 | `docs/RULE_DATA_GOVERNANCE.md` | Official sources, schema, ingestion, versions, and applicability |
| 7 | `docs/IMPLEMENTATION_ROADMAP.md` | Phased build sequence, milestones, and task gates |
| 8 | `docs/QUALITY_SECURITY_RELEASE.md` | Evaluation, test strategy, safety, security, and release checks |

## 2. Install into an Antigravity project

1. Extract this ZIP.
2. Copy the **contents** of `cricketiq-antigravity-starter/` into the root of your CricketIQ repository. The resulting repository should contain `AGENTS.md`, `README.md`, and `docs/`.
3. If your repository already has an `AGENTS.md` or `README.md`, **do not overwrite it blindly**. Ask Antigravity to compare and merge the instructions while preserving existing project-specific constraints.
4. Open the repository as the workspace in Antigravity and trust the workspace only after checking that it is the intended folder.
5. Confirm that Antigravity has loaded the workspace instructions. Its current documentation describes `AGENTS.md` as a supported workspace rules file.

### Recommended project tree

```text
cricketiq/
├── AGENTS.md
├── README.md
├── docs/
│   ├── PROJECT_BRIEF.md
│   ├── PRODUCT_REQUIREMENTS.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── RULE_DATA_GOVERNANCE.md
│   ├── IMPLEMENTATION_ROADMAP.md
│   └── QUALITY_SECURITY_RELEASE.md
├── backend/                 # Create during implementation
├── frontend/                # Create during implementation
├── data/                    # Original and processed rule documents
├── evaluation/              # Curated questions and expected evidence
└── tests/
```

## 3. The right way to vibe-code this project

Do not ask the agent to build the entire product in one enormous prompt. Use small, reviewable milestones:

1. **Discover:** inspect the repository, current dependencies, environment, and existing code. Do not modify files.
2. **Plan:** propose a small implementation slice, list files to change, risks, tests, and acceptance criteria.
3. **Implement:** change only what the approved slice requires.
4. **Verify:** run relevant tests, static checks, and the application where possible. Report actual command results.
5. **Review:** inspect the diff for regressions, secrets, data loss, insecure defaults, and unrequested scope expansion.
6. **Record:** update documentation and the roadmap when decisions or project state materially change.

### First prompt — repository discovery only

```text
Read AGENTS.md and all six documents under docs/ before doing anything.
Inspect the current repository, existing files, dependency manifests, and runtime setup.
Do not create, edit, delete, install, migrate, or deploy anything yet.
Report:
1. what already exists;
2. what is missing compared with the documented architecture;
3. risks, unknowns, and conflicting assumptions;
4. the smallest sensible first milestone;
5. a proposed implementation plan with files, commands, tests, and acceptance criteria.
Do not assume the repository is empty. Do not invent successful test results.
```

### Second prompt — approve one small milestone

```text
Implement only the first approved milestone in docs/IMPLEMENTATION_ROADMAP.md.
Follow AGENTS.md. Before editing, state the scope and files you intend to change.
Preserve existing working behaviour. Do not add optional infrastructure or dependencies
without explaining why they are needed. After implementation, run the relevant checks
and report exact commands, pass/fail outcomes, limitations, and the changed files.
Stop before the next milestone.
```

### Useful follow-up prompts

- **Plan a feature:** “Inspect the current implementation and produce a plan for [feature]. Do not code yet.”
- **Review a diff:** “Review the current changes for correctness, security, test gaps, regressions, and scope creep. Report findings by severity; do not change files.”
- **Debug:** “Reproduce the issue first. Trace the root cause, propose the smallest safe fix, add a regression test, and verify it.”
- **Prepare a release:** “Run the release checklist in `docs/QUALITY_SECURITY_RELEASE.md`. Do not deploy or publish without explicit approval.”

## 4. Antigravity conventions

- `AGENTS.md` is the persistent workspace instruction file in this pack.
- Use **Rules** for durable constraints and project invariants.
- Use **Agent Skills** for repeatable multi-step procedures when they become stable and reusable. Current Antigravity documentation describes skills under `.agents/skills/<skill-name>/SKILL.md`.
- Do not build new process guidance around legacy Workflows: Antigravity currently marks legacy Workflows as deprecated and documents migration to Agent Skills. Existing workflows may continue to work for now, but use Skills for new reusable procedures and check the current official migration guide for surface-specific instructions.
- Keep prompts and task scopes explicit. Review plans and diffs rather than treating generated output as automatically correct.

## 5. Project assumptions to confirm—not silently accept

- Initial scope: international men's and women's Test, ODI, and T20I regulations, plus the relevant underlying MCC Laws.
- Official source documents and their terms of use must be checked before ingestion or redistribution.
- Format, competition, gender/category, series or match date, and effective-date rules may affect applicability.
- The proposed stack is a starting point, not a mandate. The agent must inspect the actual repository and justify changes before selecting or adding dependencies.
- The benchmark size and quality targets in the documents are proposed targets, not existing results.

## 6. Local Setup and Commands

### Environment Setup
```powershell
# Using uv and Python 3.12+
uv venv .venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Running Test Suites
```powershell
# Backend Python test suite (103 passed, 1 skipped)
.venv\Scripts\pytest cricketiq/backend/tests -v

# Frontend TypeScript/React test suite (20 passed)
npm --prefix frontend test
```

### Running the Application Locally
```powershell
# 1. Start FastAPI Backend (Port 8000)
.venv\Scripts\uvicorn cricketiq.backend.app.main:app --port 8000 --host 127.0.0.1

# 2. In a separate terminal, start Vite Frontend Dev Server (Port 5173)
npm --prefix frontend run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### Current Development Status
- **Phase 0:** Project discovery & repository setup [COMPLETED]
- **Phase 1:** Single-source ingestion slice with SHA-256 integrity [COMPLETED]
- **Phase 2:** Structured rule store, Alembic migrations, deterministic Applicability Engine, and secure downloader [COMPLETED]
- **Phase 3:** Hybrid retrieval (Sparse FTS5 + Dense NumPy/EmbeddingStore + RRF + Bounded Evidence Expansion) [COMPLETED]
- **Phase 4:** Grounded answer API & deterministic citation validator [COMPLETED]
- **Phase 5:** Production-Grade Responsive User Interface, Context Controls & Verified Citation Drawer [COMPLETED]

## 7. Official Antigravity references

- Rules and workspace instructions: https://antigravity.google/docs/rules/
- Agent Skills: https://antigravity.google/docs/skills
- Getting started: https://antigravity.google/docs/getting-started
- Workflows-to-Skills migration: https://antigravity.google/docs/migration/workflows-to-skills/

## 7. Cricket source references

- ICC Playing Conditions: https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions
- MCC Laws of Cricket: https://www.lords.org/mcc/laws-of-cricket

Always verify the latest official document, amendment, effective date, and terms at the source before adding it to the authoritative corpus. A URL in this README is a starting point, not proof that a particular edition applies to a particular match.
