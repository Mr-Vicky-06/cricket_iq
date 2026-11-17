import React from 'react';
import {
  CheckCircle,
  AlertCircle,
  FileCheck2,
  History,
  BookOpen,
  ShieldCheck,
} from 'lucide-react';
import type { QueryResponse, CitationItem } from '../../api/types';
import { CitationCard } from '../citations/CitationCard';
import { TraceSummary } from './TraceSummary';

interface AnswerCardProps {
  response: QueryResponse;
  onSelectCitation: (citation: CitationItem) => void;
  selectedCitationId?: string | null;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({
  response,
  onSelectCitation,
  selectedCitationId,
}) => {
  const { answer, citations, claims, trace } = response;

  if (!answer) return null;

  return (
    <article className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden text-xs">
      {/* Top Status Bar */}
      <div className="bg-pitch-800 text-white px-5 py-3 flex items-center justify-between border-b border-pitch-900">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-emerald-500/20 border border-emerald-400 flex items-center justify-center text-emerald-300">
            <CheckCircle className="w-4 h-4" aria-hidden="true" />
          </div>
          <span className="font-semibold text-sm">Authoritative Grounded Ruling</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-0.5 rounded-full bg-pitch-900 text-pitch-100 font-mono text-[11px] border border-pitch-700">
            {citations.length} Verified Citation{citations.length !== 1 ? 's' : ''}
          </span>
        </div>
      </div>

      <div className="p-5 sm:p-6 space-y-6">
        {/* Direct Summary Callout */}
        <section aria-labelledby="summary-heading" className="bg-parchment-100 border border-parchment-300 rounded-xl p-4 shadow-sm">
          <h3 id="summary-heading" className="font-bold text-pitch-900 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-pitch-700" aria-hidden="true" />
            <span>Direct Summary</span>
          </h3>
          <p className="text-sm font-semibold text-gray-900 leading-relaxed font-serif">
            {answer.summary}
          </p>
        </section>

        {/* Detailed Explanation */}
        <section aria-labelledby="explanation-heading">
          <h3 id="explanation-heading" className="font-bold text-gray-900 uppercase tracking-wider text-[11px] mb-2 flex items-center gap-1.5">
            <BookOpen className="w-4 h-4 text-pitch-700" aria-hidden="true" />
            <span>Regulatory Explanation</span>
          </h3>
          <div className="text-gray-800 text-xs sm:text-sm leading-relaxed whitespace-pre-line font-serif pl-1">
            {answer.detailed_explanation}
          </div>
        </section>

        {/* Key Points */}
        {answer.key_points && answer.key_points.length > 0 && (
          <section aria-labelledby="keypoints-heading" className="pt-4 border-t border-gray-100">
            <h3 id="keypoints-heading" className="font-bold text-gray-900 uppercase tracking-wider text-[11px] mb-2.5">
              Key Rule Provisions
            </h3>
            <ul className="space-y-2">
              {answer.key_points.map((pt, i) => (
                <li key={i} className="flex items-start gap-2.5 text-gray-800">
                  <span className="w-4 h-4 rounded-full bg-pitch-100 text-pitch-800 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <span className="leading-relaxed">{pt}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Exceptions & Edge Cases */}
        {answer.exceptions_and_edge_cases && answer.exceptions_and_edge_cases.length > 0 && (
          <section aria-labelledby="exceptions-heading" className="bg-amber-50/60 border border-amber-200/80 rounded-xl p-4">
            <h3 id="exceptions-heading" className="font-bold text-amber-900 uppercase tracking-wider text-[11px] mb-2 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 text-amber-700" aria-hidden="true" />
              <span>Exceptions & Conditions</span>
            </h3>
            <ul className="space-y-1.5 pl-1">
              {answer.exceptions_and_edge_cases.map((exc, i) => (
                <li key={i} className="flex items-start gap-2 text-gray-800 text-xs">
                  <span className="text-amber-700 font-bold">•</span>
                  <span>{exc}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Historical Context if present */}
        {answer.historical_context && (
          <section aria-labelledby="history-heading" className="bg-purple-50/60 border border-purple-200 rounded-xl p-4">
            <h3 id="history-heading" className="font-bold text-purple-900 uppercase tracking-wider text-[11px] mb-1 flex items-center gap-1.5">
              <History className="w-4 h-4 text-purple-700" aria-hidden="true" />
              <span>Historical Rule Comparison / Recent Changes</span>
            </h3>
            <p className="text-purple-950 text-xs leading-relaxed pl-1">
              {answer.historical_context}
            </p>
          </section>
        )}

        {/* Claim Verification Mapping */}
        {claims && claims.length > 0 && (
          <section aria-labelledby="claims-heading" className="pt-4 border-t border-gray-100">
            <h3 id="claims-heading" className="font-bold text-gray-900 uppercase tracking-wider text-[11px] mb-2 flex items-center gap-1.5">
              <FileCheck2 className="w-4 h-4 text-emerald-700" aria-hidden="true" />
              <span>Clause Claim Support Map (100% Verified Grounding)</span>
            </h3>
            <div className="space-y-2">
              {claims.map((claim, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-gray-50 border border-gray-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2"
                >
                  <span className="text-gray-800 text-[11px] font-medium leading-snug">
                    "{claim.claim_text}"
                  </span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="text-[10px] text-gray-500">Supported by:</span>
                    {claim.supporting_citation_ids.map((citId) => (
                      <span
                        key={citId}
                        className="px-2 py-0.5 rounded bg-pitch-100 text-pitch-800 font-mono text-[10px] font-bold"
                      >
                        {citId}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Citations Grid */}
        <section aria-labelledby="citations-heading" className="pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <h3 id="citations-heading" className="font-bold text-gray-900 uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-pitch-700" aria-hidden="true" />
              <span>Authoritative Source Citations</span>
            </h3>
            <span className="text-[11px] text-gray-500">
              Click any citation to inspect verbatim source excerpt
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {citations.map((citation) => (
              <CitationCard
                key={citation.citation_id}
                citation={citation}
                isSelected={selectedCitationId === citation.citation_id}
                onSelect={onSelectCitation}
              />
            ))}
          </div>
        </section>

        {/* Telemetry Trace */}
        {trace && <TraceSummary trace={trace} />}
      </div>
    </article>
  );
};
