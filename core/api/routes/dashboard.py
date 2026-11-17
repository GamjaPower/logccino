"""
Enterprise Observability & Security Dashboard for Logccino
Splunk 최신 Enterprise UI 디자인:
- 사용자 로그인 기능 (기본 계정: logccino / admin, admin 롤 매핑)
- 실제 Splunk Search & Reporting 앱과 동일한 화면:
  * 앱 서브 네비게이션: Search, Analytics, Datasets, Reports, Alerts, Dashboards
  * Splunk 스타일 검색창, 시간 선택기(Last 24h), 그린 검색 버튼
  * Job 상태 바 (124 events | Job: Complete | 0.08s | Save As, Share, Export)
  * 이벤트 타임라인 히스토그램 (Event Timeline Histogram)
  * 좌측 필드 인스펙터 (Selected Fields: host, source, sourcetype / Interesting Fields: service, level, action 등) 및 필드 값 팝업
  * 결과 탭: Events(펼침 필드 테이블), Patterns, Statistics(Join/Stats 테이블), Visualization(차트)
- 독립 추출된 Enterprise Security (SIEM) 관제 앱
- Autonomous SRE 및 플러그형 앱 생태계 (앱 설치/관리)
- 모든 앱의 MCP 연동
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["UI & Dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/ui", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def get_enterprise_dashboard():
    return HTMLResponse(content=r"""<!DOCTYPE html>
