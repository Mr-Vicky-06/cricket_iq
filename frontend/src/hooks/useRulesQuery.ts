import { useState, useCallback } from 'react';
import { apiClient, ApiError } from '../api/client';
import type {
  MatchContextInput,
  ResponsePreferences,
  QueryResponse,
  CitationItem,
} from '../api/types';

export interface TurnItem {
  id: string;
  query: string;
  contextUsed: MatchContextInput;
  response: QueryResponse;
  timestamp: string;
}

export function useRulesQuery() {
  const [query, setQuery] = useState('');
  const [context, setContext] = useState<MatchContextInput>({});
  const [preferences, setPreferences] = useState<ResponsePreferences>({
    detail_level: 'standard',
    include_historical_comparison: false,
    include_cross_references: true,
    max_citations: 5,
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentResponse, setCurrentResponse] = useState<QueryResponse | null>(null);
  const [history, setHistory] = useState<TurnItem[]>([]);

  const [activeCitation, setActiveCitation] = useState<CitationItem | null>(null);
  const [isCitationDrawerOpen, setIsCitationDrawerOpen] = useState(false);
  const [isContextPanelOpen, setIsContextPanelOpen] = useState(false);

  const executeQuery = useCallback(
    async (queryOverride?: string, contextOverride?: MatchContextInput) => {
      const q = (queryOverride ?? query).trim();
      if (!q || q.length < 3) return;

      const activeCtx = contextOverride ?? context;

      setIsLoading(true);
      setError(null);

      try {
        const resp = await apiClient.queryRules({
          query: q,
          context: Object.keys(activeCtx).length > 0 ? activeCtx : null,
          preferences,
        });

        setCurrentResponse(resp);

        // Append turn to browser-session history
        const turn: TurnItem = {
          id: resp.trace.query_id || `turn-${Date.now()}`,
          query: q,
          contextUsed: { ...activeCtx },
          response: resp,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };

        setHistory((prev) => [turn, ...prev]);

        // Auto-select first citation if available
        if (resp.citations.length > 0) {
          setActiveCitation(resp.citations[0]);
        }
      } catch (err: unknown) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('An unexpected error occurred while communicating with the backend.');
        }
      } finally {
        setIsLoading(false);
      }
    },
    [query, context, preferences]
  );

  const resetContext = useCallback(() => {
    setContext({});
    setPreferences({
      detail_level: 'standard',
      include_historical_comparison: false,
      include_cross_references: true,
      max_citations: 5,
    });
  }, []);

  const clearSession = useCallback(() => {
    setQuery('');
    setCurrentResponse(null);
    setHistory([]);
    setError(null);
    setActiveCitation(null);
    setIsCitationDrawerOpen(false);
    resetContext();
  }, [resetContext]);

  const selectCitation = useCallback((citation: CitationItem) => {
    setActiveCitation(citation);
    setIsCitationDrawerOpen(true);
  }, []);

  return {
    query,
    setQuery,
    context,
    setContext,
    preferences,
    setPreferences,
    isLoading,
    error,
    currentResponse,
    history,
    activeCitation,
    isCitationDrawerOpen,
    setIsCitationDrawerOpen,
    isContextPanelOpen,
    setIsContextPanelOpen,
    executeQuery,
    resetContext,
    clearSession,
    selectCitation,
  };
}
