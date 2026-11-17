import React from 'react';
import { X, ExternalLink, ShieldCheck, BookOpen, Layers } from 'lucide-react';
import type { CitationItem } from '../../api/types';
import { validateOfficialUrl } from '../../api/urlValidator';

interface CitationDrawerProps {
  citations: CitationItem[];
  activeCitation: CitationItem | null;
  isOpen: boolean;
  onClose: () => void;
  onSelectCitation: (citation: CitationItem) => void;
}

export const CitationDrawer: React.FC<CitationDrawerProps> = ({
  citations,
  activeCitation,
  isOpen,
  onClose,
  onSelectCitation,
}) => {
  if (!isOpen) return null;

  const current = activeCitation || citations[0] || null;
  const urlCheck = current ? validateOfficialUrl(current.official_url) : null;

  return (
    <div
      className="fixed inset-0 z-50 overflow-hidden bg-black/40 backdrop-blur-sm flex justify-end transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="citation-drawer-title"
    >
      <div className="w-full max-w-lg bg-white h-full shadow-2xl flex flex-col border-l border-gray-200 animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between bg-parchment-100">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-pitch-800" aria-hidden="true" />
            <h2 id="citation-drawer-title" className="text-sm font-bold text-gray-900 font-serif">
              Authoritative Source Evidence
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
            aria-label="Close citation drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab List if multiple citations */}
        {citations.length > 1 && (
          <div className="px-4 py-2 bg-gray-50 border-b border-gray-200 flex items-center gap-1.5 overflow-x-auto text-xs">
            <Layers className="w-4 h-4 text-gray-400 shrink-0 mr-1" aria-hidden="true" />
            {citations.map((c, i) => (
              <button
                key={c.citation_id}
                type="button"
                onClick={() => onSelectCitation(c)}
                className={`px-3 py-1 rounded-full whitespace-nowrap font-medium transition-colors ${
                  current?.citation_id === c.citation_id
                    ? 'bg-pitch-800 text-white shadow-sm'
                    : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-100'
                }`}
              >
                [{i + 1}] Clause {c.clause_number}
              </button>
            ))}
          </div>
        )}

        {/* Detail Content */}
        {current ? (
          <div className="p-5 flex-1 overflow-y-auto space-y-5 text-xs leading-relaxed">
            {/* Clause Banner */}
            <div className="bg-pitch-50 border border-pitch-200 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-mono text-sm font-bold text-pitch-900">
                  {current.authority} — Clause {current.clause_number}
                </span>
                <span className="text-[11px] font-mono text-gray-600">
                  Pages {current.page_start}
                  {current.page_end && current.page_end !== current.page_start ? `–${current.page_end}` : ''}
                </span>
              </div>
              <div className="font-semibold text-gray-900 text-xs mb-1">
                {current.document_title}
              </div>
              <div className="text-gray-500 text-[11px]">
                Edition: {current.document_version}
              </div>
            </div>

            {/* Exact Quote Block */}
            <div>
              <h3 className="font-bold text-gray-900 uppercase tracking-wider text-[11px] mb-2 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-600" aria-hidden="true" />
                <span>Verbatim Regulatory Text (Database Hydrated)</span>
              </h3>
              <div className="bg-parchment-100 border border-parchment-300 rounded-xl p-4 text-gray-800 italic leading-relaxed font-serif text-xs shadow-inner">
                "{current.exact_quote}"
              </div>
            </div>

            {/* Provenance & Authority Details */}
            <div className="border-t border-gray-100 pt-4 space-y-2 text-gray-600">
              <div className="flex justify-between py-1 border-b border-gray-50">
                <span className="font-medium text-gray-500">Corpus Identifier:</span>
                <span className="font-mono text-gray-900">{current.clause_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-50">
                <span className="font-medium text-gray-500">Governing Body:</span>
                <span className="font-semibold text-gray-900">{current.authority}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-gray-50">
                <span className="font-medium text-gray-500">Retrieval Confidence:</span>
                <span className="font-mono text-emerald-700 font-bold">
                  {(current.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Official Source Link */}
            {urlCheck?.isValid && urlCheck.sanitizedUrl && (
              <div className="pt-2">
                <a
                  href={urlCheck.sanitizedUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-pitch-800 hover:bg-pitch-900 text-white font-medium text-xs shadow transition-colors"
                >
                  <span>Open Official Document on {urlCheck.domain}</span>
                  <ExternalLink className="w-4 h-4" aria-hidden="true" />
                </a>
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-gray-500 text-xs">
            No citation selected.
          </div>
        )}
      </div>
    </div>
  );
};
