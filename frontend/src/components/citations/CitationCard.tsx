import React from 'react';
import { ExternalLink, Bookmark, CheckCircle2, AlertCircle } from 'lucide-react';
import type { CitationItem } from '../../api/types';
import { validateOfficialUrl } from '../../api/urlValidator';

interface CitationCardProps {
  citation: CitationItem;
  onSelect?: (citation: CitationItem) => void;
  isSelected?: boolean;
}

export const CitationCard: React.FC<CitationCardProps> = ({
  citation,
  onSelect,
  isSelected = false,
}) => {
  const urlCheck = validateOfficialUrl(citation.official_url);
  const isICC = citation.authority.toUpperCase() === 'ICC';

  return (
    <div
      onClick={() => onSelect?.(citation)}
      className={`rounded-xl border p-4 transition-all text-xs cursor-pointer ${
        isSelected
          ? 'border-pitch-700 bg-pitch-50/50 ring-2 ring-pitch-700/30'
          : 'border-gray-200 bg-white hover:border-pitch-600 hover:shadow-sm'
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 flex-wrap">
          <span
            className={`px-2 py-0.5 rounded text-[11px] font-bold ${
              isICC ? 'bg-emerald-100 text-emerald-800' : 'bg-gold-100 text-amber-900'
            }`}
          >
            {citation.authority}
          </span>
          <span className="font-mono font-bold text-gray-900 text-sm">
            Clause {citation.clause_number}
          </span>
          <div className="flex items-center gap-1 text-emerald-700 font-medium text-[11px]">
            <CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Database Grounded</span>
          </div>
        </div>

        {citation.page_start && (
          <span className="text-[11px] text-gray-500 font-mono shrink-0">
            Page {citation.page_start}
            {citation.page_end && citation.page_end !== citation.page_start ? `–${citation.page_end}` : ''}
          </span>
        )}
      </div>

      <div className="text-gray-700 font-medium mb-2">{citation.document_title}</div>

      <blockquote className="bg-parchment-100 border-l-2 border-pitch-700 pl-3 py-1.5 my-2 text-gray-800 italic leading-relaxed text-[11px] rounded-r">
        "{citation.exact_quote}"
      </blockquote>

      <div className="flex items-center justify-between pt-2 border-t border-gray-100 text-gray-500 text-[11px]">
        <div className="flex items-center gap-1">
          <Bookmark className="w-3 h-3 text-pitch-700" aria-hidden="true" />
          <span>{citation.document_version}</span>
        </div>

        {urlCheck.isValid && urlCheck.sanitizedUrl ? (
          <a
            href={urlCheck.sanitizedUrl}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-pitch-800 hover:text-pitch-900 font-medium hover:underline focus-visible:ring-1 focus-visible:ring-pitch-800 rounded"
          >
            <span>Official Document</span>
            <ExternalLink className="w-3 h-3" aria-hidden="true" />
          </a>
        ) : (
          <span className="flex items-center gap-1 text-gray-400" title="URL unverified or unavailable">
            <AlertCircle className="w-3 h-3" aria-hidden="true" />
            <span>Official PDF Extracted</span>
          </span>
        )}
      </div>
    </div>
  );
};
