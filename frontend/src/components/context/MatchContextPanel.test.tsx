import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MatchContextPanel } from './MatchContextPanel';

describe('MatchContextPanel Component', () => {
  const defaultContext = {};
  const defaultPreferences = {
    detail_level: 'standard' as const,
    include_historical_comparison: false,
    include_cross_references: true,
    max_citations: 5,
  };

  it('renders toggle button and expands when isOpen is true', () => {
    const handleToggle = vi.fn();
    render(
      <MatchContextPanel
        context={defaultContext}
        preferences={defaultPreferences}
        onContextChange={vi.fn()}
        onPreferencesChange={vi.fn()}
        onReset={vi.fn()}
        isOpen={true}
        onToggle={handleToggle}
      />
    );

    expect(screen.getByText(/Match & Regulatory Context Controls/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Format/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Category/i)).toBeInTheDocument();
  });

  it('emits updated format when format dropdown changes', () => {
    const handleContextChange = vi.fn();
    render(
      <MatchContextPanel
        context={defaultContext}
        preferences={defaultPreferences}
        onContextChange={handleContextChange}
        onPreferencesChange={vi.fn()}
        onReset={vi.fn()}
        isOpen={true}
        onToggle={vi.fn()}
      />
    );

    const select = screen.getByLabelText(/Format/i);
    fireEvent.change(select, { target: { value: 'T20I' } });
    expect(handleContextChange).toHaveBeenCalledWith(
      expect.objectContaining({ format: 'T20I' })
    );
  });
});
