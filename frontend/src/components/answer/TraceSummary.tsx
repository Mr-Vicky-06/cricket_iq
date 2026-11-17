import React from 'react';
import { Clock, Cpu, FileText, GitCompare } from 'lucide-react';
import type { QueryTrace } from '../../api/types';

interface TraceSummaryProps {
  trace: QueryTrace;
}

export const TraceSummary: React.FC<TraceSummaryProps> = ({ trace }) => {
  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-[11px] text-gray-600 mt-4">
      <div className="font-semibold text-gray-700 uppercase tracking-wider text-[10px] mb-2 flex items-center justify-between">
        <span>Pipeline Audit Telemetry</span>
        <span className="font-mono text-gray-400">ID: {trace.query_id}</span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-pitch-700" aria-hidden="true" />
          <span>Latency: <strong className="font-mono text-gray-900">{trace.latency_ms.toFixed(1)}ms</strong></span>
        </div>

        <div className="flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-pitch-700" aria-hidden="true" />
          <span>Clauses Retrieved: <strong className="font-mono text-gray-900">{trace.retrieval_count}</strong></span>
        </div>

        <div className="flex items-center gap-1.5">
          <Cpu className="w-3.5 h-3.5 text-pitch-700" aria-hidden="true" />
          <span>Model: <strong className="font-mono text-gray-900">{trace.model_used}</strong></span>
        </div>

        <div className="flex items-center gap-1.5">
          <GitCompare className="w-3.5 h-3.5 text-gold-600" aria-hidden="true" />
          <span>Docs: <strong className="font-mono text-gray-900">{trace.applicable_documents.length}</strong></span>
        </div>
      </div>

      {trace.precedence_applied && (
        <div className="mt-2 pt-2 border-t border-gray-200 text-gray-700 font-medium flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-gold-600" aria-hidden="true" />
          <span>Precedence Rule: {trace.precedence_applied}</span>
        </div>
      )}
    </div>
  );
};
