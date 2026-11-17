"""
Enterprise Observability & Security Dashboard for Logccino
Splunk 최신 Enterprise UI 디자인:
- 좌측 Splunk App Bar (Search & Reporting, Enterprise Security SIEM, Autonomous SRE, Manage Apps)
- 우측 상단 Splunk Global Menu (설정/Activity/도움말 풀다운 드롭다운)
- Splunk 스타일 Cross-Index Join 검색 콘솔 (이벤트, 통계 테이블, 시각화)
- 독립 추출된 Enterprise Security (SIEM) 관제 앱
- 플러그형 앱 생태계 (앱 설치, On/Off 활성화 관리)
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI & Dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/ui", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def get_enterprise_dashboard():
    return HTMLResponse(content="""<!DOCTYPE html>
<html lang="ko" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>splunk> enterprise | Logccino Autonomous Platform</title>
  
  <!-- Tailwind CSS CDN -->
  <script src="https://cdn.tailwindcss.com"></script>
  <!-- Lucide Icons CDN -->
  <script src="https://unpkg.com/lucide@latest"></script>
  <!-- Apache ECharts CDN -->
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
  
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            slatebg: '#090d16',
            panelbg: '#0f172a',
            subpanel: '#1e293b',
            bordercolor: '#334155',
            splunkgreen: '#10b981',
            splunkaccent: '#f43f5e'
          },
          fontFamily: {
            sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
            mono: ['JetBrains Mono', 'Fira Code', 'monospace']
          }
        }
      }
    }
  </script>
  <style>
    body { background-color: #090d16; }
    .scrollbar-thin::-webkit-scrollbar { width: 5px; height: 5px; }
    .scrollbar-thin::-webkit-scrollbar-track { background: #0f172a; }
    .scrollbar-thin::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    .scrollbar-thin::-webkit-scrollbar-thumb:hover { background: #475569; }
    .dropdown-menu { transform-origin: top right; transition: all 0.15s ease-out; }
  </style>
</head>
<body class="text-slate-100 min-h-screen flex flex-col antialiased selection:bg-indigo-500 selection:text-white">

  <!-- =================================================================================== -->
  <!-- 1. Splunk Enterprise Global Navigation Header (우측 상단 풀다운 메뉴 체계)            -->
  <!-- =================================================================================== -->
  <header class="border-b border-bordercolor bg-panelbg sticky top-0 z-50 px-5 py-2.5 flex items-center justify-between shadow-md">
    <!-- Left Brand & Active App Info -->
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
        <span class="font-extrabold text-xl tracking-tight text-white font-mono flex items-center">
          <span>splunk</span><span class="text-emerald-400 font-black">&gt;</span>
        </span>
        <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">enterprise</span>
      </div>

      <div class="h-4 w-px bg-bordercolor"></div>

      <!-- Current App Breadcrumb -->
      <div class="flex items-center gap-2">
        <i data-lucide="layers" class="w-4 h-4 text-indigo-400"></i>
        <span class="text-xs text-slate-400">앱:</span>
        <span class="text-xs font-bold text-white font-mono" id="current-app-title">Search & Reporting</span>
      </div>
    </div>

    <!-- Right Global Menu & Pulldown Dropdowns -->
    <div class="flex items-center gap-3 text-xs">

      <!-- Cluster Status Pill -->
      <div class="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-subpanel border border-bordercolor">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" id="os-indicator"></span>
        <span class="text-slate-400">OpenSearch:</span>
        <span class="font-mono font-medium text-emerald-400" id="os-status">HEALTHY (2.18.0)</span>
      </div>

      <!-- Time Range Selector -->
      <div class="flex items-center rounded-md bg-subpanel border border-bordercolor p-0.5 text-[11px] font-medium text-slate-400">
        <button onclick="setTimeWindow('15m')" class="px-2 py-1 rounded hover:text-white transition" id="tw-15m">15m</button>
        <button onclick="setTimeWindow('1h')" class="px-2 py-1 rounded hover:text-white transition" id="tw-1h">1h</button>
        <button onclick="setTimeWindow('24h')" class="px-2 py-1 rounded bg-indigo-600 text-white font-semibold shadow-sm" id="tw-24h">24h</button>
        <button onclick="setTimeWindow('7d')" class="px-2 py-1 rounded hover:text-white transition" id="tw-7d">7d</button>
      </div>

      <!-- PULLDOWN MENU 1: 설정 (Settings) -->
      <div class="relative dropdown-container">
        <button onclick="toggleDropdown('settings-dropdown')" class="flex items-center gap-1.5 px-3 py-1.5 rounded-md hover:bg-slate-800 text-slate-200 border border-bordercolor transition font-medium">
          <i data-lucide="settings" class="w-3.5 h-3.5 text-indigo-400"></i>
          <span>설정</span>
          <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400"></i>
        </button>
        <div id="settings-dropdown" class="hidden absolute right-0 mt-2 w-72 bg-panelbg border border-bordercolor rounded-lg shadow-2xl z-50 p-2 text-xs divide-y divide-bordercolor/60">
          <div class="py-1.5 px-2">
            <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">KNOWLEDGE (지식 및 검색)</span>
            <a href="javascript:void(0)" onclick="openSavedSearchesModal(); closeAllDropdowns();" class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-subpanel text-slate-200 hover:text-white transition mt-1">
              <i data-lucide="bell" class="w-3.5 h-3.5 text-amber-400"></i>
              <div>
                <div class="font-medium">저장된 검색 및 알람 (Alerts)</div>
                <div class="text-[10px] text-slate-400">PPL 스케줄러 및 트리거 규칙 관리</div>
              </div>
            </a>
            <a href="javascript:void(0)" onclick="selectApp('search'); closeAllDropdowns();" class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-subpanel text-slate-200 hover:text-white transition">
              <i data-lucide="git-merge" class="w-3.5 h-3.5 text-indigo-400"></i>
              <div>
                <div class="font-medium">크로스 인덱스 Join 파이프라인</div>
                <div class="text-[10px] text-slate-400">OpenSearch 분산 해시 조인</div>
              </div>
            </a>
          </div>
          <div class="py-1.5 px-2">
            <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">SYSTEM (시스템 및 앱 관리)</span>
            <a href="javascript:void(0)" onclick="selectApp('manage_apps'); closeAllDropdowns();" class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-subpanel text-slate-200 hover:text-white transition mt-1">
              <i data-lucide="package" class="w-3.5 h-3.5 text-emerald-400"></i>
              <div>
                <div class="font-medium">앱 관리 및 설치 (Manage Apps)</div>
                <div class="text-[10px] text-slate-400">SIEM 등 플러그형 앱 활성화/설치</div>
              </div>
            </a>
            <a href="javascript:void(0)" onclick="selectApp('siem'); closeAllDropdowns();" class="siem-menu-item flex items-center gap-2 px-2 py-1.5 rounded hover:bg-subpanel text-slate-200 hover:text-white transition">
              <i data-lucide="server" class="w-3.5 h-3.5 text-rose-400"></i>
              <div>
                <div class="font-medium">보안 Syslog 수집 엔진</div>
                <div class="text-[10px] text-slate-400">Rust 1514 데몬 및 포워더</div>
              </div>
            </a>
          </div>
          <div class="py-1.5 px-2">
            <span class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">USERS & AUTH (사용자 및 권한)</span>
            <a href="javascript:void(0)" onclick="openUsersModal(); closeAllDropdowns();" class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-subpanel text-slate-200 hover:text-white transition mt-1">
              <i data-lucide="users" class="w-3.5 h-3.5 text-indigo-400"></i>
              <div>
                <div class="font-medium">사용자 및 롤 (RBAC)</div>
                <div class="text-[10px] text-slate-400">Splunk 표준 롤 및 계정 권한 관리</div>
              </div>
            </a>
          </div>
        </div>
      </div>

      <!-- PULLDOWN MENU 2: 활동 (Activity) -->
      <div class="relative dropdown-container">
        <button onclick="toggleDropdown('activity-dropdown')" class="flex items-center gap-1.5 px-3 py-1.5 rounded-md hover:bg-slate-800 text-slate-200 border border-bordercolor transition font-medium">
          <i data-lucide="activity" class="w-3.5 h-3.5 text-amber-400"></i>
          <span>활동</span>
          <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400"></i>
        </button>
        <div id="activity-dropdown" class="hidden absolute right-0 mt-2 w-64 bg-panelbg border border-bordercolor rounded-lg shadow-2xl z-50 p-2 text-xs">
          <a href="javascript:void(0)" onclick="openSavedSearchesModal(); closeAllDropdowns();" class="flex items-center gap-2 px-2 py-2 rounded hover:bg-subpanel text-slate-200 hover:text-white transition">
            <i data-lucide="bell-ring" class="w-3.5 h-3.5 text-amber-400"></i>
            <div>
              <div class="font-medium">트리거된 알람 (Triggered Alerts)</div>
              <div class="text-[10px] text-slate-400">스케줄러 자동 실행 알람 히스토리</div>
            </div>
          </a>
          <a href="javascript:void(0)" onclick="selectApp('search'); closeAllDropdowns();" class="flex items-center gap-2 px-2 py-2 rounded hover:bg-subpanel text-slate-200 hover:text-white transition">
            <i data-lucide="terminal" class="w-3.5 h-3.5 text-indigo-400"></i>
            <div>
              <div class="font-medium">검색 작업 및 쿼리 이력 (Jobs)</div>
              <div class="text-[10px] text-slate-400">실행 중인 PPL / Join 작업 현황</div>
            </div>
          </a>
        </div>
      </div>

      <!-- PULLDOWN MENU 3: 도움말 (Help) -->
      <div class="relative dropdown-container">
        <button onclick="toggleDropdown('help-dropdown')" class="flex items-center gap-1.5 px-3 py-1.5 rounded-md hover:bg-slate-800 text-slate-200 border border-bordercolor transition font-medium">
          <i data-lucide="help-circle" class="w-3.5 h-3.5 text-slate-400"></i>
          <span>도움말</span>
          <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400"></i>
        </button>
        <div id="help-dropdown" class="hidden absolute right-0 mt-2 w-56 bg-panelbg border border-bordercolor rounded-lg shadow-2xl z-50 p-2 text-xs">
          <a href="/docs" target="_blank" class="flex items-center gap-2 px-2 py-2 rounded hover:bg-subpanel text-slate-200 hover:text-white transition">
            <i data-lucide="file-text" class="w-3.5 h-3.5 text-indigo-400"></i>
            <div><div class="font-medium">API Documentation</div><div class="text-[10px] text-slate-400">FastAPI Swagger Specs</div></div>
          </a>
          <a href="javascript:void(0)" onclick="copyToClipboard(window.location.origin + '/sse'); closeAllDropdowns();" class="flex items-center gap-2 px-2 py-2 rounded hover:bg-subpanel text-slate-200 hover:text-white transition">
            <i data-lucide="network" class="w-3.5 h-3.5 text-purple-400"></i>
            <div><div class="font-medium">MCP SSE 엔드포인트 복사</div><div class="text-[10px] text-slate-400">Agent-Native Protocol</div></div>
          </a>
        </div>
      </div>

      <!-- User Account -->
      <div class="flex items-center gap-2 pl-2 border-l border-bordercolor">
        <div class="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center font-bold text-white text-xs">A</div>
        <div>
          <span class="font-semibold text-white block leading-tight">admin</span>
          <span class="text-[9px] text-emerald-400 font-mono">Administrator</span>
        </div>
      </div>
      <button onclick="toggleSiemModule()" id="siem-toggle-btn" class="hidden"></button>

    </div>
  </header>

  <!-- =================================================================================== -->
  <!-- 2. Splunk Workspace: Left Apps Bar + Right App View Area                            -->
  <!-- =================================================================================== -->
  <div class="flex flex-1 overflow-hidden">

    <!-- LEFT SPLUNK APPS BAR (좌측 앱 리스트) -->
    <aside class="w-64 bg-[#0b1120] border-r border-bordercolor flex flex-col shrink-0 select-none">
      <div class="p-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-bordercolor flex items-center justify-between">
        <span class="flex items-center gap-1.5"><i data-lucide="grid" class="w-3.5 h-3.5 text-indigo-400"></i> APPS</span>
        <button onclick="selectApp('manage_apps')" class="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold" title="앱 관리">
          <i data-lucide="sliders" class="w-3 h-3"></i> 관리
        </button>
      </div>

      <!-- Dynamic App Buttons Navigation -->
      <nav class="flex-1 p-2 space-y-1.5 overflow-y-auto scrollbar-thin" id="splunk-apps-nav">
        <!-- 1. Search & Reporting (Core App) -->
        <button onclick="selectApp('search')" id="app-nav-search" class="app-nav-btn w-full text-left p-3 rounded-lg flex items-start gap-3 transition bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm">
          <i data-lucide="search" class="w-4 h-4 mt-0.5 shrink-0 text-indigo-400"></i>
          <div>
            <div class="font-bold text-xs text-white">Search & Reporting</div>
            <div class="text-[10px] text-slate-400 mt-0.5 leading-snug">PPL 및 크로스 인덱스 Join 검색, 통계 및 시각화</div>
          </div>
        </button>

        <!-- 2. Enterprise Security (SIEM) - Extracted App -->
        <button onclick="selectApp('siem')" id="tab-security" class="app-nav-btn siem-feature siem-app-feature w-full text-left p-3 rounded-lg flex items-start gap-3 transition hover:bg-subpanel text-slate-300 border border-transparent">
          <i data-lucide="shield-alert" class="w-4 h-4 mt-0.5 shrink-0 text-rose-400"></i>
          <div>
            <div class="font-bold text-xs text-white flex items-center gap-1.5">
              <span>Enterprise Security</span>
              <span class="text-[9px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 font-mono font-semibold border border-rose-500/30">SIEM</span>
            </div>
            <div class="text-[10px] text-slate-400 mt-0.5 leading-snug">Rust Syslog 수집기, 실시간 공격 시뮬레이터 & SOC 관제</div>
          </div>
        </button>

        <!-- 3. Autonomous SRE Observability -->
        <button onclick="selectApp('sre')" id="app-nav-sre" class="app-nav-btn w-full text-left p-3 rounded-lg flex items-start gap-3 transition hover:bg-subpanel text-slate-300 border border-transparent">
          <i data-lucide="bot" class="w-4 h-4 mt-0.5 shrink-0 text-purple-400"></i>
          <div>
            <div class="font-bold text-xs text-white">Autonomous SRE</div>
            <div class="text-[10px] text-slate-400 mt-0.5 leading-snug">자율형 AI 심층 원인 진단(RCA) 및 SLO 가용성</div>
          </div>
        </button>

        <!-- 4. Manage Apps -->
        <button onclick="selectApp('manage_apps')" id="app-nav-manage_apps" class="app-nav-btn w-full text-left p-3 rounded-lg flex items-start gap-3 transition hover:bg-subpanel text-slate-300 border border-transparent">
          <i data-lucide="package-plus" class="w-4 h-4 mt-0.5 shrink-0 text-emerald-400"></i>
          <div>
            <div class="font-bold text-xs text-white">앱 관리 및 설치</div>
            <div class="text-[10px] text-slate-400 mt-0.5 leading-snug">앱 생태계 On/Off 토글 및 신규 플러그인 추가</div>
          </div>
        </button>
      </nav>

      <!-- Apps Footer / System Telemetry -->
      <div class="p-3 border-t border-bordercolor bg-panelbg/60 text-[10px] text-slate-400 space-y-1.5 font-mono">
        <div class="flex items-center justify-between">
          <span class="text-slate-500">인덱스 스키마:</span>
          <span class="text-slate-300">main, logs-*</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-slate-500">Cross-Index Join:</span>
          <span class="text-emerald-400 font-bold">READY (Hash Join)</span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-slate-500">Syslog 데몬:</span>
          <span id="aside-collector-status" class="text-slate-400">RUNNING (:1514)</span>
        </div>
      </div>
    </aside>

    <!-- RIGHT ACTIVE APP WORKSPACE (앱별 독립 화면 전환 영역) -->
    <main class="flex-1 flex flex-col overflow-y-auto bg-slatebg">

      <!-- =================================================================================== -->
      <!-- APP VIEW 1: Search & Reporting (핵심 검색, Cross-Index Join, 통계 분석 뷰)            -->
      <!-- =================================================================================== -->
      <div id="view-app-search" class="app-view flex-1 flex flex-col p-6 space-y-5">
        
        <!-- Splunk Search Console Card -->
        <div class="bg-panelbg rounded-xl border border-bordercolor shadow-xl p-5 space-y-3.5">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <i data-lucide="search" class="w-4 h-4 text-emerald-400"></i>
              <h2 class="text-xs font-bold uppercase tracking-wider text-white">Splunk PPL & Cross-Index Join Search Bar</h2>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
                <i data-lucide="git-merge" class="w-3 h-3 inline mr-1"></i>BACKEND JOIN ENABLED
              </span>
            </div>
            <div class="text-[11px] text-slate-400 font-mono">
              색인: <span class="text-slate-200">main</span> (보안 Syslog) | <span class="text-slate-200">logccino-logs-*</span> (앱 분산로그)
            </div>
          </div>

          <!-- Splunk Search Input & Execution Button -->
          <div class="flex items-start gap-2.5">
            <div class="flex-1 relative">
              <textarea id="search-query-input" rows="2" class="w-full bg-slatebg border border-bordercolor focus:border-indigo-500 rounded-lg p-3 text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none leading-relaxed resize-y" placeholder="Splunk PPL 또는 Join 쿼리를 입력하세요 (예: source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ])">source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ]</textarea>
            </div>
            <button onclick="executeSplunkSearch()" id="btn-search-run" class="px-5 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 transition shadow-lg shadow-emerald-600/20 shrink-0">
              <i data-lucide="play" class="w-4 h-4"></i>
              <span>검색 (Search)</span>
            </button>
          </div>

          <!-- Splunk Cross-Index Join Quick Presets -->
          <div class="flex items-center gap-2 overflow-x-auto scrollbar-thin pt-1 text-[11px]">
            <span class="text-[10px] uppercase font-bold text-slate-400 shrink-0 flex items-center gap-1">
              <i data-lucide="zap" class="w-3 h-3 text-amber-400"></i> Join 프리셋:
            </span>
            <button onclick="setSearchPreset('source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ]')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 font-medium transition shrink-0">
              🔗 [JOIN] 보안 로그 x 앱 로그 호스트 매핑
            </button>
            <button onclick="setSearchPreset('source = logccino-logs-* where level = \'ERROR\' | head 50 | join type=left service [ source = logccino-logs-* | stats count() as total_logs by service ]')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 font-medium transition shrink-0">
              🔗 [JOIN] 에러 로그 x 서비스 전체 처리량 조인
            </button>
            <button onclick="setSearchPreset('source = logccino-logs-* | stats count() by service, level')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 font-medium transition shrink-0">
              📊 [PPL] 서비스별 에러율 및 심각도 집계
            </button>
            <button onclick="setSearchPreset('source = main | head 30 | fields @timestamp, host, event_type, message')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor hover:border-indigo-500/40 text-slate-300 font-medium transition shrink-0">
              🛡️ [MAIN] 보안 Syslog 원천 로그 탐색
            </button>
          </div>
        </div>

        <!-- Search Results Tabs Container -->
        <div class="bg-panelbg rounded-xl border border-bordercolor shadow-xl flex-1 flex flex-col overflow-hidden min-h-[460px]">
          <!-- Result Tabs Header -->
          <div class="flex items-center justify-between border-b border-bordercolor px-4 bg-subpanel/80">
            <div class="flex">
              <button onclick="switchSearchTab('statistics')" id="subtab-statistics" class="px-4 py-3 text-xs font-bold border-b-2 border-emerald-500 text-emerald-300 flex items-center gap-1.5 transition">
                <i data-lucide="table" class="w-3.5 h-3.5"></i> 통계 테이블 (Statistics: <span id="search-stats-count">0</span>)
              </button>
              <button onclick="switchSearchTab('events')" id="subtab-events" class="px-4 py-3 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
                <i data-lucide="file-text" class="w-3.5 h-3.5"></i> 이벤트 원천 로그 (Events)
              </button>
              <button onclick="switchSearchTab('charts')" id="subtab-charts" class="px-4 py-3 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
                <i data-lucide="bar-chart-2" class="w-3.5 h-3.5"></i> 시각화 차트 (Visualizations)
              </button>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-400 font-mono">
              <span id="search-execution-info">Ready to search</span>
            </div>
          </div>

          <!-- Result Tab 1: Statistics (통계 및 Join 결과 테이블) -->
          <div id="content-search-statistics" class="flex-1 p-4 overflow-auto scrollbar-thin">
            <div id="statistics-table-container" class="overflow-x-auto">
              <p class="text-center py-20 text-slate-500 text-xs">
                상단 검색창에서 PPL 또는 Cross-Index Join 쿼리를 실행하면 통계 집계 및 조인 결과 테이블이 여기에 렌더링됩니다.
              </p>
            </div>
          </div>

          <!-- Result Tab 2: Events (원천 로그 뷰어) -->
          <div id="content-search-events" class="flex-1 p-4 overflow-y-auto scrollbar-thin hidden">
            <div id="search-events-list" class="space-y-2 text-xs">
              <p class="text-center py-20 text-slate-500 text-xs">검색 실행 결과 원천 이벤트 목록이 여기에 표시됩니다.</p>
            </div>
          </div>

          <!-- Result Tab 3: Visualizations (차트) -->
          <div id="content-search-charts" class="flex-1 p-4 overflow-y-auto scrollbar-thin hidden">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="bg-slatebg p-3 rounded-lg border border-bordercolor">
                <h3 class="text-xs font-semibold text-slate-300 mb-2">서비스별 처리량 vs 에러</h3>
                <div id="chart-services-search" class="w-full h-56"></div>
              </div>
              <div class="bg-slatebg p-3 rounded-lg border border-bordercolor">
                <h3 class="text-xs font-semibold text-slate-300 mb-2">심각도 분포</h3>
                <div id="chart-levels-search" class="w-full h-56"></div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- =================================================================================== -->
      <!-- APP VIEW 2: Enterprise Security (SIEM) - 독립 추출된 보안 관제 앱                   -->
      <!-- =================================================================================== -->
      <div id="view-app-siem" class="app-view flex-1 flex flex-col p-6 space-y-5 hidden">
        <div id="content-security" class="siem-feature flex flex-col space-y-5">
        <!-- SIEM Header -->
        <div class="flex items-center justify-between bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <i data-lucide="shield-alert" class="w-5 h-5"></i>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="font-bold text-sm text-white">Logccino Enterprise Security (ES / SIEM)</h2>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">PLUGGABLE APP ACTIVE</span>
              </div>
              <p class="text-xs text-slate-400 mt-0.5">Rust 고성능 보안 Syslog 수집기, MITRE ATT&CK 상관분석 및 자율 침해사고 대응 콘솔</p>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button onclick="selectApp('manage_apps')" class="px-3 py-1.5 rounded bg-subpanel hover:bg-slate-800 text-slate-300 border border-bordercolor text-xs transition">
              앱 설정 관리
            </button>
            <button onclick="loadSecurityEvents()" class="px-3 py-1.5 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs flex items-center gap-1.5 transition">
              <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i> 즉시 갱신
            </button>
          </div>
        </div>

        <!-- Rust Syslog Collector Controller Card -->
        <div class="p-4 bg-panelbg rounded-xl border border-bordercolor shadow-xl space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <span class="w-2.5 h-2.5 rounded-full bg-slate-500" id="collector-status-dot"></span>
              <span class="font-bold text-white text-xs">Rust High-Performance Syslog Engine (Port: 1514)</span>
              <span id="collector-status-badge" class="px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-400 border border-slate-700">CHECKING...</span>
            </div>
            <div class="flex items-center gap-2">
              <button onclick="startCollector()" id="btn-col-start" class="px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs flex items-center gap-1 transition">
                <i data-lucide="play" class="w-3 h-3"></i> 시작
              </button>
              <button onclick="stopCollector()" id="btn-col-stop" class="px-3 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs flex items-center gap-1 transition">
                <i data-lucide="square" class="w-3 h-3"></i> 중지
              </button>
              <button onclick="restartCollector()" id="btn-col-restart" class="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs flex items-center gap-1 transition border border-slate-700">
                <i data-lucide="refresh-cw" class="w-3 h-3"></i> 재시작
              </button>
            </div>
          </div>

          <!-- Collector Telemetry Metrics -->
          <div class="grid grid-cols-4 gap-3 pt-2 border-t border-bordercolor/60 text-center">
            <div class="bg-slatebg p-3 rounded-lg border border-bordercolor/50">
              <span class="text-[10px] uppercase text-slate-400 block font-semibold">수신 패킷 (Rx)</span>
              <span class="font-mono font-bold text-slate-100 text-sm" id="sec-rx">0</span>
            </div>
            <div class="bg-slatebg p-3 rounded-lg border border-bordercolor/50">
              <span class="text-[10px] uppercase text-slate-400 block font-semibold">ECS 파싱 (Parsed)</span>
              <span class="font-mono font-bold text-indigo-400 text-sm" id="sec-parsed">0</span>
            </div>
            <div class="bg-slatebg p-3 rounded-lg border border-bordercolor/50">
              <span class="text-[10px] uppercase text-slate-400 block font-semibold">OpenSearch 'main' 인덱싱</span>
              <span class="font-mono font-bold text-emerald-400 text-sm" id="sec-fwd">0</span>
            </div>
            <div class="bg-slatebg p-3 rounded-lg border border-bordercolor/50">
              <span class="text-[10px] uppercase text-slate-400 block font-semibold">위협 경고 (Alerts)</span>
              <span class="font-mono font-bold text-rose-400 text-sm" id="sec-threats">0</span>
            </div>
          </div>
        </div>

        <!-- Real-time Attack Simulator Bar -->
        <div class="p-4 bg-panelbg rounded-xl border border-bordercolor shadow-xl space-y-2.5">
          <div class="flex items-center justify-between">
            <span class="font-bold text-slate-200 flex items-center gap-2 text-xs">
              <i data-lucide="target" class="w-4 h-4 text-rose-400"></i> 실시간 보안 위협 시뮬레이션 패킷 발송기
            </span>
            <span id="inject-status-msg" class="text-xs font-mono text-emerald-400"></span>
          </div>
          <div class="flex flex-wrap gap-2">
            <button onclick="injectTestEvent('ssh_failed')" class="px-3 py-1.5 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 text-xs font-medium transition flex items-center gap-1.5">
              <i data-lucide="shield-alert" class="w-3.5 h-3.5"></i> SSH 무차별대입 공격 패킷
            </button>
            <button onclick="injectTestEvent('sudo_failed')" class="px-3 py-1.5 rounded bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 text-xs font-medium transition flex items-center gap-1.5">
              <i data-lucide="key" class="w-3.5 h-3.5"></i> 의심스러운 Sudo 권한 상승 패킷
            </button>
            <button onclick="injectTestEvent('port_scan')" class="px-3 py-1.5 rounded bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-medium transition flex items-center gap-1.5">
              <i data-lucide="radio" class="w-3.5 h-3.5"></i> 방화벽 인바운드 포트 스캔 패킷
            </button>
          </div>
        </div>

        <!-- Live Security Incidents Stream Table -->
        <div class="bg-panelbg rounded-xl border border-bordercolor shadow-xl p-4 flex-1 flex flex-col min-h-[350px]">
          <h3 class="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
            <i data-lucide="shield" class="w-4 h-4 text-rose-400"></i> 최근 탐지된 실시간 보안 침해 이벤트 (main Index)
          </h3>
          <div id="sec-events-container" class="flex-1 overflow-y-auto scrollbar-thin space-y-2">
            <p class="text-center py-16 text-slate-500 text-xs">수신된 보안 이벤트가 로드 중입니다...</p>
          </div>
        </div>
        </div>
      </div>

      <!-- =================================================================================== -->
      <!-- APP VIEW 3: Autonomous SRE Observability (대화형 RCA 및 SLO 가용성 뷰)               -->
      <!-- =================================================================================== -->
      <div id="view-app-sre" class="app-view flex-1 flex flex-col p-6 space-y-5 hidden">
        
        <!-- Executive KPI Metrics Bar -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
            <div>
              <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <i data-lucide="activity" class="w-3.5 h-3.5 text-indigo-400"></i>
                <span>전사 서비스 가용성 (SLO)</span>
              </div>
              <div class="flex items-baseline gap-2">
                <span class="text-xl font-bold font-mono text-emerald-400">99.70%</span>
                <span class="text-[11px] text-slate-400">목표 99.90%</span>
              </div>
              <p class="text-[10px] text-amber-400 font-mono mt-0.5">⚠️ Error Budget 잔여: 70% | MTTR: 4.2m</p>
            </div>
            <div class="w-10 h-10 rounded bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <i data-lucide="check-circle-2" class="w-5 h-5"></i>
            </div>
          </div>

          <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
            <div>
              <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <i data-lucide="database" class="w-3.5 h-3.5 text-emerald-400"></i>
                <span>색인 로그 총 볼륨</span>
              </div>
              <div class="flex items-baseline gap-2">
                <span class="text-xl font-bold font-mono text-white" id="total-logs-stat">0 docs</span>
              </div>
              <p class="text-[10px] text-emerald-400 font-mono mt-0.5">1 Node / 1 Shard</p>
            </div>
            <div class="w-10 h-10 rounded bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <i data-lucide="layers" class="w-5 h-5"></i>
            </div>
          </div>

          <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
            <div>
              <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <i data-lucide="cpu" class="w-3.5 h-3.5 text-amber-400"></i>
                <span>활성 AI 에이전트 모델</span>
              </div>
              <div class="flex items-baseline gap-2">
                <span class="text-xl font-bold font-mono text-amber-400">gpt-6-luna</span>
              </div>
              <p class="text-[10px] text-slate-400 font-mono mt-0.5">OpenAI SRE Agent Provider</p>
            </div>
            <div class="w-10 h-10 rounded bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
              <i data-lucide="sparkles" class="w-5 h-5"></i>
            </div>
          </div>

          <div class="bg-panelbg p-3.5 rounded-lg border border-bordercolor flex items-center justify-between">
            <div>
              <div class="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
                <i data-lucide="bot" class="w-3.5 h-3.5 text-purple-400"></i>
                <span>자율형 RCA 엔진</span>
              </div>
              <div class="flex items-baseline gap-2">
                <span class="text-xl font-bold font-mono text-purple-400">OPERATIONAL</span>
              </div>
              <p class="text-[10px] text-slate-400 font-mono mt-0.5">PPL 컴파일러 & 이상 탐지 가동</p>
            </div>
            <div class="w-10 h-10 rounded bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <i data-lucide="sparkles" class="w-5 h-5"></i>
            </div>
          </div>
        </div>

        <!-- SRE Chat & Investigation Console -->
        <div class="bg-panelbg rounded-xl border border-bordercolor shadow-2xl flex-1 flex flex-col overflow-hidden min-h-[500px]">
          <div class="px-5 py-3 border-b border-bordercolor bg-subpanel/80 flex items-center justify-between">
            <div class="flex items-center gap-2">
              <i data-lucide="terminal" class="w-4 h-4 text-indigo-400"></i>
              <h2 class="text-xs font-bold uppercase tracking-wider text-slate-200">Autonomous SRE Incident Investigation Console</h2>
            </div>
            <button onclick="clearChat()" class="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition p-1" title="대화 세션 초기화">
              <i data-lucide="rotate-ccw" class="w-3.5 h-3.5"></i> 초기화
            </button>
          </div>

          <!-- Quick Presets -->
          <div class="px-5 py-2.5 bg-slatebg/70 border-b border-bordercolor flex items-center gap-2 overflow-x-auto scrollbar-thin">
            <span class="text-[10px] uppercase font-bold text-slate-400 shrink-0">긴급 진단:</span>
            <button onclick="sendQuickPrompt('결제 서비스(payment-service) 타임아웃 및 서킷브레이커 장애 원인 분석해줘')" class="text-[11px] bg-subpanel hover:bg-indigo-600/20 border border-bordercolor text-slate-300 px-2.5 py-1 rounded transition shrink-0">
              [P1 INCIDENT] 결제 타임아웃 RCA
            </button>
            <button onclick="sendQuickPrompt('전사 마이크로서비스 24시간 가용성 및 에러율 집계 요약해줘')" class="text-[11px] bg-subpanel hover:bg-indigo-600/20 border border-bordercolor text-slate-300 px-2.5 py-1 rounded transition shrink-0">
              [SLA AUDIT] 전사 에러율 매트릭스
            </button>
            <button onclick="sendQuickPrompt('notification-service 429 쿼터 초과 및 발송 실패 원인 분석해줘')" class="text-[11px] bg-subpanel hover:bg-indigo-600/20 border border-bordercolor text-slate-300 px-2.5 py-1 rounded transition shrink-0">
              [ANOMALY] 알림 쿼터 초과 진단
            </button>
          </div>

          <!-- Chat Messages Area -->
          <div id="chat-messages" class="flex-1 p-5 overflow-y-auto space-y-4 text-xs scrollbar-thin">
            <div class="flex gap-3 text-slate-300">
              <div class="w-7 h-7 rounded-md bg-indigo-600/30 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/30">
                <i data-lucide="bot" class="w-4 h-4"></i>
              </div>
              <div class="space-y-1.5 max-w-[85%]">
                <div class="font-bold text-indigo-400 flex items-center gap-1.5">
                  Logccino SRE Agent <span class="text-[10px] font-mono text-slate-500 font-normal">Autonomous RCA</span>
                </div>
                <div class="p-3.5 rounded-lg bg-subpanel/70 border border-bordercolor leading-relaxed">
                  안녕하세요! 자율형 SRE 에이전트입니다. 전사 OpenSearch 분산 로그 클러스터와 연결되어 있습니다. 장애 원인 분석(RCA), 에러 패턴 검색, PPL 조인 질의 등을 요청하시면 자율적으로 쿼리를 생성하고 근거 데이터를 추론하여 보고합니다.
                </div>
              </div>
            </div>
          </div>

          <!-- Chat Input Bar -->
          <div class="p-4 border-t border-bordercolor bg-subpanel/40">
            <form onsubmit="handleChatSubmit(event)" class="flex gap-2">
              <input type="text" id="chat-input" class="flex-1 bg-slatebg border border-bordercolor rounded-lg px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono transition" placeholder="장애 원인 진단 질문 입력 (예: payment-service 타임아웃 원인 분석해줘)...">
              <button type="submit" id="chat-submit-btn" class="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition shrink-0">
                <i data-lucide="send" class="w-3.5 h-3.5"></i>
                <span>질문</span>
              </button>
            </form>
          </div>
        </div>

      </div>

      <!-- =================================================================================== -->
      <!-- APP VIEW 4: Manage Apps (Splunk 플러그형 앱 생태계 및 설치 관리)                     -->
      <!-- =================================================================================== -->
      <div id="view-app-manage_apps" class="app-view flex-1 flex flex-col p-6 space-y-5 hidden">
        <!-- Apps Ecosystem Header -->
        <div class="flex items-center justify-between bg-panelbg p-5 rounded-xl border border-bordercolor shadow-md">
          <div>
            <div class="flex items-center gap-2">
              <i data-lucide="package" class="w-5 h-5 text-emerald-400"></i>
              <h2 class="font-bold text-sm text-white">Logccino Enterprise Apps Ecosystem & Extension Manager</h2>
            </div>
            <p class="text-xs text-slate-400 mt-1">Splunk Enterprise 앱 생태계와 동일하게 독립된 앱을 추가 설치하거나, SIEM 등 특정 보안/관제 기능을 실시간으로 활성화/비활성화할 수 있습니다.</p>
          </div>
          <button onclick="openInstallAppModal()" class="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 transition shadow-lg shadow-emerald-600/20">
            <i data-lucide="plus-circle" class="w-4 h-4"></i>
            <span>새 앱 패키지 설치 (+ Install App)</span>
          </button>
        </div>

        <!-- Installed Apps Cards Container -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5" id="installed-apps-grid">
          <!-- Rendered dynamically by JS -->
        </div>
      </div>

    </main>
  </div>

  <!-- =================================================================================== -->
  <!-- 3. Modals (Log Detail, Alerts, Users/Roles RBAC, Install App)                       -->
  <!-- =================================================================================== -->

  <!-- Log Modal -->
  <div id="log-modal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-panelbg border border-bordercolor rounded-xl w-full max-w-3xl overflow-hidden shadow-2xl">
      <div class="px-5 py-3 border-b border-bordercolor flex items-center justify-between bg-subpanel/50">
        <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
          <i data-lucide="file-json" class="w-4 h-4 text-emerald-400"></i>
          <span>원본 로그 레코드 (Raw OpenSearch Document)</span>
        </h3>
        <button onclick="closeLogModal()" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
      </div>
      <div class="p-5 max-h-[70vh] overflow-y-auto">
        <pre id="modal-json" class="bg-slatebg p-4 rounded-lg border border-bordercolor text-emerald-400 text-xs overflow-x-auto font-mono leading-relaxed"></pre>
      </div>
    </div>
  </div>

  <!-- Install App Modal -->
  <div id="install-app-modal" class="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-panelbg border border-bordercolor rounded-xl w-full max-w-lg overflow-hidden shadow-2xl">
      <div class="px-5 py-3.5 border-b border-bordercolor flex items-center justify-between bg-subpanel/80">
        <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
          <i data-lucide="package-plus" class="w-4 h-4 text-emerald-400"></i>
          <span>새로운 Splunk / Logccino 앱 패키지 설치</span>
        </h3>
        <button onclick="closeInstallAppModal()" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
      </div>
      <form onsubmit="handleInstallApp(event)" class="p-5 space-y-3.5 text-xs">
        <div>
          <label class="block text-slate-400 font-semibold mb-1">앱 ID (App ID, 소문자 식별자)</label>
          <input type="text" id="new-app-id" required placeholder="예: apm, network_security, kubernetes_audit" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none">
        </div>
        <div>
          <label class="block text-slate-400 font-semibold mb-1">앱 명칭 (Display Name)</label>
          <input type="text" id="new-app-name" required placeholder="예: Cloud APM & Distributed Tracing" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-indigo-500 focus:outline-none">
        </div>
        <div>
          <label class="block text-slate-400 font-semibold mb-1">카테고리</label>
          <select id="new-app-category" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-indigo-500 focus:outline-none">
            <option value="observability">Observability & APM</option>
            <option value="security">Security & SOC</option>
            <option value="custom">Custom Extension</option>
          </select>
        </div>
        <div>
          <label class="block text-slate-400 font-semibold mb-1">설명</label>
          <textarea id="new-app-desc" rows="2" placeholder="앱의 주요 기능 및 역할 설명" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"></textarea>
        </div>
        <div class="flex justify-end gap-2 pt-2 border-t border-bordercolor">
          <button type="button" onclick="closeInstallAppModal()" class="px-3 py-1.5 rounded bg-subpanel hover:bg-slate-800 text-slate-300">취소</button>
          <button type="submit" class="px-4 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-semibold flex items-center gap-1">
            <i data-lucide="check" class="w-3.5 h-3.5"></i> 설치 완료
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- Saved Searches & Alerts Modal -->
  <div id="new-alert-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div id="content-alerts" class="bg-panelbg border border-bordercolor rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl">
      <div class="px-5 py-3.5 border-b border-bordercolor flex items-center justify-between bg-subpanel/80">
        <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
          <i data-lucide="bell-ring" class="w-4 h-4 text-amber-400"></i>
          <span id="alert-modal-title">Splunk Saved Searches & PPL Alert Engine</span>
        </h3>
        <button onclick="closeNewAlertModal()" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
      </div>
      <form onsubmit="handleSaveAlert(event)" class="p-5 space-y-3.5 text-xs">
        <input type="hidden" id="alert-form-id">
        <div>
          <label class="block text-slate-400 font-semibold mb-1">알람 / Saved Search 명칭</label>
          <input type="text" id="alert-form-name" required class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-indigo-500 focus:outline-none">
        </div>
        <div>
          <label class="block text-slate-400 font-semibold mb-1">실행할 PPL / Join 쿼리</label>
          <textarea id="alert-form-query" rows="2" required class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none"></textarea>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-slate-400 font-semibold mb-1">Cron 스케줄</label>
            <input type="text" id="alert-form-cron" value="*/5 * * * *" required class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none">
          </div>
          <div>
            <label class="block text-slate-400 font-semibold mb-1">트리거 임계치 (Threshold)</label>
            <input type="number" id="alert-form-threshold" value="1" required class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none">
          </div>
        </div>
        <div class="flex justify-end gap-2 pt-2 border-t border-bordercolor">
          <button type="button" onclick="closeNewAlertModal()" class="px-3 py-1.5 rounded bg-subpanel text-slate-300">취소</button>
          <button type="submit" class="px-4 py-1.5 rounded bg-amber-600 hover:bg-amber-500 text-white font-semibold">저장 및 스케줄 등록</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Users & Roles RBAC Modal -->
  <div id="users-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-panelbg border border-bordercolor rounded-xl w-full max-w-4xl max-h-[85vh] overflow-hidden shadow-2xl flex flex-col">
      <div class="px-5 py-3.5 border-b border-bordercolor flex items-center justify-between bg-subpanel/80">
        <div class="flex items-center gap-2">
          <i data-lucide="users" class="w-4 h-4 text-indigo-400"></i>
          <span class="font-bold text-xs text-slate-200">Splunk 사용자 및 역할(Roles) 권한 관리 (RBAC)</span>
        </div>
        <button onclick="closeUsersModal()" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
      </div>
      <div class="p-5 overflow-y-auto flex-1 space-y-5 text-xs">
        <div>
          <h4 class="font-bold text-slate-200 mb-2 flex items-center gap-1.5"><i data-lucide="user-check" class="w-3.5 h-3.5 text-emerald-400"></i> 등록된 사용자 계정</h4>
          <div id="users-table-container"></div>
        </div>
        <div>
          <h4 class="font-bold text-slate-200 mb-2 flex items-center gap-1.5"><i data-lucide="key" class="w-3.5 h-3.5 text-amber-400"></i> Splunk 표준 역할 및 권한</h4>
          <div id="roles-cards-container" class="grid grid-cols-2 gap-3"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- =================================================================================== -->
  <!-- 4. JavaScript Logic: Splunk Layout, Apps, Join Engine, Modals, Dropdowns            -->
  <!-- =================================================================================== -->
  <script>
    let activeApp = 'search';
    let installedApps = [];
    let currentTimeWindow = "24h";
    let servicesChartInstance = null;
    let levelsChartInstance = null;
    let conversationHistory = [];

    document.addEventListener("DOMContentLoaded", () => {
      lucide.createIcons();
      fetchApps();
      fetchOverview();
      fetchCollectorStatus();
      loadSecurityEvents();
      setInterval(fetchCollectorStatus, 4000);

      // Outside click listener to close dropdowns
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.dropdown-container')) {
          closeAllDropdowns();
        }
      });
    });

    // -------------------------------------------------------------
    // Dropdown Controllers
    // -------------------------------------------------------------
    function toggleDropdown(id) {
      const el = document.getElementById(id);
      const isHidden = el.classList.contains('hidden');
      closeAllDropdowns();
      if (isHidden) {
        el.classList.remove('hidden');
      }
    }

    function closeAllDropdowns() {
      ['settings-dropdown', 'activity-dropdown', 'help-dropdown'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.classList.add('hidden');
      });
    }

    // -------------------------------------------------------------
    // App Ecosystem & App Switching
    // -------------------------------------------------------------
    async function fetchApps() {
      try {
        const res = await fetch('/api/v1/apps');
        if (res.ok) {
          installedApps = await res.json();
          renderAppsNav();
          renderManageAppsGrid();
        }
      } catch (e) {
        console.error("Failed to load apps", e);
      }
    }

    function renderAppsNav() {
      // SIEM app visibility check
      const siemApp = installedApps.find(a => a.id === 'siem');
      const isSiemEnabled = siemApp ? siemApp.enabled : true;

      const siemElements = document.querySelectorAll('.siem-app-feature, .siem-menu-item');
      siemElements.forEach(el => {
        if (isSiemEnabled) {
          el.classList.remove('hidden');
        } else {
          el.classList.add('hidden');
        }
      });

      // If active app was SIEM but it is now disabled, switch to Search
      if (activeApp === 'siem' && !isSiemEnabled) {
        selectApp('search');
      }
    }

    function selectApp(appId) {
      activeApp = appId;
      
      // Update breadcrumb
      const titles = {
        'search': 'Search & Reporting',
        'siem': 'Enterprise Security (SIEM)',
        'sre': 'Autonomous SRE Observability',
        'manage_apps': '앱 관리 및 설치 (Manage Apps)'
      };
      document.getElementById('current-app-title').textContent = titles[appId] || appId;

      // Update Nav Buttons
      document.querySelectorAll('.app-nav-btn').forEach(btn => {
        btn.className = 'app-nav-btn w-full text-left p-3 rounded-lg flex items-start gap-3 transition hover:bg-subpanel text-slate-300 border border-transparent';
      });
      const activeBtn = document.getElementById(`app-nav-${appId}`);
      if (activeBtn) {
        activeBtn.className = 'app-nav-btn w-full text-left p-3 rounded-lg flex items-start gap-3 transition bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm';
      }

      // Switch Views
      ['search', 'siem', 'sre', 'manage_apps'].forEach(view => {
        const viewEl = document.getElementById(`view-app-${view}`);
        if (viewEl) {
          if (view === appId) {
            viewEl.classList.remove('hidden');
          } else {
            viewEl.classList.add('hidden');
          }
        }
      });

      if (appId === 'search') {
        setTimeout(initCharts, 100);
      } else if (appId === 'siem') {
        loadSecurityEvents();
        fetchCollectorStatus();
      } else if (appId === 'manage_apps') {
        renderManageAppsGrid();
      }

      lucide.createIcons();
    }

    function renderManageAppsGrid() {
      const container = document.getElementById('installed-apps-grid');
      if (!container) return;

      container.innerHTML = installedApps.map(app => {
        const isEnabled = app.enabled;
        const isSystem = app.is_system;

        return `
          <div class="bg-panelbg rounded-xl border border-bordercolor p-5 flex flex-col justify-between shadow-lg space-y-4">
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <div class="w-8 h-8 rounded-lg bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <i data-lucide="${app.icon || 'box'}" class="w-4 h-4"></i>
                  </div>
                  <div>
                    <h3 class="font-bold text-xs text-white">${app.name}</h3>
                    <span class="text-[10px] text-slate-400 font-mono">v${app.version} | ${app.author}</span>
                  </div>
                </div>
                ${isSystem ? '<span class="text-[9px] px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 font-mono">CORE SYSTEM</span>' : 
                  (isEnabled ? '<span class="text-[9px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-mono font-bold">ACTIVE</span>' : 
                  '<span class="text-[9px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">DISABLED</span>')}
              </div>
              <p class="text-xs text-slate-400 leading-relaxed">${app.description}</p>
            </div>

            <div class="pt-3 border-t border-bordercolor flex items-center justify-between">
              <span class="text-[10px] uppercase font-bold text-slate-500 font-mono">${app.category}</span>
              ${isSystem ? '<span class="text-[10px] text-slate-500 font-mono">시스템 필수 앱</span>' : `
                <button onclick="toggleAppStatus('${app.id}', ${!isEnabled})" class="px-3 py-1 rounded text-xs font-semibold font-mono transition ${isEnabled ? 'bg-rose-600/20 text-rose-300 border border-rose-500/30 hover:bg-rose-600/30' : 'bg-emerald-600 hover:bg-emerald-500 text-white'}">
                  ${isEnabled ? '비활성화 (Turn OFF)' : '활성화 (Turn ON)'}
                </button>
              `}
            </div>
          </div>
        `;
      }).join('');
      lucide.createIcons();
    }

    async function toggleSiemModule() {
      const siemApp = installedApps.find(a => a.id === 'siem');
      const targetState = siemApp ? !siemApp.enabled : false;
      await toggleAppStatus('siem', targetState);
    }

    async function toggleAppStatus(appId, targetEnabled) {
      try {
        const res = await fetch(`/api/v1/apps/${appId}/toggle?enabled=${targetEnabled}`, { method: 'POST' });
        if (res.ok) {
          await fetchApps();
        }
      } catch (e) {
        console.error("Failed to toggle app", e);
      }
    }

    // -------------------------------------------------------------
    // Splunk Search & Cross-Index Join Engine
    // -------------------------------------------------------------
    function setSearchPreset(query) {
      document.getElementById('search-query-input').value = query;
      executeSplunkSearch();
    }

    async function executeSplunkSearch() {
      const query = document.getElementById('search-query-input').value.trim();
      if (!query) return;

      const infoEl = document.getElementById('search-execution-info');
      const statsContainer = document.getElementById('statistics-table-container');
      const eventsContainer = document.getElementById('search-events-list');

      infoEl.textContent = "Executing query & cross-index joins...";
      statsContainer.innerHTML = '<p class="text-center py-16 text-slate-400 text-xs animate-pulse">OpenSearch 및 백엔드 해시 조인 연산 처리 중...</p>';

      try {
        const res = await fetch('/api/v1/search/ppl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query, limit: 100 })
        });
        const data = await res.json();

        if (res.ok && data.status === 'success') {
          const hits = data.hits || [];
          const schema = data.schema || [];
          const mode = data.mode || 'ppl';

          infoEl.innerHTML = `<span class="text-emerald-400 font-bold">${hits.length} records</span> (${mode}) | Completed`;
          document.getElementById('search-stats-count').textContent = hits.length;

          // 1. Render Statistics Table
          renderStatisticsTable(schema, hits);

          // 2. Render Raw Events List
          renderEventsList(hits);

          switchSearchTab('statistics');
        } else {
          infoEl.innerHTML = `<span class="text-rose-400 font-bold">Query Error</span>`;
          statsContainer.innerHTML = `<div class="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded text-xs font-mono">${data.detail || data.error || 'Execution failed'}</div>`;
        }
      } catch (e) {
        infoEl.textContent = "Execution failed";
        statsContainer.innerHTML = `<p class="text-rose-400 text-center py-10 text-xs">검색 중 오류 발생: ${e.message}</p>`;
      }
    }

    function renderStatisticsTable(schema, rows) {
      const container = document.getElementById('statistics-table-container');
      if (!rows || rows.length === 0) {
        container.innerHTML = '<p class="text-center py-16 text-slate-500 text-xs">일치하는 결과가 없습니다.</p>';
        return;
      }

      const columns = schema.length > 0 ? schema.map(s => s.name) : Object.keys(rows[0]);

      let html = `
        <table class="w-full text-left border-collapse text-xs">
          <thead>
            <tr class="bg-subpanel border-b border-bordercolor text-slate-300 font-mono text-[11px]">
              ${columns.map(col => `<th class="p-2.5 font-bold uppercase tracking-wider">${col}</th>`).join('')}
            </tr>
          </thead>
          <tbody class="divide-y divide-bordercolor/60 font-mono">
      `;

      rows.forEach((r, idx) => {
        html += `<tr class="hover:bg-subpanel/50 transition">`;
        columns.forEach(c => {
          let val = r[c];
          if (val === null || val === undefined) val = '<span class="text-slate-600">null</span>';
          else if (typeof val === 'object') val = JSON.stringify(val);
          html += `<td class="p-2.5 text-slate-200">${val}</td>`;
        });
        html += `</tr>`;
      });

      html += `</tbody></table>`;
      container.innerHTML = html;
    }

    function renderEventsList(events) {
      const container = document.getElementById('search-events-list');
      if (!events || events.length === 0) {
        container.innerHTML = '<p class="text-center py-16 text-slate-500 text-xs">표시할 이벤트가 없습니다.</p>';
        return;
      }

      container.innerHTML = events.map(e => `
        <div class="p-3 bg-subpanel/60 rounded-lg border border-bordercolor flex items-start justify-between gap-3 font-mono">
          <div class="space-y-1 overflow-hidden">
            <div class="flex items-center gap-2">
              <span class="text-slate-400 text-[10px]">${e['@timestamp'] || new Date().toISOString()}</span>
              <span class="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 font-bold text-[10px]">${e.service || e.host || 'system'}</span>
              ${e.level ? `<span class="px-1.5 py-0.2 rounded ${e.level === 'ERROR' ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'} font-bold text-[10px]">${e.level}</span>` : ''}
            </div>
            <p class="text-slate-200 text-xs truncate">${e.message || JSON.stringify(e)}</p>
          </div>
          <button onclick="openLogModal(${JSON.stringify(e).replace(/"/g, '&quot;')})" class="px-2 py-1 rounded bg-slate800 hover:bg-slate-700 text-slate-300 text-[11px] shrink-0 border border-slate-700">JSON</button>
        </div>
      `).join('');
    }

    function switchSearchTab(tab) {
      ['statistics', 'events', 'charts'].forEach(t => {
        const el = document.getElementById(`content-search-${t}`);
        const btn = document.getElementById(`subtab-${t}`);
        if (el) el.classList.add('hidden');
        if (btn) btn.className = 'px-4 py-3 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition';
      });

      const activeEl = document.getElementById(`content-search-${tab}`);
      const activeBtn = document.getElementById(`subtab-${tab}`);
      if (activeEl) activeEl.classList.remove('hidden');
      if (activeBtn) activeBtn.className = 'px-4 py-3 text-xs font-bold border-b-2 border-emerald-500 text-emerald-300 flex items-center gap-1.5 transition';

      if (tab === 'charts') {
        setTimeout(initCharts, 50);
      }
      lucide.createIcons();
    }

    // -------------------------------------------------------------
    // Security Syslog Collector & SOC Console
    // -------------------------------------------------------------
    async function fetchCollectorStatus() {
      try {
        const res = await fetch('/api/v1/collector/status');
        const data = await res.json();
        const isRunning = data.status === 'running';
        const badge = document.getElementById('collector-status-badge');
        const dot = document.getElementById('collector-status-dot');
        const asideCol = document.getElementById('aside-collector-status');
        const m = data.metrics || {};

        if (badge && dot) {
          if (isRunning) {
            badge.textContent = `RUNNING (PID: ${data.pid || 'live'})`;
            badge.className = 'px-2 py-0.5 rounded font-mono text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';
            dot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse';
            if (asideCol) asideCol.textContent = 'RUNNING (:1514)';
          } else {
            badge.textContent = 'STOPPED';
            badge.className = 'px-2 py-0.5 rounded font-mono text-[10px] bg-slate-800 text-slate-400 border border-slate-700';
            dot.className = 'w-2.5 h-2.5 rounded-full bg-slate-500';
            if (asideCol) asideCol.textContent = 'STOPPED';
          }
        }

        const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setTxt('sec-rx', (m.received_total || 0).toLocaleString());
        setTxt('sec-parsed', (m.parsed_total || 0).toLocaleString());
        setTxt('sec-fwd', (m.forwarded_total || 0).toLocaleString());
        setTxt('sec-threats', (m.security_alerts_total || 0).toLocaleString());
      } catch (e) {
        console.error("Collector fetch failed", e);
      }
    }

    async function loadSecurityEvents() {
      try {
        const res = await fetch('/api/v1/collector/events?limit=25');
        const data = await res.json();
        const container = document.getElementById('sec-events-container');
        if (!container) return;

        if (data.events && data.events.length > 0) {
          container.innerHTML = data.events.map(ev => {
            const isAlert = ev.event_type === 'alert' || (ev.security && ev.security.action === 'blocked');
            return `
              <div class="p-3 bg-subpanel/50 rounded-lg border ${isAlert ? 'border-rose-500/40 bg-rose-500/5' : 'border-bordercolor'} flex items-start justify-between text-xs font-mono">
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <span class="text-slate-400 text-[10px]">${ev['@timestamp'] || ''}</span>
                    <span class="px-1.5 py-0.2 rounded font-bold text-[10px] ${isAlert ? 'bg-rose-500/20 text-rose-300' : 'bg-indigo-500/20 text-indigo-300'}">${ev.event_type || 'syslog'}</span>
                    <span class="text-slate-300 font-semibold">${ev.host || 'host'} &bull; ${ev.service || 'auth'}</span>
                  </div>
                  <p class="text-slate-200">${ev.message || ''}</p>
                </div>
                <button onclick="openLogModal(${JSON.stringify(ev).replace(/"/g, '&quot;')})" class="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] shrink-0 border border-slate-700">JSON</button>
              </div>
            `;
          }).join('');
        } else {
          container.innerHTML = '<p class="text-slate-500 text-center py-12 text-xs">현재 저장된 보안 이벤트가 없습니다.</p>';
        }
      } catch (e) {
        console.error("Failed to load security events", e);
      }
    }

    async function injectTestEvent(kind) {
      const msg = document.getElementById('inject-status-msg');
      msg.textContent = '시뮬레이션 발송 중...';
      try {
        const res = await fetch(`/api/v1/collector/test-inject?kind=${kind}`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
          msg.textContent = `✓ [성공] ${data.simulated_event.event_type} 인덱싱 완료`;
          setTimeout(loadSecurityEvents, 500);
          setTimeout(() => { msg.textContent = ''; }, 3000);
        }
      } catch (e) {
        msg.textContent = `✗ 실패: ${e.message}`;
      }
    }

    async function startCollector() { await fetch('/api/v1/collector/start', { method: 'POST' }); fetchCollectorStatus(); }
    async function stopCollector() { await fetch('/api/v1/collector/stop', { method: 'POST' }); fetchCollectorStatus(); }
    async function restartCollector() { await fetch('/api/v1/collector/restart', { method: 'POST' }); fetchCollectorStatus(); }

    // -------------------------------------------------------------
    // SRE Chat & Telemetry Overview
    // -------------------------------------------------------------
    async function fetchOverview() {
      try {
        const res = await fetch('/api/v1/admin/overview');
        const data = await res.json();
        if (data.status === 'success') {
          const c = data.cluster || {};
          const isHealthy = c.status === 'green' || c.opensearch_connected;
          document.getElementById('os-status').textContent = isHealthy ? 'HEALTHY (2.18.0)' : 'DEGRADED';
          document.getElementById('os-indicator').className = isHealthy ? 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse' : 'w-2 h-2 rounded-full bg-rose-500';
          document.getElementById('total-logs-stat').textContent = (c.total_indexed_logs || 0).toLocaleString() + ' docs';
          renderOverviewCharts(data.services_summary || []);
        }
      } catch (e) {
        console.error("Overview error", e);
      }
    }

    function initCharts() {
      if (!servicesChartInstance) {
        const el = document.getElementById('chart-services-search');
        if (el) servicesChartInstance = echarts.init(el);
      }
      if (!levelsChartInstance) {
        const el = document.getElementById('chart-levels-search');
        if (el) levelsChartInstance = echarts.init(el);
      }
      fetchOverview();
    }

    function renderOverviewCharts(services) {
      if (!servicesChartInstance) initCharts();
      if (!servicesChartInstance) return;

      const names = services.map(s => s.name);
      const totals = services.map(s => s.total);
      const errors = services.map(s => s.error_count);

      servicesChartInstance.setOption({
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: names, axisLabel: { color: '#94a3b8' } },
        yAxis: { type: 'value', axisLabel: { color: '#94a3b8' } },
        series: [
          { name: 'Total', type: 'bar', data: totals, itemStyle: { color: '#6366f1' } },
          { name: 'Errors', type: 'bar', data: errors, itemStyle: { color: '#f43f5e' } }
        ]
      });

      let totalErr = errors.reduce((a, b) => a + b, 0);
      let totalAll = totals.reduce((a, b) => a + b, 0);
      let totalInfo = Math.max(0, totalAll - totalErr);

      if (levelsChartInstance) {
        levelsChartInstance.setOption({
          backgroundColor: 'transparent',
          tooltip: { trigger: 'item' },
          series: [{
            type: 'pie',
            radius: ['40%', '70%'],
            data: [
              { value: totalInfo, name: 'INFO / Normal', itemStyle: { color: '#10b981' } },
              { value: totalErr, name: 'ERROR / Alert', itemStyle: { color: '#f43f5e' } }
            ],
            label: { color: '#e2e8f0', fontSize: 11 }
          }]
        });
      }
    }

    function sendQuickPrompt(prompt) {
      selectApp('sre');
      document.getElementById('chat-input').value = prompt;
      handleChatSubmit();
    }

    async function handleChatSubmit(e) {
      if (e) e.preventDefault();
      const input = document.getElementById('chat-input');
      const text = input.value.trim();
      if (!text) return;

      const container = document.getElementById('chat-messages');
      container.innerHTML += `
        <div class="flex gap-3 text-slate-200 justify-end">
          <div class="p-3.5 rounded-lg bg-indigo-600/30 border border-indigo-500/40 max-w-[85%] font-medium leading-relaxed">${text}</div>
          <div class="w-7 h-7 rounded-md bg-indigo-600 text-white flex items-center justify-center shrink-0 text-xs font-bold">U</div>
        </div>
      `;
      input.value = '';
      container.scrollTop = container.scrollHeight;

      try {
        const res = await fetch('/api/v1/analysis/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, history: conversationHistory })
        });
        const data = await res.json();
        const reply = data.reply || data.response || "분석 완료되었습니다.";
        conversationHistory.push({ role: 'user', content: text }, { role: 'assistant', content: reply });

        container.innerHTML += `
          <div class="flex gap-3 text-slate-300">
            <div class="w-7 h-7 rounded-md bg-indigo-600/30 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/30">
              <i data-lucide="bot" class="w-4 h-4"></i>
            </div>
            <div class="space-y-1.5 max-w-[85%]">
              <div class="font-bold text-indigo-400">Logccino SRE Agent</div>
              <div class="p-3.5 rounded-lg bg-subpanel/70 border border-bordercolor leading-relaxed whitespace-pre-wrap">${reply}</div>
            </div>
          </div>
        `;
        lucide.createIcons();
        container.scrollTop = container.scrollHeight;
      } catch (err) {
        container.innerHTML += `<div class="p-3 rounded bg-rose-500/10 text-rose-300 text-xs">분석 요청 실패: ${err.message}</div>`;
      }
    }

    function clearChat() {
      conversationHistory = [];
      document.getElementById('chat-messages').innerHTML = `
        <div class="flex gap-3 text-slate-300">
          <div class="w-7 h-7 rounded-md bg-indigo-600/30 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-500/30">
            <i data-lucide="bot" class="w-4 h-4"></i>
          </div>
          <div class="space-y-1.5 max-w-[85%]">
            <div class="font-bold text-indigo-400">Logccino SRE Agent</div>
            <div class="p-3.5 rounded-lg bg-subpanel/70 border border-bordercolor leading-relaxed">대화 세션이 초기화되었습니다.</div>
          </div>
        </div>
      `;
      lucide.createIcons();
    }

    function setTimeWindow(tw) {
      currentTimeWindow = tw;
      ['15m', '1h', '24h', '7d'].forEach(w => {
        const btn = document.getElementById(`tw-${w}`);
        if (btn) btn.className = w === tw ? 'px-2 py-1 rounded bg-indigo-600 text-white font-semibold shadow-sm' : 'px-2 py-1 rounded hover:text-white transition';
      });
      fetchOverview();
    }

    // -------------------------------------------------------------
    // Modals Controls (Saved Searches, Users/Roles, Log Modal, App Install)
    // -------------------------------------------------------------
    function openLogModal(log) {
      document.getElementById('modal-json').textContent = JSON.stringify(log, null, 2);
      document.getElementById('log-modal').classList.remove('hidden');
    }
    function closeLogModal() { document.getElementById('log-modal').classList.add('hidden'); }

    function openSavedSearchesModal() {
      document.getElementById('new-alert-modal').classList.remove('hidden');
    }
    function closeNewAlertModal() { document.getElementById('new-alert-modal').classList.add('hidden'); }

    async function handleSaveAlert(e) {
      e.preventDefault();
      const payload = {
        name: document.getElementById('alert-form-name').value,
        query: document.getElementById('alert-form-query').value,
        cron_schedule: document.getElementById('alert-form-cron').value,
        alert_threshold: parseInt(document.getElementById('alert-form-threshold').value) || 1,
        is_active: true
      };
      await fetch('/api/v1/saved-searches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      closeNewAlertModal();
      alert("알람 규칙 및 스케줄러가 성공적으로 등록되었습니다!");
    }

    async function openUsersModal() {
      document.getElementById('users-modal').classList.remove('hidden');
      loadUsersAndRoles();
    }
    function closeUsersModal() { document.getElementById('users-modal').classList.add('hidden'); }

    async function loadUsersAndRoles() {
      try {
        const [uRes, rRes] = await Promise.all([fetch('/api/v1/users'), fetch('/api/v1/roles')]);
        const users = await uRes.json();
        const roles = await rRes.json();

        // Render users
        document.getElementById('users-table-container').innerHTML = `
          <table class="w-full text-left border border-bordercolor rounded overflow-hidden">
            <thead class="bg-subpanel text-slate-300 font-mono text-[11px]">
              <tr><th class="p-2">사용자 ID</th><th class="p-2">이름</th><th class="p-2">역할(Roles)</th><th class="p-2">기본 인덱스</th><th class="p-2">상태</th></tr>
            </thead>
            <tbody class="divide-y divide-bordercolor">
              ${users.map(u => `
                <tr class="hover:bg-subpanel/50">
                  <td class="p-2 font-bold text-white">${u.username}</td>
                  <td class="p-2 text-slate-300">${u.full_name || ''}</td>
                  <td class="p-2">${(u.roles || []).map(r => `<span class="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono mr-1">${r}</span>`).join('')}</td>
                  <td class="p-2 font-mono text-emerald-400">${u.default_index || 'main'}</td>
                  <td class="p-2"><span class="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 text-[10px]">ACTIVE</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;

        // Render roles
        document.getElementById('roles-cards-container').innerHTML = roles.map(r => `
          <div class="bg-slatebg p-3 rounded-lg border border-bordercolor space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-bold text-white text-xs">${r.name}</span>
              <span class="text-[9px] text-slate-400 font-mono">${r.default_index || 'main'}</span>
            </div>
            <p class="text-[11px] text-slate-400">${r.description || ''}</p>
            <div class="pt-1 flex flex-wrap gap-1">
              ${(r.capabilities || []).map(c => `<span class="px-1 py-0.2 rounded bg-subpanel text-slate-300 text-[9px] font-mono">${c}</span>`).join('')}
            </div>
          </div>
        `).join('');
      } catch (e) {
        console.error("Failed to load users/roles", e);
      }
    }

    function openInstallAppModal() {
      document.getElementById('install-app-modal').classList.remove('hidden');
    }
    function closeInstallAppModal() {
      document.getElementById('install-app-modal').classList.add('hidden');
    }

    async function handleInstallApp(e) {
      e.preventDefault();
      const payload = {
        id: document.getElementById('new-app-id').value.trim(),
        name: document.getElementById('new-app-name').value.trim(),
        category: document.getElementById('new-app-category').value,
        description: document.getElementById('new-app-desc').value.trim(),
        version: "1.0.0",
        enabled: true
      };

      try {
        const res = await fetch('/api/v1/apps/install', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          closeInstallAppModal();
          await fetchApps();
          alert(`새 앱 '${payload.name}'이 성공적으로 설치되었습니다!`);
        } else {
          const err = await res.json();
          alert(`설치 실패: ${err.detail || 'Error'}`);
        }
      } catch (err) {
        alert(`오류: ${err.message}`);
      }
    }

    function copyToClipboard(text) {
      navigator.clipboard.writeText(text).then(() => {
        alert("원격 MCP SSE URL이 클립보드에 복사되었습니다: " + text);
      });
    }
  </script>
</body>
</html>
""")
