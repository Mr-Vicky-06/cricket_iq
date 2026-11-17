# CricketIQ — Frontend User Interface

Production-grade, evidence-grounded web interface for **CricketIQ — ICC Playing Conditions & MCC Laws Assistant**.

Built with **React 19**, **TypeScript 5.7**, **Vite 6**, **Tailwind CSS 3.4**, **Lucide Icons**, and **Vitest**.

---

## 1. Architectural Highlights

- **Stateless Backend Contract**: The frontend handles local browser session memory while communicating with the strictly stateless `POST /v1/rules/query` endpoint. Follow-up queries explicitly attach active match context parameters.
- **No Premature Streaming**: Answers and citations are displayed only after the backend finishes complete regulatory grounding and claim verification. An accessible verification indicator informs users while retrieval and verification are in progress.
- **Zero Hallucinated UI**: Clause numbers, titles, editions, and quotes are hydrated directly from SQLite/FTS5 rule metadata. The UI never fabricates page numbers, clause IDs, or dates.
- **Strict Link Safety**: Official links are strictly verified against an HTTPS allowlist limited to `icc-cricket.com` and `lords.org`.
- **Accessible & Responsive**: Fully compliant with WCAG 2.2 AA accessibility guidelines (focus rings, ARIA live regions, semantic HTML) and responsive across mobile (375px) through desktop (1280px+).

---

## 2. Design System & Palette

Crafted specifically for the cricket regulatory domain:
- **Pitch Green (`#0F3826`)**: Primary authority tone for headers, badges, and primary buttons.
- **Regulation Gold (`#C59B27`)**: Accent color for clause citations and official highlights.
- **Rulebook Parchment (`#FBFBF9` / `#F4F4EE`)**: Neutral warm background evoking traditional law printings.
- **Clarity Red / Rose (`#E11D48`)**: Strict abstention notices (e.g. domestic tournament screening).

---

## 3. Directory Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── client.ts             # Typed fetch client with 30s timeout & error handling
│   │   ├── types.ts              # OpenAPI TypeScript interfaces matching FastAPI
│   │   └── urlValidator.ts       # Domain allowlist validator for official links
│   ├── components/
│   │   ├── answer/
│   │   │   ├── AbstentionCard.tsx # Domain abstention & clarification cards
│   │   │   ├── AnswerCard.tsx     # Grounded ruling, claim map & citations
│   │   │   └── TraceSummary.tsx   # Telemetry: latency, retrieval count & model
│   │   ├── citations/
│   │   │   ├── CitationCard.tsx   # Inline citation card with verified link
│   │   │   └── CitationDrawer.tsx # Accessible slide-over drawer with verbatim text
│   │   ├── composer/
│   │   │   ├── ExampleQueries.tsx # Benchmark scenario chips
│   │   │   └── QuestionInput.tsx  # Accessible auto-resizing composer
│   │   ├── context/
│   │   │   └── MatchContextPanel.tsx # Format, category & date controls
│   │   └── layout/
│   │       ├── Header.tsx         # Brand header & live corpus status probe
│   │       └── Footer.tsx         # Regulatory disclaimer & official sources
│   ├── hooks/
│   │   └── useRulesQuery.ts      # Query orchestration & browser session state
│   ├── styles/
│   │   └── index.css             # Tailwind base & custom utility tokens
│   ├── App.tsx                   # Main application layout shell
│   └── main.tsx                  # Application entrypoint
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 4. Commands & Scripts

### Development Server
```bash
npm run dev
# Starts local dev server at http://localhost:5173 with proxy to backend at http://127.0.0.1:8000
```

### Production Build & Preview
```bash
npm run build
# Compiles production bundle to frontend/dist

npm run preview
# Serves the compiled production bundle locally
```

### Quality & Tests
```bash
npm run typecheck
# Strict TypeScript validation (tsc --noEmit)

npm test
# Runs Vitest unit & component test suite
```

---

## 5. Security & Verification Guarantees

1. **Origin Verification**: External links in citation cards and drawers only render if pointing to `https://*.icc-cricket.com` or `https://*.lords.org`. Any other URL is rendered as text without an active hyperlink.
2. **Context Retention**: When users select suggested follow-up clarifications (e.g. switching from IPL to ICC T20I), the active context is preserved and passed with the query.
3. **No Phantom Citations**: If the backend returns an abstention (`clarification_required` or `unsupported_competition`), no fictitious citations are generated.
