import React from 'react';
import { ExternalLink, ShieldAlert } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-parchment-200 border-t border-parchment-300 py-6 text-xs text-gray-600 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
            <p>
              <span className="font-semibold text-gray-800">Regulatory Reference Notice:</span> CricketIQ provides
              grounded interpretations based on published ICC Playing Conditions and MCC Laws of Cricket. It is an
              informational aid and does not supersede on-field match umpire discretionary decisions.
            </p>
          </div>
          <div className="flex items-center gap-4 text-gray-500 whitespace-nowrap">
            <a
              href="https://www.lords.org/mcc/the-laws-of-cricket"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-pitch-800 hover:underline flex items-center gap-1"
            >
              MCC Laws
              <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
            <span aria-hidden="true">•</span>
            <a
              href="https://www.icc-cricket.com/about/cricket/rules-and-regulations/playing-conditions"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-pitch-800 hover:underline flex items-center gap-1"
            >
              ICC Conditions
              <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};
