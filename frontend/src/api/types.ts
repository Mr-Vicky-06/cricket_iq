/**
 * CricketIQ Authoritative Frontend API Types
 * Grounded directly in FastAPI / OpenAPI contracts.
 */

export type CricketFormat = 'Test' | 'ODI' | 'T20I' | 'General';
export type GenderCategory = "Men's" | "Women's" | "Universal";
export type RuleAuthority = 'MCC' | 'ICC';

export interface MatchContextInput {
  cricket_level?: string | null;
  governing_body?: string | null;
  competition?: string | null;
  format?: CricketFormat | null;
  category?: GenderCategory | null;
  match_date?: string | null;
  series_start_date?: string | null;
  season?: string | null;
  applicable_rules?: RuleAuthority | null;
}

export type DetailLevel = 'concise' | 'standard' | 'detailed';

export interface ResponsePreferences {
  detail_level?: DetailLevel;
  include_historical_comparison?: boolean;
  include_cross_references?: boolean;
  max_citations?: number;
}

export interface QueryRequest {
  query: string;
  context?: MatchContextInput | null;
  preferences?: ResponsePreferences | null;
}

export type QueryStatus =
  | 'answered'
  | 'clarification_required'
  | 'unsupported_competition'
  | 'insufficient_evidence'
  | 'error';

export interface AnswerPayload {
  summary: string;
  detailed_explanation: string;
  key_points: string[];
  exceptions_and_edge_cases: string[];
  historical_context?: string | null;
}

export interface CitationItem {
  citation_id: string;
  clause_id: string;
  clause_number: string;
  document_id: string;
  document_title: string;
  document_version: string;
  authority: string;
  official_url?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  exact_quote: string;
  confidence: number;
}

export interface ClaimSupportItem {
  claim_text: string;
  supporting_citation_ids: string[];
  is_verified: boolean;
}

export interface QueryTrace {
  query_id: string;
  latency_ms: number;
  retrieval_count: number;
  applicable_documents: string[];
  precedence_applied?: string | null;
  model_used: string;
}

export interface QueryResponse {
  status: QueryStatus;
  answer?: AnswerPayload | null;
  citations: CitationItem[];
  claims: ClaimSupportItem[];
  abstention_reason?: string | null;
  suggested_clarifications: string[];
  trace: QueryTrace;
}

export interface HealthReadyResponse {
  status: 'ready' | 'not_ready';
  database: string;
  documents_count: number;
  clauses_count: number;
}

export interface HealthLiveResponse {
  status: 'alive';
}
