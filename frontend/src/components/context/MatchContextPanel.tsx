import React from 'react';
import { SlidersHorizontal, RotateCcw, Calendar, Trophy, ChevronDown, ChevronUp } from 'lucide-react';
import type { MatchContextInput, CricketFormat, GenderCategory, ResponsePreferences } from '../../api/types';

interface MatchContextPanelProps {
  context: MatchContextInput;
  preferences: ResponsePreferences;
  onContextChange: (updated: MatchContextInput) => void;
  onPreferencesChange: (updated: ResponsePreferences) => void;
  onReset: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const MatchContextPanel: React.FC<MatchContextPanelProps> = ({
  context,
  preferences,
  onContextChange,
  onPreferencesChange,
  onReset,
  isOpen,
  onToggle,
}) => {
  const hasActiveOverrides =
    Boolean(context.format) ||
    Boolean(context.category) ||
    Boolean(context.series_start_date) ||
    Boolean(context.match_date) ||
    Boolean(context.competition) ||
    preferences.detail_level !== 'standard' ||
    preferences.include_historical_comparison;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mb-4 transition-all">
      {/* Header bar toggle */}
      <button
        type="button"
        onClick={onToggle}
        className="w-full px-4 py-2.5 flex items-center justify-between bg-parchment-100 hover:bg-parchment-200 text-left transition-colors text-xs font-medium text-gray-700"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-pitch-700" aria-hidden="true" />
          <span className="font-semibold text-gray-900">Match & Regulatory Context Controls</span>
          {hasActiveOverrides && (
            <span className="px-2 py-0.5 rounded-full bg-pitch-100 text-pitch-800 text-[10px] font-bold">
              Custom Context Set
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 text-gray-500">
          <span>{isOpen ? 'Hide Options' : 'Customize Context'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Expanded Controls */}
      {isOpen && (
        <div className="p-4 border-t border-gray-200 space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Format Selector */}
            <div>
              <label htmlFor="context-format" className="block font-semibold text-gray-700 mb-1">
                Format
              </label>
              <select
                id="context-format"
                value={context.format ?? ''}
                onChange={(e) =>
                  onContextChange({
                    ...context,
                    format: (e.target.value as CricketFormat) || null,
                  })
                }
                className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-pitch-800"
              >
                <option value="">Auto-Detect from Question</option>
                <option value="Test">Test Match</option>
                <option value="ODI">One Day International (ODI)</option>
                <option value="T20I">Twenty20 International (T20I)</option>
                <option value="General">General / Baseline Laws</option>
              </select>
            </div>

            {/* Gender / Category */}
            <div>
              <label htmlFor="context-category" className="block font-semibold text-gray-700 mb-1">
                Category
              </label>
              <select
                id="context-category"
                value={context.category ?? ''}
                onChange={(e) =>
                  onContextChange({
                    ...context,
                    category: (e.target.value as GenderCategory) || null,
                  })
                }
                className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-pitch-800"
              >
                <option value="">Auto-Detect from Question</option>
                <option value="Men's">Men's Playing Conditions</option>
                <option value="Women's">Women's Playing Conditions</option>
                <option value="Universal">Universal MCC Laws</option>
              </select>
            </div>

            {/* Series Start Date (Transition Boundary) */}
            <div>
              <label
                htmlFor="context-series-start"
                className="block font-semibold text-gray-700 mb-1 flex items-center gap-1"
                title="ICC Oct 2026 rules apply to series starting on or after 1 Oct 2026"
              >
                <Calendar className="w-3.5 h-3.5 text-pitch-700" aria-hidden="true" />
                <span>Series Start Date</span>
              </label>
              <input
                type="date"
                id="context-series-start"
                value={context.series_start_date ?? ''}
                onChange={(e) =>
                  onContextChange({
                    ...context,
                    series_start_date: e.target.value || null,
                  })
                }
                className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-pitch-800"
              />
            </div>

            {/* Match Date */}
            <div>
              <label htmlFor="context-match-date" className="block font-semibold text-gray-700 mb-1 flex items-center gap-1">
                <Calendar className="w-3.5 h-3.5 text-gray-500" aria-hidden="true" />
                <span>Match Date</span>
              </label>
              <input
                type="date"
                id="context-match-date"
                value={context.match_date ?? ''}
                onChange={(e) =>
                  onContextChange({
                    ...context,
                    match_date: e.target.value || null,
                  })
                }
                className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-pitch-800"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2 border-t border-gray-100">
            {/* Competition */}
            <div>
              <label htmlFor="context-competition" className="block font-semibold text-gray-700 mb-1 flex items-center gap-1">
                <Trophy className="w-3.5 h-3.5 text-gold-600" aria-hidden="true" />
                <span>Competition Overlay</span>
              </label>
              <input
                type="text"
                id="context-competition"
                placeholder="e.g. WTC, T20 World Cup..."
                value={context.competition ?? ''}
                onChange={(e) =>
                  onContextChange({
                    ...context,
                    competition: e.target.value || null,
                  })
                }
                className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-pitch-800"
              />
            </div>

            {/* Detail Level */}
            <div>
              <label htmlFor="pref-detail" className="block font-semibold text-gray-700 mb-1">
                Explanation Depth
              </label>
              <select
                id="pref-detail"
                value={preferences.detail_level ?? 'standard'}
                onChange={(e) =>
                  onPreferencesChange({
                    ...preferences,
                    detail_level: e.target.value as 'concise' | 'standard' | 'detailed',
                  })
                }
                className="w-full px-2.5 py-1.5 rounded-lg border border-gray-300 bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-pitch-800"
              >
                <option value="concise">Concise Ruling</option>
                <option value="standard">Standard with Citations</option>
                <option value="detailed">Detailed Regulatory Analysis</option>
              </select>
            </div>

            {/* Historical Comparison Toggle */}
            <div className="flex items-center gap-2 pt-5">
              <input
                type="checkbox"
                id="pref-history"
                checked={preferences.include_historical_comparison ?? false}
                onChange={(e) =>
                  onPreferencesChange({
                    ...preferences,
                    include_historical_comparison: e.target.checked,
                  })
                }
                className="w-4 h-4 rounded text-pitch-800 focus:ring-pitch-800 border-gray-300"
              />
              <label htmlFor="pref-history" className="text-xs text-gray-700 font-medium cursor-pointer">
                Include Historical Comparison (2022 vs 2026 Editions)
              </label>
            </div>
          </div>

          {/* Reset Action */}
          {hasActiveOverrides && (
            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={onReset}
                className="flex items-center gap-1.5 px-3 py-1 text-xs text-rose-700 hover:text-rose-900 hover:bg-rose-50 rounded-lg transition-colors border border-rose-200"
              >
                <RotateCcw className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Reset to Default Auto-Detect</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
