"""
Logccino Enterprise Web Dashboard Router
Enterprise-Grade Distributed Observability & Autonomous SRE Management Console
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Enterprise Web Dashboard"])

ENTERPRISE_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="ko" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Logccino Enterprise | Autonomous SRE Observability & Big Data Intelligence</title>
  <!-- Tailwind CSS, Fonts & Icons -->
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
            enterprise: {
              50: '#f8fafc',
              100: '#f1f5f9',
              500: '#6366f1',
              600: '#4f46e5',
              700: '#4338ca',
              900: '#1e1b4b',
            },
            slatebg: '#090d16',
            panelbg: '#0f172a',
            subpanel: '#151e33',
            bordercolor: '#1e293b',
            accentborder: '#334155'
          }
        }
      }
    }
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&family=Pretendard:wght@400;500;600;700&display=swap');
    body { font-family: 'Inter', 'Pretendard', -apple-system, sans-serif; background-color: #090d16; }
    code, pre, .font-mono { font-family: 'JetBrains Mono', monospace; }
    .scrollbar-thin::-webkit-scrollbar { width: 5px; height: 5px; }
    .scrollbar-thin::-webkit-scrollbar-track { background: #090d16; }
    .scrollbar-thin::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 3px; }
    .scrollbar-thin::-webkit-scrollbar-thumb:hover { background: #334155; }
    .prose h1, .prose h2, .prose h3 { color: #f8fafc; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; }
    .prose p { margin-top: 0.4rem; margin-bottom: 0.4rem; line-height: 1.6; }
    .prose ul, .prose ol { padding-left: 1.25rem; margin-top: 0.4rem; margin-bottom: 0.4rem; }
    .prose code { background: #1e293b; padding: 0.15rem 0.35rem; border-radius: 0.25rem; font-size: 0.85em; color: #a5b4fc; }
    .prose pre { background: #090d16; border: 1px solid #1e293b; border-radius: 0.5rem; padding: 0.75rem; margin-top: 0.5rem; margin-bottom: 0.5rem; }
    .prose pre code { background: transparent; padding: 0; color: #34d399; }
  </style>
</head>
<body class="text-slate-100 min-h-screen flex flex-col antialiased selection:bg-indigo-500 selection:text-white">

  <!-- Enterprise Top Global Navigation -->
  <header class="border-b border-bordercolor bg-panelbg/90 backdrop-blur sticky top-0 z-50 px-6 py-2.5 flex items-center justify-between">
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-md bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20">
          <i data-lucide="shield-alert" class="w-4 h-4"></i>
        </div>
        <div>
          <div class="flex items-center gap-2">
            <h1 class="font-bold text-base tracking-tight text-white flex items-center gap-1.5">
              <span>LOGCCINO</span>
              <span class="text-indigo-400 font-semibold text-xs tracking-wider">ENTERPRISE</span>
            </h1>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">v0.3.0 PROD</span>
            <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">SOC2 COMPLIANT</span>
          </div>
          <p class="text-[11px] text-slate-400">Autonomous SRE Observability & Distributed Big Data Intelligence</p>
        </div>
      </div>
    </div>

    <!-- Cluster Telemetry Quick Bar -->
    <div class="flex items-center gap-3 text-xs">
      <!-- Cluster Telemetry -->
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-subpanel border border-bordercolor">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" id="os-indicator"></span>
        <span class="text-slate-400">OpenSearch:</span>
        <span class="font-mono font-medium text-emerald-400" id="os-status">HEALTHY (2.18.0)</span>
      </div>

      <!-- Active AI Engine -->
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-subpanel border border-bordercolor">
        <i data-lucide="cpu" class="w-3.5 h-3.5 text-indigo-400"></i>
        <span class="text-slate-400">AI Model:</span>
        <span class="font-mono text-slate-200" id="ai-model-tag">gpt-6-luna (OpenAI)</span>
      </div>

      <!-- Remote MCP SSE Status -->
      <div class="flex items-center gap-2 px-3 py-1.5 rounded-md bg-subpanel border border-bordercolor">
        <i data-lucide="network" class="w-3.5 h-3.5 text-indigo-400"></i>
        <span class="text-slate-400">MCP Protocol:</span>
        <span class="font-mono text-slate-300">SSE Active</span>
        <button onclick="copyToClipboard(window.location.origin + '/sse')" class="text-slate-400 hover:text-white transition ml-1" title="엔드포인트 복사">
          <i data-lucide="copy" class="w-3 h-3"></i>
        </button>
      </div>

      <!-- Time Range Selector -->
      <div class="flex items-center rounded-md bg-subpanel border border-bordercolor p-0.5 text-[11px] font-medium text-slate-400">
        <button onclick="setTimeWindow('15m')" class="px-2 py-1 rounded hover:text-white transition" id="tw-15m">15m</button>
        <button onclick="setTimeWindow('1h')" class="px-2 py-1 rounded hover:text-white transition" id="tw-1h">1h</button>
        <button onclick="setTimeWindow('24h')" class="px-2 py-1 rounded bg-indigo-600 text-white font-semibold shadow-sm" id="tw-24h">24h</button>
        <button onclick="setTimeWindow('7d')" class="px-2 py-1 rounded hover:text-white transition" id="tw-7d">7d</button>
      </div>

      <a href="/docs" target="_blank" class="flex items-center gap-1 px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition">
        <i data-lucide="external-link" class="w-3.5 h-3.5"></i>
        <span>API Docs</span>
      </a>
    </div>
  </header>

  <!-- Enterprise Executive KPI Metrics Bar -->
  <section class="border-b border-bordercolor bg-subpanel/50 px-6 py-3">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      
      <!-- KPI 1: System Availability & SLO -->
      <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
        <div>
          <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <i data-lucide="activity" class="w-3.5 h-3.5 text-indigo-400"></i>
            <span>전사 서비스 가용성 (SLO)</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-xl font-bold font-mono text-emerald-400" id="slo-value">99.70%</span>
            <span class="text-[11px] text-slate-400">목표 99.90%</span>
          </div>
          <p class="text-[10px] text-amber-400 font-mono mt-0.5">⚠️ Error Budget 잔여: 70% | MTTR: 4.2m</p>
        </div>
        <div class="w-10 h-10 rounded bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
          <i data-lucide="check-circle-2" class="w-5 h-5"></i>
        </div>
      </div>

      <!-- KPI 2: Total 24h Ingestion Volume -->
      <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
        <div>
          <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <i data-lucide="database" class="w-3.5 h-3.5 text-blue-400"></i>
            <span>24H 인제스천 볼륨</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-xl font-bold font-mono text-white" id="total-logs-stat">26,203 docs</span>
            <span class="text-[11px] text-slate-400 font-mono">18.2 eps</span>
          </div>
          <p class="text-[10px] text-slate-400 font-mono mt-0.5">인덱스: logccino-logs-* | Hot Tier</p>
        </div>
        <div class="w-10 h-10 rounded bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
          <i data-lucide="layers" class="w-5 h-5"></i>
        </div>
      </div>

      <!-- KPI 3: Microservice Anomaly Matrix -->
      <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
        <div>
          <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <i data-lucide="alert-triangle" class="w-3.5 h-3.5 text-rose-400"></i>
            <span>임계치 초과 서비스</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-xl font-bold font-mono text-rose-400" id="anomaly-summary">1 경고, 1 주의</span>
            <span class="text-[11px] text-slate-400">총 3개 서비스</span>
          </div>
          <p class="text-[10px] text-slate-400 font-mono mt-0.5">최대 이상: notification-service (2.87%)</p>
        </div>
        <div class="w-10 h-10 rounded bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
          <i data-lucide="alert-octagon" class="w-5 h-5"></i>
        </div>
      </div>

      <!-- KPI 4: SRE Autonomous Agent Status -->
      <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
        <div>
          <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
            <i data-lucide="sparkles" class="w-3.5 h-3.5 text-purple-400"></i>
            <span>자율형 SRE 에이전트</span>
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-xl font-bold font-mono text-purple-400">OPERATIONAL</span>
            <span class="text-[11px] text-slate-400 font-mono">NL-to-Query</span>
          </div>
          <p class="text-[10px] text-slate-400 font-mono mt-0.5">PPL 파이프라인 컴파일러 & RCA 엔진 가동</p>
        </div>
        <div class="w-10 h-10 rounded bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
          <i data-lucide="bot" class="w-5 h-5"></i>
        </div>
      </div>

    </div>
  </section>

  <!-- Main Observability Workspace -->
  <main class="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 overflow-hidden">

    <!-- Left Column (7 cols): Autonomous SRE Incident Investigation Console -->
    <section class="lg:col-span-7 flex flex-col bg-panelbg rounded-xl border border-bordercolor shadow-2xl overflow-hidden">
      <!-- Section Header -->
      <div class="px-5 py-3.5 border-b border-bordercolor bg-subpanel/80 flex items-center justify-between">
        <div class="flex items-center gap-2.5">
          <i data-lucide="terminal" class="w-4 h-4 text-indigo-400"></i>
          <div>
            <h2 class="text-xs font-bold uppercase tracking-wider text-slate-200">Autonomous SRE Incident Investigation Console</h2>
            <p class="text-[10px] text-slate-400">자연어 심층 원인 진단(RCA), 타임라인 상관분석 및 긴급 조치 가이드</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">LIVE AGENT READY</span>
          <button onclick="clearChat()" class="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition p-1" title="대화 세션 초기화">
            <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i>
          </button>
        </div>
      </div>

      <!-- Quick Enterprise Incident Presets -->
      <div class="px-5 py-2.5 bg-slatebg/70 border-b border-bordercolor flex items-center gap-2 overflow-x-auto scrollbar-thin">
        <span class="text-[10px] uppercase font-bold text-slate-400 shrink-0 flex items-center gap-1">
          <i data-lucide="zap" class="w-3 h-3 text-amber-400"></i> 긴급 프리셋:
        </span>
        <button onclick="sendQuickPrompt('결제 서비스(payment-service) 타임아웃 및 서킷브레이커 장애 원인 분석해줘')" class="text-[11px] bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition shrink-0 font-medium">
          [P1 INCIDENT] 결제 타임아웃 RCA
        </button>
        <button onclick="sendQuickPrompt('전사 마이크로서비스 24시간 가용성 및 에러율 집계 요약해줘')" class="text-[11px] bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition shrink-0 font-medium">
          [SLA AUDIT] 전사 에러율 매트릭스
        </button>
        <button onclick="sendQuickPrompt('보안 syslog 수집기 침해사고 및 공격자 IP 분석해줘')" class="text-[11px] bg-subpanel hover:bg-rose-600/20 border border-bordercolor hover:border-rose-500/40 text-rose-300 hover:text-rose-200 px-2.5 py-1 rounded transition shrink-0 font-medium flex items-center gap-1">
          <i data-lucide="shield-alert" class="w-3 h-3 text-rose-400"></i> [SOC THREAT] 침해사고 & 공격 IP 분석
        </button>
        <button onclick="sendQuickPrompt('최근 발생한 의심스러운 sudo 권한 상승 및 실패한 SSH 로그인 명령 추적해줘')" class="text-[11px] bg-subpanel hover:bg-amber-600/20 border border-bordercolor hover:border-amber-500/40 text-amber-300 hover:text-amber-200 px-2.5 py-1 rounded transition shrink-0 font-medium flex items-center gap-1">
          <i data-lucide="key" class="w-3 h-3 text-amber-400"></i> [PRIVILEGE] 비인가 Sudo 권한 상승
        </button>
        <button onclick="sendQuickPrompt('notification-service 429 쿼터 초과 및 발송 실패 원인 분석해줘')" class="text-[11px] bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition shrink-0 font-medium">
          [ANOMALY] 알림 쿼터 초과 진단
        </button>
      </div>

      <!-- Interactive Messages Scrollable Area -->
      <div id="chat-messages" class="flex-1 p-5 overflow-y-auto space-y-4 scrollbar-thin max-h-[calc(100vh-370px)]">
        <!-- Initial Executive Welcome Message -->
        <div class="flex items-start gap-3">
          <div class="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 font-mono text-xs">
            SRE
          </div>
          <div class="bg-subpanel/80 border border-bordercolor rounded-xl rounded-tl-none p-4 text-xs text-slate-200 max-w-[90%] shadow-lg leading-relaxed">
            <div class="flex items-center justify-between border-b border-bordercolor/60 pb-2 mb-2">
              <span class="font-semibold text-white flex items-center gap-1.5">
                <i data-lucide="check-circle" class="w-3.5 h-3.5 text-emerald-400"></i>
                Logccino Enterprise Autonomous SRE Agent 초기화 완료
              </span>
              <span class="text-[10px] font-mono text-slate-400">ENGINE: gpt-6-luna</span>
            </div>
            <p class="text-slate-300 mb-2">
              분산 OpenSearch 2.18 클러스터에 인덱싱된 마이크로서비스 로그 및 분산 트레이스를 실시간 모니터링 중입니다.
              장애 현상, 특정 타임아웃, 트레이스 ID 또는 거시적 SLA 상태를 자연어로 질의하시면 엔터프라이즈 SRE 진단 보고서 규격으로 즉시 분석합니다.
            </p>
          </div>
        </div>
      </div>

      <!-- Suggested Next Steps Chips Container -->
      <div id="chips-container" class="px-5 py-2 border-t border-bordercolor bg-subpanel/40 flex items-center gap-2 overflow-x-auto scrollbar-thin hidden">
        <span class="text-[11px] text-slate-400 shrink-0 flex items-center gap-1 font-medium">
          <i data-lucide="lightbulb" class="w-3 h-3 text-amber-400"></i> 권장 후속 조사:
        </span>
        <div id="chips-list" class="flex gap-1.5 shrink-0"></div>
      </div>

      <!-- Command Input Bar -->
      <div class="p-4 border-t border-bordercolor bg-subpanel/70">
        <form onsubmit="handleChatSubmit(event)" class="flex gap-2">
          <div class="relative flex-1">
            <input type="text" id="chat-input" placeholder="엔터프라이즈 SRE 질의 입력 (예: 'auth-service 최근 로그인 실패 원인과 영향도 분석해줘')..."
                   class="w-full bg-slatebg border border-bordercolor rounded-lg pl-4 pr-10 py-2.5 text-xs text-white focus:outline-none focus:border-indigo-500 transition font-sans placeholder:text-slate-500 shadow-inner">
          </div>
          <button type="submit" id="send-btn" class="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition disabled:opacity-50 shadow-md shadow-indigo-600/20">
            <i data-lucide="send" class="w-3.5 h-3.5"></i>
            <span>실행</span>
          </button>
        </form>
      </div>
    </section>

    <!-- Right Column (5 cols): Enterprise Observability & Evidence Hub -->
    <section class="lg:col-span-5 flex flex-col gap-6">

      <!-- Top Panel: Evidence Logs / Telemetry / MCP Hub -->
      <div class="flex-1 bg-panelbg rounded-xl border border-bordercolor shadow-2xl flex flex-col overflow-hidden min-h-[460px]">
        
        <!-- Tab Navigation Header -->
        <div class="flex items-center justify-between border-b border-bordercolor px-4 bg-subpanel/80">
          <div class="flex">
            <button onclick="switchTab('evidence')" id="tab-evidence" class="px-3.5 py-3 text-xs font-semibold border-b-2 border-indigo-500 text-indigo-300 flex items-center gap-1.5 transition">
              <i data-lucide="file-text" class="w-3.5 h-3.5"></i> 근거 로그 (<span id="evidence-count">0</span>)
            </button>
            <button onclick="switchTab('charts')" id="tab-charts" class="px-3.5 py-3 text-xs font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="bar-chart-2" class="w-3.5 h-3.5"></i> 시계열 텔레메트리
            </button>
            <button onclick="switchTab('security')" id="tab-security" class="px-3.5 py-3 text-xs font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="shield" class="w-3.5 h-3.5 text-rose-400"></i> 보안 수집기 (<span id="sec-alert-count">0</span>)
            </button>
            <button onclick="switchTab('mcp')" id="tab-mcp" class="px-3.5 py-3 text-xs font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="network" class="w-3.5 h-3.5"></i> MCP 게이트웨이
            </button>
          </div>
          <button onclick="refreshOverview()" class="text-slate-400 hover:text-white text-xs p-1.5 rounded hover:bg-slate-800 transition" title="텔레메트리 즉시 갱신">
            <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
          </button>
        </div>

        <!-- Tab 1: Evidence Log Explorer -->
        <div id="content-evidence" class="flex-1 p-3.5 overflow-y-auto scrollbar-thin max-h-[430px]">
          <div id="evidence-list" class="space-y-2 text-xs">
            <p class="text-slate-500 text-center py-16">
              자연어 질문을 실행하면 분산 클러스터에서 추출된 실제 근거 로그 및 트레이스가 여기에 스트리밍됩니다.
            </p>
          </div>
        </div>

        <!-- Tab 2: Telemetry & Anomaly Analytics -->
        <div id="content-charts" class="flex-1 p-4 hidden flex flex-col gap-4 overflow-y-auto max-h-[430px] scrollbar-thin">
          <div class="bg-slatebg/80 p-3.5 rounded-lg border border-bordercolor">
            <h3 class="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
              <i data-lucide="bar-chart" class="w-3.5 h-3.5 text-indigo-400"></i> 서비스별 로그 처리 볼륨 vs 에러 건수
            </h3>
            <div id="chart-services" class="w-full h-44"></div>
          </div>
          <div class="bg-slatebg/80 p-3.5 rounded-lg border border-bordercolor">
            <h3 class="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
              <i data-lucide="pie-chart" class="w-3.5 h-3.5 text-indigo-400"></i> 로그 심각도 비율 (INFO vs ERROR)
            </h3>
            <div id="chart-levels" class="w-full h-40"></div>
          </div>
        </div>

        <!-- Tab 3: Enterprise AI Agent Gateway (MCP Hub) -->
        <div id="content-mcp" class="flex-1 p-4 hidden overflow-y-auto max-h-[430px] scrollbar-thin text-xs space-y-4">
          <div class="p-3 bg-indigo-500/5 rounded-lg border border-indigo-500/20 text-indigo-300 leading-relaxed">
            <span class="font-bold flex items-center gap-1 mb-1">
              <i data-lucide="info" class="w-3.5 h-3.5"></i> 원격 MCP (Server-Sent Events) 게이트웨이
            </span>
            Claude Desktop, Antigravity, Cursor IDE 설정에 아래 JSON 블록을 복사하여 즉시 연결할 수 있습니다.
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-semibold text-slate-200 font-mono">Claude Desktop (`claude_desktop_config.json`)</span>
              <button onclick="copySnippet('claude-cfg')" class="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold">
                <i data-lucide="copy" class="w-3 h-3"></i> 복사
              </button>
            </div>
            <pre id="claude-cfg" class="bg-slatebg p-3 rounded border border-bordercolor text-slate-300 overflow-x-auto text-[11px] font-mono"></pre>
          </div>

          <div>
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-semibold text-slate-200 font-mono">Cursor IDE / Google Antigravity CLI</span>
              <button onclick="copySnippet('cursor-cfg')" class="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold">
                <i data-lucide="copy" class="w-3 h-3"></i> 복사
              </button>
            </div>
            <pre id="cursor-cfg" class="bg-slatebg p-3 rounded border border-bordercolor text-slate-300 overflow-x-auto text-[11px] font-mono"></pre>
          </div>
        </div>

        <!-- Tab 4: Enterprise Security Syslog Collector & SIEM Console -->
        <div id="content-security" class="flex-1 p-3.5 hidden overflow-y-auto max-h-[430px] scrollbar-thin text-xs space-y-3">
          <!-- Daemon Control Card -->
          <div class="p-3 bg-subpanel rounded-lg border border-bordercolor space-y-2.5">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-slate-500" id="collector-status-dot"></span>
                <span class="font-bold text-white text-xs">Rust High-Performance Syslog Engine</span>
                <span id="collector-status-badge" class="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-400 border border-slate-700">CHECKING...</span>
              </div>
              <div class="flex items-center gap-1.5">
                <button onclick="startCollector()" id="btn-col-start" class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-[11px] flex items-center gap-1 transition shadow-sm">
                  <i data-lucide="play" class="w-3 h-3"></i> 시작
                </button>
                <button onclick="stopCollector()" id="btn-col-stop" class="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium text-[11px] flex items-center gap-1 transition shadow-sm">
                  <i data-lucide="square" class="w-3 h-3"></i> 중지
                </button>
                <button onclick="restartCollector()" id="btn-col-restart" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-[11px] flex items-center gap-1 transition border border-slate-700">
                  <i data-lucide="refresh-cw" class="w-3 h-3"></i> 재시작
                </button>
              </div>
            </div>

            <!-- Metrics Grid -->
            <div class="grid grid-cols-4 gap-2 pt-1 border-t border-bordercolor/60 text-center">
              <div class="bg-slatebg/80 p-2 rounded border border-bordercolor/50">
                <span class="text-[9px] uppercase text-slate-400 block font-semibold">수신 패킷 (Rx)</span>
                <span class="font-mono font-bold text-slate-100 text-xs" id="sec-rx">0</span>
              </div>
              <div class="bg-slatebg/80 p-2 rounded border border-bordercolor/50">
                <span class="text-[9px] uppercase text-slate-400 block font-semibold">ECS 파싱 (Parsed)</span>
                <span class="font-mono font-bold text-indigo-400 text-xs" id="sec-parsed">0</span>
              </div>
              <div class="bg-slatebg/80 p-2 rounded border border-bordercolor/50">
                <span class="text-[9px] uppercase text-slate-400 block font-semibold">포워딩 (Ingested)</span>
                <span class="font-mono font-bold text-emerald-400 text-xs" id="sec-fwd">0</span>
              </div>
              <div class="bg-slatebg/80 p-2 rounded border border-bordercolor/50">
                <span class="text-[9px] uppercase text-slate-400 block font-semibold">위협 경고 (Alerts)</span>
                <span class="font-mono font-bold text-rose-400 text-xs" id="sec-threats">0</span>
              </div>
            </div>

            <div class="flex items-center justify-between text-[10px] text-slate-400 font-mono px-1">
              <span>바인드: UDP/TCP 0.0.0.0:1514 | 포워더: :8000</span>
              <span>가동 시간: <span id="sec-uptime" class="text-slate-200">0s</span> | <span id="sec-eps" class="text-slate-200">0.0 eps</span></span>
            </div>
          </div>

          <!-- Attack Simulator Injection Bar -->
          <div class="p-3 bg-subpanel rounded-lg border border-bordercolor space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-200 flex items-center gap-1.5 text-xs">
                <i data-lucide="target" class="w-3.5 h-3.5 text-rose-400"></i> 실시간 보안 위협 시뮬레이션 패킷 발송
              </span>
              <span id="inject-status-msg" class="text-[10px] font-mono text-emerald-400"></span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button onclick="injectTestEvent('ssh_failed')" class="px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[11px] font-medium transition flex items-center gap-1">
                <i data-lucide="shield-alert" class="w-3 h-3"></i> SSH 무차별대입 실패
              </button>
              <button onclick="injectTestEvent('sudo_escalation')" class="px-2.5 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[11px] font-medium transition flex items-center gap-1">
                <i data-lucide="lock" class="w-3 h-3"></i> 비인가 Sudo 실행
              </button>
              <button onclick="injectTestEvent('ufw_block')" class="px-2.5 py-1 rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 border border-blue-500/30 text-[11px] font-medium transition flex items-center gap-1">
                <i data-lucide="shield-off" class="w-3 h-3"></i> UFW 방화벽 차단
              </button>
              <button onclick="injectTestEvent('pam_failure')" class="px-2.5 py-1 rounded bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 text-[11px] font-medium transition flex items-center gap-1">
                <i data-lucide="key" class="w-3 h-3"></i> PAM 인증 실패
              </button>
              <button onclick="injectTestEvent('ssh_accepted')" class="px-2.5 py-1 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-medium transition flex items-center gap-1">
                <i data-lucide="check" class="w-3 h-3"></i> 정상 SSH 로그인
              </button>
            </div>
          </div>

          <!-- Security Events Stream Table -->
          <div class="space-y-1.5">
            <div class="flex items-center justify-between px-1">
              <span class="font-bold text-slate-300 text-xs flex items-center gap-1">
                <i data-lucide="flame" class="w-3.5 h-3.5 text-rose-400"></i> 실시간 보안 이벤트 스트림 (최신 50건)
              </span>
              <button onclick="loadSecurityEvents()" class="text-slate-400 hover:text-white text-xs flex items-center gap-1 transition">
                <i data-lucide="refresh-cw" class="w-3 h-3"></i> 새로고침
              </button>
            </div>
            <div id="security-events-list" class="space-y-1.5 max-h-[220px] overflow-y-auto scrollbar-thin">
              <p class="text-slate-500 text-center py-6 text-xs">보안 로그를 조회 중입니다...</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Bottom Panel: Enterprise Infrastructure Telemetry Grid -->
      <div class="bg-panelbg rounded-xl border border-bordercolor p-4 shadow-xl">
        <div class="flex items-center justify-between mb-3 border-b border-bordercolor/60 pb-2">
          <span class="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <i data-lucide="server" class="w-3.5 h-3.5 text-indigo-400"></i> 분산 클러스터 인프라 매트릭스
          </span>
          <span class="text-[10px] font-mono text-slate-400" id="cluster-name-tag">logccino-cluster</span>
        </div>
        <div class="grid grid-cols-3 gap-3 text-center">
          <div class="bg-subpanel p-2.5 rounded-lg border border-bordercolor">
            <span class="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">클러스터 상태</span>
            <span class="text-sm font-bold text-emerald-400 font-mono" id="cluster-health-status">GREEN</span>
          </div>
          <div class="bg-subpanel p-2.5 rounded-lg border border-bordercolor">
            <span class="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">활성 노드 / 샤드</span>
            <span class="text-sm font-bold text-slate-100 font-mono" id="cluster-nodes-count">1 Node / 1 Shard</span>
          </div>
          <div class="bg-subpanel p-2.5 rounded-lg border border-bordercolor">
            <span class="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">관제 서비스 수</span>
            <span class="text-sm font-bold text-indigo-400 font-mono" id="cluster-services-count">3 Services</span>
          </div>
        </div>
      </div>

    </section>
  </main>

  <!-- Enterprise Log Detail Inspector Modal -->
  <div id="log-modal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-panelbg border border-bordercolor rounded-xl max-w-3xl w-full max-h-[85vh] flex flex-col shadow-2xl">
      <div class="px-5 py-3.5 border-b border-bordercolor flex items-center justify-between bg-subpanel">
        <h3 class="text-xs font-bold uppercase tracking-wider text-white flex items-center gap-2">
          <i data-lucide="file-code" class="w-4 h-4 text-indigo-400"></i> 엔터프라이즈 로그 상세 인스펙터 (JSON)
        </h3>
        <button onclick="closeModal()" class="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>
      <div class="p-4 flex-1 overflow-y-auto scrollbar-thin">
        <pre id="modal-json" class="bg-slatebg p-4 rounded-lg border border-bordercolor text-emerald-400 text-xs overflow-x-auto font-mono leading-relaxed"></pre>
      </div>
      <div class="px-5 py-2.5 border-t border-bordercolor bg-subpanel/50 flex justify-end">
        <button onclick="copySnippet('modal-json')" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold flex items-center gap-1 transition">
          <i data-lucide="copy" class="w-3 h-3"></i> JSON 복사
        </button>
      </div>
    </div>
  </div>

  <script>
    let conversationHistory = [];
    let currentLogsContext = "";
    let evidenceLogs = [];
    let servicesChartInstance = null;
    let levelsChartInstance = null;
    let currentTimeWindow = "24h";

    document.addEventListener("DOMContentLoaded", () => {
      lucide.createIcons();
      refreshOverview();
      loadMCPConfigs();
      fetchCollectorStatus();
      setInterval(fetchCollectorStatus, 4000);
    });

    function setTimeWindow(tw) {
      currentTimeWindow = tw;
      ['15m', '1h', '24h', '7d'].forEach(w => {
        const btn = document.getElementById(`tw-${w}`);
        if (w === tw) {
          btn.className = 'px-2 py-1 rounded bg-indigo-600 text-white font-semibold shadow-sm';
        } else {
          btn.className = 'px-2 py-1 rounded hover:text-white transition';
        }
      });
      refreshOverview();
    }

    async function refreshOverview() {
      try {
        const res = await fetch('/api/v1/admin/overview');
        const data = await res.json();
        if (data.status === 'success') {
          const cluster = data.cluster || {};
          const isHealthy = cluster.status === 'green' || cluster.opensearch_connected;
          
          document.getElementById('os-status').textContent = isHealthy ? 'HEALTHY (2.18.0)' : 'DEGRADED';
          document.getElementById('os-indicator').className = isHealthy ? 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse' : 'w-2 h-2 rounded-full bg-rose-500';
          document.getElementById('cluster-health-status').textContent = (cluster.status || 'GREEN').toUpperCase();
          document.getElementById('cluster-health-status').className = isHealthy ? 'text-sm font-bold text-emerald-400 font-mono' : 'text-sm font-bold text-rose-400 font-mono';
          document.getElementById('cluster-name-tag').textContent = cluster.cluster_name || 'logccino-cluster';
          
          const totalDocs = cluster.total_indexed_logs || 0;
          document.getElementById('total-logs-stat').textContent = totalDocs.toLocaleString() + ' docs';
          document.getElementById('cluster-nodes-count').textContent = (cluster.number_of_nodes || 1) + ' Node / 1 Shard';
          document.getElementById('cluster-services-count').textContent = (data.services_count || 3) + ' Services';

          renderCharts(data.services_summary || []);
        }
      } catch (e) {
        console.error("Telemetry fetch failed", e);
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
          grid: { top: 20, right: 15, bottom: 25, left: 45 },
          xAxis: { type: 'category', data: services.map(s => s.service), axisLabel: { fontSize: 10, color: '#94a3b8' } },
          yAxis: { type: 'value', axisLabel: { fontSize: 10, color: '#94a3b8' }, splitLine: { lineStyle: { color: '#1e293b' } } },
          series: [
            { name: 'Total Logs', type: 'bar', data: services.map(s => s.total_logs), itemStyle: { color: '#6366f1', borderRadius: [3, 3, 0, 0] } },
            { name: 'Errors', type: 'bar', data: services.map(s => s.error_count), itemStyle: { color: '#ef4444', borderRadius: [3, 3, 0, 0] } }
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
            radius: ['45%', '72%'],
            data: [
              { value: totalInfos, name: 'INFO', itemStyle: { color: '#10b981' } },
              { value: totalErrors, name: 'ERROR', itemStyle: { color: '#ef4444' } }
            ],
            label: { show: true, fontSize: 10, color: '#e2e8f0', formatter: '{b}: {d}%' }
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

      const loadingId = appendLoadingMessage();

      try {
        if (conversationHistory.length <= 1) {
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

            renderEvidenceLogs(data.evidence_logs || []);
            extractFollowupChips(data.analysis_report);
          } else {
            appendAssistantMessage("엔터프라이즈 분석 실패: " + (data.detail || '알 수 없는 오류'));
          }
        } else {
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
        appendAssistantMessage("통신 장애 발생: " + err.message);
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
        <div class="bg-indigo-600 text-white rounded-xl rounded-tr-none px-4 py-2.5 text-xs max-w-[85%] shadow-md font-sans">
          ${escapeHtml(text)}
        </div>
        <div class="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-xs font-mono text-slate-300 shrink-0 border border-bordercolor">
          SRE
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
        <div class="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 font-mono text-xs">
          SRE
        </div>
        <div class="bg-subpanel border border-bordercolor rounded-xl rounded-tl-none p-4 text-xs text-slate-200 max-w-[92%] shadow-xl prose prose-invert leading-relaxed font-sans">
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
        <div class="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 font-mono text-xs">
          SRE
        </div>
        <div class="bg-subpanel border border-bordercolor rounded-xl rounded-tl-none px-4 py-3 text-xs text-slate-400 flex items-center gap-2">
          <i data-lucide="loader" class="w-4 h-4 animate-spin text-indigo-400"></i>
          <span>분산 OpenSearch 클러스터 쿼리 컴파일 및 심층 원인 진단 수행 중...</span>
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
        listDom.innerHTML = '<p class="text-slate-500 text-center py-12">조회된 조건에 부합하는 로그가 없습니다.</p>';
        return;
      }

      listDom.innerHTML = logs.map((log, idx) => {
        const lvl = (log.level || 'INFO').toUpperCase();
        const badgeColor = (lvl === 'ERROR' || lvl === 'FATAL') ? 'bg-rose-500/10 text-rose-400 border-rose-500/30' :
                           lvl === 'WARN' ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' :
                           'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
        return `
          <div onclick="openModal(${idx})" class="p-2.5 bg-slatebg border border-bordercolor rounded-lg hover:border-indigo-500/50 cursor-pointer transition flex flex-col gap-1">
            <div class="flex items-center justify-between text-[10px]">
              <span class="px-1.5 py-0.5 rounded font-mono font-bold border ${badgeColor}">${lvl}</span>
              <span class="font-semibold text-slate-200 font-mono">${escapeHtml(log.service || 'unknown')}</span>
              <span class="text-slate-500 font-mono">${log['@timestamp'] ? log['@timestamp'].split('T')[1].slice(0, 8) : ''}</span>
            </div>
            <p class="text-slate-300 truncate font-mono text-[11px]">${escapeHtml(log.message || '')}</p>
            ${log.trace_id ? `<span class="text-[9px] text-indigo-400 font-mono">trace: ${log.trace_id}</span>` : ''}
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
        if (match[1].length > 5 && match[1].length < 45) questions.push(match[1]);
      }

      if (questions.length > 0) {
        chipsList.innerHTML = questions.slice(0, 3).map(q => `
          <button onclick="sendQuickPrompt('${escapeHtml(q)}')" class="text-[11px] bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 hover:text-indigo-300 px-2.5 py-1 rounded transition whitespace-nowrap font-medium">
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
      ['evidence', 'charts', 'mcp', 'security'].forEach(t => {
        const el = document.getElementById(`content-${t}`);
        const tabBtn = document.getElementById(`tab-${t}`);
        if (el) el.classList.add('hidden');
        if (tabBtn) tabBtn.className = 'px-3.5 py-3 text-xs font-semibold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition';
      });
      const activeEl = document.getElementById(`content-${tab}`);
      const activeBtn = document.getElementById(`tab-${tab}`);
      if (activeEl) activeEl.classList.remove('hidden');
      if (activeBtn) activeBtn.className = 'px-3.5 py-3 text-xs font-semibold border-b-2 border-indigo-500 text-indigo-300 flex items-center gap-1.5 transition';

      if (tab === 'charts') {
        setTimeout(() => {
          if (servicesChartInstance) servicesChartInstance.resize();
          if (levelsChartInstance) levelsChartInstance.resize();
        }, 50);
      } else if (tab === 'security') {
        loadSecurityEvents();
      }
      lucide.createIcons();
    }

    async function fetchCollectorStatus() {
      try {
        const res = await fetch('/api/v1/collector/status');
        const data = await res.json();
        const isRunning = data.status === 'running';
        const badge = document.getElementById('collector-status-badge');
        const dot = document.getElementById('collector-status-dot');
        const m = data.metrics || {};

        if (badge && dot) {
          if (isRunning) {
            badge.textContent = `RUNNING (PID: ${data.pid || 'live'})`;
            badge.className = 'px-2 py-0.5 rounded font-mono text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
            dot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse';
          } else {
            badge.textContent = 'STOPPED';
            badge.className = 'px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-400 border border-slate-700';
            dot.className = 'w-2.5 h-2.5 rounded-full bg-slate-500';
          }
        }

        const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setTxt('sec-rx', (m.received_total || 0).toLocaleString());
        setTxt('sec-parsed', (m.parsed_total || 0).toLocaleString());
        setTxt('sec-fwd', (m.forwarded_total || 0).toLocaleString());
        setTxt('sec-threats', (m.security_alerts_total || 0).toLocaleString());
        setTxt('sec-alert-count', m.security_alerts_total || 0);
        setTxt('sec-uptime', (m.uptime_seconds || 0) + 's');
        setTxt('sec-eps', (m.throughput_eps || 0.0).toFixed(1) + ' eps');
      } catch (e) {
        console.error("Collector status fetch failed", e);
      }
    }

    async function startCollector() {
      try {
        const res = await fetch('/api/v1/collector/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        await fetchCollectorStatus();
      } catch (e) {
        alert("수집기 시작 오류: " + e.message);
      }
    }

    async function stopCollector() {
      try {
        await fetch('/api/v1/collector/stop', { method: 'POST' });
        await fetchCollectorStatus();
      } catch (e) {
        alert("수집기 중지 오류: " + e.message);
      }
    }

    async function restartCollector() {
      try {
        await fetch('/api/v1/collector/restart', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        await fetchCollectorStatus();
      } catch (e) {
        alert("수집기 재시작 오류: " + e.message);
      }
    }

    async function injectTestEvent(type) {
      const msgEl = document.getElementById('inject-status-msg');
      if (msgEl) msgEl.textContent = '패킷 전송 중...';
      try {
        const res = await fetch('/api/v1/collector/test-event', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ event_type: type })
        });
        const data = await res.json();
        if (msgEl) msgEl.textContent = `✅ 패킷 전송 완료 (${type})`;
        setTimeout(() => { if (msgEl) msgEl.textContent = ''; }, 3000);
        setTimeout(async () => {
          await fetchCollectorStatus();
          await loadSecurityEvents();
        }, 800);
      } catch (e) {
        if (msgEl) msgEl.textContent = '❌ 전송 실패: ' + e.message;
      }
    }

    async function loadSecurityEvents() {
      const listDom = document.getElementById('security-events-list');
      if (!listDom) return;
      try {
        const res = await fetch('/api/v1/collector/security-events?limit=30');
        const data = await res.json();
        const events = data.events || [];
        if (events.length === 0) {
          listDom.innerHTML = '<p class="text-slate-500 text-center py-6 text-xs">수집된 보안 이벤트가 없습니다. 상단의 위협 시뮬레이션 버튼을 눌러 테스트 패킷을 발송해보세요.</p>';
          return;
        }

        listDom.innerHTML = events.map(ev => {
          const sec = ev.security || (ev.attributes && ev.attributes.security) || {};
          const action = sec.action || 'syslog_event';
          const srcIp = sec.source_ip || ev.host || 'unknown';
          const user = sec.user_name || '';
          const ts = (ev['@timestamp'] || '').replace('T', ' ').split('.')[0];
          
          let actionColor = 'bg-slate-700 text-slate-300';
          if (action.includes('failed') || action.includes('failure')) actionColor = 'bg-rose-500/20 text-rose-300 border border-rose-500/30';
          else if (action.includes('sudo') || action.includes('escalation')) actionColor = 'bg-amber-500/20 text-amber-300 border border-amber-500/30';
          else if (action.includes('block') || action.includes('drop')) actionColor = 'bg-blue-500/20 text-blue-300 border border-blue-500/30';
          else if (action.includes('accepted')) actionColor = 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';

          return `
            <div class="p-2 bg-slatebg rounded border border-bordercolor text-xs flex flex-col gap-1">
              <div class="flex items-center justify-between text-[10px]">
                <div class="flex items-center gap-1.5">
                  <span class="px-1.5 py-0.5 rounded font-mono font-semibold text-[9px] ${actionColor}">${escapeHtml(action)}</span>
                  ${srcIp ? `<span class="font-mono text-slate-300">SRC: ${escapeHtml(srcIp)}</span>` : ''}
                  ${user ? `<span class="font-mono text-indigo-300">USER: ${escapeHtml(user)}</span>` : ''}
                </div>
                <span class="text-slate-500 font-mono text-[9px]">${escapeHtml(ts)}</span>
              </div>
              <p class="text-slate-400 font-mono text-[10px] truncate">${escapeHtml(ev.message || '')}</p>
            </div>
          `;
        }).join('');
      } catch (e) {
        listDom.innerHTML = `<p class="text-rose-400 text-center py-4 text-xs">보안 로그 조회 실패: ${escapeHtml(e.message)}</p>`;
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
      appendAssistantMessage("대화 세션이 초기화되었습니다. 새로운 장애 조사 및 로그 질의를 입력하세요.");
    }

    function copyToClipboard(text) {
      navigator.clipboard.writeText(text);
      alert("엔드포인트가 클립보드에 복사되었습니다: " + text);
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
    """자체 제작 엔터프라이즈 자율형 SRE 관제 및 대화형 로그 분석 웹 대시보드"""
    return HTMLResponse(content=ENTERPRISE_DASHBOARD_HTML)
