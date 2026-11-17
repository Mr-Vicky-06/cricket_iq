import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AbstentionCard } from './AbstentionCard';
import type { QueryResponse } from '../../api/types';

describe('AbstentionCard Component', () => {
  it('renders clarification required state with suggested questions', () => {
    const handleClarification = vi.fn();
    const resp: QueryResponse = {
      status: 'clarification_required',
      abstention_reason: 'Please specify whether Test or T20I rules apply.',
      suggested_clarifications: ['Are you referring to Test or T20I matches?'],
      citations: [],
      claims: [],
      trace: {
        query_id: 'q-clarif',
        latency_ms: 12.0,
        retrieval_count: 0,
        applicable_documents: [],
        model_used: 'none',
      },
    };

    render(
      <AbstentionCard
        response={resp}
        onSelectClarification={handleClarification}
      />
    );

    expect(screen.getByText(/Clarification Required/i)).toBeInTheDocument();
    expect(
      screen.getByText('Please specify whether Test or T20I rules apply.')
    ).toBeInTheDocument();

    const sugBtn = screen.getByRole('button', {
      name: /Are you referring to Test or T20I matches\?/i,
    });
    fireEvent.click(sugBtn);
    expect(handleClarification).toHaveBeenCalledWith(
      'Are you referring to Test or T20I matches?'
    );
  });

  it('renders unsupported competition state for domestic franchise leagues', () => {
    const resp: QueryResponse = {
      status: 'unsupported_competition',
      abstention_reason:
        'Domestic competitions like IPL operate under local board regulations.',
      suggested_clarifications: [
        'Would you like the rule according to official ICC T20I Playing Conditions?',
      ],
      citations: [],
      claims: [],
      trace: {
        query_id: 'q-dom',
        latency_ms: 5.0,
        retrieval_count: 0,
        applicable_documents: [],
        model_used: 'none',
      },
    };

    render(<AbstentionCard response={resp} />);

    expect(
      screen.getByText(/Domestic Competition Notice/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Domestic competitions like IPL operate/i)
    ).toBeInTheDocument();
  });
});
