import React from 'react';
import { BookOpen, ShieldCheck, Scale } from 'lucide-react';

interface HeaderProps {
  isBackendConnected?: boolean;
}

export const Header: React.FC<HeaderProps> = ({ isBackendConnected = true }) => {
  return (
    <header className="bg-pitch-800 text-white border-b border-pitch-900 shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Logo & Identity */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gold-500/20 border border-gold-500 flex items-center justify-center text-gold-500 shadow-inner">
              <Scale className="w-6 h-6" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white font-serif">CricketIQ</h1>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gold-500 text-pitch-900 uppercase tracking-wider">
                  Official Rules Intelligence
                </span>
              </div>
              <p className="text-xs text-pitch-100">
                Authoritative reference for ICC Playing Conditions & MCC Laws of Cricket
              </p>
            </div>
          </div>

          {/* Authoritative Badges & Status */}
          <div className="flex items-center flex-wrap gap-2 text-xs">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-pitch-900/60 border border-pitch-700 text-pitch-100">
              <BookOpen className="w-3.5 h-3.5 text-gold-500" aria-hidden="true" />
              <span>MCC 2017 Code (2026 Ed.)</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-pitch-900/60 border border-pitch-700 text-pitch-100">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" aria-hidden="true" />
              <span>ICC Playing Conditions (Oct 2026)</span>
            </div>
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border ${
                isBackendConnected
                  ? 'bg-emerald-950/60 border-emerald-600 text-emerald-300'
                  : 'bg-rose-950/60 border-rose-600 text-rose-300'
              }`}
              title={isBackendConnected ? 'Connected to local SQLite/FTS5 rule store' : 'Backend offline'}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isBackendConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'
                }`}
                aria-hidden="true"
              />
              <span>{isBackendConnected ? 'Corpus Ready (11,008 Clauses)' : 'Offline'}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
