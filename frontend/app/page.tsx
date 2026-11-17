'use client';

import React, { useState, useEffect } from 'react';
import { StatusIndicator } from '../components/StatusIndicator';
import { ChatPanel } from '../components/ChatPanel';
import { EvidenceLogViewer } from '../components/EvidenceLogViewer';
import { MetricsCharts } from '../components/MetricsCharts';
import { McpConfigModal } from '../components/McpConfigModal';
import { FileText, BarChart2, Cpu, Database, RefreshCw } from 'lucide-react';

export default function DashboardPage() {
  const [clusterInfo, setClusterInfo] = useState<any>({});
  const [servicesSummary, setServicesSummary] = useState<any[]>([]);
  const [evidenceLogs, setEvidenceLogs] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'evidence' | 'charts' | 'mcp'>('evidence');
  const [mcpEndpoint, setMcpEndpoint] = useState('http://localhost:8000/sse');

  const fetchOverview = async () => {
    try {
      const res = await fetch('/api/v1/admin/overview');
      const data = await res.json();
      if (data.status === 'success') {
        setClusterInfo(data.cluster || {});
        setServicesSummary(data.services_summary || []);
      }
    } catch (e) {
      console.error('Failed to fetch overview', e);
    }
  };

  useEffect(() => {
    fetchOverview();
    if (typeof window !== 'undefined') {
      setMcpEndpoint(window.location.origin + '/sse');
    }
  }, []);

  return (
    <div className="flex-1 flex flex-col min-h-screen">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-purple-500/20">
            ☕
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-lg tracking-tight text-white">Logccino</h1>
              <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Agent-Native
              </span>
            </div>
            <p className="text-xs text-slate-400">Big Data & Real-Time Intelligence Backend</p>
          </div>
        </div>

        <StatusIndicator
          clusterStatus={clusterInfo.status || 'Checking'}
          opensearchConnected={Boolean(clusterInfo.opensearch_connected)}
        />
      </header>

      {/* Main Grid */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6">
        {/* Left Column: Chat AI (7 cols) */}
        <section className="lg:col-span-7 flex flex-col min-h-[580px]">
          <ChatPanel
            onEvidenceReceived={(logs) => {
              setEvidenceLogs(logs);
              setActiveTab('evidence');
            }}
            onAnalysisDone={fetchOverview}
          />
        </section>

        {/* Right Column: Evidence & Visualization (5 cols) */}
        <section className="lg:col-span-5 flex flex-col gap-6">
          <div className="flex-1 bg-slate-900 rounded-xl border border-slate-800 shadow-xl flex flex-col overflow-hidden min-h-[420px]">
            {/* Tabs Header */}
            <div className="flex items-center justify-between border-b border-slate-800 px-4 bg-slate-950/40">
              <div className="flex">
                <button
                  onClick={() => setActiveTab('evidence')}
                  className={`px-3.5 py-3 text-xs font-medium border-b-2 flex items-center gap-1.5 transition ${
                    activeTab === 'evidence'
                      ? 'border-purple-500 text-purple-300'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" /> 근거 로그 ({evidenceLogs.length})
                </button>
                <button
                  onClick={() => setActiveTab('charts')}
                  className={`px-3.5 py-3 text-xs font-medium border-b-2 flex items-center gap-1.5 transition ${
                    activeTab === 'charts'
                      ? 'border-purple-500 text-purple-300'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <BarChart2 className="w-3.5 h-3.5" /> 시계열 & 통계
                </button>
                <button
                  onClick={() => setActiveTab('mcp')}
                  className={`px-3.5 py-3 text-xs font-medium border-b-2 flex items-center gap-1.5 transition ${
                    activeTab === 'mcp'
                      ? 'border-purple-500 text-purple-300'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Cpu className="w-3.5 h-3.5" /> MCP 설정
                </button>
              </div>

              <button
                onClick={fetchOverview}
                className="text-slate-400 hover:text-white text-xs p-1"
                title="새로고침"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Tab Contents */}
            {activeTab === 'evidence' && <EvidenceLogViewer logs={evidenceLogs} />}
            {activeTab === 'charts' && <MetricsCharts services={servicesSummary} />}
            {activeTab === 'mcp' && <McpConfigModal mcpEndpoint={mcpEndpoint} />}
          </div>

          {/* Cluster Summary Card */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 shadow-xl">
            <h3 className="text-xs font-semibold text-slate-300 mb-3 flex items-center justify-between">
              <span className="flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-purple-400" /> OpenSearch 분산 클러스터 요약
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {clusterInfo.cluster_name || 'logccino-cluster'}
              </span>
            </h3>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400 block mb-0.5">총 인덱싱 로그</span>
                <span className="text-base font-bold text-white font-mono">
                  {(clusterInfo.total_indexed_logs || 0).toLocaleString()}
                </span>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400 block mb-0.5">클러스터 노드</span>
                <span className="text-base font-bold text-emerald-400 font-mono">
                  {clusterInfo.number_of_nodes || 1}
                </span>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[11px] text-slate-400 block mb-0.5">마이크로서비스</span>
                <span className="text-base font-bold text-indigo-400 font-mono">
                  {servicesSummary.length || 3}
                </span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
