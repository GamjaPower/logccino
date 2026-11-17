'use client';

import React, { useState } from 'react';
import { Copy, Check, Terminal } from 'lucide-react';

interface Props {
  mcpEndpoint: string;
}

export function McpConfigModal({ mcpEndpoint }: Props) {
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const claudeConfig = {
    mcpServers: {
      logccino: {
        url: mcpEndpoint
      }
    }
  };

  const cursorConfig = {
    mcpServers: {
      logccino: {
        url: mcpEndpoint
      }
    }
  };

  const copyText = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="flex-1 p-4 space-y-4 text-xs overflow-y-auto">
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-semibold text-slate-200">Claude Desktop 원격 연동 설정</span>
          <button
            onClick={() => copyText('claude', JSON.stringify(claudeConfig, null, 2))}
            className="text-purple-400 hover:text-purple-300 flex items-center gap-1"
          >
            {copiedKey === 'claude' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>복사</span>
          </button>
        </div>
        <p className="text-[11px] text-slate-400 mb-2">
          `~/.config/Claude/claude_desktop_config.json` 에 붙여넣으세요.
        </p>
        <pre className="bg-slate-950 p-3 rounded border border-slate-800 text-slate-300 overflow-x-auto text-[11px] font-mono">
          {JSON.stringify(claudeConfig, null, 2)}
        </pre>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="font-semibold text-slate-200">Cursor IDE / Antigravity 설정</span>
          <button
            onClick={() => copyText('cursor', JSON.stringify(cursorConfig, null, 2))}
            className="text-purple-400 hover:text-purple-300 flex items-center gap-1"
          >
            {copiedKey === 'cursor' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            <span>복사</span>
          </button>
        </div>
        <pre className="bg-slate-950 p-3 rounded border border-slate-800 text-slate-300 overflow-x-auto text-[11px] font-mono">
          {JSON.stringify(cursorConfig, null, 2)}
        </pre>
      </div>
    </div>
  );
}
