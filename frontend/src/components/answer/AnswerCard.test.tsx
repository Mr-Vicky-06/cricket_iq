import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AnswerCard } from './AnswerCard';
import type { QueryResponse } from '../../api/types';

describe('AnswerCard Component', () => {
  const mockResponse: QueryResponse = {
    status: 'answered',
    answer: {
      summary: 'A batter cannot be out caught on a free hit.',
      detailed_explanation: 'Under ICC T20I clause 21.18.2...',
      key_points: ['Free hit delivery follows a no ball', 'Run out permitted'],
      exceptions_and_edge_cases: ['Change of striker allows field change'],
      historical_context: 'Unchanged in 2026 update',
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
        claim_text: 'A batter cannot be out caught on a free hit.',
        supporting_citation_ids: ['cit-1'],
        is_verified: true,
      },
    ],
    abstention_reason: null,
    suggested_clarifications: [],
    trace: {
      query_id: 'q-456',
      latency_ms: 135.2,
      retrieval_count: 2,
      applicable_documents: ['ICC_T20I_MEN_2026'],
      precedence_applied: null,
      model_used: 'FakeLLMProvider',
    },
  };

  it('renders summary, explanation, key points, and citation card', () => {
    render(<AnswerCard response={mockResponse} onSelectCitation={vi.fn()} />);

    expect(screen.getByText('Direct Summary')).toBeInTheDocument();
    expect(
      screen.getByText('A batter cannot be out caught on a free hit.')
    ).toBeInTheDocument();
    expect(screen.getByText(/Under ICC T20I clause 21.18.2/)).toBeInTheDocument();
    expect(screen.getByText('Clause 21.18.2')).toBeInTheDocument();
    expect(screen.getByText('Run out permitted')).toBeInTheDocument();
    expect(screen.getByText(/Change of striker/)).toBeInTheDocument();
  });
});
