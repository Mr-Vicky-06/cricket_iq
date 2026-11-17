# ADR 0004: Frontend Technology Stack and Architectural Boundaries for CricketIQ

- **Status:** Accepted (Stack: React 19 + TypeScript + Vite + Tailwind CSS + Vitest)
- **Date:** 2026-11-17
- **Deciders:** Principal Frontend Architect, Senior React Engineer, Application Security Engineer
- **Context:** CricketIQ Phase 5 — Minimal User Interface

---

## 1. Context and Problem Statement

CricketIQ requires an accessible, responsive, high-performance web interface to expose its grounded-answer API (`POST /v1/rules/query`). The UI must provide:
1. Natural language query composition with context controls (format, gender, competition, dates).
2. Clean presentation of structured answers, key points, exceptions, and historical context.
3. Interactive, verifiable citation drawer/cards with official document links, page locators, and verbatim quotes.
4. Transparent applicability metadata indicating which authority and playing conditions were applied.
5. First-class treatment of non-answer states: clarification requests, domestic competition screening, and insufficient evidence abstentions.
6. Responsive behavior across mobile, tablet, and desktop viewports, targeting WCAG 2.2 AA accessibility.

The backend is stateless and validates responses before returning them. No streaming or partial generation is permitted.

---

## 2. Decision Matrix & Stack Selection

We evaluated three candidate architectures against weighted selection criteria:

| Criterion | Weight | React + Vite + TypeScript (SPA) | Next.js (App Router) | Lightweight Vanilla / HTMX |
| :--- | :---: | :---: | :---: | :---: |
| **Maintainability** | 20% | **9.0 / 10** (Clean separation, typed contracts) | 7.0 / 10 (Node server runtime overhead) | 6.0 / 10 (Complex state for citation drawers) |
| **Developer Velocity** | 15% | **9.5 / 10** (Fast HMR, instant dev startup) | 7.5 / 10 (Route conventions & SSR complexity)| 7.0 / 10 (Manual DOM wiring) |
| **Performance** | 15% | **9.0 / 10** (Zero SSR cold start, < 300KB bundle) | 8.5 / 10 (SSR overhead for private SPA) | 9.0 / 10 (Small, but harder accessibility) |
| **Accessibility Ecosystem** | 10% | **9.0 / 10** (Headless primitives, ARIA attributes)| 9.0 / 10 (Same ecosystem) | 5.0 / 10 (Custom ARIA focus traps required) |
| **API Integration / Type Safety** | 15% | **9.5 / 10** (Direct TypeScript OpenAPI client)| 9.0 / 10 (Extra server-action layer) | 6.0 / 10 (Limited typing at boundaries) |
| **Deployment Simplicity** | 10% | **10.0 / 10** (Static assets; serve via Nginx/S3/FastAPI) | 6.0 / 10 (Requires Node/Vercel server daemon) | 9.0 / 10 (Static or templated) |
| **Security & Operational Simplicity** | 15% | **9.0 / 10** (No server-side secrets; static asset) | 7.0 / 10 (SSR secret leakage risks) | 8.0 / 10 (Moderate attack surface) |
| **Weighted Total** | **100%** | **9.25 / 10** | **7.70 / 10** | **7.10 / 10** |

*Weighted calculation: $\sum (\text{rating} \times \text{weight}) / 100$. All weights sum to exactly 100%.*

### Chosen Stack:
- **Framework & Bundler:** **React 19 + TypeScript (strict mode) + Vite**.
- **Styling:** **Tailwind CSS v3** with custom CricketIQ editorial color palette (forest pitch green `#0F3826`, warm off-white `#F9F9F7`, gold rule accents `#C29B38`).
- **Icons:** **Lucide React** (tree-shaken, accessible).
- **Component Primitives:** Headless accessible UI patterns (dialogs, drawers, accordions, focus rings) meeting WCAG 2.2 AA.
- **Client Testing:** **Vitest** + **React Testing Library** for unit and component testing; **Playwright** for end-to-end browser journeys.

---

## 3. Architectural Boundaries & Directory Structure

The frontend application will reside in a top-level `/frontend` directory:

```text
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── public/
│   └── favicon.svg
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   ├── client.ts              # Strongly typed API client for /v1/rules/query
│   │   ├── types.ts               # Authoritative TypeScript types matching OpenAPI
│   │   └── urlValidator.ts        # Official MCC/ICC link safety & domain allowlist
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx         # App brand, authority badge, status indicator
│   │   │   └── Footer.tsx         # Legal disclaimer (reference only, not umpire ruling)
│   │   ├── composer/
│   │   │   ├── QuestionInput.tsx  # Multiline composer with length counter & keyboard submit
│   │   │   └── ExampleQueries.tsx # Benchmark-grounded example prompts
│   │   ├── context/
│   │   │   └── MatchContextPanel.tsx # Collapsible format, category, date controls
│   │   ├── answer/
│   │   │   ├── AnswerCard.tsx     # Direct summary, detailed explanation, key points
│   │   │   ├── ExceptionsCard.tsx # Edge cases & conditions
│   │   │   ├── HistoricalCard.tsx # Historical edition notes
│   │   │   ├── AbstentionCard.tsx # Clarification, Unsupported, Insufficient evidence
│   │   │   └── TraceSummary.tsx   # Latency, model, documents resolved, precedence
│   │   ├── citations/
│   │   │   ├── CitationCard.tsx   # Clause card with quote, page locator, verified badge
│   │   │   └── CitationDrawer.tsx # Mobile/desktop slide-over inspection drawer
│   │   └── ui/
│   │       ├── Badge.tsx
│   │       ├── Button.tsx
│   │       └── Skeleton.tsx       # Accessible loading state
│   ├── hooks/
│   │   └── useRulesQuery.ts       # State hook managing query lifecycle, error, response
│   └── styles/
│       └── index.css              # Tailwind base, tokens, focus rings, reduced motion
```

---

## 4. Invariants & Security Principles

1. **Zero Hallucinated UI:** The frontend renders only metadata returned by the backend. If `official_url` or `page_start` is null, the UI does not manufacture or guess them.
2. **Safe Link Execution:** Links to official documents are validated against the strict domain allowlist (`icc-cricket.com`, `lords.org`) and opened with `rel="noopener noreferrer"`.
3. **No Unvalidated Streaming:** The UI displays a clean, accessible loading skeleton while the backend executes its 10-step retrieval, generation, and validation lifecycle.
4. **Client-Session Follow-Up:** Conversation turns are preserved in memory during the browser session. When a follow-up is submitted, active match context is explicitly re-transmitted to the stateless backend.
