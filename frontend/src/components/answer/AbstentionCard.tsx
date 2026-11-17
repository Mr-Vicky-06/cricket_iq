import React from 'react';
import { HelpCircle, AlertTriangle, Info, RefreshCw } from 'lucide-react';
import type { QueryResponse } from '../../api/types';

interface AbstentionCardProps {
  response: QueryResponse;
  onSelectClarification?: (clarificationText: string) => void;
  onRetry?: () => void;
}

export const AbstentionCard: React.FC<AbstentionCardProps> = ({
  response,
  onSelectClarification,
  onRetry,
}) => {
  const { status, abstention_reason, suggested_clarifications } = response;

  if (status === 'clarification_required') {
    return (
      <div className="bg-amber-50/80 border border-amber-200 rounded-xl p-5 shadow-sm text-xs">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-amber-100 text-amber-800 shrink-0">
            <HelpCircle className="w-5 h-5" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-bold text-amber-900 uppercase tracking-wider text-[11px]">
                Clarification Required
              </span>
              <span className="px-2 py-0.5 rounded bg-amber-200/70 text-amber-800 text-[10px] font-semibold">
                Context Ambiguity
              </span>
            </div>
            <p className="text-gray-800 font-medium mb-3 leading-relaxed">
              {abstention_reason || 'Additional context is required to determine the exact applicable cricket regulations.'}
            </p>

            {suggested_clarifications && suggested_clarifications.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-amber-200/60">
                <span className="font-semibold text-amber-900 block text-[11px]">
                  Suggested follow-up questions:
                </span>
                <div className="flex flex-col sm:flex-row flex-wrap gap-2 pt-1">
                  {suggested_clarifications.map((sc, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => onSelectClarification?.(sc)}
                      className="px-3 py-1.5 rounded-lg bg-white border border-amber-300 hover:bg-amber-100 text-amber-900 font-medium transition-colors text-left shadow-sm"
                    >
                      {sc}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (status === 'unsupported_competition') {
    return (
      <div className="bg-blue-50/80 border border-blue-200 rounded-xl p-5 shadow-sm text-xs">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-blue-100 text-blue-800 shrink-0">
            <Info className="w-5 h-5" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-bold text-blue-900 uppercase tracking-wider text-[11px]">
                Domestic Competition Notice
              </span>
              <span className="px-2 py-0.5 rounded bg-blue-200/70 text-blue-800 text-[10px] font-semibold">
                Outside ICC / MCC Scope
              </span>
            </div>
            <p className="text-gray-800 font-medium mb-3 leading-relaxed">
              {abstention_reason ||
                'Domestic competitions (such as IPL, BBL, or County Championship) operate under local board-specific playing conditions. CricketIQ currently covers official ICC international playing conditions and MCC Laws of Cricket.'}
            </p>

            {suggested_clarifications && suggested_clarifications.length > 0 && (
              <div className="space-y-1.5 pt-2 border-t border-blue-200/60">
                <span className="font-semibold text-blue-900 block text-[11px]">
                  You can query official international equivalents:
                </span>
                <div className="flex flex-col sm:flex-row flex-wrap gap-2 pt-1">
                  {suggested_clarifications.map((sc, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => onSelectClarification?.(sc)}
                      className="px-3 py-1.5 rounded-lg bg-white border border-blue-300 hover:bg-blue-100 text-blue-900 font-medium transition-colors text-left shadow-sm"
                    >
                      {sc}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (status === 'insufficient_evidence') {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 shadow-sm text-xs">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-gray-200 text-gray-700 shrink-0">
            <AlertTriangle className="w-5 h-5" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-bold text-gray-800 uppercase tracking-wider text-[11px]">
                Insufficient Authoritative Evidence
              </span>
              <span className="px-2 py-0.5 rounded bg-gray-200 text-gray-700 text-[10px] font-semibold">
                Strict Grounding Policy
              </span>
            </div>
            <p className="text-gray-700 leading-relaxed mb-3">
              {abstention_reason ||
                'No authoritative clauses in the official cricket regulations provide a ruling on this inquiry. CricketIQ strictly abstains rather than speculating.'}
            </p>
            {suggested_clarifications && suggested_clarifications.length > 0 && (
              <div className="flex flex-col sm:flex-row flex-wrap gap-2 pt-2 border-t border-gray-200">
                {suggested_clarifications.map((sc, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => onSelectClarification?.(sc)}
                    className="px-3 py-1.5 rounded-lg bg-white border border-gray-300 hover:bg-gray-100 text-gray-800 font-medium transition-colors text-left"
                  >
                    {sc}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Error status
  return (
    <div className="bg-rose-50 border border-rose-200 rounded-xl p-5 shadow-sm text-xs">
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-rose-100 text-rose-700 shrink-0">
          <AlertTriangle className="w-5 h-5" aria-hidden="true" />
        </div>
        <div className="flex-1">
          <div className="font-bold text-rose-900 uppercase tracking-wider text-[11px] mb-1">
            Inquiry Execution Error
          </div>
          <p className="text-gray-800 mb-3">{abstention_reason || 'An unexpected error occurred while processing the rules query.'}</p>
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-rose-300 text-rose-800 hover:bg-rose-100 font-medium text-xs transition-colors shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Retry Query</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
