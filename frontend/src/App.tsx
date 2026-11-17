import React, { useEffect, useState } from 'react';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { QuestionInput } from './components/composer/QuestionInput';
import { ExampleQueries } from './components/composer/ExampleQueries';
import { MatchContextPanel } from './components/context/MatchContextPanel';
import { AnswerCard } from './components/answer/AnswerCard';
import { AbstentionCard } from './components/answer/AbstentionCard';
import { CitationDrawer } from './components/citations/CitationDrawer';
import { useRulesQuery } from './hooks/useRulesQuery';
import { apiClient } from './api/client';
import { AlertCircle, History, RotateCcw, BookOpen } from 'lucide-react';
import type { CricketFormat } from './api/types';

export const App: React.FC = () => {
  const {
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
  } = useRulesQuery();

  const [isBackendHealthy, setIsBackendHealthy] = useState(true);

  // Probe backend health on mount
  useEffect(() => {
    let isMounted = true;
    apiClient
      .checkHealthLive()
      .then(() => {
        if (isMounted) setIsBackendHealthy(true);
      })
      .catch(() => {
        if (isMounted) setIsBackendHealthy(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleExampleSelect = (exQuery: string, formatHint?: CricketFormat) => {
    setQuery(exQuery);
    if (formatHint) {
      setContext((prev) => ({ ...prev, format: formatHint }));
    }
  };

  const handleClarificationSelect = (clarificationQuery: string) => {
    setQuery(clarificationQuery);
    executeQuery(clarificationQuery);
  };

  return (
    <div className="min-h-screen flex flex-col bg-parchment-100 font-sans">
      <Header isBackendConnected={isBackendHealthy} />

      <main className="flex-1 max-w-5xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Match Context Controls Drawer / Panel */}
        <section aria-label="Match and tournament context settings">
          <MatchContextPanel
            context={context}
            preferences={preferences}
            onContextChange={setContext}
            onPreferencesChange={setPreferences}
            onReset={resetContext}
            isOpen={isContextPanelOpen}
            onToggle={() => setIsContextPanelOpen((prev) => !prev)}
          />
        </section>

        {/* Question Composer & Example Prompts */}
        <section aria-label="Ask a cricket rule question">
          <QuestionInput
            query={query}
            onChange={setQuery}
            onSubmit={() => executeQuery()}
            isLoading={isLoading}
            onClear={() => setQuery('')}
          />
          <ExampleQueries onSelectQuery={handleExampleSelect} disabled={isLoading} />
        </section>

        {/* Global Error Banner */}
        {error && (
          <div
            className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-3 shadow-sm animate-in fade-in"
            role="alert"
          >
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" aria-hidden="true" />
            <div className="flex-1">
              <span className="font-semibold block mb-0.5">Communication Error</span>
              <p>{error}</p>
            </div>
            <button
              type="button"
              onClick={() => executeQuery()}
              className="px-3 py-1 bg-white border border-rose-300 hover:bg-rose-100 rounded-md text-xs font-semibold shrink-0"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State Skeleton */}
        {isLoading && (
          <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm space-y-4 animate-pulse">
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 rounded-full bg-pitch-200" />
              <div className="h-4 bg-gray-200 rounded w-1/3" />
            </div>
            <div className="h-20 bg-parchment-200 rounded-xl" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-200 rounded w-full" />
              <div className="h-3 bg-gray-200 rounded w-5/6" />
              <div className="h-3 bg-gray-200 rounded w-4/6" />
            </div>
            <div className="pt-4 border-t border-gray-100 flex gap-4">
              <div className="h-24 bg-gray-100 rounded-xl w-1/2" />
              <div className="h-24 bg-gray-100 rounded-xl w-1/2" />
            </div>
          </div>
        )}

        {/* Active Answer or Abstention Display */}
        {!isLoading && currentResponse && (
          <section aria-live="polite" className="space-y-4">
            {currentResponse.status === 'answered' ? (
              <AnswerCard
                response={currentResponse}
                onSelectCitation={selectCitation}
                selectedCitationId={activeCitation?.citation_id}
              />
            ) : (
              <AbstentionCard
                response={currentResponse}
                onSelectClarification={handleClarificationSelect}
                onRetry={() => executeQuery()}
              />
            )}
          </section>
        )}

        {/* Session Turn History */}
        {history.length > 1 && (
          <section aria-labelledby="session-history-title" className="pt-8 border-t border-gray-200 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-pitch-800" aria-hidden="true" />
                <h2 id="session-history-title" className="text-sm font-bold text-gray-900 font-serif">
                  Session History ({history.length} Queries)
                </h2>
              </div>
              <button
                type="button"
                onClick={clearSession}
                className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-rose-700 transition-colors"
                title="Clear browser-session conversation history"
              >
                <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Clear Session</span>
              </button>
            </div>

            <div className="space-y-3">
              {history.slice(1).map((turn) => (
                <div
                  key={turn.id}
                  className="bg-white rounded-xl border border-gray-200 p-4 text-xs shadow-sm hover:border-gray-300 transition-colors"
                >
                  <div className="flex items-center justify-between gap-2 mb-1.5 text-gray-500 text-[11px]">
                    <span className="font-semibold text-gray-900 font-serif">"{turn.query}"</span>
                    <span className="font-mono">{turn.timestamp}</span>
                  </div>
                  {turn.response.answer ? (
                    <p className="text-gray-700 line-clamp-2 leading-relaxed font-serif">
                      {turn.response.answer.summary}
                    </p>
                  ) : (
                    <span className="text-amber-800 italic">
                      Abstained: {turn.response.status.replace('_', ' ')}
                    </span>
                  )}
                  <div className="mt-2 pt-2 border-t border-gray-100 flex items-center justify-between text-[11px] text-gray-400">
                    <span>
                      {turn.response.citations.length} Citation
                      {turn.response.citations.length !== 1 ? 's' : ''} Grounded
                    </span>
                    <button
                      type="button"
                      onClick={() => setQuery(turn.query)}
                      className="text-pitch-800 hover:underline font-medium"
                    >
                      Re-ask this question
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Empty State Welcome when no query has been asked yet */}
        {!currentResponse && !isLoading && !error && (
          <div className="text-center py-12 px-4 space-y-3 bg-white rounded-2xl border border-dashed border-gray-300">
            <div className="w-12 h-12 rounded-full bg-pitch-50 text-pitch-800 border border-pitch-200 flex items-center justify-center mx-auto shadow-inner">
              <BookOpen className="w-6 h-6" aria-hidden="true" />
            </div>
            <h3 className="text-base font-bold text-gray-900 font-serif">Welcome to CricketIQ</h3>
            <p className="text-xs text-gray-600 max-w-md mx-auto leading-relaxed">
              Ask any question regarding cricket laws, dismissals, playing condition differences, boundary catches,
              DRS protocols, or rain interruptions. Every answer is strictly grounded in official ICC & MCC evidence.
            </p>
          </div>
        )}
      </main>

      {/* Slide-over Citation Drawer */}
      <CitationDrawer
        citations={currentResponse?.citations || []}
        activeCitation={activeCitation}
        isOpen={isCitationDrawerOpen}
        onClose={() => setIsCitationDrawerOpen(false)}
        onSelectCitation={selectCitation}
      />

      <Footer />
    </div>
  );
};
