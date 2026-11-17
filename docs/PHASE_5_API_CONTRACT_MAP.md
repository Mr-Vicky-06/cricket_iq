# CricketIQ — Phase 5 API Contract Map
## Authoritative OpenAPI & Pydantic Schema Specification

- **Source API:** CricketIQ FastAPI (`/openapi.json`)
- **Backend Baseline:** Commit `15995d3`
- **Primary Endpoint:** `POST /v1/rules/query`
- **Health Endpoints:** `GET /health/live`, `GET /health/ready`

---

## 1. Primary Endpoint: `POST /v1/rules/query`

### 1.1 Inbound Payload: `QueryRequest`

```typescript
export interface QueryRequest {
  /** Natural language question about cricket rules (min length: 3, max length: 1000) */
  query: string;
  /** Explicit user-supplied match or tournament context */
  context?: MatchContextInput | null;
  /** Answer formatting and citation preferences */
  preferences?: ResponsePreferences | null;
}

export interface MatchContextInput {
  /** 'international', 'domestic', or 'unspecified' */
  cricket_level?: string | null;
  /** Governing authority e.g. 'ICC', 'MCC', 'BCCI' */
  governing_body?: string | null;
  /** Tournament identifier e.g. 'WTC', 'T20_WORLD_CUP_2026', 'IPL' */
  competition?: string | null;
  /** Match format: 'Test' | 'ODI' | 'T20I' | 'General' */
  format?: 'Test' | 'ODI' | 'T20I' | 'General' | null;
  /** Category: "Men's" | "Women's" | "Universal" */
  category?: "Men's" | "Women's" | "Universal" | null;
  /** Match date in ISO format YYYY-MM-DD */
  match_date?: string | null;
  /** Series start date in ISO format YYYY-MM-DD (crucial for ICC Oct 2026 transition) */
  series_start_date?: string | null;
  /** Season string e.g. '2025-2027' */
  season?: string | null;
  /** Preferred authority: 'MCC' | 'ICC' */
  applicable_rules?: 'MCC' | 'ICC' | null;
}

export interface ResponsePreferences {
  /** Explanation depth: 'concise' | 'standard' | 'detailed' (default: 'standard') */
  detail_level?: 'concise' | 'standard' | 'detailed';
  /** Whether to compare historical editions (default: false) */
  include_historical_comparison?: boolean;
  /** Whether to include parent and cross-referenced clauses (default: true) */
  include_cross_references?: boolean;
  /** Maximum authoritative citations to return, between 1 and 10 (default: 5) */
  max_citations?: number;
}
```

### 1.2 Outbound Response: `QueryResponse`

```typescript
export type QueryStatus =
  | 'answered'
  | 'clarification_required'
  | 'unsupported_competition'
  | 'insufficient_evidence'
  | 'error';

export interface QueryResponse {
  /** Execution status for rule query processing */
  status: QueryStatus;
  /** Synthesized answer payload (present when status === 'answered') */
  answer?: AnswerPayload | null;
  /** Authoritative citations backing the answer */
  citations: CitationItem[];
  /** Substantive claims paired with supporting citation IDs */
  claims: ClaimSupportItem[];
  /** Detailed reason when assistant abstains from answering */
  abstention_reason?: string | null;
  /** Targeted follow-up clarification questions */
  suggested_clarifications: string[];
  /** Audit and telemetry trace of the pipeline */
  trace: QueryTrace;
}

export interface AnswerPayload {
  /** Concise high-level answer to user query */
  summary: string;
  /** Detailed regulatory explanation with clause citations */
  detailed_explanation: string;
  /** Core bullet-point takeaways */
  key_points: string[];
  /** Applicable exceptions, conditions, or umpire discretions */
  exceptions_and_edge_cases: string[];
  /** Comparison to previous editions or notes on recent amendments */
  historical_context?: string | null;
}

export interface CitationItem {
  /** Unique citation identifier e.g. 'cit-1' */
  citation_id: string;
  /** Corpus clause identifier e.g. 'ICC_T20I_MEN_2026:21.18.2' */
  clause_id: string;
  /** Official clause number e.g. '21.18.2' or 'APP_D:3.2' */
  clause_number: string;
  /** Source document identifier e.g. 'ICC_T20I_MEN_2026' */
  document_id: string;
  /** Official publication title */
  document_title: string;
  /** Document edition / publication version e.g. 'October 2026' */
  document_version: string;
  /** Governing authority e.g. 'ICC' or 'MCC' */
  authority: string;
  /** Canonical official URL */
  official_url?: string | null;
  /** Starting printed / PDF page */
  page_start?: number | null;
  /** Ending printed / PDF page */
  page_end?: number | null;
  /** Verbatim excerpt from source clause */
  exact_quote: string;
  /** Retrieval / relevance confidence score (0.0 to 1.0) */
  confidence: number;
}

export interface ClaimSupportItem {
  /** Specific substantive claim statement made in answer */
  claim_text: string;
  /** Citation IDs supporting this claim e.g. ['cit-1'] */
  supporting_citation_ids: string[];
  /** True if claim is substantiated by at least one citation */
  is_verified: boolean;
}

export interface QueryTrace {
  /** UUID for transaction */
  query_id: string;
  /** Total pipeline latency in milliseconds */
  latency_ms: number;
  /** Number of evidence clauses retrieved */
  retrieval_count: number;
  /** IDs of documents resolved as applicable */
  applicable_documents: string[];
  /** Precedence applied description */
  precedence_applied?: string | null;
  /** LLM model or provider used */
  model_used: string;
}
```

---

## 2. Health Endpoints

### 2.1 `GET /health/live`
- **Response 200:** `{"status": "alive"}`

### 2.2 `GET /health/ready`
- **Response 200:**
  ```json
  {
    "status": "ready",
    "database": "connected",
    "documents_count": 11,
    "clauses_count": 11008
  }
  ```
- **Response 503:** Service Unavailable (if database query fails)

---

## 3. Allowed Source Domain Allowlist

For client-side link safety, official source links must match this allowlist:
- `www.icc-cricket.com` / `icc-cricket.com`
- `www.lords.org` / `lords.org`
- Protocol must strictly be `https:`. All other schemes (`http:`, `javascript:`, `data:`, `file:`) must be rejected.
