'use client';

import React, { useState, useEffect } from 'react';
import { StatusIndicator } from '../components/StatusIndicator';
import { ChatPanel } from '../components/ChatPanel';
import { EvidenceLogViewer } from '../components/EvidenceLogViewer';
import { MetricsCharts } from '../components/MetricsCharts';
import { McpConfigModal } from '../components/McpConfigModal';
import {
  FileText,
  BarChart2,
  Network,
  Server,
  RefreshCw,
  Activity,
  Database,
  AlertTriangle,
  Sparkles,
  ShieldAlert
} from 'lucide-react';

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

  const totalLogs = (clusterInfo.total_indexed_logs || 0).toLocaleString();

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-[#090d16] text-slate-100">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
                <span>LOGCCINO</span>
                <span className="text-indigo-400 font-semibold text-xs tracking-wider">ENTERPRISE</span>
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                v0.3.0 PROD
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Autonomous SRE Observability & Distributed Big Data Intelligence</p>
          </div>
        </div>

        <StatusIndicator
          clusterStatus={clusterInfo.status || 'HEALTHY'}
          opensearchConnected={Boolean(clusterInfo.opensearch_connected)}
        />
      </header>

      <!-- KPI Executive Metrics Bar -->
      <section className="border-b border-slate-800 bg-slate-900/40 px-6 py-3">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-900 p-3.5 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <Activity className="w-3.5 h-3.5 text-indigo-400" />
                <span>전사 서비스 가용성 (SLO)</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-emerald-400">99.70%</span>
                <span className="text-[11px] text-slate-400">목표 99.90%</span>
              </div>
              <p className="text-[10px] text-amber-400 font-mono mt-0.5">⚠️ Error Budget 잔여: 70% | MTTR: 4.2m</p>
            </div>
          </div>

          <div className="bg-slate-900 p-3.5 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <Database className="w-3.5 h-3.5 text-blue-400" />
                <span>24H 인제스천 볼륨</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-white">{totalLogs} docs</span>
                <span className="text-[11px] text-slate-400 font-mono">18.2 eps</span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono mt-0.5">인덱스: logccino-logs-* | Hot Tier</p>
            </div>
          </div>

          <div className="bg-slate-900 p-3.5 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                <span>임계치 초과 서비스</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-rose-400">1 경고, 1 주의</span>
                <span className="text-[11px] text-slate-400">총 3개 서비스</span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono mt-0.5">최대 이상: notification-service (2.87%)</p>
            </div>
          </div>

          <div className="bg-slate-900 p-3.5 rounded-lg border border-slate-800 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                <span>자율형 SRE 에이전트</span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl font-bold font-mono text-purple-400">OPERATIONAL</span>
                <span className="text-[11px] text-slate-400 font-mono">gpt-6-luna</span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono mt-0.5">PPL 파이프라인 컴파일러 & RCA 엔진 가동</p>
            </div>
          </div>
        </div>
      </section>

      {/* Main Grid */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6">
        {/* Left Column: SRE Incident Console (7 cols) */}
        <section className="lg:col-span-7 flex flex-col min-h-[580px]">
          <ChatPanel
            onEvidenceReceived={(logs) => {
              setEvidenceLogs(logs);
              setActiveTab('evidence');
            }}
            onAnalysisDone={fetchOverview}
          />
        </section>

        {/* Right Column: Evidence & Telemetry (5 cols) */}
        <section className="lg:col-span-5 flex flex-col gap-6">
          <div className="flex-1 bg-slate-900 rounded-xl border border-slate-800 shadow-xl flex flex-col overflow-hidden min-h-[460px]">
            {/* Tabs Header */}
            <div className="flex items-center justify-between border-b border-slate-800 px-4 bg-slate-950/40">
              <div className="flex">
                <button
                  onClick={() => setActiveTab('evidence')}
                  className={`px-3.5 py-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition ${
                    activeTab === 'evidence'
                      ? 'border-indigo-500 text-indigo-300'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" /> 근거 로그 ({evidenceLogs.length})
                </button>
                <button
                  onClick={() => setActiveTab('charts')}
                  className={`px-3.5 py-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition ${
                    activeTab === 'charts'
                      ? 'border-indigo-500 text-indigo-300'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <BarChart2 className="w-3.5 h-3.5" /> 시계열 텔레메트리
                </button>
                <button
                  onClick={() => setActiveTab('mcp')}
                  className={`px-3.5 py-3 text-xs font-semibold border-b-2 flex items-center gap-1.5 transition ${
                    activeTab === 'mcp'
                      ? 'border-indigo-500 text-indigo-300'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Network className="w-3.5 h-3.5" /> MCP 게이트웨이
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

          {/* Infrastructure Matrix Card */}
          <div className="bg-slate-900 rounded-xl border border-slate-800 p-4 shadow-xl">
            <h3 className="text-xs font-semibold text-slate-300 mb-3 flex items-center justify-between border-b border-slate-800/80 pb-2">
              <span className="flex items-center gap-1.5 font-bold uppercase tracking-wider">
                <Server className="w-3.5 h-3.5 text-indigo-400" /> 분산 클러스터 인프라 매트릭스
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {clusterInfo.cluster_name || 'logccino-cluster'}
              </span>
            </h3>
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">클러스터 상태</span>
                <span className="text-sm font-bold text-emerald-400 font-mono">
                  {(clusterInfo.status || 'GREEN').toUpperCase()}
                </span>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">활성 노드 / 샤드</span>
                <span className="text-sm font-bold text-slate-100 font-mono">
                  {clusterInfo.number_of_nodes || 1} Node / 1 Shard
                </span>
              </div>
              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">관제 서비스 수</span>
                <span className="text-sm font-bold text-indigo-400 font-mono">
                  {servicesSummary.length || 3} Services
                </span>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
