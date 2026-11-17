import React from 'react';
import { HelpCircle } from 'lucide-react';

interface ExampleQueriesProps {
  onSelectQuery: (query: string, formatHint?: 'Test' | 'ODI' | 'T20I') => void;
  disabled?: boolean;
}

const EXAMPLES: { label: string; query: string; formatHint?: 'Test' | 'ODI' | 'T20I' }[] = [
  {
    label: 'Free Hit Caught Dismissal',
    query: "Can a batter be dismissed caught on a free hit in Men's T20I?",
    formatHint: 'T20I',
  },
  {
    label: 'ODI Bouncers Limit',
    query: "How many short-pitched bouncers per over are allowed in Men's ODI cricket?",
    formatHint: 'ODI',
  },
  {
    label: 'Concussion Replacement',
    query: "What is the like-for-like concussion substitute rule in Test cricket?",
    formatHint: 'Test',
  },
  {
    label: 'MCC vs ICC Free Hits',
    query: "Do free hits exist in the baseline MCC Laws of Cricket?",
  },
  {
    label: 'Boundary Catching Relay',
    query: "What happens if a fielder catches the ball outside the boundary ropes?",
  },
  {
    label: 'Domestic Screening (IPL)',
    query: "What is the Impact Player substitution rule in the IPL?",
  },
];

export const ExampleQueries: React.FC<ExampleQueriesProps> = ({ onSelectQuery, disabled = false }) => {
  return (
    <div className="mt-3">
      <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-2 font-medium">
        <HelpCircle className="w-3.5 h-3.5 text-pitch-700" aria-hidden="true" />
        <span>Try asking about authentic match regulations:</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((ex, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectQuery(ex.query, ex.formatHint)}
            className="text-xs px-3 py-1.5 rounded-full bg-white border border-gray-300 hover:border-pitch-700 hover:bg-pitch-50 text-gray-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed text-left focus-visible:ring-2 focus-visible:ring-pitch-800"
          >
            {ex.label}
          </button>
        ))}
      </div>
    </div>
  );
};
