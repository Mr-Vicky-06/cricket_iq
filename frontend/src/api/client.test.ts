import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CricketIQClient, ApiError } from './client';
import type { QueryResponse } from './types';

describe('CricketIQClient', () => {
  let client: CricketIQClient;

  beforeEach(() => {
    client = new CricketIQClient('http://localhost:8000');
    vi.restoreAllMocks();
  });

  it('submits query request and parses successful response', async () => {
    const mockResponse: QueryResponse = {
      status: 'answered',
      answer: {
        summary: 'A batter cannot be dismissed caught on a free hit.',
        detailed_explanation: 'Under Clause 21.18.2...',
        key_points: ['Free hit follows any No ball', 'Dismissal restricted'],
        exceptions_and_edge_cases: ['Run out is permitted'],
        historical_context: null,
      },
      citations: [
        {
          citation_id: 'cit-1',
          clause_id: 'ICC_T20I_MEN_2026:21.18.2',
          clause_number: '21.18.2',
          document_id: 'ICC_T20I_MEN_2026',
          document_title: "ICC Men's T20I Playing Conditions",
          document_version: 'October 2026',
          authority: 'ICC',
          official_url: 'https://www.icc-cricket.com/rules',
          page_start: 45,
          page_end: 45,
          exact_quote: 'The delivery following a No ball shall be a free hit.',
          confidence: 0.95,
        },
      ],
      claims: [
        {
          claim_text: 'A batter cannot be dismissed caught.',
          supporting_citation_ids: ['cit-1'],
          is_verified: true,
        },
      ],
      abstention_reason: null,
      suggested_clarifications: [],
      trace: {
        query_id: 'q-test-123',
        latency_ms: 120.5,
        retrieval_count: 3,
        applicable_documents: ['ICC_T20I_MEN_2026'],
        precedence_applied: null,
        model_used: 'FakeLLMProvider',
      },
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const result = await client.queryRules({ query: 'Free hit caught out rule' });
    expect(result.status).toBe('answered');
    expect(result.answer?.summary).toContain('cannot be dismissed caught');
    expect(result.citations).toHaveLength(1);
    expect(result.citations[0].clause_number).toBe('21.18.2');
  });

  it('throws ApiError on HTTP error status with server detail', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({ detail: 'String should have at least 3 characters' }),
    } as Response);

    await expect(client.queryRules({ query: 'hi' })).rejects.toThrow(ApiError);
  });

  it('handles network failure with clear user-safe message', async () => {
    global.fetch = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));

    await expect(client.queryRules({ query: 'Is this ball legal?' })).rejects.toThrow(
      'Unable to connect to CricketIQ backend'
    );
  });
});