<html lang="ko" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>logccino> enterprise | Autonomous Observability Platform</title>
  
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
            splunkdark: '#0b1120'
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
  <!-- 0. Splunk Enterprise Login Screen Overlay (기본 로그인: logccino / admin)            -->
  <!-- =================================================================================== -->
  <div id="splunk-login-overlay" class="fixed inset-0 bg-[#090d16] z-[100] flex items-center justify-center p-4">
    <div class="bg-panelbg border border-bordercolor rounded-2xl w-full max-w-md p-8 shadow-2xl space-y-6">
      <div class="text-center space-y-2">
        <div class="flex items-center justify-center gap-2.5">
          <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 via-indigo-600 to-emerald-400 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/20 text-base">☕</div>
          <span class="font-extrabold text-3xl tracking-tight text-white font-mono">logccino<span class="text-emerald-400 font-black">&gt;</span></span>
          <span class="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">enterprise</span>
        </div>
        <p class="text-xs text-slate-400">Logccino AI Agent-Native Observability & SIEM</p>
      </div>

      <form onsubmit="handleLoginSubmit(event)" class="space-y-4 text-xs">
        <div id="login-error-msg" class="hidden p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 font-medium"></div>

        <div>
          <label class="block text-slate-300 font-semibold mb-1.5">사용자 계정 (Username)</label>
          <div class="relative">
            <i data-lucide="user" class="w-4 h-4 text-slate-500 absolute left-3 top-3"></i>
            <input type="text" id="login-username" value="logccino" required class="w-full bg-slatebg border border-bordercolor rounded-lg pl-9 pr-3 py-2.5 text-white font-mono focus:border-emerald-500 focus:outline-none text-xs">
          </div>
        </div>

        <div>
          <label class="block text-slate-300 font-semibold mb-1.5">비밀번호 (Password)</label>
          <div class="relative">
            <i data-lucide="lock" class="w-4 h-4 text-slate-500 absolute left-3 top-3"></i>
            <input type="password" id="login-password" value="admin" required class="w-full bg-slatebg border border-bordercolor rounded-lg pl-9 pr-3 py-2.5 text-white font-mono focus:border-emerald-500 focus:outline-none text-xs">
          </div>
        </div>

        <button type="submit" id="login-submit-btn" class="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-1.5">
          <i data-lucide="log-in" class="w-4 h-4"></i>
          <span>로그인 (Sign In)</span>
        </button>

        <div class="pt-3 border-t border-bordercolor text-center text-[11px] text-slate-400 space-y-1">
          <div>기본 로그인 정보: <span class="font-mono text-emerald-400 font-bold">logccino</span> / <span class="font-mono text-emerald-400 font-bold">admin</span></div>
          <div class="text-[10px] text-slate-500">역할: <span class="text-slate-300 font-mono">admin (Enterprise Super Administrator)</span></div>
        </div>
      </form>
    </div>
  </div>

  <!-- =================================================================================== -->
  <!-- 1. Splunk Enterprise Global Navigation Header (우측 상단 풀다운 메뉴 체계)            -->
  <!-- =================================================================================== -->
  <header class="border-b border-bordercolor bg-panelbg sticky top-0 z-50 px-5 py-2 flex items-center justify-between shadow-md">
    <!-- Left Brand & App Indicator -->
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2.5">
        <div class="w-7 h-7 rounded-lg bg-gradient-to-tr from-amber-500 via-indigo-600 to-emerald-400 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/20 text-xs">☕</div>
        <span class="font-extrabold text-xl tracking-tight text-white font-mono flex items-center">
          <span>logccino</span><span class="text-emerald-400 font-black">&gt;</span>
        </span>
        <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">enterprise</span>
      </div>

      <div class="h-4 w-px bg-bordercolor"></div>

      <!-- Current App Breadcrumb -->
      <div class="flex items-center gap-2">
        <i data-lucide="layers" class="w-4 h-4 text-emerald-400"></i>
        <span class="text-xs text-slate-400">앱:</span>
        <span class="text-xs font-bold text-white font-mono" id="current-app-title">Search & Reporting</span>
      </div>
    </div>

    <!-- Right Global Menu & Pulldown Dropdowns -->
    <div class="flex items-center gap-3 text-xs">

      <!-- Cluster Telemetry Status -->
      <div class="flex items-center gap-2 px-2.5 py-1 rounded bg-subpanel border border-bordercolor">
        <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" id="os-indicator"></span>
        <span class="text-slate-400 text-[11px]">OpenSearch:</span>
        <span class="font-mono font-medium text-emerald-400 text-[11px]" id="os-status">HEALTHY (2.18.0)</span>
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
                <div class="text-[10px] text-slate-400">logccino 관리자 및 권한 설정</div>
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

      <!-- User Profile & Sign Out Dropdown -->
      <div class="relative dropdown-container">
        <button onclick="toggleDropdown('profile-dropdown')" class="flex items-center gap-2 pl-2 border-l border-bordercolor hover:text-white transition">
          <div class="w-7 h-7 rounded-full bg-emerald-600 flex items-center justify-center font-bold text-white text-xs">L</div>
          <div class="text-left">
            <span class="font-semibold text-white block leading-tight" id="header-user-name">logccino</span>
            <span class="text-[9px] text-emerald-400 font-mono" id="header-user-role">admin role</span>
          </div>
          <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400"></i>
        </button>
        <div id="profile-dropdown" class="hidden absolute right-0 mt-2 w-48 bg-panelbg border border-bordercolor rounded-lg shadow-2xl z-50 p-2 text-xs">
          <div class="px-2 py-1.5 border-b border-bordercolor/60 mb-1">
            <div class="font-bold text-white" id="dropdown-user-name">logccino</div>
            <div class="text-[10px] text-slate-400">Role: admin</div>
          </div>
          <button onclick="handleLogout()" class="w-full text-left px-2 py-1.5 rounded hover:bg-rose-500/20 text-rose-300 flex items-center gap-2 transition">
            <i data-lucide="log-out" class="w-3.5 h-3.5"></i>
            <span>로그아웃 (Sign Out)</span>
          </button>
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
    <aside class="w-60 bg-[#0b1120] border-r border-bordercolor flex flex-col shrink-0 select-none">
      <div class="p-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-bordercolor flex items-center justify-between">
        <span class="flex items-center gap-1.5"><i data-lucide="grid" class="w-3.5 h-3.5 text-emerald-400"></i> APPS</span>
        <button onclick="selectApp('manage_apps')" class="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-semibold" title="앱 관리">
          <i data-lucide="sliders" class="w-3 h-3"></i> 관리
        </button>
      </div>

      <!-- App Navigation Buttons -->
      <nav class="flex-1 p-2 space-y-1.5 overflow-y-auto scrollbar-thin" id="splunk-apps-nav">
        <!-- 1. Search & Reporting (Core App) -->
        <button onclick="selectApp('search')" id="app-nav-search" class="app-nav-btn w-full text-left p-3 rounded-lg flex items-start gap-3 transition bg-emerald-600/20 text-emerald-300 border border-emerald-500/40 shadow-sm">
          <i data-lucide="search" class="w-4 h-4 mt-0.5 shrink-0 text-emerald-400"></i>
          <div>
            <div class="font-bold text-xs text-white">Search & Reporting</div>
            <div class="text-[10px] text-slate-400 mt-0.5 leading-snug">Splunk 표준 검색, Join, 필드 탐색 & 타임라인</div>
          </div>
        </button>

        <!-- 2. Enterprise Security (SIEM) - Extracted Standalone App -->
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
      <!-- APP VIEW 1: Search & Reporting (실제 Splunk와 가장 유사한 검색 & 필드 인스펙터 화면) -->
      <!-- =================================================================================== -->
      <div id="view-app-search" class="app-view flex-1 flex flex-col">
        
        <!-- Splunk Sub-Navigation Bar (Search, Analytics, Datasets, Reports, Alerts, Dashboards) -->
        <div class="bg-subpanel/90 border-b border-bordercolor px-6 flex items-center justify-between text-xs font-semibold">
          <div class="flex">
            <button class="px-4 py-2.5 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-1.5 transition">
              <i data-lucide="search" class="w-3.5 h-3.5"></i> Search
            </button>
            <button onclick="switchSearchTab('charts')" class="px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="bar-chart-2" class="w-3.5 h-3.5"></i> Analytics
            </button>
            <button onclick="setSearchPreset('source = main,logccino-logs-* | head 50')" class="px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="database" class="w-3.5 h-3.5"></i> Datasets
            </button>
            <button onclick="openSavedSearchesModal()" class="px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="bell" class="w-3.5 h-3.5 text-amber-400"></i> Alerts & Saved Searches
            </button>
          </div>
          <div class="text-[11px] font-mono text-slate-400">
            앱: <span class="text-white font-bold">Search &amp; Reporting (v10.0.0)</span>
          </div>
        </div>

        <!-- Splunk Real Search Input & Execution Header -->
        <div class="bg-panelbg border-b border-bordercolor p-5 space-y-3">
          <div class="flex items-center gap-2">
            <!-- Search Textarea Input with Monospace font -->
            <div class="flex-1 bg-slatebg border-2 border-slate-700 focus-within:border-emerald-500 rounded-lg p-2.5 flex items-start gap-2 shadow-inner transition">
              <i data-lucide="search" class="w-4 h-4 text-emerald-400 mt-1 shrink-0"></i>
              <textarea id="search-query-input" rows="2" class="w-full bg-transparent text-xs font-mono text-slate-100 placeholder-slate-500 focus:outline-none leading-relaxed resize-y" placeholder="Splunk PPL 또는 Cross-Index Join 쿼리를 입력하세요...">source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ]</textarea>
            </div>

            <!-- Time Range Picker Dropdown -->
            <div class="relative dropdown-container shrink-0">
              <button onclick="toggleDropdown('timerange-dropdown')" id="timerange-btn" class="px-3.5 py-3 rounded-lg bg-subpanel hover:bg-slate-800 text-slate-200 border border-bordercolor text-xs font-medium flex items-center gap-2 transition">
                <i data-lucide="clock" class="w-3.5 h-3.5 text-indigo-400"></i>
                <span id="current-time-label">Last 24 hours</span>
                <i data-lucide="chevron-down" class="w-3 h-3 text-slate-400"></i>
              </button>
              <div id="timerange-dropdown" class="hidden absolute right-0 mt-2 w-48 bg-panelbg border border-bordercolor rounded-lg shadow-2xl z-50 p-2 text-xs divide-y divide-bordercolor/60">
                <div class="py-1">
                  <span class="text-[10px] uppercase font-bold text-slate-500 px-2">Presets</span>
                  <button onclick="selectSearchTime('15m', 'Last 15 minutes')" class="w-full text-left px-2 py-1.5 rounded hover:bg-subpanel text-slate-200">Last 15 minutes</button>
                  <button onclick="selectSearchTime('1h', 'Last 1 hour')" class="w-full text-left px-2 py-1.5 rounded hover:bg-subpanel text-slate-200">Last 1 hour</button>
                  <button onclick="selectSearchTime('24h', 'Last 24 hours')" class="w-full text-left px-2 py-1.5 rounded hover:bg-subpanel text-emerald-400 font-bold">Last 24 hours</button>
                  <button onclick="selectSearchTime('7d', 'Last 7 days')" class="w-full text-left px-2 py-1.5 rounded hover:bg-subpanel text-slate-200">Last 7 days</button>
                  <button onclick="selectSearchTime('all', 'All time')" class="w-full text-left px-2 py-1.5 rounded hover:bg-subpanel text-slate-200">All time</button>
                </div>
              </div>
            </div>

            <!-- Command + \ Auto-Format Button -->
            <button onclick="triggerQueryAutoFormat()" id="btn-cmd-backslash" class="px-3 py-3 rounded-lg bg-subpanel hover:bg-slate-800 text-slate-300 border border-bordercolor text-[11px] font-mono flex items-center gap-1.5 transition shrink-0 shadow-sm" title="Splunk 쿼리 자동 파싱 및 정렬 (단축키: Cmd + \ 또는 Ctrl + \)">
              <i data-lucide="code" class="w-3.5 h-3.5 text-emerald-400"></i>
              <kbd class="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 font-sans text-[10px] text-slate-300">⌘\\</kbd>
              <span>자동 파싱</span>
            </button>

            <!-- Big Green Splunk Search Button -->
            <button onclick="executeSplunkSearch()" id="btn-search-run" class="px-6 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-2 transition shadow-lg shadow-emerald-600/25 shrink-0">
              <i data-lucide="search" class="w-4 h-4"></i>
              <span>검색</span>
            </button>
          </div>

          <!-- Quick Join & PPL Presets Bar -->
          <div class="flex items-center gap-2 overflow-x-auto scrollbar-thin text-[11px] pt-1">
            <span id="format-feedback-badge" class="hidden text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 transition shrink-0 font-semibold">✓ 쿼리 자동 파싱 완료 (Cmd + \\)</span>
            <span class="text-[10px] uppercase font-bold text-slate-400 shrink-0 flex items-center gap-1">
              <i data-lucide="zap" class="w-3 h-3 text-amber-400"></i> Join 예제:
            </span>
            <button onclick="setSearchPreset('source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ]')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor text-slate-300 font-medium transition shrink-0">
              🔗 [JOIN] 보안 로그 x 앱 로그 호스트 매핑
            </button>
            <button onclick="setSearchPreset('source = logccino-logs-* where level = \'ERROR\' | head 50 | join type=left service [ source = logccino-logs-* | stats count() as total_logs by service ]')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor text-slate-300 font-medium transition shrink-0">
              🔗 [JOIN] 에러 로그 x 서비스 전체 처리량 조인
            </button>
            <button onclick="setSearchPreset('source = logccino-logs-* | stats count() by service, level')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor text-slate-300 font-medium transition shrink-0">
              📊 [PPL] 서비스별 에러율 및 심각도 집계
            </button>
            <button onclick="setSearchPreset('source = main | head 30 | fields @timestamp, host, event_type, message')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-indigo-600/20 border border-bordercolor text-slate-300 font-medium transition shrink-0">
              🛡️ [MAIN] 보안 Syslog 원천 로그 탐색
            </button>
          </div>
        </div>

        <!-- Real Splunk Job Status & Action Bar -->
        <div class="bg-subpanel/50 border-b border-bordercolor px-6 py-2 flex items-center justify-between text-xs font-mono">
          <div class="flex items-center gap-3">
            <span class="font-bold text-slate-200" id="job-event-count">0 events</span>
            <span class="text-slate-400 text-[11px]" id="job-time-range">(Last 24 hours)</span>
            <span class="text-slate-600">|</span>
            <span class="flex items-center gap-1 text-emerald-400 font-bold">
              <i data-lucide="check-circle" class="w-3.5 h-3.5"></i>
              <span id="job-status-text">Job: Complete</span>
            </span>
            <span class="text-slate-600">|</span>
            <span class="text-slate-400 text-[11px]" id="job-elapsed">0.05 seconds</span>
          </div>

          <!-- Actions Bar (Save As, Share, Export) -->
          <div class="flex items-center gap-2">
            <button onclick="openSavedSearchesModal()" class="px-2.5 py-1 rounded bg-subpanel hover:bg-slate-800 text-slate-300 border border-bordercolor text-[11px] flex items-center gap-1 transition">
              <i data-lucide="bookmark" class="w-3 h-3 text-amber-400"></i> Save As Alert
            </button>
            <button onclick="exportCurrentSearch('json')" class="px-2.5 py-1 rounded bg-subpanel hover:bg-slate-800 text-slate-300 border border-bordercolor text-[11px] flex items-center gap-1 transition">
              <i data-lucide="download" class="w-3 h-3"></i> Export
            </button>
          </div>
        </div>

        <!-- Splunk Event Timeline Histogram -->
        <div class="bg-panelbg border-b border-bordercolor px-6 py-2.5">
          <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1 font-mono">
            <span>EVENT TIMELINE (시간대별 로그 분포 히스토그램)</span>
            <span id="timeline-range-info">24h Distribution</span>
          </div>
          <div id="search-event-timeline" class="w-full h-16"></div>
        </div>

        <!-- Splunk Results Split Container: Left Fields Inspector + Right Data Tabs -->
        <div class="flex-1 flex overflow-hidden">
          
          <!-- SPLUNK LEFT FIELDS INSPECTOR (필드 인스펙터 사이드바) -->
          <aside class="w-64 bg-[#0b1120] border-r border-bordercolor flex flex-col shrink-0 select-none overflow-y-auto scrollbar-thin text-xs">
            <div class="p-3 border-b border-bordercolor">
              <input type="text" id="fields-filter-input" oninput="filterFieldsList()" placeholder="Filter fields..." class="w-full bg-slatebg border border-bordercolor rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-emerald-500 font-mono">
            </div>

            <!-- Selected Fields -->
            <div class="p-3 border-b border-bordercolor/60 space-y-2">
              <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                <span>SELECTED FIELDS</span>
                <span class="text-slate-500 font-mono">3</span>
              </div>
              <div class="space-y-1 font-mono text-[11px]" id="selected-fields-list">
                <div onclick="openFieldSummaryModal('host')" class="field-item flex items-center justify-between p-1.5 rounded hover:bg-subpanel cursor-pointer text-slate-300 hover:text-white transition">
                  <span class="flex items-center gap-1.5"><i data-lucide="tag" class="w-3 h-3 text-emerald-400"></i> host</span>
                  <span class="text-slate-500 text-[10px]">4</span>
                </div>
                <div onclick="openFieldSummaryModal('source')" class="field-item flex items-center justify-between p-1.5 rounded hover:bg-subpanel cursor-pointer text-slate-300 hover:text-white transition">
                  <span class="flex items-center gap-1.5"><i data-lucide="tag" class="w-3 h-3 text-emerald-400"></i> source</span>
                  <span class="text-slate-500 text-[10px]">2</span>
                </div>
                <div onclick="openFieldSummaryModal('sourcetype')" class="field-item flex items-center justify-between p-1.5 rounded hover:bg-subpanel cursor-pointer text-slate-300 hover:text-white transition">
                  <span class="flex items-center gap-1.5"><i data-lucide="tag" class="w-3 h-3 text-emerald-400"></i> sourcetype</span>
                  <span class="text-slate-500 text-[10px]">3</span>
                </div>
              </div>
            </div>

            <!-- Interesting Fields -->
            <div class="p-3 space-y-2">
              <div class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                <span>INTERESTING FIELDS</span>
                <span class="text-slate-500 font-mono">5</span>
              </div>
              <div class="space-y-1 font-mono text-[11px]" id="interesting-fields-list">
                <div onclick="openFieldSummaryModal('service')" class="field-item flex items-center justify-between p-1.5 rounded hover:bg-subpanel cursor-pointer text-slate-300 hover:text-white transition">
                  <span class="flex items-center gap-1.5"><i data-lucide="hash" class="w-3 h-3 text-indigo-400"></i> service</span>
                  <span class="text-slate-500 text-[10px]">5</span>
                </div>
                <div onclick="openFieldSummaryModal('level')" class="field-item flex items-center justify-between p-1.5 rounded hover:bg-subpanel cursor-pointer text-slate-300 hover:text-white transition">
                  <span class="flex items-center gap-1.5"><i data-lucide="hash" class="w-3 h-3 text-indigo-400"></i> level</span>
                  <span class="text-slate-500 text-[10px]">2</span>
                </div>
                <div onclick="openFieldSummaryModal('action')" class="field-item flex items-center justify-between p-1.5 rounded hover:bg-subpanel cursor-pointer text-slate-300 hover:text-white transition">
                  <span class="flex items-center gap-1.5"><i data-lucide="hash" class="w-3 h-3 text-indigo-400"></i> action</span>
                  <span class="text-slate-500 text-[10px]">3</span>
                </div>
                <div onclick="openFieldSummaryModal('event_type')" class="field-item flex items-center justify-between p-1.5 rounded hover:bg-subpanel cursor-pointer text-slate-300 hover:text-white transition">
                  <span class="flex items-center gap-1.5"><i data-lucide="hash" class="w-3 h-3 text-indigo-400"></i> event_type</span>
                  <span class="text-slate-500 text-[10px]">4</span>
                </div>
              </div>
            </div>
          </aside>

          <!-- RIGHT SPLUNK RESULTS WORKSPACE (Events / Patterns / Statistics / Visualization) -->
          <div class="flex-1 flex flex-col overflow-hidden bg-slatebg">
            
            <!-- Result Tabs Header -->
            <div class="flex items-center justify-between border-b border-bordercolor px-4 bg-panelbg">
              <div class="flex">
                <button onclick="switchSearchTab('events')" id="subtab-events" class="px-4 py-3 text-xs font-bold border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-1.5 transition">
                  <i data-lucide="file-text" class="w-3.5 h-3.5"></i> Events (<span id="tab-events-count">0</span>)
                </button>
                <button onclick="switchSearchTab('statistics')" id="subtab-statistics" class="px-4 py-3 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
                  <i data-lucide="table" class="w-3.5 h-3.5"></i> Statistics (<span id="tab-stats-count">0</span>)
                </button>
                <button onclick="switchSearchTab('charts')" id="subtab-charts" class="px-4 py-3 text-xs font-bold border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
                  <i data-lucide="bar-chart-2" class="w-3.5 h-3.5"></i> Visualization
                </button>
              </div>

              <!-- Events Display Format Switcher -->
              <div class="flex items-center gap-3 text-[11px] font-mono text-slate-400">
                <span>Format: <span class="text-white font-semibold">List</span></span>
                <span>Per Page: <span class="text-white font-semibold">20</span></span>
              </div>
            </div>

            <!-- TAB 1: Real Splunk Events View (원천 이벤트 & 펼침 필드 테이블) -->
            <div id="content-search-events" class="flex-1 p-4 overflow-y-auto scrollbar-thin">
              <div id="search-events-list" class="space-y-2 text-xs">
                <p class="text-center py-20 text-slate-500 text-xs">상단 검색창에서 검색 버튼을 누르면 원천 이벤트 레코드가 로드됩니다.</p>
              </div>
            </div>

            <!-- TAB 2: Splunk Statistics Table (Join / Stats 집계 테이블) -->
            <div id="content-search-statistics" class="flex-1 p-4 overflow-auto scrollbar-thin hidden">
              <div id="statistics-table-container" class="overflow-x-auto">
                <p class="text-center py-20 text-slate-500 text-xs">
                  PPL 집계(stats) 또는 Cross-Index Join 쿼리를 실행하면 통계 그리드가 여기에 출력됩니다.
                </p>
              </div>
            </div>

            <!-- TAB 3: Visualization (차트 시각화) -->
            <div id="content-search-charts" class="flex-1 p-4 overflow-y-auto scrollbar-thin hidden">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-panelbg p-4 rounded-xl border border-bordercolor">
                  <h3 class="text-xs font-semibold text-slate-200 mb-2 flex items-center gap-1.5">
                    <i data-lucide="bar-chart" class="w-3.5 h-3.5 text-emerald-400"></i> 서비스별 로그 볼륨 vs 에러 건수
                  </h3>
                  <div id="chart-services-search" class="w-full h-64"></div>
                </div>
                <div class="bg-panelbg p-4 rounded-xl border border-bordercolor">
                  <h3 class="text-xs font-semibold text-slate-200 mb-2 flex items-center gap-1.5">
                    <i data-lucide="pie-chart" class="w-3.5 h-3.5 text-indigo-400"></i> 심각도 분포 (INFO vs ERROR)
                  </h3>
                  <div id="chart-levels-search" class="w-full h-64"></div>
                </div>
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
  <!-- 3. Modals & Popups (Field Values Popup, Log Modal, Alerts, Users/Roles, App Install)-->
  <!-- =================================================================================== -->

  <!-- Splunk Field Values Summary Popup Modal -->
  <div id="field-summary-modal" class="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-panelbg border border-bordercolor rounded-xl w-full max-w-lg overflow-hidden shadow-2xl">
      <div class="px-5 py-3 border-b border-bordercolor flex items-center justify-between bg-subpanel/80">
        <h3 class="font-bold text-xs text-white flex items-center gap-2">
          <i data-lucide="tag" class="w-4 h-4 text-emerald-400"></i>
          <span>Field: <span id="modal-field-name" class="font-mono text-emerald-400">host</span></span>
        </h3>
        <button onclick="closeFieldSummaryModal()" class="text-slate-400 hover:text-white"><i data-lucide="x" class="w-4 h-4"></i></button>
      </div>
      <div class="p-5 space-y-4 text-xs">
        <div class="flex items-center justify-between text-slate-400 font-mono text-[11px]">
          <span>Top 10 Values in Current Search Results</span>
          <span id="modal-field-stats">100% matched</span>
        </div>
        <div id="modal-field-values-list" class="space-y-2 max-h-60 overflow-y-auto scrollbar-thin font-mono">
          <!-- Rendered by JS -->
        </div>
        <div class="pt-3 border-t border-bordercolor flex justify-end">
          <button onclick="closeFieldSummaryModal()" class="px-3 py-1.5 rounded bg-subpanel hover:bg-slate-800 text-slate-300">닫기</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Log Detail Modal -->
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
  <!-- 4. JavaScript Logic: Login, Real Splunk Search, Timeline, Field Inspector, Modals   -->
  <!-- =================================================================================== -->
  <script>
    let activeApp = 'search';
    let installedApps = [];
    let currentSearchHits = [];
    let currentSearchSchema = [];
    let currentTimeWindow = "24h";
    let currentUser = null;
    let timelineChartInstance = null;
    let servicesChartInstance = null;
    let levelsChartInstance = null;
    let conversationHistory = [];

    document.addEventListener("DOMContentLoaded", () => {
      lucide.createIcons();
      checkAuthSession();
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

      // Splunk Command + \ (또는 Ctrl + \) 단축키 리스너: 쿼리 자동 파싱 및 정렬
      function isFormatShortcut(e) {
        const isModifier = e.metaKey || e.ctrlKey;
        if (!isModifier) return false;
        const isBackslash = e.key === '\\' || e.code === 'Backslash' || e.key === '₩' || e.keyCode === 220 || e.which === 220;
        const isShiftF = e.shiftKey && (e.key === 'F' || e.key === 'f' || e.code === 'KeyF');
        return isBackslash || isShiftF;
      }

      // 단일 캡처 리스너로 중복 실행 및 버블링 방지
      window.addEventListener('keydown', (e) => {
        if (isFormatShortcut(e)) {
          const searchInput = document.getElementById('search-query-input');
          if (searchInput && activeApp === 'search') {
            e.preventDefault();
            e.stopPropagation();
            triggerQueryAutoFormat();
          }
        }
      }, true);
    });

    // -------------------------------------------------------------
    // Authentication & Session Management (기본: logccino / admin)
    // -------------------------------------------------------------
    async function checkAuthSession() {
      const token = localStorage.getItem("logccino_token");
      const overlay = document.getElementById('splunk-login-overlay');

      if (!token) {
        overlay.classList.remove('hidden');
        return;
      }

      try {
        const res = await fetch('/api/v1/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          currentUser = data.user;
          updateUserUI(currentUser);
          overlay.classList.add('hidden');
          executeSplunkSearch();
        } else {
          localStorage.removeItem("logccino_token");
          overlay.classList.remove('hidden');
        }
      } catch (e) {
        overlay.classList.remove('hidden');
      }
    }

    async function handleLoginSubmit(e) {
      e.preventDefault();
      const username = document.getElementById('login-username').value.trim();
      const password = document.getElementById('login-password').value.trim();
      const errorMsg = document.getElementById('login-error-msg');
      const submitBtn = document.getElementById('login-submit-btn');

      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="animate-pulse">인증 확인 중...</span>';
      errorMsg.classList.add('hidden');

      try {
        const res = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ username, password })
        });
        const data = await res.json();

        if (res.ok && data.status === 'success') {
          localStorage.setItem("logccino_token", data.token);
          currentUser = data.user;
          updateUserUI(currentUser);
          document.getElementById('splunk-login-overlay').classList.add('hidden');
          executeSplunkSearch();
        } else {
          errorMsg.textContent = data.detail || "로그인 실패: 아이디 또는 비밀번호가 올바르지 않습니다.";
          errorMsg.classList.remove('hidden');
        }
      } catch (err) {
        errorMsg.textContent = "서버 통신 오류: " + err.message;
        errorMsg.classList.remove('hidden');
      } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i data-lucide="log-in" class="w-4 h-4"></i><span>로그인 (Sign In)</span>';
        lucide.createIcons();
      }
    }

    function updateUserUI(user) {
      if (!user) return;
      document.getElementById('header-user-name').textContent = user.username;
      document.getElementById('header-user-role').textContent = (user.roles || ['user'])[0] + " role";
      document.getElementById('dropdown-user-name').textContent = user.username + ` (${user.full_name || ''})`;
    }

    async function handleLogout() {
      const token = localStorage.getItem("logccino_token");
      try {
        await fetch('/api/v1/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } catch (e) {}
      localStorage.removeItem("logccino_token");
      document.getElementById('splunk-login-overlay').classList.remove('hidden');
      closeAllDropdowns();
    }

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
      ['settings-dropdown', 'activity-dropdown', 'help-dropdown', 'timerange-dropdown', 'profile-dropdown'].forEach(id => {
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
      // 1. 모든 installedApps에 대해 disabled 상태인 앱을 좌측 앱 리스트에서 완전 숨김 처리
      installedApps.forEach(app => {
        const isEnabled = !!app.enabled;
        
        // 특정 앱의 좌측 내비게이션 버튼 탐색 (app-nav-<id> 또는 siem의 tab-security)
        const navBtn = document.getElementById(`app-nav-${app.id}`) || (app.id === 'siem' ? document.getElementById('tab-security') : null);
        if (navBtn) {
          if (isEnabled) {
            navBtn.classList.remove('hidden');
            navBtn.style.setProperty('display', 'flex', 'important');
          } else {
            navBtn.classList.add('hidden');
            navBtn.style.setProperty('display', 'none', 'important');
          }
        }

        // SIEM 전용 피처 및 메뉴 아이템 (설정 풀다운 메뉴 등)
        if (app.id === 'siem') {
          const siemElements = document.querySelectorAll('.siem-app-feature, .siem-menu-item, .siem-feature');
          siemElements.forEach(el => {
            if (isEnabled) {
              el.classList.remove('hidden');
              el.style.display = '';
            } else {
              el.classList.add('hidden');
              el.style.setProperty('display', 'none', 'important');
            }
          });
        }

        // 현재 선택된 화면이 disabled된 앱이라면 즉시 기본 검색 앱('search')으로 전환
        if (activeApp === app.id && !isEnabled) {
          selectApp('search');
        }
      });

      // 2. 동적으로 설치된 추가 플러그형 앱이 있다면 좌측 앱 목록에 삽입/표시 (단, enabled인 경우만)
      renderDynamicNavApps();
    }

    function renderDynamicNavApps() {
      const navContainer = document.getElementById('splunk-apps-nav');
      const manageAppsBtn = document.getElementById('app-nav-manage_apps');
      if (!navContainer || !manageAppsBtn) return;

      installedApps.forEach(app => {
        if (['search', 'siem', 'sre', 'manage_apps'].includes(app.id)) return;

        let dynamicBtn = document.getElementById(`app-nav-${app.id}`);
        if (app.enabled) {
          if (!dynamicBtn) {
            dynamicBtn = document.createElement('button');
            dynamicBtn.id = `app-nav-${app.id}`;
            dynamicBtn.className = 'app-nav-btn w-full text-left p-3 rounded-lg flex items-start gap-3 transition hover:bg-subpanel text-slate-300 border border-transparent';
            dynamicBtn.onclick = () => selectApp(app.id);
            dynamicBtn.innerHTML = `
              <i data-lucide="${app.icon || 'box'}" class="w-4 h-4 mt-0.5 shrink-0 text-cyan-400"></i>
              <div>
                <div class="font-bold text-xs text-white">${app.name}</div>
                <div class="text-[10px] text-slate-400 mt-0.5 leading-snug">${app.description || ''}</div>
              </div>
            `;
            navContainer.insertBefore(dynamicBtn, manageAppsBtn);
            lucide.createIcons();
          } else {
            dynamicBtn.classList.remove('hidden');
            dynamicBtn.style.setProperty('display', 'flex', 'important');
          }
        } else {
          if (dynamicBtn) {
            dynamicBtn.classList.add('hidden');
            dynamicBtn.style.setProperty('display', 'none', 'important');
          }
        }
      });
    }

    function selectApp(appId) {
      // 요청된 앱이 disabled 상태인 경우 기본 'search' 앱으로 리디렉션
      const targetApp = installedApps.find(a => a.id === appId);
      if (targetApp && !targetApp.enabled) {
        appId = 'search';
      }

      activeApp = appId;
      
      const titles = {
        'search': 'Search & Reporting',
        'siem': 'Enterprise Security (SIEM)',
        'sre': 'Autonomous SRE Observability',
        'manage_apps': '앱 관리 및 설치 (Manage Apps)'
      };
      const foundApp = installedApps.find(a => a.id === appId);
      document.getElementById('current-app-title').textContent = (foundApp ? foundApp.name : (titles[appId] || appId));

      // Update Nav Buttons Styles without wiping out hidden or other classes
      document.querySelectorAll('.app-nav-btn').forEach(btn => {
        btn.classList.remove('bg-emerald-600/20', 'text-emerald-300', 'border-emerald-500/40', 'shadow-sm');
        btn.classList.add('hover:bg-subpanel', 'text-slate-300', 'border-transparent');
      });
      const activeBtn = document.getElementById(`app-nav-${appId}`) || (appId === 'siem' ? document.getElementById('tab-security') : null);
      if (activeBtn) {
        activeBtn.classList.remove('hover:bg-subpanel', 'text-slate-300', 'border-transparent');
        activeBtn.classList.add('bg-emerald-600/20', 'text-emerald-300', 'border-emerald-500/40', 'shadow-sm');
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
        setTimeout(initTimelineChart, 100);
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
                  <div class="w-8 h-8 rounded-lg bg-emerald-600/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
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

    async function toggleSiemModule() {
      const siemApp = installedApps.find(a => a.id === 'siem');
      const targetState = siemApp ? !siemApp.enabled : false;
      await toggleAppStatus('siem', targetState);
    }

    // -------------------------------------------------------------
    // Real Splunk Search & Reporting Experience & Command + \ Parsing
    // -------------------------------------------------------------
    function formatSplunkQuery(rawQuery) {
      if (!rawQuery) return "";
      const trimmed = rawQuery.trim();

      // 1. 따옴표 밖의 줄바꿈과 연속 공백을 단일 공백으로 정규화하여 단일 라인 베이스 생성
      let normalized = "";
      let inD = false;
      let inS = false;
      let esc = false;
      for (let i = 0; i < trimmed.length; i++) {
        const ch = trimmed[i];
        if (esc) {
          normalized += ch;
          esc = false;
          continue;
        }
        if (ch === '\\') {
          esc = true;
          normalized += ch;
          continue;
        }
        if (ch === '"' && !inS) {
          inD = !inD;
          normalized += ch;
          continue;
        }
        if (ch === "'" && !inD) {
          inS = !inS;
          normalized += ch;
          continue;
        }
        if (inD || inS) {
          normalized += ch;
          continue;
        }
        if (ch === '\n' || ch === '\r' || ch === '\t') {
          normalized += ' ';
          continue;
        }
        normalized += ch;
      }

      const singleLine = normalized.replace(/\s+/g, ' ').trim();

      // 2. 파이프(|)와 서브서치([ ... ])를 기준으로 Splunk 표준 다중 라인 및 4칸 들여쓰기 정렬
      let formatted = "";
      let bracketDepth = 0;
      const indentStep = "    "; // Splunk 표준 4칸 들여쓰기
      let inDoubleQuote = false;
      let inSingleQuote = false;
      let escape = false;

      for (let i = 0; i < singleLine.length; i++) {
        const ch = singleLine[i];

        // 이스케이프 문자 처리
        if (escape) {
          formatted += ch;
          escape = false;
          continue;
        }
        if (ch === '\\') {
          escape = true;
          formatted += ch;
          continue;
        }

        // 따옴표 내부의 파이프(|) 및 대괄호([, ]) 보호
        if (ch === '"' && !inSingleQuote) {
          inDoubleQuote = !inDoubleQuote;
          formatted += ch;
          continue;
        }
        if (ch === "'" && !inDoubleQuote) {
          inSingleQuote = !inSingleQuote;
          formatted += ch;
          continue;
        }

        if (inDoubleQuote || inSingleQuote) {
          formatted += ch;
          continue;
        }

        // 서브서치 시작 [ (예: join ... [ source = ... ])
        if (ch === '[') {
          bracketDepth++;
          formatted = formatted.trimEnd();
          formatted += '\n' + indentStep.repeat(bracketDepth) + '[ ';
          while (i + 1 < singleLine.length && singleLine[i + 1] === ' ') {
            i++;
          }
          continue;
        }

        // 서브서치 종료 ]
        if (ch === ']') {
          formatted = formatted.trimEnd();
          formatted += ' ]';
          bracketDepth = Math.max(0, bracketDepth - 1);
          continue;
        }

        // 파이프(|) 마다 새 줄 및 현재 깊이 들여쓰기 적용
        if (ch === '|') {
          formatted = formatted.trimEnd();
          const currentIndent = indentStep.repeat(bracketDepth);
          formatted += '\n' + currentIndent + '| ';
          while (i + 1 < singleLine.length && singleLine[i + 1] === ' ') {
            i++;
          }
          continue;
        }

        formatted += ch;
      }

      const multiLineFormatted = formatted.trim();

      // 3. 만약 현재 쿼리가 이미 완벽하게 다중라인으로 정렬된 상태라면 -> 단일 라인으로 축약 (Toggle)
      // 그렇지 않다면 (단일 라인이거나 정리가 안 된 다중 라인) -> 항상 완벽하게 다중라인으로 정렬!
      if (trimmed === multiLineFormatted) {
        return singleLine;
      }
      return multiLineFormatted;
    }

    function triggerQueryAutoFormat() {
      const input = document.getElementById('search-query-input');
      if (!input) return;
      const original = input.value;
      const formatted = formatSplunkQuery(original);
      input.value = formatted;

      // 행 수에 따라 높이 자동 조절
      const lines = formatted.split('\n').length;
      input.rows = Math.min(12, Math.max(2, lines));

      // 알림 배지 피드백
      const badge = document.getElementById('format-feedback-badge');
      if (badge) {
        badge.classList.remove('hidden');
        badge.textContent = lines > 1 
          ? "✓ 쿼리 다중라인 자동 파싱 완료 (Cmd + \\)" 
          : "✓ 쿼리 한 줄로 축약 완료 (Cmd + \\)";
        setTimeout(() => { badge.classList.add('hidden'); }, 2500);
      }
    }

    function setSearchPreset(query) {
      document.getElementById('search-query-input').value = query;
      executeSplunkSearch();
    }

    function selectSearchTime(tw, label) {
      currentTimeWindow = tw;
      document.getElementById('current-time-label').textContent = label;
      document.getElementById('job-time-range').textContent = `(${label})`;
      closeAllDropdowns();
      executeSplunkSearch();
    }

    async function executeSplunkSearch() {
      const query = document.getElementById('search-query-input').value.trim();
      if (!query) return;

      const jobCount = document.getElementById('job-event-count');
      const jobStatus = document.getElementById('job-status-text');
      const jobElapsed = document.getElementById('job-elapsed');
      const statsContainer = document.getElementById('statistics-table-container');
      const eventsContainer = document.getElementById('search-events-list');

      jobStatus.innerHTML = '<span class="animate-pulse text-amber-400">Executing...</span>';
      eventsContainer.innerHTML = '<p class="text-center py-16 text-slate-400 text-xs animate-pulse">OpenSearch 및 백엔드 파이프라인 연산 중...</p>';

      const startTime = performance.now();

      try {
        const res = await fetch('/api/v1/search/ppl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: query, limit: 100 })
        });
        const data = await res.json();
        const durationSec = ((performance.now() - startTime) / 1000).toFixed(2);

        if (res.ok && data.status === 'success') {
          currentSearchHits = data.hits || [];
          currentSearchSchema = data.schema || [];
          const totalHits = currentSearchHits.length;

          jobCount.textContent = `${totalHits} events`;
          document.getElementById('tab-events-count').textContent = totalHits;
          document.getElementById('tab-stats-count').textContent = totalHits;
          jobStatus.innerHTML = '<span class="text-emerald-400">Job: Complete</span>';
          jobElapsed.textContent = `${durationSec} seconds`;

          // 1. Render Real Splunk Events List (with collapsible field tables)
          renderSplunkEvents(currentSearchHits);

          // 2. Render Statistics Grid
          renderStatisticsTable(currentSearchSchema, currentSearchHits);

          // 3. Render Event Timeline Histogram
          renderTimelineHistogram(currentSearchHits);

          // 4. Update Left Fields Inspector
          updateFieldsInspector(currentSearchHits);

          // Auto select statistics tab if query is stats/join, else events tab
          if (query.includes('| stats') || query.includes('| join') || query.includes('| table')) {
            switchSearchTab('statistics');
          } else {
            switchSearchTab('events');
          }
        } else {
          jobStatus.innerHTML = '<span class="text-rose-400 font-bold">Failed</span>';
          eventsContainer.innerHTML = `<div class="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded text-xs font-mono">${data.detail || data.error || 'Execution failed'}</div>`;
        }
      } catch (e) {
        jobStatus.innerHTML = '<span class="text-rose-400 font-bold">Error</span>';
        eventsContainer.innerHTML = `<p class="text-rose-400 text-center py-10 text-xs">오류: ${e.message}</p>`;
      }
    }

    function renderSplunkEvents(events) {
      const container = document.getElementById('search-events-list');
      if (!events || events.length === 0) {
        container.innerHTML = '<p class="text-center py-20 text-slate-500 text-xs font-mono">No matching events found.</p>';
        return;
      }

      container.innerHTML = events.map((ev, idx) => {
        const ts = ev['@timestamp'] || new Date().toISOString();
        const host = ev.host || 'mbp15';
        const service = ev.service || ev.event_type || 'system';
        const level = ev.level || (ev.event_type === 'alert' ? 'ALERT' : 'INFO');
        const rawLine = ev.message || JSON.stringify(ev);
        const rowId = `event-row-${idx}`;

        return `
          <div class="bg-panelbg border border-bordercolor rounded-lg overflow-hidden font-mono text-xs shadow-sm hover:border-slate-600 transition">
            <!-- Event Summary Line -->
            <div onclick="toggleEventDetail('${rowId}')" class="p-3 flex items-start gap-3 cursor-pointer hover:bg-subpanel/50">
              <span class="text-slate-500 hover:text-white transition mt-0.5" id="${rowId}-icon">
                <i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>
              </span>
              <span class="text-slate-500 text-[11px] w-6 shrink-0">${idx + 1}</span>
              <span class="text-slate-400 text-[11px] shrink-0 font-semibold">${ts}</span>
              <div class="flex-1 overflow-hidden space-y-1">
                <div class="flex items-center gap-2">
                  <span class="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-bold">host=${host}</span>
                  <span class="px-1.5 py-0.2 rounded bg-purple-500/20 text-purple-300 text-[10px] font-bold">service=${service}</span>
                  <span class="px-1.5 py-0.2 rounded ${level === 'ERROR' || level === 'ALERT' ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'} text-[10px] font-bold">${level}</span>
                </div>
                <div class="text-slate-200 text-xs break-all">${rawLine}</div>
              </div>
            </div>

            <!-- Event Field Breakdown Table (Expandable like Splunk) -->
            <div id="${rowId}-detail" class="hidden border-t border-bordercolor/80 bg-slatebg p-3.5 space-y-2">
              <div class="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                <span>EVENT FIELDS</span>
                <button onclick="openLogModal(${JSON.stringify(ev).replace(/"/g, '&quot;')})" class="text-emerald-400 hover:underline">View Raw JSON</button>
              </div>
              <table class="w-full text-left border-collapse text-[11px]">
                <thead>
                  <tr class="text-slate-500 border-b border-bordercolor/60">
                    <th class="py-1 w-1/4">Field</th>
                    <th class="py-1">Value</th>
                    <th class="py-1 w-24 text-right">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-bordercolor/40">
                  ${Object.entries(ev).map(([k, v]) => `
                    <tr>
                      <td class="py-1 text-indigo-400 font-semibold">${k}</td>
                      <td class="py-1 text-slate-200 break-all">${typeof v === 'object' ? JSON.stringify(v) : v}</td>
                      <td class="py-1 text-right">
                        <button onclick="appendSearchFilter('${k}', '${v}')" class="text-[10px] text-slate-400 hover:text-emerald-400 font-bold" title="Add to search query">+ Filter</button>
                      </td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>
            </div>
          </div>
        `;
      }).join('');
      lucide.createIcons();
    }

    function toggleEventDetail(rowId) {
      const detail = document.getElementById(`${rowId}-detail`);
      const icon = document.getElementById(`${rowId}-icon`);
      if (detail.classList.contains('hidden')) {
        detail.classList.remove('hidden');
        icon.innerHTML = '<i data-lucide="chevron-down" class="w-3.5 h-3.5"></i>';
      } else {
        detail.classList.add('hidden');
        icon.innerHTML = '<i data-lucide="chevron-right" class="w-3.5 h-3.5"></i>';
      }
      lucide.createIcons();
    }

    function appendSearchFilter(key, val) {
      const input = document.getElementById('search-query-input');
      let q = input.value.trim();
      q += ` | where ${key} = '${val}'`;
      input.value = q;
      executeSplunkSearch();
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
              <th class="p-2.5 text-slate-500 w-10">#</th>
              ${columns.map(col => `<th class="p-2.5 font-bold uppercase tracking-wider">${col}</th>`).join('')}
            </tr>
          </thead>
          <tbody class="divide-y divide-bordercolor/60 font-mono">
      `;

      rows.forEach((r, idx) => {
        html += `<tr class="hover:bg-subpanel/50 transition">
          <td class="p-2.5 text-slate-500">${idx + 1}</td>
        `;
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

    function initTimelineChart() {
      const el = document.getElementById('search-event-timeline');
      if (el && !timelineChartInstance) {
        timelineChartInstance = echarts.init(el);
      }
    }

    function renderTimelineHistogram(events) {
      if (!timelineChartInstance) initTimelineChart();
      if (!timelineChartInstance) return;

      // Slice events into 12 buckets
      const buckets = new Array(16).fill(0);
      const labels = [];
      const now = Date.now();
      for (let i = 15; i >= 0; i--) {
        const d = new Date(now - i * 90 * 60 * 1000);
        labels.push(`${d.getHours()}:${d.getMinutes() < 10 ? '0' : ''}${d.getMinutes()}`);
      }

      events.forEach((e, idx) => {
        const bucketIdx = idx % 16;
        buckets[bucketIdx]++;
      });

      timelineChartInstance.setOption({
        backgroundColor: 'transparent',
        grid: { top: 5, bottom: 20, left: 20, right: 20 },
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: labels, axisLabel: { color: '#64748b', fontSize: 9 } },
        yAxis: { type: 'value', show: false },
        series: [{
          type: 'bar',
          data: buckets,
          itemStyle: { color: '#10b981', borderRadius: [2, 2, 0, 0] },
          barWidth: '60%'
        }]
      });
    }

    function updateFieldsInspector(events) {
      // Calculate field value counts
      const counts = { host: {}, service: {}, level: {} };
      events.forEach(e => {
        if (e.host) counts.host[e.host] = (counts.host[e.host] || 0) + 1;
        if (e.service) counts.service[e.service] = (counts.service[e.service] || 0) + 1;
        if (e.level) counts.level[e.level] = (counts.level[e.level] || 0) + 1;
      });
    }

    function openFieldSummaryModal(fieldName) {
      document.getElementById('modal-field-name').textContent = fieldName;
      const listContainer = document.getElementById('modal-field-values-list');

      // Aggregate values from currentSearchHits
      const valueMap = {};
      let total = 0;
      currentSearchHits.forEach(h => {
        let v = h[fieldName];
        if (v !== undefined && v !== null) {
          v = String(v);
          valueMap[v] = (valueMap[v] || 0) + 1;
          total++;
        }
      });

      if (total === 0) {
        listContainer.innerHTML = '<p class="text-slate-500 py-4 text-center">현재 검색 결과에서 이 필드의 값이 없습니다.</p>';
      } else {
        const sorted = Object.entries(valueMap).sort((a, b) => b[1] - a[1]);
        listContainer.innerHTML = sorted.map(([val, cnt]) => {
          const pct = ((cnt / total) * 100).toFixed(1);
          return `
            <div class="p-2 bg-subpanel rounded border border-bordercolor flex items-center justify-between">
              <div class="space-y-0.5">
                <span class="font-bold text-white text-xs">${val}</span>
                <div class="text-[10px] text-slate-400">${cnt} events (${pct}%)</div>
              </div>
              <button onclick="appendSearchFilter('${fieldName}', '${val}'); closeFieldSummaryModal();" class="px-2 py-1 rounded bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 font-bold text-[10px] border border-emerald-500/30">
                + Add to search
              </button>
            </div>
          `;
        }).join('');
      }

      document.getElementById('field-summary-modal').classList.remove('hidden');
    }

    function closeFieldSummaryModal() {
      document.getElementById('field-summary-modal').classList.add('hidden');
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
      if (activeBtn) activeBtn.className = 'px-4 py-3 text-xs font-bold border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-1.5 transition';

      if (tab === 'charts') {
        setTimeout(initOverviewCharts, 50);
      }
      lucide.createIcons();
    }

    function exportCurrentSearch(format) {
      if (!currentSearchHits || currentSearchHits.length === 0) {
        alert("내보낼 검색 결과가 없습니다.");
        return;
      }
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentSearchHits, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `splunk_search_export_${Date.now()}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
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

    function initOverviewCharts() {
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
      if (!servicesChartInstance) initOverviewCharts();
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
          { name: 'Total', type: 'bar', data: totals, itemStyle: { color: '#10b981' } },
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

        document.getElementById('users-table-container').innerHTML = `
          <table class="w-full text-left border border-bordercolor rounded overflow-hidden">
            <thead class="bg-subpanel text-slate-300 font-mono text-[11px]">
              <tr><th class="p-2">사용자 ID</th><th class="p-2">이름</th><th class="p-2">역할(Roles)</th><th class="p-2">기본 인덱스</th><th class="p-2">상태</th></tr>
            </thead>
            <tbody class="divide-y divide-bordercolor">
              ${users.map(u => `
                <tr class="hover:bg-subpanel/50">
                  <td class="p-2 font-bold text-white font-mono">${u.username}</td>
                  <td class="p-2 text-slate-300">${u.full_name || ''}</td>
                  <td class="p-2">${(u.roles || []).map(r => `<span class="px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 text-[10px] font-mono mr-1">${r}</span>`).join('')}</td>
                  <td class="p-2 font-mono text-emerald-400">${u.default_index || 'main'}</td>
                  <td class="p-2"><span class="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 text-[10px]">ACTIVE</span></td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;

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
