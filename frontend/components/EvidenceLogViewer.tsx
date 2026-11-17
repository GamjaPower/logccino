'use client';

import React, { useState } from 'react';
import { FileJson, X } from 'lucide-react';

interface LogItem {
  '@timestamp'?: string;
  service?: string;
  level?: string;
  message?: string;
  host?: string;
  trace_id?: string;
  [key: string]: any;
}

interface Props {
  logs: LogItem[];
}

export function EvidenceLogViewer({ logs }: Props) {
  const [selectedLog, setSelectedLog] = useState<LogItem | null>(null);

  const getBadgeStyle = (level?: string) => {
    switch (level?.toUpperCase()) {
      case 'ERROR':
      case 'FATAL':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      case 'WARN':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'DEBUG':
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <div className="flex-1 p-3 overflow-y-auto space-y-2 text-xs">
        {logs.length === 0 ? (
          <p className="text-slate-500 text-center py-10">
            자연어 질문을 전송하면 OpenSearch에서 수집된 실제 근거 로그가 여기에 표시됩니다.
          </p>
        ) : (
          logs.map((log, idx) => (
            <div
              key={idx}
              onClick={() => setSelectedLog(log)}
              className="p-2.5 bg-slate-950/70 border border-slate-800 rounded-lg hover:border-purple-500/50 cursor-pointer transition flex flex-col gap-1"
            >
              <div className="flex items-center justify-between text-[11px]">
                <span className={`px-1.5 py-0.5 rounded font-mono font-semibold border ${getBadgeStyle(log.level)}`}>
                  {log.level || 'INFO'}
                </span>
                <span className="font-semibold text-slate-300 font-mono">{log.service || 'unknown'}</span>
                <span className="text-slate-500 font-mono">
                  {log['@timestamp'] ? log['@timestamp'].split('T')[1]?.slice(0, 8) : ''}
                </span>
              </div>
              <p className="text-slate-300 truncate font-mono text-[11px]">
                {log.message || JSON.stringify(log)}
              </p>
              {log.trace_id && (
                <span className="text-[10px] text-purple-400 font-mono">trace: {log.trace_id}</span>
              )}
            </div>
          ))
        )}
      </div>

      {/* JSON Modal */}
      {selectedLog && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <div className="px-5 py-3.5 border-b border-slate-800 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <FileJson className="w-4 h-4 text-purple-400" /> 로그 상세 정보 (JSON)
              </h3>
              <button onClick={() => setSelectedLog(null)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 flex-1 overflow-y-auto">
              <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-emerald-400 text-xs overflow-x-auto font-mono">
                {JSON.stringify(selectedLog, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
