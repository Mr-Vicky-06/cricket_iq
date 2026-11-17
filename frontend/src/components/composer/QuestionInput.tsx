import React, { useRef, useEffect } from 'react';
import { Send, X, Loader2 } from 'lucide-react';

interface QuestionInputProps {
  query: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
  onClear?: () => void;
}

export const QuestionInput: React.FC<QuestionInputProps> = ({
  query,
  onChange,
  onSubmit,
  isLoading,
  onClear,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const charCount = query.length;
  const isTooShort = charCount > 0 && charCount < 3;
  const isTooLong = charCount > 1000;
  const isValid = charCount >= 3 && charCount <= 1000;

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (isValid && !isLoading) {
        onSubmit();
      }
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-300 shadow-sm focus-within:border-pitch-700 focus-within:ring-2 focus-within:ring-pitch-700/20 transition-all p-3">
      <label htmlFor="rules-question-input" className="sr-only">
        Ask a cricket rules question
      </label>
      <div className="relative">
        <textarea
          ref={textareaRef}
          id="rules-question-input"
          rows={2}
          value={query}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a cricket rules question (e.g. Can a batter be out on a free hit in T20I?)..."
          disabled={isLoading}
          className="w-full resize-none text-sm text-gray-900 placeholder-gray-400 focus:outline-none disabled:bg-gray-50 leading-relaxed pr-10"
        />
        {query.length > 0 && !isLoading && onClear && (
          <button
            type="button"
            onClick={onClear}
            className="absolute right-0 top-0 text-gray-400 hover:text-gray-600 p-1 rounded-full"
            aria-label="Clear question text"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-gray-100 pt-2 mt-1">
        <div className="flex items-center gap-3 text-xs">
          <span
            className={`${
              isTooLong
                ? 'text-rose-600 font-semibold'
                : isTooShort
                ? 'text-amber-600'
                : 'text-gray-400'
            }`}
          >
            {charCount}/1000 characters
          </span>
          <span className="hidden sm:inline text-gray-400">
            Press <kbd className="px-1.5 py-0.5 rounded bg-gray-100 border border-gray-300 text-gray-600 font-mono">Enter</kbd> to search, <kbd className="px-1.5 py-0.5 rounded bg-gray-100 border border-gray-300 text-gray-600 font-mono">Shift+Enter</kbd> for newline
          </span>
        </div>

        <button
          type="button"
          onClick={onSubmit}
          disabled={!isValid || isLoading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-pitch-800 hover:bg-pitch-900 text-white font-medium text-xs transition-colors shadow-sm disabled:opacity-40 disabled:cursor-not-allowed focus-visible:ring-2 focus-visible:ring-pitch-800"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
              <span>Verifying Evidence...</span>
            </>
          ) : (
            <>
              <Send className="w-3.5 h-3.5" aria-hidden="true" />
              <span>Ask CricketIQ</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
