'use client';

import React from 'react';
import { Radio, BookOpen, Copy, Check } from 'lucide-react';

interface StatusProps {
  clusterStatus: string;
  opensearchConnected: boolean;
}

export function StatusIndicator({ clusterStatus, opensearchConnected }: StatusProps) {
  const [copied, setCopied] = React.useState(false);

  const copySse = () => {
    if (typeof window !== 'undefined') {
      navigator.clipboard.writeText(window.location.origin + '/sse');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="flex items-center gap-4 text-xs">
      {/* OpenSearch Indicator */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800">
        <span
          className={`w-2 h-2 rounded-full ${
            opensearchConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
          }`}
        />
        <span className="text-slate-400">OpenSearch:</span>
        <span className={`font-medium ${opensearchConnected ? 'text-emerald-400' : 'text-rose-400'}`}>
          {opensearchConnected ? (clusterStatus || 'Connected') : 'Disconnected'}
        </span>
      </div>

      {/* MCP SSE Endpoint */}
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900 border border-slate-800">
        <Radio className="w-3.5 h-3.5 text-purple-400" />
        <span className="text-slate-400">MCP SSE:</span>
        <span className="font-mono text-slate-200">/sse</span>
        <button
          onClick={copySse}
          className="text-slate-400 hover:text-white transition ml-1"
          title="엔드포인트 URL 복사"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
        </button>
      </div>

      {/* API Docs Link */}
      <a
        href="http://localhost:8000/docs"
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-slate-850 hover:bg-slate-800 text-slate-300 border border-slate-800 transition"
      >
        <BookOpen className="w-3.5 h-3.5" />
        <span>API Docs</span>
      </a>
    </div>
  );
}
