"""
Logccino Web Dashboard Router
Kibana를 대체하는 자체 대화형 AI 로그 분석 및 모니터링 대시보드
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web Dashboard"])

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ko" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Logccino | Agent-Native Big Data Intelligence</title>
  <!-- Tailwind CSS & Fonts -->
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#f5f3ff', 500: '#8b5cf6', 600: '#7c3aed', 700: '#6d28d9', 900: '#4c1d95' },
            darkbg: '#0f172a',
            darkcard: '#1e293b',
            darkborder: '#334155'
          }
        }
      }
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Pretendard:wght@300;400;500;600;700&display=swap');
    body { font-family: 'Pretendard', sans-serif; }
    code, pre { font-family: 'JetBrains Mono', monospace; }
    .scrollbar-thin::-webkit-scrollbar { width: 6px; height: 6px; }
    .scrollbar-thin::-webkit-scrollbar-track { background: #0f172a; }
    .scrollbar-thin::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
  </style>
</head>
<body class="bg-darkbg text-slate-100 min-h-screen flex flex-col">

  <!-- Header -->
  <header class="border-b border-darkborder bg-darkcard/80 backdrop-blur sticky top-0 z-40 px-6 py-3 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-brand-500/20">
        ☕
      </div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="font-bold text-lg tracking-tight text-white">Logccino</h1>
          <span class="text-[10px] uppercase font-semibold px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">Agent-Native</span>
        </div>
        <p class="text-xs text-slate-400">Big Data & Real-Time Intelligence Backend</p>
      </div>
    </div>

    <!-- Status Indicators -->
    <div class="flex items-center gap-4 text-xs">
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900/60 border border-darkborder">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" id="os-indicator"></span>
        <span class="text-slate-400">OpenSearch:</span>
        <span class="font-medium text-emerald-400" id="os-status">Checking...</span>
      </div>

      <div class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-slate-900/60 border border-darkborder">
        <i data-lucide="radio" class="w-3.5 h-3.5 text-brand-400"></i>
        <span class="text-slate-400">MCP SSE:</span>
        <span class="font-mono text-slate-200">/sse</span>
        <button onclick="copyToClipboard(window.location.origin + '/sse')" class="text-slate-400 hover:text-white" title="복사">
          <i data-lucide="copy" class="w-3 h-3"></i>
        </button>
      </div>

      <a href="/docs" target="_blank" class="flex items-center gap-1 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition">
        <i data-lucide="book-open" class="w-3.5 h-3.5"></i>
        <span>API Docs</span>
      </a>
    </div>
  </header>

  <!-- Main Grid -->
  <main class="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-hidden">

    <!-- Left Column: Chat AI Analyst (7 cols) -->
    <section class="lg:col-span-7 flex flex-col bg-darkcard rounded-xl border border-darkborder shadow-xl overflow-hidden">
      <!-- Chat Header -->
      <div class="px-5 py-3.5 border-b border-darkborder bg-slate-900/40 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <i data-lucide="sparkles" class="w-4 h-4 text-brand-400"></i>
          <h2 class="text-sm font-semibold text-white">AI 자연어 로그 분석가 (Natural & Chat Analyst)</h2>
        </div>
        <button onclick="clearChat()" class="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition">
          <i data-lucide="rotate-ccw" class="w-3 h-3"></i> 대화 초기화
        </button>
      </div>

      <!-- Messages Stream -->
      <div id="chat-messages" class="flex-1 p-5 overflow-y-auto space-y-4 scrollbar-thin max-h-[calc(100vh-280px)]">
        <!-- Initial Welcome Message -->
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-full bg-brand-600/30 border border-brand-500/40 flex items-center justify-center text-sm shrink-0">
            🤖
          </div>
          <div class="bg-slate-900/80 border border-darkborder rounded-2xl rounded-tl-none p-4 text-sm text-slate-200 max-w-[90%] leading-relaxed">
            <p class="font-medium text-white mb-1.5">안녕하세요! Logccino AI 로그 분석가입니다. ☕</p>
            <p class="text-slate-300 text-xs mb-3">복잡한 쿼리 없이 자연어로 질문하시면 분산 OpenSearch 클러스터에서 실시간 로그를 검색·집계하여 원인과 조치 방안을 분석해 드립니다.</p>
            <div class="flex flex-wrap gap-1.5 pt-1">
              <button onclick="sendQuickPrompt('어제 결제 모듈에서 발생한 타임아웃 에러 원인 분석해줘')" class="text-xs bg-slate-800 hover:bg-brand-600/30 border border-darkborder hover:border-brand-500/50 text-slate-300 hover:text-brand-300 px-2.5 py-1 rounded-full transition">
                💳 결제 타임아웃 원인 분석
              </button>
              <button onclick="sendQuickPrompt('서비스별 24시간 로그 볼륨과 에러율 통계 표로 보여줘')" class="text-xs bg-slate-800 hover:bg-brand-600/30 border border-darkborder hover:border-brand-500/50 text-slate-300 hover:text-brand-300 px-2.5 py-1 rounded-full transition">
                📊 서비스별 에러율 통계
              </button>
              <button onclick="sendQuickPrompt('notification-service에서 발생하는 에러 패턴과 스택트레이스 알려줘')" class="text-xs bg-slate-800 hover:bg-brand-600/30 border border-darkborder hover:border-brand-500/50 text-slate-300 hover:text-brand-300 px-2.5 py-1 rounded-full transition">
                🔔 알림 서비스 에러 진단
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Suggestion Chips Container -->
      <div id="chips-container" class="px-5 py-2 border-t border-darkborder/50 bg-slate-900/30 flex items-center gap-2 overflow-x-auto scrollbar-thin hidden">
        <span class="text-[11px] text-slate-400 shrink-0 flex items-center gap-1">
          <i data-lucide="lightbulb" class="w-3 h-3 text-amber-400"></i> 추천 질문:
        </span>
        <div id="chips-list" class="flex gap-1.5 shrink-0"></div>
      </div>

      <!-- Input Form -->
      <div class="p-4 border-t border-darkborder bg-slate-900/60">
        <form onsubmit="handleChatSubmit(event)" class="flex gap-2">
          <input type="text" id="chat-input" placeholder="로그 질문 입력 (예: 'auth-service 최근 로그인 실패 원인 알려줘')..."
                 class="flex-1 bg-slate-950 border border-darkborder rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-brand-500 transition placeholder:text-slate-500">
          <button type="submit" id="send-btn" class="px-4 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium flex items-center gap-1.5 transition disabled:opacity-50">
            <i data-lucide="send" class="w-4 h-4"></i>
            <span>전송</span>
          </button>
        </form>
      </div>
    </section>

    <!-- Right Column: Evidence & Visualization (5 cols) -->
    <section class="lg:col-span-5 flex flex-col gap-6">

      <!-- Top Tab Panel: Evidence Logs & Charts -->
      <div class="flex-1 bg-darkcard rounded-xl border border-darkborder shadow-xl flex flex-col overflow-hidden">
        <!-- Tabs -->
        <div class="flex items-center justify-between border-b border-darkborder px-4 bg-slate-900/40">
          <div class="flex">
            <button onclick="switchTab('evidence')" id="tab-evidence" class="px-3.5 py-3 text-xs font-medium border-b-2 border-brand-500 text-brand-300 flex items-center gap-1.5">
              <i data-lucide="file-text" class="w-3.5 h-3.5"></i> 근거 로그 (<span id="evidence-count">0</span>)
            </button>
            <button onclick="switchTab('charts')" id="tab-charts" class="px-3.5 py-3 text-xs font-medium border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5">
              <i data-lucide="bar-chart-2" class="w-3.5 h-3.5"></i> 시계열 & 통계
            </button>
            <button onclick="switchTab('mcp')" id="tab-mcp" class="px-3.5 py-3 text-xs font-medium border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5">
              <i data-lucide="cpu" class="w-3.5 h-3.5"></i> MCP 설정
            </button>
          </div>
          <button onclick="refreshOverview()" class="text-slate-400 hover:text-white text-xs p-1" title="새로고침">
            <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
          </button>
        </div>

        <!-- Tab 1: Evidence Log Viewer -->
        <div id="content-evidence" class="flex-1 p-4 overflow-y-auto scrollbar-thin max-h-[380px]">
          <div id="evidence-list" class="space-y-2 text-xs">
            <p class="text-slate-500 text-center py-8">자연어 분석 질문을 전송하면 OpenSearch에서 수집된 실제 근거 로그가 여기에 표시됩니다.</p>
          </div>
        </div>

        <!-- Tab 2: Charts Panel -->
        <div id="content-charts" class="flex-1 p-4 hidden flex flex-col gap-4 overflow-y-auto max-h-[380px] scrollbar-thin">
          <div class="bg-slate-950/60 p-3 rounded-lg border border-darkborder">
            <h3 class="text-xs font-medium text-slate-300 mb-2 flex items-center gap-1.5">
              <i data-lucide="activity" class="w-3 h-3 text-brand-400"></i> 서비스별 로그 볼륨 & 에러 현황
            </h3>
            <div id="chart-services" class="w-full h-44"></div>
          </div>
          <div class="bg-slate-950/60 p-3 rounded-lg border border-darkborder">
            <h3 class="text-xs font-medium text-slate-300 mb-2 flex items-center gap-1.5">
              <i data-lucide="pie-chart" class="w-3 h-3 text-indigo-400"></i> 로그 레벨 분포 (INFO vs ERROR)
            </h3>
            <div id="chart-levels" class="w-full h-40"></div>
          </div>
        </div>

        <!-- Tab 3: MCP Agent Configs -->
        <div id="content-mcp" class="flex-1 p-4 hidden overflow-y-auto max-h-[380px] scrollbar-thin text-xs space-y-4">
          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-semibold text-slate-200">Claude Desktop 설정 (`claude_desktop_config.json`)</span>
              <button onclick="copySnippet('claude-cfg')" class="text-brand-400 hover:text-brand-300 flex items-center gap-1">
                <i data-lucide="copy" class="w-3 h-3"></i> 복사
              </button>
            </div>
            <pre id="claude-cfg" class="bg-slate-950 p-3 rounded border border-darkborder text-slate-300 overflow-x-auto text-[11px]"></pre>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-semibold text-slate-200">Google Antigravity / Cursor 설정</span>
              <button onclick="copySnippet('cursor-cfg')" class="text-brand-400 hover:text-brand-300 flex items-center gap-1">
                <i data-lucide="copy" class="w-3 h-3"></i> 복사
              </button>
            </div>
            <pre id="cursor-cfg" class="bg-slate-950 p-3 rounded border border-darkborder text-slate-300 overflow-x-auto text-[11px]"></pre>
          </div>
        </div>
      </div>

      <!-- Bottom Card: Cluster Overview Metrics -->
      <div class="bg-darkcard rounded-xl border border-darkborder p-4 shadow-xl">
        <h3 class="text-xs font-semibold text-slate-300 mb-3 flex items-center justify-between">
          <span class="flex items-center gap-1.5"><i data-lucide="database" class="w-3.5 h-3.5 text-brand-400"></i> OpenSearch 분산 클러스터 요약</span>
          <span class="text-[10px] text-slate-400 font-mono" id="cluster-name">-</span>
        </h3>
        <div class="grid grid-cols-3 gap-3 text-center">
          <div class="bg-slate-900/60 p-2.5 rounded-lg border border-darkborder">
            <span class="text-[11px] text-slate-400 block mb-0.5">총 인덱싱 로그</span>
            <span class="text-base font-bold text-white font-mono" id="total-logs">-</span>
          </div>
          <div class="bg-slate-900/60 p-2.5 rounded-lg border border-darkborder">
            <span class="text-[11px] text-slate-400 block mb-0.5">활성 노드 수</span>
            <span class="text-base font-bold text-emerald-400 font-mono" id="nodes-count">-</span>
          </div>
          <div class="bg-slate-900/60 p-2.5 rounded-lg border border-darkborder">
            <span class="text-[11px] text-slate-400 block mb-0.5">마이크로서비스</span>
            <span class="text-base font-bold text-indigo-400 font-mono" id="services-count">-</span>
          </div>
        </div>
      </div>

    </section>
  </main>

  <!-- Log Detail Modal -->
  <div id="log-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-darkcard border border-darkborder rounded-xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
      <div class="px-5 py-3.5 border-b border-darkborder flex items-center justify-between">
        <h3 class="text-sm font-semibold text-white flex items-center gap-2">
          <i data-lucide="file-json" class="w-4 h-4 text-brand-400"></i> 로그 상세 정보 (JSON)
        </h3>
        <button onclick="closeModal()" class="text-slate-400 hover:text-white">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>
      <div class="p-4 flex-1 overflow-y-auto scrollbar-thin">
        <pre id="modal-json" class="bg-slate-950 p-4 rounded-lg border border-darkborder text-emerald-400 text-xs overflow-x-auto"></pre>
      </div>
    </div>
  </div>

  <script>
    let conversationHistory = [];
    let currentLogsContext = "";
    let evidenceLogs = [];
    let servicesChartInstance = null;
    let levelsChartInstance = null;

    // 초기화
    document.addEventListener("DOMContentLoaded", () => {
      lucide.createIcons();
      refreshOverview();
      loadMCPConfigs();
    });

    async function refreshOverview() {
      try {
        const res = await fetch('/api/v1/admin/overview');
        const data = await res.json();
        if (data.status === 'success') {
          const cluster = data.cluster || {};
          document.getElementById('os-status').textContent = cluster.status === 'green' || cluster.opensearch_connected ? 'Connected' : 'Degraded';
          document.getElementById('cluster-name').textContent = cluster.cluster_name || 'logccino-cluster';
          document.getElementById('total-logs').textContent = (cluster.total_indexed_logs || 0).toLocaleString();
          document.getElementById('nodes-count').textContent = cluster.number_of_nodes || 1;
          document.getElementById('services-count').textContent = data.services_count || 3;

          renderCharts(data.services_summary || []);
        }
      } catch (e) {
        document.getElementById('os-status').textContent = 'Disconnected';
        document.getElementById('os-indicator').className = 'w-2 h-2 rounded-full bg-red-500';
      }
    }

    function renderCharts(services) {
      if (!services || services.length === 0) return;

      const chartDom1 = document.getElementById('chart-services');
      if (chartDom1) {
        if (!servicesChartInstance) servicesChartInstance = echarts.init(chartDom1, 'dark');
        servicesChartInstance.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'axis' },
          grid: { top: 20, right: 20, bottom: 25, left: 50 },
          xAxis: { type: 'category', data: services.map(s => s.service), axisLabel: { fontSize: 10 } },
          yAxis: { type: 'value', axisLabel: { fontSize: 10 } },
          series: [
            { name: 'Total Logs', type: 'bar', data: services.map(s => s.total_logs), itemStyle: { color: '#6366f1' } },
            { name: 'Errors', type: 'bar', data: services.map(s => s.error_count), itemStyle: { color: '#ef4444' } }
          ]
        });
      }

      const chartDom2 = document.getElementById('chart-levels');
      if (chartDom2) {
        if (!levelsChartInstance) levelsChartInstance = echarts.init(chartDom2, 'dark');
        const totalLogs = services.reduce((acc, s) => acc + (s.total_logs || 0), 0);
        const totalErrors = services.reduce((acc, s) => acc + (s.error_count || 0), 0);
        const totalInfos = Math.max(0, totalLogs - totalErrors);

        levelsChartInstance.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'item' },
          series: [{
            type: 'pie',
            radius: ['45%', '75%'],
            data: [
              { value: totalInfos, name: 'INFO', itemStyle: { color: '#10b981' } },
              { value: totalErrors, name: 'ERROR', itemStyle: { color: '#ef4444' } }
            ],
            label: { show: true, fontSize: 11, formatter: '{b}: {d}%' }
          }]
        });
      }
    }

    async function loadMCPConfigs() {
      try {
        const res = await fetch('/api/v1/admin/mcp/config');
        const data = await res.json();
        const claudeSnippet = data.claude_desktop_remote_k8s_aws || {};
        document.getElementById('claude-cfg').textContent = JSON.stringify(claudeSnippet, null, 2);

        const cursorSnippet = {
          "mcpServers": {
            "logccino": {
              "url": window.location.origin + "/sse"
            }
          }
        };
        document.getElementById('cursor-cfg').textContent = JSON.stringify(cursorSnippet, null, 2);
      } catch (e) {
        console.error("Failed to load MCP config", e);
      }
    }

    async function handleChatSubmit(e) {
      if (e) e.preventDefault();
      const input = document.getElementById('chat-input');
      const question = input.value.trim();
      if (!question) return;

      input.value = '';
      appendUserMessage(question);

      const sendBtn = document.getElementById('send-btn');
      sendBtn.disabled = true;

      // Loading bubble
      const loadingId = appendLoadingMessage();

      try {
        if (conversationHistory.length <= 1) {
          // 1단계: Natural Analysis 엔드포인트 호출
          const res = await fetch('/api/v1/analyze/natural', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: question, sample_size: 30 })
          });
          const data = await res.json();
          removeLoadingMessage(loadingId);

          if (data.status === 'success') {
            appendAssistantMessage(data.analysis_report);
            conversationHistory.push({ role: 'assistant', content: data.analysis_report });
            currentLogsContext = JSON.stringify(data.evidence_logs || []).slice(0, 4000);

            // 근거 로그 업데이트
            renderEvidenceLogs(data.evidence_logs || []);
            extractFollowupChips(data.analysis_report);
          } else {
            appendAssistantMessage("오류가 발생했습니다: " + (data.detail || '알 수 없는 에러'));
          }
        } else {
          // 후속 대화: Chat Endpoint 호출
          const res = await fetch('/api/v1/analyze/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              question: question,
              conversation_history: conversationHistory,
              logs_context: currentLogsContext
            })
          });
          const data = await res.json();
          removeLoadingMessage(loadingId);

          appendAssistantMessage(data.response);
          conversationHistory.push({ role: 'assistant', content: data.response });
          extractFollowupChips(data.response);
        }
      } catch (err) {
        removeLoadingMessage(loadingId);
        appendAssistantMessage("서버 통신 실패: " + err.message);
      } finally {
        sendBtn.disabled = false;
        refreshOverview();
      }
    }

    function appendUserMessage(text) {
      conversationHistory.push({ role: 'user', content: text });
      const container = document.getElementById('chat-messages');
      const msgDiv = document.createElement('div');
      msgDiv.className = 'flex items-start gap-3 justify-end';
      msgDiv.innerHTML = `
        <div class="bg-brand-600 text-white rounded-2xl rounded-tr-none px-4 py-2.5 text-sm max-w-[85%] shadow-md">
          ${escapeHtml(text)}
        </div>
        <div class="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-sm shrink-0">
          👤
        </div>
      `;
      container.appendChild(msgDiv);
      container.scrollTop = container.scrollHeight;
    }

    function appendAssistantMessage(markdown) {
      const container = document.getElementById('chat-messages');
      const msgDiv = document.createElement('div');
      msgDiv.className = 'flex items-start gap-3';
      const renderedHtml = marked.parse(markdown);
      msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-brand-600/30 border border-brand-500/40 flex items-center justify-center text-sm shrink-0">
          🤖
        </div>
        <div class="bg-slate-900/90 border border-darkborder rounded-2xl rounded-tl-none p-4 text-sm text-slate-200 max-w-[90%] shadow-lg prose prose-invert prose-sm leading-relaxed">
          ${renderedHtml}
        </div>
      `;
      container.appendChild(msgDiv);
      container.scrollTop = container.scrollHeight;
      lucide.createIcons();
    }

    function appendLoadingMessage() {
      const id = 'loading-' + Date.now();
      const container = document.getElementById('chat-messages');
      const msgDiv = document.createElement('div');
      msgDiv.id = id;
      msgDiv.className = 'flex items-start gap-3';
      msgDiv.innerHTML = `
        <div class="w-8 h-8 rounded-full bg-brand-600/30 border border-brand-500/40 flex items-center justify-center text-sm shrink-0">
          🤖
        </div>
        <div class="bg-slate-900/90 border border-darkborder rounded-2xl rounded-tl-none px-4 py-3 text-sm text-slate-400 flex items-center gap-2">
          <i data-lucide="loader-2" class="w-4 h-4 animate-spin text-brand-400"></i>
          <span>OpenSearch 로그 분석 중...</span>
        </div>
      `;
      container.appendChild(msgDiv);
      container.scrollTop = container.scrollHeight;
      lucide.createIcons();
      return id;
    }

    function removeLoadingMessage(id) {
      const el = document.getElementById(id);
      if (el) el.remove();
    }

    function renderEvidenceLogs(logs) {
      evidenceLogs = logs;
      document.getElementById('evidence-count').textContent = logs.length;
      const listDom = document.getElementById('evidence-list');
      if (logs.length === 0) {
        listDom.innerHTML = '<p class="text-slate-500 text-center py-8">매칭된 로그가 없습니다.</p>';
        return;
      }

      listDom.innerHTML = logs.map((log, idx) => {
        const lvl = log.level || 'INFO';
        const badgeColor = lvl === 'ERROR' ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                           lvl === 'WARN' ? 'bg-amber-500/20 text-amber-400 border-amber-500/30' :
                           'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
        return `
          <div onclick="openModal(${idx})" class="p-2.5 bg-slate-950/70 border border-darkborder rounded-lg hover:border-brand-500/50 cursor-pointer transition flex flex-col gap-1">
            <div class="flex items-center justify-between text-[11px]">
              <span class="px-1.5 py-0.5 rounded font-mono font-semibold border ${badgeColor}">${lvl}</span>
              <span class="font-semibold text-slate-300 font-mono">${escapeHtml(log.service || 'unknown')}</span>
              <span class="text-slate-500 font-mono">${log['@timestamp'] ? log['@timestamp'].split('T')[1].slice(0, 8) : ''}</span>
            </div>
            <p class="text-slate-300 truncate font-mono text-[11px]">${escapeHtml(log.message || '')}</p>
          </div>
        `;
      }).join('');
    }

    function extractFollowupChips(text) {
      const chipsContainer = document.getElementById('chips-container');
      const chipsList = document.getElementById('chips-list');
      const regex = /["'](.*?[?？])["']/g;
      let match;
      const questions = [];
      while ((match = regex.exec(text)) !== null) {
        if (match[1].length > 5 && match[1].length < 40) questions.push(match[1]);
      }

      if (questions.length > 0) {
        chipsList.innerHTML = questions.slice(0, 3).map(q => `
          <button onclick="sendQuickPrompt('${escapeHtml(q)}')" class="text-xs bg-slate-800 hover:bg-brand-600/30 border border-darkborder hover:border-brand-500/50 text-slate-300 hover:text-brand-300 px-2.5 py-0.5 rounded-full transition whitespace-nowrap">
            ${escapeHtml(q)}
          </button>
        `).join('');
        chipsContainer.classList.remove('hidden');
      }
    }

    function sendQuickPrompt(prompt) {
      document.getElementById('chat-input').value = prompt;
      handleChatSubmit();
    }

    function switchTab(tab) {
      ['evidence', 'charts', 'mcp'].forEach(t => {
        document.getElementById(`content-${t}`).classList.add('hidden');
        document.getElementById(`tab-${t}`).className = 'px-3.5 py-3 text-xs font-medium border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5';
      });
      document.getElementById(`content-${tab}`).classList.remove('hidden');
      document.getElementById(`tab-${tab}`).className = 'px-3.5 py-3 text-xs font-medium border-b-2 border-brand-500 text-brand-300 flex items-center gap-1.5';

      if (tab === 'charts') {
        setTimeout(() => {
          if (servicesChartInstance) servicesChartInstance.resize();
          if (levelsChartInstance) levelsChartInstance.resize();
        }, 50);
      }
    }

    function openModal(idx) {
      const log = evidenceLogs[idx];
      document.getElementById('modal-json').textContent = JSON.stringify(log, null, 2);
      document.getElementById('log-modal').classList.remove('hidden');
    }

    function closeModal() {
      document.getElementById('log-modal').classList.add('hidden');
    }

    function clearChat() {
      conversationHistory = [];
      document.getElementById('chat-messages').innerHTML = '';
      document.getElementById('chips-container').classList.add('hidden');
      appendAssistantMessage("대화가 초기화되었습니다. 새로운 질문을 입력해 주세요! ☕");
    }

    function copyToClipboard(text) {
      navigator.clipboard.writeText(text);
      alert("클립보드에 복사되었습니다: " + text);
    }

    function copySnippet(id) {
      const text = document.getElementById(id).textContent;
      navigator.clipboard.writeText(text);
      alert("설정이 클립보드에 복사되었습니다!");
    }

    function escapeHtml(str) {
      return (str || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }
  </script>
</body>
</html>
"""

@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/ui", response_class=HTMLResponse)
async def get_dashboard():
    """자체 제작 관리 및 AI 대화형 로그 분석 웹 대시보드"""
    return HTMLResponse(content=DASHBOARD_HTML)
