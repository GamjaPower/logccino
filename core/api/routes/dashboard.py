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

      <!-- App Sidebar Toggle Button (좌측 앱 리스트 화면 토글) -->
      <button onclick="toggleAppsSidebar()" id="btn-toggle-apps-sidebar" class="px-2 py-1 rounded hover:bg-slate-800 text-slate-400 hover:text-emerald-400 border border-bordercolor transition flex items-center gap-1.5 text-[11px] font-medium" title="좌측 앱 리스트 화면 숨기기/보이기">
        <i data-lucide="panel-left" class="w-3.5 h-3.5 text-emerald-400"></i>
        <span id="apps-sidebar-toggle-text">앱 리스트 숨기기</span>
      </button>

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
  <div class="flex flex-1 overflow-hidden relative">

    <!-- LEFT SPLUNK APPS BAR (좌측 앱 리스트) -->
    <aside id="splunk-apps-sidebar" class="w-60 bg-[#0b1120] border-r border-bordercolor flex flex-col shrink-0 select-none transition-all duration-200">
      <div class="p-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-bordercolor flex items-center justify-between">
        <span class="flex items-center gap-1.5"><i data-lucide="grid" class="w-3.5 h-3.5 text-emerald-400"></i> APPS</span>
        <div class="flex items-center gap-1">
          <button onclick="selectApp('manage_apps')" class="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1 font-semibold px-1.5 py-0.5 rounded hover:bg-slate-800/60" title="앱 관리">
            <i data-lucide="sliders" class="w-3 h-3"></i> 관리
          </button>
          <button onclick="toggleAppsSidebar()" id="btn-hide-apps-sidebar" class="text-xs text-slate-400 hover:text-rose-400 p-1 rounded hover:bg-slate-800 flex items-center gap-1 transition" title="앱 리스트 화면 숨기기">
            <i data-lucide="panel-left-close" class="w-3.5 h-3.5"></i>
          </button>
        </div>
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
        
        <!-- Splunk Sub-Navigation Bar (Search, Analytics, Datasets) -->
        <div class="bg-subpanel/90 border-b border-bordercolor px-6 flex items-center justify-between text-xs font-semibold shrink-0">
          <div class="flex">
            <button onclick="switchSearchSubView('search')" id="search-subnav-search" class="px-4 py-2.5 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-1.5 transition font-bold">
              <i data-lucide="search" class="w-3.5 h-3.5"></i> Search
            </button>
            <button onclick="switchSearchSubView('analytics')" id="search-subnav-analytics" class="px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="bar-chart-2" class="w-3.5 h-3.5"></i> Analytics
            </button>
            <button onclick="switchSearchSubView('datasets')" id="search-subnav-datasets" class="px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition">
              <i data-lucide="database" class="w-3.5 h-3.5"></i> Datasets
            </button>
          </div>
          <div class="text-[11px] font-mono text-slate-400">
            앱: <span class="text-white font-bold">Search &amp; Reporting (v10.0.0)</span>
          </div>
        </div>

        <!-- ===================================================================== -->
        <!-- SUB-VIEW 1: Search (검색창, 필드 인스펙터, 이벤트 & 통계 결과)         -->
        <!-- ===================================================================== -->
        <div id="search-subview-search" class="flex-1 flex flex-col overflow-hidden">

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
            <button onclick="openSavedSearchesModal(true)" class="px-2.5 py-1 rounded bg-subpanel hover:bg-slate-800 text-slate-300 border border-bordercolor text-[11px] flex items-center gap-1 transition" title="현재 쿼리를 Splunk 알람/스케줄러로 저장">
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

        </div> <!-- End search-subview-search -->

        <!-- ===================================================================== -->
        <!-- SUB-VIEW 2: Analytics (심층 메트릭, 시계열 분석 & 원클릭 PPL 생성기) -->
        <!-- ===================================================================== -->
        <div id="search-subview-analytics" class="flex-1 flex flex-col overflow-y-auto p-6 space-y-6 hidden bg-slatebg">
          <!-- Analytics Header -->
          <div class="flex items-center justify-between bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md">
            <div>
              <h2 class="text-sm font-bold text-white flex items-center gap-2">
                <i data-lucide="bar-chart-2" class="w-4 h-4 text-emerald-400"></i>
                <span>Splunk Real-Time Analytics &amp; Metrics Explorer</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Live Ingest Telemetry</span>
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">클러스터 인덱스별 이벤트 유입량, 에러 발생 추이, 엔드포인트 지연시간 및 보안 이벤트 종합 분석</p>
            </div>
            <div class="flex items-center gap-2">
              <button onclick="loadAnalyticsData()" class="px-3 py-1.5 rounded-lg bg-subpanel hover:bg-slate-800 text-slate-200 border border-bordercolor text-xs flex items-center gap-1.5 transition">
                <i data-lucide="refresh-cw" class="w-3.5 h-3.5 text-indigo-400"></i>
                <span>새로고침</span>
              </button>
            </div>
          </div>

          <!-- KPI Stats Bar -->
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-sm">
              <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">총 인제스트 볼륨 (24h)</div>
              <div class="text-2xl font-black font-mono text-white flex items-baseline gap-2">
                <span id="analytics-total-events">128,450</span>
                <span class="text-xs text-emerald-400 font-semibold">+8.4%</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1">main: 14.2K | logccino-logs: 114.2K</div>
            </div>
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-sm">
              <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">평균 검색 지연 (Latency)</div>
              <div class="text-2xl font-black font-mono text-emerald-400 flex items-baseline gap-2">
                <span>14.2 ms</span>
                <span class="text-xs text-slate-400 font-normal">p95: 28.6ms</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1">OpenSearch PPL 직접 실행 엔진</div>
            </div>
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-sm">
              <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">시스템 에러율 (Error Rate)</div>
              <div class="text-2xl font-black font-mono text-amber-400 flex items-baseline gap-2">
                <span>0.38 %</span>
                <span class="text-xs text-emerald-400 font-semibold">정상 (Good)</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1">488건의 ERROR/CRITICAL 예외 감지</div>
            </div>
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-sm">
              <div class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">활성 호스트 / 마이크로서비스</div>
              <div class="text-2xl font-black font-mono text-indigo-400 flex items-baseline gap-2">
                <span>14 Hosts</span>
                <span class="text-xs text-slate-400 font-normal">28 Services</span>
              </div>
              <div class="text-[10px] text-slate-500 mt-1">Syslog 1514 &amp; REST Ingest 수집 중</div>
            </div>
          </div>

          <!-- 2x2 Analytics Chart Grid -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <!-- Panel 1: Time Series Trend -->
            <div class="bg-panelbg p-5 rounded-xl border border-bordercolor shadow-sm space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
                  <i data-lucide="activity" class="w-4 h-4 text-emerald-400"></i>
                  <span>인덱스별 이벤트 수집 추이 (Event Ingestion Trend)</span>
                </h3>
                <span class="text-[10px] font-mono text-slate-400">최근 24시간 추이</span>
              </div>
              <div class="h-44 w-full flex items-end gap-1.5 pt-4 pb-2 px-2 bg-slatebg/70 rounded-lg border border-bordercolor/50" id="analytics-trend-bars">
                <!-- Dynamically generated bars via JS -->
              </div>
              <div class="flex items-center justify-between text-[10px] font-mono text-slate-400 px-1">
                <span>24시간 전</span>
                <div class="flex items-center gap-3">
                  <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded bg-emerald-500"></span> logccino-logs-*</span>
                  <span class="flex items-center gap-1"><span class="w-2.5 h-2.5 rounded bg-indigo-500"></span> main (Syslog)</span>
                </div>
                <span>현재 (Now)</span>
              </div>
            </div>

            <!-- Panel 2: Severity Distribution -->
            <div class="bg-panelbg p-5 rounded-xl border border-bordercolor shadow-sm space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
                  <i data-lucide="pie-chart" class="w-4 h-4 text-indigo-400"></i>
                  <span>로그 레벨 심각도 분포 (Log Severity Breakdown)</span>
                </h3>
                <span class="text-[10px] font-mono text-slate-400">전체 128,450건 기준</span>
              </div>
              <div class="p-4 bg-slatebg/70 rounded-lg border border-bordercolor/50 space-y-3">
                <div>
                  <div class="flex justify-between text-[11px] mb-1 font-mono">
                    <span class="text-slate-300 font-semibold flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-400"></span> INFO / DEBUG</span>
                    <span class="text-slate-300">121,980건 (95.0%)</span>
                  </div>
                  <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div class="bg-emerald-500 h-2 rounded-full" style="width: 95%"></div>
                  </div>
                </div>
                <div>
                  <div class="flex justify-between text-[11px] mb-1 font-mono">
                    <span class="text-amber-400 font-semibold flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-amber-400"></span> WARN / NOTICE</span>
                    <span class="text-amber-300">5,982건 (4.6%)</span>
                  </div>
                  <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div class="bg-amber-500 h-2 rounded-full" style="width: 4.6%"></div>
                  </div>
                </div>
                <div>
                  <div class="flex justify-between text-[11px] mb-1 font-mono">
                    <span class="text-rose-400 font-semibold flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-rose-400"></span> ERROR / CRITICAL</span>
                    <span class="text-rose-300">488건 (0.4%)</span>
                  </div>
                  <div class="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                    <div class="bg-rose-500 h-2 rounded-full" style="width: 1.5%"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Panel 3: Top Talkers -->
            <div class="bg-panelbg p-5 rounded-xl border border-bordercolor shadow-sm space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
                  <i data-lucide="server" class="w-4 h-4 text-cyan-400"></i>
                  <span>상위 로그 발신 호스트 (Top Talkers by Host)</span>
                </h3>
                <span class="text-[10px] font-mono text-slate-400">Top 4 엔드포인트</span>
              </div>
              <div class="space-y-2 text-xs">
                <div class="p-2.5 rounded bg-slatebg/70 border border-bordercolor/50 flex items-center justify-between font-mono">
                  <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded bg-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center text-[10px]">1</span>
                    <span class="text-white font-semibold">bastion-gw</span>
                    <span class="text-[10px] text-slate-400">(리눅스 보안 게이트웨이)</span>
                  </div>
                  <span class="font-bold text-emerald-400">48,200건 (37.5%)</span>
                </div>
                <div class="p-2.5 rounded bg-slatebg/70 border border-bordercolor/50 flex items-center justify-between font-mono">
                  <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded bg-indigo-500/20 text-indigo-400 font-bold flex items-center justify-center text-[10px]">2</span>
                    <span class="text-white font-semibold">mbp15</span>
                    <span class="text-[10px] text-slate-400">(엔드포인트 에이전트)</span>
                  </div>
                  <span class="font-bold text-indigo-400">36,400건 (28.3%)</span>
                </div>
                <div class="p-2.5 rounded bg-slatebg/70 border border-bordercolor/50 flex items-center justify-between font-mono">
                  <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded bg-slate-800 text-slate-400 font-bold flex items-center justify-center text-[10px]">3</span>
                    <span class="text-white font-semibold">auth-service-01</span>
                    <span class="text-[10px] text-slate-400">(인증 마이크로서비스)</span>
                  </div>
                  <span class="font-bold text-slate-300">22,100건 (17.2%)</span>
                </div>
                <div class="p-2.5 rounded bg-slatebg/70 border border-bordercolor/50 flex items-center justify-between font-mono">
                  <div class="flex items-center gap-2">
                    <span class="w-5 h-5 rounded bg-slate-800 text-slate-400 font-bold flex items-center justify-center text-[10px]">4</span>
                    <span class="text-white font-semibold">payment-gateway</span>
                    <span class="text-[10px] text-slate-400">(결제 트랜잭션 서비스)</span>
                  </div>
                  <span class="font-bold text-slate-300">14,250건 (11.1%)</span>
                </div>
              </div>
            </div>

            <!-- Panel 4: Security Events Breakdown -->
            <div class="bg-panelbg p-5 rounded-xl border border-bordercolor shadow-sm space-y-3">
              <div class="flex items-center justify-between">
                <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
                  <i data-lucide="shield-check" class="w-4 h-4 text-purple-400"></i>
                  <span>보안 감사 이벤트 액션 분석 (Security Action Breakdown)</span>
                </h3>
                <span class="text-[10px] font-mono text-slate-400">Syslog main 인덱스</span>
              </div>
              <div class="space-y-2 text-xs">
                <div class="p-2.5 rounded bg-rose-500/10 border border-rose-500/20 flex items-center justify-between">
                  <div>
                    <div class="font-bold text-rose-300">SSH 로그인 실패 (ssh_login_failure)</div>
                    <div class="text-[10px] text-slate-400">비인가 패스워드 무차별 대입 시도</div>
                  </div>
                  <span class="font-mono font-bold text-rose-400">14건 탐지</span>
                </div>
                <div class="p-2.5 rounded bg-amber-500/10 border border-amber-500/20 flex items-center justify-between">
                  <div>
                    <div class="font-bold text-amber-300">비인가 Sudo 권한 상승 (sudo_escalation)</div>
                    <div class="text-[10px] text-slate-400">root 권한 셸 명령 실행 감사</div>
                  </div>
                  <span class="font-mono font-bold text-amber-400">6건 탐지</span>
                </div>
                <div class="p-2.5 rounded bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-between">
                  <div>
                    <div class="font-bold text-indigo-300">방화벽 차단 드롭 (firewall_drop)</div>
                    <div class="text-[10px] text-slate-400">UFW 경계 비인가 포트 접근 차단</div>
                  </div>
                  <span class="font-mono font-bold text-indigo-400">42건 탐지</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Metric Query Generator Card -->
          <div class="bg-panelbg p-5 rounded-xl border border-bordercolor shadow-sm space-y-3">
            <h3 class="font-bold text-xs text-slate-200 flex items-center gap-2">
              <i data-lucide="terminal" class="w-4 h-4 text-emerald-400"></i>
              <span>원클릭 PPL 통계 쿼리 생성기 (Metric Explorer to Search)</span>
            </h3>
            <p class="text-xs text-slate-400">아래 파라미터를 선택하면 Splunk PPL 집계 쿼리를 즉시 생성하여 Search 탭에서 실행합니다.</p>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-3 pt-1">
              <div>
                <label class="block text-slate-400 text-[11px] font-semibold mb-1">인덱스 데이터셋</label>
                <select id="analytics-gen-index" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white text-xs focus:border-emerald-500 focus:outline-none">
                  <option value="logccino-logs-*">logccino-logs-* (마이크로서비스)</option>
                  <option value="main">main (보안 Syslog)</option>
                  <option value="main,logccino-logs-*">Cross-Index (전체)</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[11px] font-semibold mb-1">집계 함수 (Metric)</label>
                <select id="analytics-gen-metric" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white text-xs focus:border-emerald-500 focus:outline-none">
                  <option value="count()">count() (이벤트 건수)</option>
                  <option value="avg(duration_ms)">avg(duration_ms) (평균 소요시간)</option>
                  <option value="max(duration_ms)">max(duration_ms) (최대 지연)</option>
                </select>
              </div>
              <div>
                <label class="block text-slate-400 text-[11px] font-semibold mb-1">기준 필드 (Group By)</label>
                <select id="analytics-gen-group" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white text-xs focus:border-emerald-500 focus:outline-none">
                  <option value="service, level">service, level (서비스 및 레벨)</option>
                  <option value="host">host (호스트별)</option>
                  <option value="service">service (서비스별)</option>
                  <option value="level">level (로그 레벨별)</option>
                </select>
              </div>
              <div class="flex items-end">
                <button onclick="executeGeneratedAnalyticsQuery()" class="w-full px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center justify-center gap-1.5 transition shadow">
                  <i data-lucide="play" class="w-3.5 h-3.5"></i>
                  <span>Search 탭에서 실행</span>
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- ===================================================================== -->
        <!-- SUB-VIEW 3: Datasets (데이터 모델, 인덱스 카탈로그 & 스키마 딕셔너리)   -->
        <!-- ===================================================================== -->
        <div id="search-subview-datasets" class="flex-1 flex flex-col overflow-y-auto p-6 space-y-6 hidden bg-slatebg">
          <!-- Datasets Header -->
          <div class="flex items-center justify-between bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md">
            <div>
              <h2 class="text-sm font-bold text-white flex items-center gap-2">
                <i data-lucide="database" class="w-4 h-4 text-emerald-400"></i>
                <span>Splunk Data Models &amp; Datasets Catalog</span>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Schema &amp; Field Dictionary</span>
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">클러스터 내의 이벤트 인덱스, 가속화 데이터 모델, 룩업(Lookup) 테이블 메타데이터 및 스키마 사전 탐색</p>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono text-slate-400">총 5개 데이터셋 등록됨</span>
            </div>
          </div>

          <!-- Two-column Layout: Left Dataset Cards, Right Dataset Detail & Schema -->
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <!-- Left: Dataset List (5 cols) -->
            <div class="lg:col-span-5 space-y-3" id="datasets-list-container">
              <!-- Cards rendered dynamically via JS -->
            </div>

            <!-- Right: Selected Dataset Detail & Schema Inspector (7 cols) -->
            <div class="lg:col-span-7 bg-panelbg p-5 rounded-xl border border-bordercolor shadow-md flex flex-col space-y-4" id="dataset-detail-inspector">
              <!-- Content rendered via JS -->
            </div>
          </div>
        </div>

      </div>

      <!-- =================================================================================== -->
      <!-- APP VIEW 2: Enterprise Security (SIEM) - 독립 추출된 보안 관제 앱                   -->
      <!-- =================================================================================== -->
      <div id="view-app-siem" class="app-view flex-1 flex flex-col p-6 space-y-4 hidden">
        <div id="content-security" class="siem-feature flex flex-col space-y-4">
        <!-- SIEM Header -->
        <div class="flex items-center justify-between bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
              <i data-lucide="shield-alert" class="w-5 h-5"></i>
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="font-bold text-sm text-white">Logccino Autonomous AI SIEM & Enterprise Security</h2>
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20 font-semibold">30 NEXT-GEN AI FEATURES ACTIVE</span>
              </div>
              <p class="text-xs text-slate-400 mt-0.5">Rust 고성능 Syslog 수집기, 자율 트리아지, 생성형 위협 헌팅, MITRE 스토리보드, 능동 SOAR 및 SOC 코파일럿</p>
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

        <!-- SIEM SOC 업무 순서 기반 7대 서브 내비게이션 탭 -->
        <div class="flex items-center gap-1 border-b border-bordercolor pb-2 overflow-x-auto scrollbar-thin text-xs">
          <button onclick="switchSiemSubTab('collection')" id="siem-subtab-collection" class="siem-subtab-btn px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 bg-rose-600/20 text-rose-300 border border-rose-500/30">
            <i data-lucide="radio" class="w-3.5 h-3.5"></i> 1. 수집 & 텔레메트리
          </button>
          <button onclick="switchSiemSubTab('monitoring')" id="siem-subtab-monitoring" class="siem-subtab-btn px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200 hover:bg-subpanel">
            <i data-lucide="activity" class="w-3.5 h-3.5"></i> 2. 실시간 감시 & 탐지
          </button>
          <button onclick="switchSiemSubTab('triage')" id="siem-subtab-triage" class="siem-subtab-btn px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200 hover:bg-subpanel">
            <i data-lucide="cpu" class="w-3.5 h-3.5"></i> 3. 자율 트리아지 & 심층 분석
          </button>
          <button onclick="switchSiemSubTab('hunting')" id="siem-subtab-hunting" class="siem-subtab-btn px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200 hover:bg-subpanel">
            <i data-lucide="search" class="w-3.5 h-3.5"></i> 4. 위협 헌팅 & 인과 추적
          </button>
          <button onclick="switchSiemSubTab('response')" id="siem-subtab-response" class="siem-subtab-btn px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200 hover:bg-subpanel">
            <i data-lucide="zap" class="w-3.5 h-3.5"></i> 5. 능동 대응 & SOAR
          </button>
          <button onclick="switchSiemSubTab('intel')" id="siem-subtab-intel" class="siem-subtab-btn px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200 hover:bg-subpanel">
            <i data-lucide="crosshair" class="w-3.5 h-3.5"></i> 6. 위협 인텔리전스 & 디셉션
          </button>
          <button onclick="switchSiemSubTab('copilot')" id="siem-subtab-copilot" class="siem-subtab-btn px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 text-slate-400 hover:text-slate-200 hover:bg-subpanel">
            <i data-lucide="bot" class="w-3.5 h-3.5"></i> 7. 관제 보고 & 코파일럿
          </button>
        </div>

        <!-- =================================================================== -->
        <!-- SOC STAGE 1: 수집 & 텔레메트리 (Collection & Telemetry)             -->
        <!-- =================================================================== -->
        <div id="siem-subview-collection" class="siem-subview space-y-4">
          <!-- Rust Syslog Collector Controller Card -->
          <div class="p-4 bg-panelbg rounded-xl border border-bordercolor shadow-xl space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <span class="w-2.5 h-2.5 rounded-full bg-slate-500" id="collector-status-dot"></span>
                <span class="font-bold text-white text-xs">Rust High-Performance Syslog Engine (Port: 1514 UDP/TCP)</span>
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

          <!-- PII Masking & WORM Hashchain -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- PII Inline Masking -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="eye-off" class="w-4 h-4 text-emerald-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">실시간 PII 인라인 마스킹 (ISMS-P 개인정보보호)</h3>
                </div>
                <button onclick="runPIIMaskingTest()" class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition">
                  마스킹 실행
                </button>
              </div>
              <input id="pii-input-box" type="text" value="홍길동 고객의 주민번호는 900101-1234567 이며 카드번호는 4518-1234-5678-9012, 전화번호는 010-1234-5678 입니다." class="w-full bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-xs text-white" />
              <div id="pii-result-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">수신 즉시 주민번호, 카드번호, 휴대전화, 이메일을 인라인에서 자동 탐지하고 마스킹합니다.</p>
              </div>
            </div>

            <!-- WORM Hashchain Integrity -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="shield-check" class="w-4 h-4 text-indigo-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">로그 무결성(WORM) 블록 해시체인 & 머클트리</h3>
                </div>
                <div class="flex items-center gap-2">
                  <button onclick="runSealBlockTest()" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition">
                    새 블록 봉인
                  </button>
                  <button onclick="runVerifyIntegrityTest()" class="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition">
                    무결성 전수 검증
                  </button>
                </div>
              </div>
              <div id="integrity-result-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">블록 단위 SHA-256 해시체인과 머클 루트로 원본 로그의 위변조 여부를 실시간 입증합니다.</p>
              </div>
            </div>
          </div>

          <!-- Connector & Plugin App Store Catalog -->
          <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <i data-lucide="store" class="w-4 h-4 text-indigo-400"></i>
                <h3 class="text-xs font-bold text-white uppercase">보안 장비 플러그블 커넥터 스토어 (AhnLab V3, FortiGate, AWS)</h3>
              </div>
              <button onclick="loadConnectorStoreCatalog()" class="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition">
                스토어 카탈로그 로드
              </button>
            </div>
            <div id="connector-store-container" class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
              <p class="text-slate-400 col-span-3 text-center py-6">스토어 카탈로그 로드 버튼을 누르면 원클릭 설치 가능 커넥터가 표시됩니다.</p>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SOC STAGE 2: 실시간 감시 & 탐지 (Monitoring & Detection)            -->
        <!-- =================================================================== -->
        <div id="siem-subview-monitoring" class="siem-subview space-y-4 hidden">
          <!-- In-Memory Stream Sliding Window CEP Engine -->
          <div class="p-4 bg-panelbg rounded-xl border border-bordercolor shadow-xl space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <i data-lucide="zap" class="w-4 h-4 text-amber-400"></i>
                <h3 class="text-xs font-bold text-white uppercase">인메모리 스트림 윈도우 CEP 엔진 (디스크 색인 전 0.1초 즉시 탐지)</h3>
              </div>
              <div class="flex items-center gap-2">
                <button onclick="injectCEPStreamTest()" class="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition">
                  SSH 5회 폭증 스트림 주입
                </button>
                <button onclick="loadCEPMetrics()" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-medium transition">
                  CEP 메트릭 조회
                </button>
              </div>
            </div>
            <div id="cep-result-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2 font-mono text-emerald-400">
              디스크 색인 전 60초 슬라이딩 윈도우에서 복합 위협 패턴을 0.1초 내 탐지합니다.
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

        <!-- =================================================================== -->
        <!-- SOC STAGE 3: 자율 트리아지 & 심층 분석 (Triage & Investigation)     -->
        <!-- =================================================================== -->
        <div id="siem-subview-triage" class="siem-subview space-y-4 hidden">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 01: 자율 다차원 인시던트 트리아지 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="cpu" class="w-4 h-4 text-rose-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 01. 자율 다차원 인시던트 트리아지 (CoT)</h3>
                </div>
                <button onclick="runSampleTriage()" class="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition">
                  트리아지 실행
                </button>
              </div>
              <div id="triage-result-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">알람 유입 시 거짓 양성을 10초 내 자동 분류하고 CoT 추론 체인을 생성합니다.</p>
              </div>
            </div>

            <!-- Feature 02: 동적 가상 분석관 스웜 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="users" class="w-4 h-4 text-indigo-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 02. 가상 분석관 스웜 (IR & Malware & Network)</h3>
                </div>
                <button onclick="runSampleSwarm()" class="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition">
                  스웜 토론 소집
                </button>
              </div>
              <div id="swarm-result-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">3개 페르소나 분석관 에이전트의 다단계 토론을 통해 오판율 75% 감소 합의 결론을 도출합니다.</p>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 03: 근본 원인(Root-Cause) 인과 그래프 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="git-branch" class="w-4 h-4 text-emerald-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 03. 근본 원인(Patient Zero) DAG 그래프</h3>
                </div>
                <button onclick="runSampleAttackGraph()" class="px-2.5 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium transition">
                  공격 그래프 생성
                </button>
              </div>
              <div id="attack-graph-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">최초 침투점부터 현재 감염 상태까지의 인과 추론 비순환 그래프를 시각화합니다.</p>
              </div>
            </div>

            <!-- Feature 04: 경보 노이즈 소멸기 & 유사 알람 군집화 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="filter" class="w-4 h-4 text-amber-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 04. 경보 노이즈 소멸기 & 군집화</h3>
                </div>
                <button onclick="runNoiseEliminator()" class="px-2.5 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium transition">
                  노이즈 소멸 실행
                </button>
              </div>
              <div id="noise-result-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">유사 경보 클러스터링을 통해 알람 피로도를 최대 85%까지 삭감합니다.</p>
              </div>
            </div>
          </div>

          <!-- Feature 05: 엔티티 이상행동 기반 공격 서사화 -->
          <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <i data-lucide="user-check" class="w-4 h-4 text-indigo-400"></i>
                <h3 class="text-xs font-bold text-white uppercase">Feature 05. 엔티티(계정·호스트) 이상행동 기반 공격 서사화</h3>
              </div>
              <button onclick="loadEntityStoryboard()" class="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition">
                엔티티 스토리 로드
              </button>
            </div>
            <div id="entity-storyboard-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-300">
              <p class="text-slate-400">계정의 30일간 행동 편차를 파악하여 평상시와 다른 침해 활동을 서사로 재구성합니다.</p>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SOC STAGE 4: 위협 헌팅 & 인과 추적 (Hunting & Storyboard)            -->
        <!-- =================================================================== -->
        <div id="siem-subview-hunting" class="siem-subview space-y-4 hidden">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 11: MITRE ATT&CK 킬체인 스토리보드 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="git-commit" class="w-4 h-4 text-rose-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 11. MITRE ATT&CK 킬체인 실시간 스토리보드</h3>
                </div>
                <button onclick="loadMitreStoryboard()" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium rounded transition">
                  스토리보드 로드
                </button>
              </div>
              <div id="mitre-storyboard-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-3">
                <p class="text-slate-400">알람 이벤트를 14개 ATT&CK 전술에 실시간 매핑하고 킬체인 진행률을 시각화합니다.</p>
              </div>
            </div>

            <!-- Feature 13: 횡적 이동 경로 재구성 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="repeat" class="w-4 h-4 text-amber-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 13. 계정-네트워크 횡적 이동(Lateral Movement) 재구성</h3>
                </div>
                <button onclick="loadLateralMovement()" class="px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium rounded transition">
                  경로 추적
                </button>
              </div>
              <div id="lateral-movement-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-300">
                <p class="text-slate-400">도용된 크리덴셜 경로와 네트워크 피벗 과정을 시각화합니다.</p>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- Feature 12: 크로스 타임라인 정합성 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-white flex items-center gap-1.5"><i data-lucide="clock" class="w-3.5 h-3.5 text-indigo-400"></i> Feature 12. 크로스 타임라인</h4>
                <button onclick="loadStitchedTimeline()" class="px-2 py-0.5 bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] rounded transition">합성</button>
              </div>
              <div id="stitched-timeline-box" class="p-2.5 bg-slatebg rounded border border-bordercolor/60 text-xs text-slate-400">
                이종 소스 타임라인 정합성 검증
              </div>
            </div>

            <!-- Feature 14: 데이터 유출 잠행 서사화 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-white flex items-center gap-1.5"><i data-lucide="cloud-download" class="w-3.5 h-3.5 text-rose-400"></i> Feature 14. 데이터 유출 서사</h4>
                <button onclick="loadExfiltrationNarrative()" class="px-2 py-0.5 bg-rose-600 hover:bg-rose-500 text-white text-[11px] rounded transition">추적</button>
              </div>
              <div id="exfil-narrative-box" class="p-2.5 bg-slatebg rounded border border-bordercolor/60 text-xs text-slate-400">
                DNS/HTTPS 채널 은닉 유출 추적
              </div>
            </div>

            <!-- Feature 15: K8s/클라우드 설정 변조 추적 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-white flex items-center gap-1.5"><i data-lucide="server" class="w-3.5 h-3.5 text-amber-400"></i> Feature 15. 인프라 변조</h4>
                <button onclick="loadConfigTampering()" class="px-2 py-0.5 bg-amber-600 hover:bg-amber-500 text-white text-[11px] rounded transition">조회</button>
              </div>
              <div id="config-tamper-box" class="p-2.5 bg-slatebg rounded border border-bordercolor/60 text-xs text-slate-400">
                Kubernetes & Cloud 변조 탐지
              </div>
            </div>
          </div>

          <!-- Feature 06: 자연어 NL-to-PPL 합성기 -->
          <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
            <div class="flex items-center gap-2">
              <i data-lucide="sparkles" class="w-4 h-4 text-amber-400"></i>
              <h3 class="text-xs font-bold text-white uppercase">Feature 06. 자연어 기반 제로샷 PPL/Join 쿼리 자동 합성</h3>
            </div>
            <div class="flex items-center gap-2">
              <input id="nl-hunt-input" type="text" value="어제 로그인 실패가 5번 넘은 호스트와 해당 호스트의 5xx 에러 조인해줘" class="flex-1 bg-slatebg border border-bordercolor rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500" />
              <button onclick="synthesizeNLQuery()" class="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs rounded-lg transition flex items-center gap-1.5">
                <i data-lucide="zap" class="w-3.5 h-3.5"></i> PPL 쿼리 합성
              </button>
            </div>
            <div id="nl-hunt-output" class="hidden p-3 bg-slatebg rounded-lg border border-amber-500/30 text-xs font-mono text-emerald-400 whitespace-pre overflow-x-auto"></div>
          </div>

          <!-- Feature 07 & Feature 10 -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 07: 가설 주도형 자율 위협 헌팅 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="compass" class="w-4 h-4 text-indigo-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 07. 가설 주도형 자율 위협 헌팅</h3>
                </div>
                <button onclick="loadHuntingHypotheses()" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded transition">
                  가설 전수 탐사 실행
                </button>
              </div>
              <div id="hypotheses-container" class="grid grid-cols-1 gap-2 text-xs">
                <p class="text-slate-400 text-center py-6">가설 탐사 실행 버튼을 누르면 자율 에이전트가 탐색을 개시합니다.</p>
              </div>
            </div>

            <!-- Feature 10: 레드팀 헌팅 시뮬레이터 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="shield-alert" class="w-4 h-4 text-rose-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 10. 공격자 관점 헌팅 시뮬레이터</h3>
                </div>
                <div class="flex items-center gap-2">
                  <select id="sel-threat-actor" class="bg-slatebg border border-bordercolor text-xs rounded px-2 py-1 text-slate-200">
                    <option value="APT29">APT29 (Cozy Bear - Russia SVR)</option>
                    <option value="Lazarus Group">Lazarus Group (북한 해킹 그룹)</option>
                  </select>
                  <button onclick="runAdversaryEmulation()" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium rounded transition">
                    역추적
                  </button>
                </div>
              </div>
              <div id="adversary-emu-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-300">
                <p class="text-slate-400">APT 그룹의 TTP 페르소나를 장착하여 은닉된 역추적 PPL 쿼리를 생성합니다.</p>
              </div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SOC STAGE 5: 능동 대응 & SOAR (Response & SOAR)                     -->
        <!-- =================================================================== -->
        <div id="siem-subview-response" class="siem-subview space-y-4 hidden">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 4: 비주얼 SOAR 플레이북 & 승인 게이트 (Logpresso Maestro) -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="git-pull-request" class="w-4 h-4 text-rose-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Maestro 비주얼 SOAR & Human-in-the-Loop</h3>
                </div>
                <button onclick="triggerVisualPlaybookTest()" class="px-2.5 py-1 rounded bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition">
                  Maestro 플레이북 구동
                </button>
              </div>
              <div id="visual-playbook-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">5단계 워크플로 실행 및 분석가 승인 게이트(Human-in-the-loop)를 거쳐 능동 차단을 집행합니다.</p>
              </div>
            </div>

            <!-- Feature 18: 실시간 능동 대응 오케스트레이터 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center gap-2">
                <i data-lucide="shield" class="w-4 h-4 text-rose-400"></i>
                <h3 class="text-xs font-bold text-white uppercase">Feature 18. 실시간 능동 대응 오케스트레이터 (1초 내 차단)</h3>
              </div>
              <div class="flex flex-wrap gap-2">
                <button onclick="executeActiveAction('block_ip', '198.51.100.42')" class="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white font-medium text-xs rounded transition flex items-center gap-1">
                  <i data-lucide="slash" class="w-3 h-3"></i> IP 198.51.100.42 방화벽 DROP
                </button>
                <button onclick="executeActiveAction('revoke_session', 'sst96')" class="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs rounded transition flex items-center gap-1">
                  <i data-lucide="lock" class="w-3 h-3"></i> 사용자 sst96 세션 강제 무효화
                </button>
                <button onclick="executeActiveAction('isolate_host', 'bastion-gateway')" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded transition flex items-center gap-1">
                  <i data-lucide="server" class="w-3 h-3"></i> Bastion 호스트 네트워크 격리
                </button>
              </div>
              <div id="active-response-log" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs font-mono text-emerald-400 min-h-[60px]">
                대응 명령 실행 대기 중...
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- Feature 16: 동적 플레이북 자동 합성 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="zap" class="w-4 h-4 text-emerald-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 16. 플레이북 합성</h3>
                </div>
                <button onclick="loadAdaptivePlaybook()" class="px-2 py-0.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded transition">생성</button>
              </div>
              <div id="playbook-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">인시던트 맞춤형 5단계 대응 절차 자동 합성</p>
              </div>
            </div>

            <!-- Feature 17: 조치 영향도 사전 시뮬레이터 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="activity" class="w-4 h-4 text-amber-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 17. 무중단 영향도 시뮬</h3>
                </div>
                <button onclick="simulateRemediationImpact()" class="px-2 py-0.5 bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium rounded transition">검증</button>
              </div>
              <div id="impact-sim-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-400">
                격리·차단 시 업무 서비스 영향도 사전 진단
              </div>
            </div>

            <!-- Feature 19: 영속성(Persistence) 완전 소탕 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="trash-2" class="w-4 h-4 text-rose-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 19. 잔존 위협 소탕</h3>
                </div>
                <button onclick="sweepPersistenceThreats()" class="px-2 py-0.5 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium rounded transition">소탕</button>
              </div>
              <div id="persistence-sweep-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-400">
                Cron, 서비스 백도어, 웹쉘 전수 탐색
              </div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SOC STAGE 6: 위협 인텔리전스 & 디셉션 (Intel & Deception)           -->
        <!-- =================================================================== -->
        <div id="siem-subview-intel" class="siem-subview space-y-4 hidden">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 21: 비정형 CTI RAG -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="database" class="w-4 h-4 text-indigo-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 21. 비정형 사이버 위협 인텔리전스 RAG</h3>
                </div>
                <button onclick="queryCTIRAG()" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded transition">
                  CTI RAG 검색
                </button>
              </div>
              <input id="cti-rag-input" type="text" value="CVE-2026-3819 웹 프레임워크 원격 코드 실행 취약점" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-xs text-white" />
              <div id="cti-rag-result" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">PDF 백서, CISA 권고문, PoC 문서를 벡터 검색하여 내부 관측치와 교차 대조합니다.</p>
              </div>
            </div>

            <!-- Feature 22: 동적 카나리 허니팟 토큰 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="crosshair" class="w-4 h-4 text-emerald-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 22. 동적 허니팟 & 카나리 토큰 자동 합성 (오탐 0%)</h3>
                </div>
                <button onclick="deployCanaryToken()" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded transition">
                  카나리 토큰 배포
                </button>
              </div>
              <div id="canary-token-result" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                <p class="text-slate-400">진짜처럼 보이는 가짜 AWS Key 및 DB 접속 정보를 생성하여 건드리는 순간 즉시 경보를 발생시킵니다.</p>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- Feature 23: 공급망 Blast Radius -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-white flex items-center gap-1.5"><i data-lucide="git-pull-request" class="w-3.5 h-3.5 text-amber-400"></i> Feature 23. 공급망 위험</h4>
                <button onclick="assessSupplyChainBlastRadius()" class="px-2 py-0.5 bg-amber-600 hover:bg-amber-500 text-white text-[11px] rounded transition">분석</button>
              </div>
              <div id="blast-radius-box" class="p-2.5 bg-slatebg rounded border border-bordercolor/60 text-xs text-slate-400">
                Log4j 등 오픈소스 의존성 취약점 피해 반경 분석
              </div>
            </div>

            <!-- Feature 24: APT 조직 추론기 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-white flex items-center gap-1.5"><i data-lucide="globe" class="w-3.5 h-3.5 text-rose-400"></i> Feature 24. APT 배후 추론</h4>
                <button onclick="profileAPTAttribution()" class="px-2 py-0.5 bg-rose-600 hover:bg-rose-500 text-white text-[11px] rounded transition">추론</button>
              </div>
              <div id="apt-profile-box" class="p-2.5 bg-slatebg rounded border border-bordercolor/60 text-xs text-slate-400">
                국가 배후 해킹 그룹 TTP 자동 추론
              </div>
            </div>

            <!-- Feature 25: 다크웹 유출 계정 상관분석 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="text-xs font-bold text-white flex items-center gap-1.5"><i data-lucide="key" class="w-3.5 h-3.5 text-indigo-400"></i> Feature 25. 다크웹 계정</h4>
                <button onclick="correlateDarkwebCreds()" class="px-2 py-0.5 bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] rounded transition">조회</button>
              </div>
              <div id="darkweb-box" class="p-2.5 bg-slatebg rounded border border-bordercolor/60 text-xs text-slate-400">
                유출 크리덴셜과 사내 로그인 교차 대조
              </div>
            </div>
          </div>
        </div>

        <!-- =================================================================== -->
        <!-- SOC STAGE 7: 관제 보고 & 코파일럿 (Copilot & Governance)            -->
        <!-- =================================================================== -->
        <div id="siem-subview-copilot" class="siem-subview space-y-4 hidden">
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 26: 실시간 대화형 SOC 코파일럿 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3 flex flex-col h-[380px]">
              <div class="flex items-center gap-2">
                <i data-lucide="bot" class="w-4 h-4 text-emerald-400"></i>
                <h3 class="text-xs font-bold text-white uppercase">Feature 26. 대화형 실시간 SOC 코파일럿 (MCP Tool Execution)</h3>
              </div>
              <div id="copilot-chat-history" class="flex-1 overflow-y-auto space-y-2 bg-slatebg p-3 rounded-lg border border-bordercolor/60 text-xs">
                <div class="text-slate-400">Logccino SOC Copilot입니다. 무엇을 조사하거나 조치할까요? (예: "트리아지 실행해줘", "공격자 IP 차단해줘")</div>
              </div>
              <div class="flex items-center gap-2">
                <input id="copilot-input" type="text" placeholder="지시사항 입력 (예: 최근 알람 트리아지해줘)" class="flex-1 bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-xs text-white" onkeydown="if(event.key==='Enter') sendCopilotMsg()" />
                <button onclick="sendCopilotMsg()" class="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded transition">전송</button>
              </div>
            </div>

            <!-- Feature 27: 교대 근무 인수인계 & 음성 브리핑 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3 flex flex-col justify-between">
              <div>
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-2">
                    <i data-lucide="mic" class="w-4 h-4 text-indigo-400"></i>
                    <h3 class="text-xs font-bold text-white uppercase">Feature 27. 교대 인수인계 5줄 요약 & 음성 브리핑</h3>
                  </div>
                  <button onclick="loadShiftHandover()" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded transition">
                    인수인계 생성
                  </button>
                </div>
                <div id="shift-handover-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs space-y-2">
                  <p class="text-slate-400">지난 12시간 발생 인시던트를 5줄 요약 및 브리핑 음성(TTS) 스크립트로 합성합니다.</p>
                </div>
              </div>
              <div class="pt-2">
                <button onclick="speakHandoverAudio()" class="w-full py-2 bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/30 rounded-lg text-xs font-medium flex items-center justify-center gap-2 transition">
                  <i data-lucide="volume-2" class="w-4 h-4 text-indigo-400"></i> 음성 브리핑 재생 (Web Speech TTS)
                </button>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 20: 사후 보고서 자동 생성 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="file-text" class="w-4 h-4 text-indigo-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 20. 인시던트 사후 보고서(Post-Mortem) 자동 생성</h3>
                </div>
                <div class="flex items-center gap-2">
                  <select id="sel-report-audience" class="bg-slatebg border border-bordercolor text-xs rounded px-2 py-1 text-slate-200">
                    <option value="executive">경영진 보고용 (Executive Summary)</option>
                    <option value="kisa_regulatory">KISA 법적 신고용 (침해사고 신고서)</option>
                    <option value="technical">기술팀 포스트모텀 (Technical Root Cause)</option>
                  </select>
                  <button onclick="generatePostMortemReport()" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded transition">
                    보고서 즉시 생성
                  </button>
                </div>
              </div>
              <div id="post-mortem-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs whitespace-pre-wrap font-mono text-slate-200">
                대상자별 양식(경영진 1장 요약 / KISA 법적 신고 / 기술 상세)을 1초 만에 자동 작성합니다.
              </div>
            </div>

            <!-- Feature 29: ISMS-P / ISO 27001 상시 감사기 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="award" class="w-4 h-4 text-amber-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 29. 규제 준수(ISMS-P / ISO 27001) 상시 감사기</h3>
                </div>
                <button onclick="runComplianceAudit()" class="px-2.5 py-1 bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium rounded transition">
                  상시 감사 검사
                </button>
              </div>
              <div id="compliance-audit-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-300">
                <p class="text-slate-400">로그 1년 이상 보존, 관리자 권한 분립, 접근 통제 항목을 상시 자동 감사합니다.</p>
              </div>
            </div>
          </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Feature 28: Detection-as-Code 탐지 룰 자동 튜닝 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="sliders" class="w-4 h-4 text-emerald-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 28. Detection-as-Code 탐지 룰 자동 튜너</h3>
                </div>
                <button onclick="loadDetectionTuning()" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded transition">
                  룰 튜닝 제안
                </button>
              </div>
              <div id="tuning-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-300">
                <p class="text-slate-400">오탐률이 높은 룰의 PPL 쿼리를 자동으로 분석하여 오탐 삭감 필터를 제안합니다.</p>
              </div>
            </div>

            <!-- Feature 30: 워게임(War-Game) 상시 시뮬레이션 -->
            <div class="bg-panelbg p-4 rounded-xl border border-bordercolor shadow-md space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <i data-lucide="swords" class="w-4 h-4 text-rose-400"></i>
                  <h3 class="text-xs font-bold text-white uppercase">Feature 30. 인터랙티브 워게임(War-Game) 시뮬레이션 & 코치</h3>
                </div>
                <button onclick="loadWarGameScenarios()" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium rounded transition">
                  훈련 시나리오
                </button>
              </div>
              <div id="war-game-box" class="p-3 bg-slatebg rounded-lg border border-bordercolor/60 text-xs text-slate-300">
                <p class="text-slate-400">실전 침해 시나리오를 바탕으로 분석가의 대응 스텝을 실시간 평가하고 피드백을 제공합니다.</p>
              </div>
            </div>
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

  <!-- Saved Searches & Alerts Modal (Splunk Enterprise Style) -->
  <div id="new-alert-modal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div id="content-alerts" class="bg-panelbg border border-bordercolor rounded-xl w-full max-w-5xl max-h-[90vh] overflow-hidden shadow-2xl flex flex-col">
      <!-- Modal Header -->
      <div class="px-6 py-3.5 border-b border-bordercolor flex items-center justify-between bg-subpanel/80 shrink-0">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <i data-lucide="bell-ring" class="w-4 h-4"></i>
          </div>
          <div>
            <h3 class="font-bold text-sm text-slate-100 flex items-center gap-2">
              <span id="alert-modal-title">Splunk Saved Searches & PPL Alert Engine</span>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">savedsearches.conf 호환</span>
            </h3>
            <p class="text-[11px] text-slate-400">PPL 스케줄러, 디스패치 시간 범위, 알람 조건, Throttling(억제) 및 복합 액션 통합 관리</p>
          </div>
        </div>
        <button onclick="closeNewAlertModal()" class="text-slate-400 hover:text-white p-1 rounded hover:bg-slate-800 transition">
          <i data-lucide="x" class="w-5 h-5"></i>
        </button>
      </div>

      <!-- Navigation Tabs: List vs Form -->
      <div class="flex items-center justify-between border-b border-bordercolor bg-[#0f172a] px-6 text-xs font-semibold shrink-0">
        <div class="flex">
          <button type="button" id="tab-btn-alert-list" onclick="switchAlertModalTab('list')" class="px-4 py-3 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-2 transition">
            <i data-lucide="list" class="w-3.5 h-3.5"></i> 알람 규칙 목록 (<span id="alert-rules-count">4</span>)
          </button>
          <button type="button" id="tab-btn-alert-form" onclick="switchAlertModalTab('form')" class="px-4 py-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2 transition">
            <i data-lucide="plus-circle" class="w-3.5 h-3.5"></i> <span id="alert-form-tab-title">신규 알람 등록</span>
          </button>
        </div>
        <div id="alert-list-quick-actions" class="flex items-center gap-2">
          <button onclick="resetAlertForm(); switchAlertModalTab('form');" class="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow">
            <i data-lucide="plus" class="w-3.5 h-3.5"></i> 새로운 알람 규칙
          </button>
        </div>
      </div>

      <!-- Modal Body (Scrollable) -->
      <div class="flex-1 overflow-y-auto p-6 text-xs">

        <!-- TAB 1: 알람 규칙 목록 (Rules List Table) -->
        <div id="alert-modal-view-list" class="space-y-4">
          <div class="flex items-center justify-between">
            <div class="text-slate-400 text-xs">
              백그라운드에서 주기적으로 PPL 쿼리를 실행하여 침입 시도, 권한 상승 및 장애를 실시간 감시합니다.
            </div>
            <button onclick="loadSavedSearchesList()" class="px-2.5 py-1 rounded bg-subpanel hover:bg-slate-800 text-slate-300 border border-bordercolor flex items-center gap-1 text-[11px] transition">
              <i data-lucide="refresh-cw" class="w-3 h-3 text-indigo-400"></i> 새로고침
            </button>
          </div>
          <div id="saved-searches-table-container" class="border border-bordercolor rounded-lg overflow-hidden bg-subpanel/40">
            <!-- Table will be rendered dynamically -->
          </div>
        </div>

        <!-- TAB 2: 알람 등록 / 수정 상세 폼 (Full Splunk savedsearches.conf Editor) -->
        <div id="alert-modal-view-form" class="hidden">
          <form onsubmit="handleSaveAlert(event)" class="space-y-5">
            <input type="hidden" id="alert-form-id">

            <!-- 1. 일반 정보 (General Settings) -->
            <div class="p-4 rounded-lg bg-subpanel/50 border border-bordercolor space-y-3">
              <div class="font-bold text-slate-200 flex items-center gap-2 text-xs border-b border-bordercolor/60 pb-2">
                <i data-lucide="info" class="w-4 h-4 text-emerald-400"></i> 1. 일반 정보 및 소유권 (General &amp; Ownership)
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div class="md:col-span-2">
                  <label class="block text-slate-400 font-semibold mb-1">알람 / Saved Search 명칭 *</label>
                  <input type="text" id="alert-form-name" required placeholder="예: [SEC-01] SSH 로그인 실패 및 무차별 대입 급증" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-emerald-500 focus:outline-none">
                </div>
                <div class="md:col-span-2">
                  <label class="block text-slate-400 font-semibold mb-1">알람 상세 설명</label>
                  <input type="text" id="alert-form-desc" placeholder="알람 목적, 대응 절차(SOP) 및 모니터링 가이드 요약" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-emerald-500 focus:outline-none">
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">App Context (앱 컨텍스트)</label>
                  <select id="alert-form-app" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-emerald-500 focus:outline-none">
                    <option value="search">Search &amp; Reporting</option>
                    <option value="enterprise_security">Enterprise Security (SIEM)</option>
                    <option value="autonomous_sre">Autonomous SRE</option>
                  </select>
                </div>
                <div class="grid grid-cols-2 gap-2">
                  <div>
                    <label class="block text-slate-400 font-semibold mb-1">소유자 (Owner)</label>
                    <input type="text" id="alert-form-owner" value="logccino" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-emerald-500 focus:outline-none">
                  </div>
                  <div>
                    <label class="block text-slate-400 font-semibold mb-1">공유 범위 (Sharing)</label>
                    <select id="alert-form-sharing" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-emerald-500 focus:outline-none">
                      <option value="app">App (앱 내 공유)</option>
                      <option value="global">Global (전사 공유)</option>
                      <option value="private">Private (개인 비공개)</option>
                    </select>
                  </div>
                </div>
                <div class="flex items-center gap-2 pt-1">
                  <input type="checkbox" id="alert-form-enabled" checked class="w-4 h-4 rounded text-emerald-500 focus:ring-emerald-500 border-bordercolor bg-slatebg">
                  <label for="alert-form-enabled" class="text-slate-300 font-medium">스케줄러 활성화 (Enable Scheduler)</label>
                </div>
              </div>
            </div>

            <!-- 2. PPL 검색 쿼리 및 디스패치 시간 범위 (Dispatch & Query) -->
            <div class="p-4 rounded-lg bg-subpanel/50 border border-bordercolor space-y-3">
              <div class="font-bold text-slate-200 flex items-center justify-between text-xs border-b border-bordercolor/60 pb-2">
                <span class="flex items-center gap-2"><i data-lucide="terminal" class="w-4 h-4 text-indigo-400"></i> 2. 검색 쿼리 및 디스패치 시간 범위 (Query &amp; Time Window)</span>
                <span class="text-[10px] text-slate-400 font-mono">⌘\ (Cmd+\) 쿼리 자동 정렬</span>
              </div>
              <div>
                <label class="block text-slate-400 font-semibold mb-1">실행할 PPL / Join 쿼리 *</label>
                <textarea id="alert-form-query" rows="3" required placeholder="source = logccino-logs-* | where level = 'ERROR' | head 50" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none"></textarea>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">디스패치 시작 시간 (Earliest Time)</label>
                  <select id="alert-form-earliest" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none">
                    <option value="-15m">-15m (최근 15분)</option>
                    <option value="-30m">-30m (최근 30분)</option>
                    <option value="-1h">-1h (최근 1시간)</option>
                    <option value="-4h">-4h (최근 4시간)</option>
                    <option value="-24h">-24h (최근 24시간)</option>
                    <option value="-7d">-7d (최근 7일)</option>
                    <option value="@d">@d (오늘 시작 시각부터)</option>
                    <option value="0">0 (전체 시간)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">디스패치 종료 시간 (Latest Time)</label>
                  <input type="text" id="alert-form-latest" value="now" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none">
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">샘플링 비율 (Sample Ratio)</label>
                  <select id="alert-form-sampleratio" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-indigo-500 focus:outline-none">
                    <option value="1">1:1 (전체 100% 검사)</option>
                    <option value="10">1:10 (10% 샘플링)</option>
                    <option value="100">1:100 (1% 대용량 샘플링)</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 3. 스케줄링 (Schedule Settings) -->
            <div class="p-4 rounded-lg bg-subpanel/50 border border-bordercolor space-y-3">
              <div class="font-bold text-slate-200 flex items-center gap-2 text-xs border-b border-bordercolor/60 pb-2">
                <i data-lucide="clock" class="w-4 h-4 text-cyan-400"></i> 3. 스케줄링 및 우선순위 (Schedule Settings)
              </div>
              <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">스케줄 방식 (Schedule Type)</label>
                  <select id="alert-form-sched-type" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-cyan-500 focus:outline-none">
                    <option value="interval">초 주기 실행 (Interval)</option>
                    <option value="cron">표준 Cron 스케줄</option>
                    <option value="realtime">실시간 우선 스케줄</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">실행 주기 (초, Interval)</label>
                  <input type="number" id="alert-form-interval" value="60" min="5" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-cyan-500 focus:outline-none">
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">Cron 표현식</label>
                  <input type="text" id="alert-form-cron" value="*/5 * * * *" placeholder="*/5 * * * *" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-cyan-500 focus:outline-none">
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">우선순위 (Schedule Priority)</label>
                  <select id="alert-form-priority" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-cyan-500 focus:outline-none">
                    <option value="default">Default (기본)</option>
                    <option value="higher">Higher (높음)</option>
                    <option value="highest">Highest (최우선)</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 4. 트리거 조건 (Trigger Condition) -->
            <div class="p-4 rounded-lg bg-subpanel/50 border border-bordercolor space-y-3">
              <div class="font-bold text-slate-200 flex items-center gap-2 text-xs border-b border-bordercolor/60 pb-2">
                <i data-lucide="zap" class="w-4 h-4 text-amber-400"></i> 4. 트리거 조건 (Trigger Condition)
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">조건 기준 (Trigger When)</label>
                  <select id="alert-form-type" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-amber-500 focus:outline-none">
                    <option value="number_of_results">Number of Results (결과 레코드 수)</option>
                    <option value="number_of_events">Number of Events (이벤트 건수)</option>
                    <option value="number_of_hosts">Number of Hosts (고유 호스트 수)</option>
                    <option value="number_of_sources">Number of Sources (고유 소스/프로그램 수)</option>
                    <option value="custom">Custom Condition (커스텀 조건식)</option>
                    <option value="always">Always (스케줄 시 무조건 트리거)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">비교 연산자 (Comparator)</label>
                  <select id="alert-form-op" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-amber-500 focus:outline-none">
                    <option value="gt">&gt; (is greater than)</option>
                    <option value="gte">&gt;= (is greater than or equal to)</option>
                    <option value="lt">&lt; (is less than)</option>
                    <option value="lte">&lt;= (is less than or equal to)</option>
                    <option value="eq">== (is equal to)</option>
                    <option value="neq">!= (is not equal to)</option>
                    <option value="drops_by">drops by (임계치 이하 급감)</option>
                    <option value="rises_by">rises by (임계치 이상 급증)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">임계치 (Threshold) *</label>
                  <input type="number" step="0.1" id="alert-form-threshold" value="0.0" required class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-amber-500 focus:outline-none">
                </div>
              </div>
            </div>

            <!-- 5. 빈도, 심각도 및 Throttling 억제 (Frequency & Throttling) -->
            <div class="p-4 rounded-lg bg-subpanel/50 border border-bordercolor space-y-3">
              <div class="font-bold text-slate-200 flex items-center gap-2 text-xs border-b border-bordercolor/60 pb-2">
                <i data-lucide="shield-alert" class="w-4 h-4 text-rose-400"></i> 5. 알람 빈도 및 Throttling 억제 (Frequency &amp; Suppression)
              </div>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">트리거 빈도 (Trigger Mode)</label>
                  <select id="alert-form-trigger-mode" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white focus:border-rose-500 focus:outline-none">
                    <option value="once">Once (조건 충족 시 1회 발송)</option>
                    <option value="for_each_result">For each result (결과 행마다 개별 발송)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">알람 심각도 (Severity Level)</label>
                  <select id="alert-form-severity" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-semibold focus:border-rose-500 focus:outline-none">
                    <option value="CRITICAL" class="text-rose-400">CRITICAL (심각)</option>
                    <option value="HIGH" selected class="text-amber-400">HIGH (높음)</option>
                    <option value="MEDIUM" class="text-yellow-400">MEDIUM (보통)</option>
                    <option value="LOW" class="text-blue-400">LOW (낮음)</option>
                    <option value="INFO" class="text-slate-400">INFO (정보)</option>
                  </select>
                </div>
                <div>
                  <label class="block text-slate-400 font-semibold mb-1">알람 보관 만료 (Expires)</label>
                  <select id="alert-form-expires" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-rose-500 focus:outline-none">
                    <option value="24h">24h (24시간 보관)</option>
                    <option value="7d">7d (7일 보관)</option>
                    <option value="30d">30d (30일 보관)</option>
                  </select>
                </div>
              </div>
              <div class="pt-2 border-t border-bordercolor/60 space-y-2">
                <div class="flex items-center gap-2">
                  <input type="checkbox" id="alert-form-suppress" class="w-4 h-4 rounded text-rose-500 focus:ring-rose-500 border-bordercolor bg-slatebg">
                  <label for="alert-form-suppress" class="text-slate-200 font-semibold">알람 억제(Throttling) 활성화 - 동일 원인의 반복 알람 스팸 차단</label>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pl-6">
                  <div>
                    <label class="block text-slate-400 font-semibold mb-1">억제 기간 (Suppress Period)</label>
                    <input type="text" id="alert-form-suppress-period" value="5m" placeholder="예: 5m, 1h, 1d" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-rose-500 focus:outline-none">
                  </div>
                  <div>
                    <label class="block text-slate-400 font-semibold mb-1">억제 기준 필드 (Suppress Fields, 쉼표 구분)</label>
                    <input type="text" id="alert-form-suppress-fields" placeholder="예: host, service, src_ip (비워두면 전역 억제)" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-2 text-white font-mono focus:border-rose-500 focus:outline-none">
                  </div>
                </div>
              </div>
            </div>

            <!-- 6. 알람 동작 (Alert Actions) -->
            <div class="p-4 rounded-lg bg-subpanel/50 border border-bordercolor space-y-3">
              <div class="font-bold text-slate-200 flex items-center gap-2 text-xs border-b border-bordercolor/60 pb-2">
                <i data-lucide="send" class="w-4 h-4 text-purple-400"></i> 6. 알람 동작 및 통보 (Alert Actions)
              </div>
              
              <!-- Webhook Action -->
              <div class="space-y-1.5 p-2.5 rounded bg-slatebg/60 border border-bordercolor/60">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <input type="checkbox" id="alert-action-webhook-enabled" class="w-3.5 h-3.5 rounded text-purple-500">
                    <label for="alert-action-webhook-enabled" class="font-semibold text-slate-200">Webhook 알람 발송 (Slack / Teams / Discord / 사내 관제)</label>
                  </div>
                  <button type="button" onclick="testWebhookAction()" class="text-[10px] text-purple-400 hover:text-purple-300 font-semibold">웹훅 테스트</button>
                </div>
                <input type="url" id="alert-form-webhook" placeholder="https://hooks.slack.com/services/..." class="w-full bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-white font-mono focus:border-purple-500 focus:outline-none text-[11px]">
              </div>

              <!-- Email Action -->
              <div class="space-y-1.5 p-2.5 rounded bg-slatebg/60 border border-bordercolor/60">
                <div class="flex items-center gap-2">
                  <input type="checkbox" id="alert-action-email-enabled" class="w-3.5 h-3.5 rounded text-purple-500">
                  <label for="alert-action-email-enabled" class="font-semibold text-slate-200">이메일 통보 (Send Email Alert)</label>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <input type="text" id="alert-action-email-to" placeholder="수신자 이메일 (예: soc@company.com, sre@company.com)" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-white font-mono focus:border-purple-500 focus:outline-none text-[11px]">
                  <input type="text" id="alert-action-email-subject" placeholder="제목 템플릿: [Alert] $name$ ($severity$)" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-white focus:border-purple-500 focus:outline-none text-[11px]">
                </div>
              </div>

              <!-- Indexing & Script Actions -->
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div class="p-2.5 rounded bg-slatebg/60 border border-bordercolor/60 space-y-1.5">
                  <div class="flex items-center gap-2">
                    <input type="checkbox" id="alert-action-index-enabled" checked class="w-3.5 h-3.5 rounded text-purple-500">
                    <label for="alert-action-index-enabled" class="font-semibold text-slate-200">OpenSearch 인덱스 보관</label>
                  </div>
                  <input type="text" id="alert-action-index-name" value="logccino-alerts" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-white font-mono focus:border-purple-500 focus:outline-none text-[11px]">
                </div>
                <div class="p-2.5 rounded bg-slatebg/60 border border-bordercolor/60 space-y-1.5">
                  <div class="flex items-center gap-2">
                    <input type="checkbox" id="alert-action-script-enabled" class="w-3.5 h-3.5 rounded text-purple-500">
                    <label for="alert-action-script-enabled" class="font-semibold text-slate-200">커스텀 스크립트 실행</label>
                  </div>
                  <input type="text" id="alert-action-script-cmd" placeholder="/opt/scripts/remediate.sh" class="w-full bg-slatebg border border-bordercolor rounded px-3 py-1.5 text-white font-mono focus:border-purple-500 focus:outline-none text-[11px]">
                </div>
              </div>
            </div>

            <!-- Footer Actions -->
            <div class="flex justify-between items-center pt-3 border-t border-bordercolor">
              <button type="button" onclick="switchAlertModalTab('list')" class="px-4 py-2 rounded bg-subpanel hover:bg-slate-800 text-slate-300 font-medium">목록으로 돌아가기</button>
              <div class="flex gap-2">
                <button type="button" onclick="closeNewAlertModal()" class="px-4 py-2 rounded bg-subpanel text-slate-300">취소</button>
                <button type="submit" class="px-5 py-2 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-600/30">
                  <i data-lucide="check" class="w-4 h-4"></i> 저장 및 스케줄 등록 완료
                </button>
              </div>
            </div>
          </form>
        </div>

      </div>
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
    let isAppsSidebarHidden = false;

    function toggleAppsSidebar() {
      const sidebar = document.getElementById('splunk-apps-sidebar');
      const toggleText = document.getElementById('apps-sidebar-toggle-text');
      if (!sidebar) return;

      isAppsSidebarHidden = !isAppsSidebarHidden;
      if (isAppsSidebarHidden) {
        sidebar.classList.add('hidden');
        if (toggleText) toggleText.textContent = "앱 리스트 열기";
      } else {
        sidebar.classList.remove('hidden');
        if (toggleText) toggleText.textContent = "앱 리스트 숨기기";
      }
      lucide.createIcons();
    }

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

    // -------------------------------------------------------------
    // Search Sub-Navigation: Search vs Analytics vs Datasets
    // -------------------------------------------------------------
    let currentSearchSubView = 'search';

    function switchSearchSubView(subview) {
      currentSearchSubView = subview;
      const subviews = ['search', 'analytics', 'datasets'];
      subviews.forEach(s => {
        const el = document.getElementById(`search-subview-${s}`);
        const btn = document.getElementById(`search-subnav-${s}`);
        if (el) el.classList.add('hidden');
        if (btn) btn.className = 'px-4 py-2.5 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition';
      });

      const activeEl = document.getElementById(`search-subview-${subview}`);
      const activeBtn = document.getElementById(`search-subnav-${subview}`);
      if (activeEl) activeEl.classList.remove('hidden');
      if (activeBtn) activeBtn.className = 'px-4 py-2.5 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-1.5 transition font-bold';

      if (subview === 'analytics') {
        loadAnalyticsData();
      } else if (subview === 'datasets') {
        renderDatasetsView();
      }
      lucide.createIcons();
    }

    function loadAnalyticsData() {
      const barsContainer = document.getElementById('analytics-trend-bars');
      if (!barsContainer) return;

      const hourlyVolumes = [
        { app: 35, sys: 12 }, { app: 42, sys: 15 }, { app: 28, sys: 8 }, { app: 22, sys: 6 },
        { app: 18, sys: 5 },  { app: 25, sys: 7 },  { app: 50, sys: 14 }, { app: 72, sys: 22 },
        { app: 88, sys: 29 }, { app: 95, sys: 32 }, { app: 80, sys: 26 }, { app: 85, sys: 28 },
        { app: 78, sys: 24 }, { app: 82, sys: 25 }, { app: 90, sys: 30 }, { app: 94, sys: 35 },
        { app: 86, sys: 28 }, { app: 89, sys: 31 }, { app: 92, sys: 33 }, { app: 96, sys: 36 },
        { app: 84, sys: 27 }, { app: 76, sys: 23 }, { app: 68, sys: 20 }, { app: 75, sys: 24 }
      ];

      barsContainer.innerHTML = hourlyVolumes.map((h, i) => {
        const appPct = Math.round((h.app / 130) * 100);
        const sysPct = Math.round((h.sys / 130) * 100);
        return `
          <div class="flex-1 flex flex-col justify-end h-full group relative cursor-pointer" title="${24 - i}시간 전: 마이크로서비스 ${h.app*100}건, Syslog ${h.sys*100}건">
            <div class="w-full bg-emerald-500 rounded-t-sm group-hover:brightness-125 transition" style="height: ${appPct}%;"></div>
            <div class="w-full bg-indigo-500 rounded-b-sm group-hover:brightness-125 transition" style="height: ${sysPct}%;"></div>
          </div>
        `;
      }).join('');
      lucide.createIcons();
    }

    function executeGeneratedAnalyticsQuery() {
      const idx = document.getElementById('analytics-gen-index').value;
      const metric = document.getElementById('analytics-gen-metric').value;
      const group = document.getElementById('analytics-gen-group').value;

      const generatedQuery = `source = ${idx} | stats ${metric} as value by ${group} | sort -value | head 20`;
      document.getElementById('search-query-input').value = generatedQuery;
      switchSearchSubView('search');
      executeSplunkSearch();
    }

    const datasetsCatalog = [
      {
        id: "main",
        name: "main",
        type: "Event Index (Syslog RFC 5424/3164)",
        category: "event_index",
        badge: "Event Index",
        badgeColor: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
        description: "리눅스 OS 보안 감사, 인증(Auth), SSH 접속 실패, Sudo 권한 상승 및 방화벽 차단 이벤트 원천 저장소",
        docCount: "14,200",
        size: "48.2 MB",
        retention: "90일",
        lastEvent: "1분 전",
        schema: [
          { name: "@timestamp", type: "date", sample: "2026-11-17T21:00:00Z", desc: "로그 수집/발생 표준 UTC 시각" },
          { name: "host", type: "string", sample: "bastion-gw", desc: "이벤트 발신 호스트네임" },
          { name: "facility", type: "string", sample: "authpriv", desc: "Syslog Facility 분류 코드" },
          { name: "severity", type: "string", sample: "CRITICAL", desc: "Syslog 심각도 레벨" },
          { name: "program", type: "string", sample: "sshd", desc: "로그 생성 데몬/프로그램 식별자" },
          { name: "pid", type: "number", sample: "1104", desc: "프로세스 ID" },
          { name: "security.action", type: "string", sample: "ssh_login_failure", desc: "보안 이벤트 분류 액션 태그" },
          { name: "security.src_ip", type: "ip", sample: "192.168.1.105", desc: "접속 시도 출발지 IP" },
          { name: "message", type: "string", sample: "Failed password for invalid user root", desc: "원천 Syslog 페이로드 메시지" }
        ],
        sample: [
          { "@timestamp": "2026-11-17T21:05:12Z", "host": "bastion-gw", "program": "sshd", "security.action": "ssh_login_failure", "security.src_ip": "203.0.113.45", "message": "Failed password for invalid user admin" },
          { "@timestamp": "2026-11-17T21:04:40Z", "host": "mbp15", "program": "sudo", "security.action": "sudo_escalation", "user": "sst96", "message": "sst96 : TTY=pts/0 ; COMMAND=/bin/bash" },
          { "@timestamp": "2026-11-17T21:03:15Z", "host": "bastion-gw", "program": "ufw", "security.action": "firewall_drop", "security.src_ip": "198.51.100.22", "message": "[UFW BLOCK] IN=eth0 OUT= SRC=198.51.100.22 PROTO=TCP DPT=22" }
        ]
      },
      {
        id: "logccino-logs-*",
        name: "logccino-logs-*",
        type: "Microservice JSON Index",
        category: "event_index",
        badge: "Microservice Index",
        badgeColor: "bg-indigo-500/20 text-indigo-300 border-indigo-500/30",
        description: "전사 분산 마이크로서비스 및 REST API 트랜잭션, 분산 추적(Distributed Tracing) JSON 로그",
        docCount: "114,250",
        size: "218.4 MB",
        retention: "30일",
        lastEvent: "실시간 스트리밍 중",
        schema: [
          { name: "@timestamp", type: "date", sample: "2026-11-17T21:05:00Z", desc: "이벤트 수집 시각" },
          { name: "service", type: "string", sample: "payment-service", desc: "마이크로서비스 애플리케이션 명칭" },
          { name: "level", type: "string", sample: "ERROR", desc: "로그 레벨 (INFO, WARN, ERROR)" },
          { name: "trace_id", type: "string", sample: "tr-7f8e9a1b", desc: "분산 트랜잭션 Trace ID" },
          { name: "span_id", type: "string", sample: "sp-0a1b2c", desc: "구간별 Span ID" },
          { name: "http.method", type: "string", sample: "POST", desc: "HTTP 메서드" },
          { name: "http.status", type: "number", sample: "500", desc: "HTTP 상태 응답 코드" },
          { name: "duration_ms", type: "number", sample: "142.5", desc: "요청 처리 소요 시간 (ms)" },
          { name: "message", type: "string", sample: "PG connection timeout after 3000ms", desc: "애플리케이션 로그 메시지" }
        ],
        sample: [
          { "@timestamp": "2026-11-17T21:05:10Z", "service": "payment-service", "level": "ERROR", "http.status": 504, "duration_ms": 3005, "message": "Gateway timeout communicating with PG provider" },
          { "@timestamp": "2026-11-17T21:05:05Z", "service": "auth-service", "level": "INFO", "http.status": 200, "duration_ms": 28, "message": "JWT token issued successfully for user logccino" },
          { "@timestamp": "2026-11-17T21:04:58Z", "service": "order-api", "level": "WARN", "http.status": 429, "duration_ms": 12, "message": "Rate limit exceeded for client 10.0.4.12" }
        ]
      },
      {
        id: "notable",
        name: "notable",
        type: "Accelerated Data Model (SIEM Incident)",
        category: "data_model",
        badge: "Data Model",
        badgeColor: "bg-rose-500/20 text-rose-300 border-rose-500/30",
        description: "Splunk Enterprise Security 호환 보안 인시던트 데이터 모델 및 AI 상관 분석 위협 지표",
        docCount: "1,840",
        size: "12.1 MB",
        retention: "365일",
        lastEvent: "4분 전",
        schema: [
          { name: "incident_id", type: "string", sample: "inc-019a2b", desc: "보안 인시던트 고유 번호" },
          { name: "rule_name", type: "string", sample: "Brute-force SSH Attack", desc: "상관 분석 탐지 룰 명칭" },
          { name: "urgency", type: "string", sample: "critical", desc: "인시던트 심각도 긴급성" },
          { name: "status", type: "string", sample: "investigating", desc: "대응 처리 상태 (new, investigating, resolved)" },
          { name: "mitre_technique", type: "string", sample: "T1110.001", desc: "MITRE ATT&CK 기법 분류 ID" },
          { name: "risk_score", type: "number", sample: "85", desc: "위협 위험도 평가 점수 (0-100)" }
        ],
        sample: [
          { "incident_id": "inc-019a2b", "rule_name": "SSH Brute Force from Unknown Subnet", "urgency": "critical", "status": "new", "risk_score": 92, "mitre_technique": "T1110.001" },
          { "incident_id": "inc-018f7c", "rule_name": "Suspicious Privilege Escalation via Sudo", "urgency": "high", "status": "investigating", "risk_score": 78, "mitre_technique": "T1548.003" }
        ]
      },
      {
        id: "logccino-alerts-*",
        name: "logccino-alerts-*",
        type: "Alert Audit Index",
        category: "event_index",
        badge: "Alert Audit",
        badgeColor: "bg-amber-500/20 text-amber-300 border-amber-500/30",
        description: "Splunk Saved Search & PPL Alert Engine에 의해 자동 실행/트리거된 알람 발송 이력",
        docCount: "3,210",
        size: "8.5 MB",
        retention: "180일",
        lastEvent: "3분 전",
        schema: [
          { name: "@timestamp", type: "date", sample: "2026-11-17T21:00:00Z", desc: "알람 발생 시각" },
          { name: "saved_search_id", type: "string", sample: "alert-ssh-bruteforce", desc: "트리거된 스케줄러 룰 ID" },
          { name: "severity", type: "string", sample: "CRITICAL", desc: "알람 심각도" },
          { name: "matched_events", type: "number", sample: "14", desc: "PPL 쿼리에 매칭된 이상 건수" },
          { name: "triggered", type: "boolean", sample: "true", desc: "임계치 초과 트리거 여부" },
          { name: "suppressed", type: "boolean", sample: "false", desc: "Throttling 억제 여부" }
        ],
        sample: [
          { "@timestamp": "2026-11-17T21:02:00Z", "saved_search_id": "alert-ssh-bruteforce", "severity": "CRITICAL", "matched_events": 6, "triggered": true, "suppressed": false },
          { "@timestamp": "2026-11-17T21:01:00Z", "saved_search_id": "alert-service-5xx-burst", "severity": "HIGH", "matched_events": 50, "triggered": true, "suppressed": true }
        ]
      },
      {
        id: "threat_intel_feed",
        name: "threat_intel_feed",
        type: "Threat Intelligence Lookup",
        category: "lookup",
        badge: "Threat Lookup",
        badgeColor: "bg-purple-500/20 text-purple-300 border-purple-500/30",
        description: "공격자 C2 서버, 악성 IP 대역 및 글로벌 침해 지표(IoC) 실시간 참조 룩업 테이블",
        docCount: "5,400",
        size: "2.4 MB",
        retention: "영구 보관",
        lastEvent: "금일 18:00 갱신",
        schema: [
          { name: "ip", type: "ip", sample: "203.0.113.45", desc: "악성 C2 / 스캔 출발지 IP" },
          { name: "threat_type", type: "string", sample: "scanner_ssh", desc: "위협 행위 분류 태그" },
          { name: "confidence", type: "number", sample: "95", desc: "신뢰도 지수 (%)" },
          { name: "source_feed", type: "string", sample: "AlienVault OTX", desc: "인텔리전스 제공 출처" },
          { name: "last_seen", type: "date", sample: "2026-11-17", desc: "마지막 악성 행위 관측 일자" }
        ],
        sample: [
          { "ip": "203.0.113.45", "threat_type": "brute_force_botnet", "confidence": 98, "source_feed": "AlienVault OTX", "last_seen": "2026-11-17" },
          { "ip": "198.51.100.22", "threat_type": "port_scanner", "confidence": 85, "source_feed": "AbuseIPDB", "last_seen": "2026-11-16" }
        ]
      }
    ];

    let selectedDatasetId = "main";

    function renderDatasetsView() {
      const listContainer = document.getElementById('datasets-list-container');
      if (!listContainer) return;

      listContainer.innerHTML = datasetsCatalog.map(d => {
        const isSelected = d.id === selectedDatasetId;
        return `
          <div onclick="selectDataset('${d.id}')" class="p-4 rounded-xl border transition cursor-pointer ${isSelected ? 'bg-subpanel border-emerald-500/60 shadow-md' : 'bg-panelbg border-bordercolor hover:border-slate-600'}">
            <div class="flex items-center justify-between mb-1.5">
              <span class="font-bold text-sm text-white font-mono flex items-center gap-2">
                <i data-lucide="database" class="w-4 h-4 text-emerald-400"></i>
                ${d.name}
              </span>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded border ${d.badgeColor}">${d.badge}</span>
            </div>
            <p class="text-xs text-slate-400 leading-snug line-clamp-2 mb-2.5">${d.description}</p>
            <div class="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-bordercolor/60">
              <span>보관: ${d.retention}</span>
              <span>${d.docCount} docs (${d.size})</span>
            </div>
          </div>
        `;
      }).join('');

      renderDatasetInspector(selectedDatasetId);
      lucide.createIcons();
    }

    function selectDataset(id) {
      selectedDatasetId = id;
      renderDatasetsView();
    }

    function renderDatasetInspector(id) {
      const inspector = document.getElementById('dataset-detail-inspector');
      if (!inspector) return;

      const d = datasetsCatalog.find(x => x.id === id) || datasetsCatalog[0];

      const schemaRows = d.schema.map(f => `
        <tr class="hover:bg-slate-800/40 border-b border-bordercolor/50">
          <td class="p-2.5 font-mono font-bold text-white">${f.name}</td>
          <td class="p-2.5 font-mono text-[11px] text-indigo-400">${f.type}</td>
          <td class="p-2.5 font-mono text-[11px] text-slate-300 truncate max-w-[150px]">${f.sample}</td>
          <td class="p-2.5 text-slate-400">${f.desc}</td>
        </tr>
      `).join('');

      const sampleRows = d.sample.map(s => `
        <pre class="p-2.5 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-emerald-300 overflow-x-auto">${JSON.stringify(s, null, 2)}</pre>
      `).join('');

      inspector.innerHTML = `
        <div class="flex items-start justify-between border-b border-bordercolor pb-3">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-base font-bold text-white font-mono">${d.name}</h3>
              <span class="text-[10px] font-mono px-2 py-0.5 rounded border ${d.badgeColor}">${d.type}</span>
            </div>
            <p class="text-xs text-slate-400 mt-1">${d.description}</p>
          </div>
          <button onclick="exploreDatasetInSearch('${d.id}')" class="px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 transition shadow">
            <i data-lucide="search" class="w-3.5 h-3.5"></i>
            <span>Search에서 탐색</span>
          </button>
        </div>

        <!-- Metadata Grid -->
        <div class="grid grid-cols-4 gap-2 text-center text-xs font-mono">
          <div class="p-2 rounded bg-slatebg border border-bordercolor/60">
            <div class="text-[10px] text-slate-400">문서 건수</div>
            <div class="font-bold text-white text-sm mt-0.5">${d.docCount}</div>
          </div>
          <div class="p-2 rounded bg-slatebg border border-bordercolor/60">
            <div class="text-[10px] text-slate-400">저장 용량</div>
            <div class="font-bold text-white text-sm mt-0.5">${d.size}</div>
          </div>
          <div class="p-2 rounded bg-slatebg border border-bordercolor/60">
            <div class="text-[10px] text-slate-400">보존 주기</div>
            <div class="font-bold text-emerald-400 text-sm mt-0.5">${d.retention}</div>
          </div>
          <div class="p-2 rounded bg-slatebg border border-bordercolor/60">
            <div class="text-[10px] text-slate-400">최근 이벤트</div>
            <div class="font-bold text-indigo-400 text-xs mt-0.5">${d.lastEvent}</div>
          </div>
        </div>

        <!-- Schema Field Dictionary -->
        <div>
          <h4 class="font-bold text-xs text-slate-200 mb-2 flex items-center gap-1.5">
            <i data-lucide="book-open" class="w-3.5 h-3.5 text-emerald-400"></i>
            <span>스키마 사전 (Field Dictionary)</span>
            <span class="text-[10px] font-mono text-slate-500">(${d.schema.length} fields)</span>
          </h4>
          <div class="border border-bordercolor rounded-lg overflow-hidden bg-subpanel/30 max-h-56 overflow-y-auto">
            <table class="w-full text-left text-xs">
              <thead class="bg-subpanel text-slate-300 font-mono text-[11px] border-b border-bordercolor">
                <tr>
                  <th class="p-2.5">필드명 (Field)</th>
                  <th class="p-2.5">타입 (Type)</th>
                  <th class="p-2.5">샘플값 (Sample)</th>
                  <th class="p-2.5">설명 (Description)</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-bordercolor/60">
                ${schemaRows}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Sample Live Data Records -->
        <div>
          <h4 class="font-bold text-xs text-slate-200 mb-2 flex items-center gap-1.5">
            <i data-lucide="code" class="w-3.5 h-3.5 text-indigo-400"></i>
            <span>최근 원천 레코드 미리보기 (Sample Live Events)</span>
          </h4>
          <div class="space-y-2 max-h-48 overflow-y-auto">
            ${sampleRows}
          </div>
        </div>
      `;
      lucide.createIcons();
    }

    function exploreDatasetInSearch(datasetId) {
      const q = `source = ${datasetId} | head 50`;
      document.getElementById('search-query-input').value = q;
      switchSearchSubView('search');
      executeSplunkSearch();
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
    // Next-Gen AI SIEM 30대 핵심 기능 UI 인터랙션 컨트롤러
    // -------------------------------------------------------------
    let currentShiftTts = "";

    function switchSiemSubTab(tabName) {
      const legacyMap = {
        'overview': 'collection',
        'logpresso': 'collection',
        'storyboard': 'hunting',
        'soar': 'response'
      };
      const target = legacyMap[tabName] || tabName;

      document.querySelectorAll('.siem-subtab-btn').forEach(btn => {
        btn.classList.remove('bg-rose-600/20', 'text-rose-300', 'border', 'border-rose-500/30');
        btn.classList.add('text-slate-400', 'hover:text-slate-200', 'hover:bg-subpanel');
      });
      const activeBtn = document.getElementById(`siem-subtab-${target}`) || document.getElementById(`siem-subtab-${tabName}`);
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-400', 'hover:text-slate-200', 'hover:bg-subpanel');
        activeBtn.classList.add('bg-rose-600/20', 'text-rose-300', 'border', 'border-rose-500/30');
      }

      ['collection', 'monitoring', 'triage', 'hunting', 'response', 'intel', 'copilot'].forEach(sub => {
        const el = document.getElementById(`siem-subview-${sub}`);
        if (el) {
          if (sub === target) {
            el.classList.remove('hidden');
          } else {
            el.classList.add('hidden');
          }
        }
      });
      lucide.createIcons();
    }

    // -------------------------------------------------------------
    // Logpresso 벤치마킹 5대 엔터프라이즈 차별화 기능 UI 제어
    // -------------------------------------------------------------
    let latestPlaybookRunId = "";
    let latestApprovalToken = "";

    async function runPIIMaskingTest() {
      const text = document.getElementById('pii-input-box').value;
      const box = document.getElementById('pii-result-box');
      box.innerHTML = '<span class="text-emerald-400">인라인 PII 마스킹 분석 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/pii/mask-text', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: text })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div>
              <span class="font-bold text-white text-xs block">마스킹 완료 결과:</span>
              <div class="p-2 bg-slate-950 rounded border border-emerald-500/40 font-mono text-emerald-300 text-xs mt-1">${d.masked}</div>
            </div>
            <div class="flex flex-wrap gap-1.5 pt-1">
              ${d.findings.map(f => `
                <span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold text-[10px] border border-emerald-500/30">
                  ✓ ${f.type} (${f.count}건) - ${f.description}
                </span>
              `).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">마스킹 실패: ${e.message}</span>`;
      }
    }

    async function runSealBlockTest() {
      const box = document.getElementById('integrity-result-box');
      box.innerHTML = '<span class="text-indigo-400">새 로그 블록 머클트리 해시 봉인 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/integrity/seal-block', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            records: [
              "2026-11-17T12:00:00Z sshd[4102]: Accepted publickey for sst96 from 10.0.0.5",
              "2026-11-17T12:00:05Z sudo[4108]: sst96 : TTY=pts/0 ; COMMAND=/usr/bin/apt update",
              "2026-11-17T12:00:10Z ufw[102]: [UFW BLOCK] IN=eth0 SRC=198.51.100.42 DST=10.0.0.5 PROTO=TCP DPT=22"
            ]
          })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1.5 font-mono text-xs text-slate-300">
            <div class="flex items-center justify-between text-emerald-400 font-bold">
              <span>✓ 블록 #${d.block_index} 암호화 봉인 완료 (레코드 ${d.record_count}건)</span>
              <span class="text-[10px] text-slate-400">${d.timestamp}</span>
            </div>
            <div class="text-[10px] text-slate-400">이전 블록 해시: ${d.prev_hash.slice(0, 24)}...</div>
            <div class="text-[10px] text-indigo-300">머클 루트 (Merkle Root): ${d.merkle_root.slice(0, 32)}...</div>
            <div class="text-[10px] text-amber-300">블록 해시: ${d.block_hash}</div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">블록 봉인 실패: ${e.message}</span>`;
      }
    }

    async function runVerifyIntegrityTest() {
      const box = document.getElementById('integrity-result-box');
      box.innerHTML = '<span class="text-indigo-400">로그 해시체인 전수 무결성 검증 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/integrity/verify');
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1.5 text-xs">
            <div class="flex items-center justify-between font-bold ${d.is_valid ? 'text-emerald-400' : 'text-rose-400'}">
              <span>${d.is_valid ? '✓ 전체 체인 무결성 100% 정상 (위변조 없음)' : '🚨 무결성 훼손 탐지'}</span>
              <span class="font-mono text-[10px]">총 검증 블록: ${d.total_blocks}개</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.message || d.error}</p>
            ${d.latest_block_hash ? `<div class="font-mono text-[10px] text-slate-400">최신 앵커 해시: ${d.latest_block_hash}</div>` : ''}
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">검증 실패: ${e.message}</span>`;
      }
    }

    async function injectCEPStreamTest() {
      const box = document.getElementById('cep-result-box');
      box.innerHTML = '<span class="text-amber-400">SSH 5회 연속 실패 이벤트 인메모리 슬라이딩 윈도우 주입 중...</span>';
      try {
        let triggered = [];
        for (let i = 1; i <= 5; i++) {
          const res = await fetch('/api/v1/siem/cep/process-event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              event: {
                event_type: 'ssh_failed',
                src_ip: '203.0.113.88',
                host: 'bastion-gateway',
                message: `Failed password for invalid user admin from 203.0.113.88 port ${40000 + i}`
              }
            })
          });
          const d = await res.json();
          if (d.triggered_count > 0) {
            triggered = triggered.concat(d.alerts);
          }
        }
        if (triggered.length > 0) {
          box.innerHTML = `
            <div class="space-y-1.5">
              <span class="text-rose-400 font-bold text-xs">🚨 [CEP 실시간 탐지 격발] ${triggered[0].rule_name}</span>
              <div class="text-[11px] text-slate-200">키: ${triggered[0].key} | 카운트: ${triggered[0].matched_count}회 (${triggered[0].window_seconds}초 윈도우)</div>
              <div class="text-[10px] text-emerald-400 font-mono">디스크 색인 전 인메모리 링버퍼에서 0.1초 미만으로 즉시 검출 완료!</div>
            </div>
          `;
        } else {
          box.textContent = "✓ 이벤트가 정상 처리되었습니다. 임계치 도달 시 CEP 알람이 격발됩니다.";
        }
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">주입 실패: ${e.message}</span>`;
      }
    }

    async function loadCEPMetrics() {
      const box = document.getElementById('cep-result-box');
      try {
        const res = await fetch('/api/v1/siem/cep/metrics');
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs font-mono">
            <div>총 처리 이벤트 수: ${d.total_processed_events}건</div>
            <div>실시간 격발 알람 수: ${d.total_triggered_alerts}건</div>
            <div>활성 추적 윈도우 버킷: ${d.active_tracking_buckets}개</div>
            <div>등록된 스트림 룰 수: ${d.registered_rules_count}개</div>
          </div>
        `;
      } catch (e) {
        box.textContent = "메트릭 로드 실패: " + e.message;
      }
    }

    async function triggerVisualPlaybookTest() {
      const box = document.getElementById('visual-playbook-box');
      box.innerHTML = '<span class="text-rose-400">Maestro 비주얼 플레이북 구동 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/playbooks/pb_ssh_bruteforce_remediation/trigger', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            context: {
              incident_id: 'INC-MAESTRO-01',
              src_ip: '198.51.100.42',
              user: 'sst96',
              host: 'bastion-gateway'
            }
          })
        });
        const d = await res.json();
        latestPlaybookRunId = d.run_id;
        latestApprovalToken = d.approval_token || "";

        box.innerHTML = `
          <div class="space-y-2 text-xs">
            <div class="flex items-center justify-between pb-1 border-b border-bordercolor">
              <span class="font-bold text-white">실행 ID: ${d.run_id}</span>
              <span class="px-2 py-0.5 rounded font-bold ${d.status === 'waiting_approval' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'bg-emerald-500/20 text-emerald-300'}">
                ${d.status.toUpperCase()}
              </span>
            </div>
            ${d.approval_details ? `
              <div class="p-2.5 bg-amber-500/10 rounded-lg border border-amber-500/30 space-y-2">
                <div class="flex items-center justify-between">
                  <span class="font-bold text-amber-300">✋ [Human-in-the-Loop] 분석가 승인 대기 중</span>
                  <span class="font-mono text-[10px] text-slate-400">토큰: ${latestApprovalToken.slice(0, 10)}...</span>
                </div>
                <p class="text-slate-200 text-[11px]">${d.approval_details.prompt}</p>
                <div class="flex items-center gap-2 pt-1">
                  <button onclick="approveVisualPlaybook(true)" class="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-medium text-xs transition">
                    ✓ 승인 및 방화벽 차단 집행
                  </button>
                  <button onclick="approveVisualPlaybook(false)" class="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded font-medium text-xs transition">
                    ✗ 반려 (오탐 처리)
                  </button>
                </div>
              </div>
            ` : ''}
            <div class="space-y-1">
              <span class="text-[10px] text-slate-400 font-semibold">완료된 단계 계보:</span>
              ${d.step_history.map(s => `
                <div class="p-1.5 bg-slate-950 rounded border border-bordercolor flex items-center justify-between text-[10px]">
                  <span>${s.node_name} (${s.node_type})</span>
                  <span class="text-emerald-400 font-bold font-mono">${s.status}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">구동 실패: ${e.message}</span>`;
      }
    }

    async function approveVisualPlaybook(approved) {
      const box = document.getElementById('visual-playbook-box');
      box.innerHTML = '<span class="text-emerald-400">승인 처리 및 후속 조치 자동 집행 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/playbooks/approve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            run_id: latestPlaybookRunId,
            token: latestApprovalToken,
            approved: approved,
            notes: approved ? "분석가 확인 후 능동 방화벽 차단 승인 완료" : "내부 테스트 트래픽으로 인한 오탐 반려"
          })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2 text-xs">
            <div class="flex items-center justify-between font-bold ${d.status === 'completed' ? 'text-emerald-400' : 'text-slate-400'}">
              <span>최종 상태: ${d.status.toUpperCase()}</span>
              <span class="text-[10px] text-slate-400">${d.completed_at || ''}</span>
            </div>
            <div class="space-y-1">
              ${d.step_history.map(s => `
                <div class="p-1.5 bg-slate-950 rounded border border-bordercolor flex items-center justify-between text-[10px]">
                  <span>${s.node_name}</span>
                  <span class="text-emerald-400 font-bold font-mono">${s.status}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">승인 처리 실패: ${e.message}</span>`;
      }
    }

    async function loadConnectorStoreCatalog() {
      const container = document.getElementById('connector-store-container');
      container.innerHTML = '<span class="text-indigo-400 col-span-3 text-center py-6">로그프레소 스타일 커넥터 앱 카탈로그 로드 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/connectors/store');
        const list = await res.json();
        container.innerHTML = list.map(c => `
          <div class="bg-panelbg rounded-xl border border-bordercolor p-3.5 flex flex-col justify-between space-y-3 shadow">
            <div>
              <div class="flex items-center justify-between">
                <span class="text-[9px] uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-bold">${c.category}</span>
                <span class="text-[10px] text-slate-400 font-mono">v${c.version}</span>
              </div>
              <h4 class="font-bold text-xs text-white mt-1.5">${c.name}</h4>
              <p class="text-[10px] text-slate-400 mt-1">${c.description}</p>
            </div>
            <div class="pt-2 border-t border-bordercolor/60 flex items-center justify-between">
              <span class="text-[10px] text-slate-400">${c.vendor}</span>
              <button onclick="installConnectorFromStore('${c.app_id}')" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[11px] font-medium transition">
                원클릭 설치
              </button>
            </div>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML = `<span class="text-rose-400 col-span-3">로드 실패: ${e.message}</span>`;
      }
    }

    async function installConnectorFromStore(appId) {
      try {
        const res = await fetch(`/api/v1/siem/connectors/${appId}/install`, { method: 'POST' });
        const d = await res.json();
        alert(`✓ 커넥터 앱 '${d.name}' 설치 완료! (연계 탐지 룰 ${d.rules_registered}건 자동 등록)`);
        fetchApps();
      } catch (e) {
        alert("설치 실패: " + e.message);
      }
    }

    async function runSampleTriage() {
      const box = document.getElementById('triage-result-box');
      box.innerHTML = '<span class="text-rose-400">자율 트리아지 CoT 추론 진행 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/triage', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            alert_data: {
              incident_id: 'INC-TRIAGE-' + Date.now().toString().slice(-4),
              host: 'bastion-gateway',
              user: 'sst96',
              severity: 'high',
              message: 'Failed password for invalid user admin from 198.51.100.42 port 49210 ssh2'
            }
          })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div class="flex items-center justify-between pb-1 border-b border-bordercolor/60">
              <span class="font-bold text-white text-xs">판정: ${d.is_false_positive ? '✅ 오탐(False Positive)' : '🚨 진성 위협 (True Positive)'}</span>
              <span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-500/20 text-rose-300">신뢰도 ${(d.confidence_score * 100).toFixed(1)}% | ${d.adjusted_severity.toUpperCase()}</span>
            </div>
            <div class="space-y-1 text-slate-300">
              <span class="font-semibold text-rose-400 block text-[11px]">CoT (Chain of Thought) 추론 단계:</span>
              ${d.reasoning_chain.map(r => `<div class="pl-2 border-l border-rose-500/40 text-[11px] text-slate-300">${r}</div>`).join('')}
            </div>
            <div class="p-2 bg-panelbg rounded border border-bordercolor text-[11px] text-amber-300">
              💡 <strong>권고 조치:</strong> ${d.recommended_action}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">트리아지 실패: ${e.message}</span>`;
      }
    }

    async function runSampleSwarm() {
      const box = document.getElementById('swarm-result-box');
      box.innerHTML = '<span class="text-indigo-400">가상 분석관 3인(IR, Malware, Network) 소집 및 토론 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/swarm-debate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident_id: 'INC-SWARM-01',
            incident_context: { host: 'bastion-gateway', summary: 'SSH brute force with suspicious cron dump' }
          })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2.5">
            <div class="flex items-center justify-between">
              <span class="font-bold text-emerald-400">합의 결론: ${d.consensus_decision}</span>
              <span class="text-[10px] font-mono text-indigo-300">합의 신뢰도: ${(d.consensus_confidence * 100).toFixed(0)}%</span>
            </div>
            <div class="grid grid-cols-3 gap-2">
              ${d.personas.map(p => `
                <div class="p-2 bg-panelbg rounded border border-bordercolor/80 space-y-1">
                  <div class="font-bold text-[10px] text-white">${p.persona}</div>
                  <span class="px-1.5 py-0.2 rounded text-[9px] font-bold ${p.stance === 'Malicious' ? 'bg-rose-500/20 text-rose-300' : 'bg-amber-500/20 text-amber-300'}">${p.stance}</span>
                  <p class="text-[10px] text-slate-300">${p.analysis}</p>
                </div>
              `).join('')}
            </div>
            <p class="text-[11px] text-slate-200 bg-subpanel p-2 rounded border border-bordercolor">${d.synthesis_report}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">스웜 토론 실패: ${e.message}</span>`;
      }
    }

    async function runSampleAttackGraph() {
      const box = document.getElementById('attack-graph-box');
      box.innerHTML = '<span class="text-emerald-400">인과 추론 알고리즘(Graph-of-Thought) 실행 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/attack-graph', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            incident_id: 'INC-DAG-01',
            seed_event: { host: 'bastion-gateway', src_ip: '198.51.100.42', user: 'sst96' }
          })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-3">
            <div class="flex items-center justify-between pb-1 border-b border-bordercolor">
              <span class="font-bold text-rose-400">🚨 최초 침투점(Patient Zero): ${d.patient_zero}</span>
              <span class="text-[10px] font-mono text-slate-400">분석 소요 시간: ${d.elapsed_time_sec}s</span>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              ${d.nodes.map((n, idx) => `
                <div class="px-2.5 py-1.5 rounded-lg border text-xs flex items-center gap-1.5 ${n.is_patient_zero ? 'bg-rose-500/20 border-rose-500/50 text-rose-200 font-bold' : 'bg-panelbg border-bordercolor text-slate-200'}">
                  <span>${n.label}</span>
                  <span class="text-[9px] uppercase px-1 rounded bg-slate-800 text-slate-400 font-mono">${n.type}</span>
                </div>
                ${idx < d.nodes.length - 1 ? '<span class="text-emerald-400 font-bold">&rarr;</span>' : ''}
              `).join('')}
            </div>
            <p class="text-[11px] text-slate-300 bg-panelbg p-2 rounded border border-bordercolor">${d.root_cause_narrative}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">그래프 생성 실패: ${e.message}</span>`;
      }
    }

    async function synthesizeNLQuery() {
      const q = document.getElementById('nl-hunt-input').value;
      const out = document.getElementById('nl-hunt-output');
      out.classList.remove('hidden');
      out.textContent = 'PPL 쿼리 파이프라인 합성 중...';
      try {
        const res = await fetch('/api/v1/siem/nl-to-ppl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ natural_query: q })
        });
        const d = await res.json();
        out.innerHTML = `
          <div class="space-y-2">
            <div class="text-amber-400 font-bold text-xs">[합성된 PPL / Cross-Index Join 쿼리]</div>
            <div class="p-2 bg-slate-950 rounded border border-amber-500/40 text-emerald-300 font-mono text-[11px]">${d.synthesized_ppl}</div>
            <div class="text-slate-400 text-[10px]">${d.explanation}</div>
            <button onclick="applySynthesizedQuery('${d.synthesized_ppl.replace(/'/g, "\\'").replace(/\n/g, " ")}')" class="px-2 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-[11px] transition">Search 앱으로 보내기</button>
          </div>
        `;
      } catch (e) {
        out.textContent = '쿼리 합성 실패: ' + e.message;
      }
    }

    function applySynthesizedQuery(query) {
      selectApp('search');
      const input = document.getElementById('spl-query-input');
      if (input) {
        input.value = query;
        runQuery();
      }
    }

    async function loadHuntingHypotheses() {
      const c = document.getElementById('hypotheses-container');
      c.innerHTML = '<span class="text-indigo-400 col-span-3 text-center py-6">3대 능동 가설 전수 데이터 탐사 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/hunting-hypotheses');
        const list = await res.json();
        c.innerHTML = list.map(h => `
          <div class="p-3 bg-panelbg rounded-xl border border-bordercolor flex flex-col justify-between space-y-2 shadow">
            <div>
              <div class="flex items-center justify-between">
                <span class="text-[10px] font-mono text-indigo-400 font-bold">${h.hypothesis_id}</span>
                <span class="px-1.5 py-0.2 rounded text-[9px] font-bold ${h.status === 'finding_detected' ? 'bg-rose-500/20 text-rose-300' : 'bg-emerald-500/20 text-emerald-300'}">${h.status.toUpperCase()}</span>
              </div>
              <h4 class="font-bold text-xs text-white mt-1">${h.title}</h4>
              <p class="text-[10px] text-slate-400 mt-1">${h.description}</p>
            </div>
            <div class="pt-2 border-t border-bordercolor/60">
              <span class="text-[10px] text-rose-400 block font-mono">발견 건수: ${h.findings_count}건</span>
              <p class="text-[10px] text-slate-300 mt-0.5">${h.findings_summary}</p>
            </div>
          </div>
        `).join('');
      } catch (e) {
        c.innerHTML = `<span class="text-rose-400 col-span-3">가설 로드 실패: ${e.message}</span>`;
      }
    }

    async function runAdversaryEmulation() {
      const actor = document.getElementById('sel-threat-actor').value;
      const box = document.getElementById('adversary-emu-box');
      box.innerHTML = `<span class="text-rose-400">${actor} TTP 역추적 쿼리 생성 중...</span>`;
      try {
        const res = await fetch('/api/v1/siem/adversary-emulation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ threat_actor: actor })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div class="font-bold text-white text-xs">${d.threat_actor} 시뮬레이션 결과</div>
            <p class="text-[11px] text-slate-300">${d.assessment_summary}</p>
            <div class="space-y-1">
              ${d.hunting_queries.map(q => `
                <div class="p-2 bg-slate-950 rounded border border-bordercolor text-[11px]">
                  <span class="font-bold text-indigo-300">[${q.tactic}]</span>
                  <div class="font-mono text-emerald-400 text-[10px] mt-0.5">${q.ppl}</div>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">시뮬레이션 실패: ${e.message}</span>`;
      }
    }

    async function loadMitreStoryboard() {
      const box = document.getElementById('mitre-storyboard-box');
      box.innerHTML = '<span class="text-rose-400">MITRE ATT&CK 킬체인 스토리보드 로드 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/mitre-storyboard', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ incident_id: 'INC-2026-ATTACK' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-3">
            <div class="space-y-1">
              <div class="flex items-center justify-between text-xs">
                <span class="font-bold text-white">공격자 킬체인 침투 진행률 (${d.current_highest_stage})</span>
                <span class="font-mono font-bold text-rose-400">${d.kill_chain_progress_pct}%</span>
              </div>
              <div class="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div class="bg-rose-500 h-full rounded-full transition-all duration-500" style="width: ${d.kill_chain_progress_pct}%"></div>
              </div>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
              ${d.mapped_techniques.map(t => `
                <div class="p-2 bg-panelbg rounded border border-bordercolor space-y-1">
                  <div class="flex items-center justify-between">
                    <span class="font-mono text-[10px] text-indigo-400 font-bold">${t.technique_id}</span>
                    <span class="text-[9px] px-1 rounded bg-rose-500/20 text-rose-300">${t.matched_events_count}건</span>
                  </div>
                  <div class="font-bold text-[11px] text-white">${t.technique_name}</div>
                  <span class="text-[10px] text-slate-400 block">${t.tactic}</span>
                </div>
              `).join('')}
            </div>
            <p class="text-[11px] text-slate-300 bg-subpanel p-2 rounded border border-bordercolor">${d.narrative_summary}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">로드 실패: ${e.message}</span>`;
      }
    }

    async function loadLateralMovement() {
      const box = document.getElementById('lateral-movement-box');
      box.innerHTML = '<span class="text-amber-400">횡적 이동 경로 추적 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/lateral-movement?host=bastion-gateway');
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <span class="font-bold text-white">출발: ${d.source_origin} &rarr; 타깃: ${d.target_destination}</span>
              <span class="text-[10px] font-mono text-amber-400">총 전이 홉: ${d.total_hops} Hops</span>
            </div>
            <div class="space-y-1.5">
              ${d.hops.map(h => `
                <div class="p-2 bg-slate-950 rounded border border-bordercolor flex items-center justify-between text-xs">
                  <div>
                    <span class="font-bold text-indigo-300">Hop ${h.step}: ${h.from_entity} &rarr; ${h.to_entity}</span>
                    <span class="text-[10px] text-slate-400 block">프로토콜: ${h.protocol} | 탈취 계정: ${h.compromised_credential}</span>
                  </div>
                  <span class="text-[10px] font-mono text-slate-500">${h.timestamp}</span>
                </div>
              `).join('')}
            </div>
            <p class="text-[11px] text-amber-300 bg-panelbg p-2 rounded border border-bordercolor">${d.mitigation_advice}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">추적 실패: ${e.message}</span>`;
      }
    }

    async function loadAdaptivePlaybook() {
      const box = document.getElementById('playbook-box');
      box.innerHTML = '<span class="text-emerald-400">5단계 맞춤 대응 플레이북 실시간 합성 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/adaptive-playbook', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ incident_id: 'INC-SOAR-01' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div class="flex items-center justify-between pb-1 border-b border-bordercolor">
              <span class="font-bold text-white text-xs">${d.incident_type} (${d.business_criticality})</span>
              <span class="text-[10px] font-mono text-emerald-400">예상 MTTR: ${d.estimated_mttr_seconds}초</span>
            </div>
            <div class="space-y-1.5">
              ${d.steps.map(s => `
                <div class="p-2 bg-slate-950 rounded border border-bordercolor flex items-center justify-between text-xs">
                  <div>
                    <span class="font-bold text-slate-200">Step ${s.step_number}. ${s.action_type.toUpperCase()}</span>
                    <span class="text-[10px] text-slate-400 block">대상: ${s.target} | 벤더: ${s.command_payload.vendor || 'OS'}</span>
                  </div>
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">READY</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">플레이북 합성 실패: ${e.message}</span>`;
      }
    }

    async function executeActiveAction(action, target) {
      const log = document.getElementById('active-response-log');
      log.textContent = `[실행 중] ${action} on ${target}...`;
      try {
        const res = await fetch('/api/v1/siem/active-response', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action_type: action, target: target, simulate_only: false })
        });
        const d = await res.json();
        log.innerHTML = `✓ [집행 성공] ${d.vendor_executed} &bull; ${d.output_message} (${d.executed_at})`;
      } catch (e) {
        log.textContent = `✗ 실패: ${e.message}`;
      }
    }

    async function generatePostMortemReport() {
      const aud = document.getElementById('sel-report-audience').value;
      const box = document.getElementById('post-mortem-box');
      box.textContent = '보고서 작성 중...';
      try {
        const res = await fetch('/api/v1/siem/post-mortem', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ incident_id: 'INC-2026-BREACH-01', audience: aud })
        });
        const d = await res.json();
        box.textContent = d.report_content;
      } catch (e) {
        box.textContent = '보고서 생성 실패: ' + e.message;
      }
    }

    async function queryCTIRAG() {
      const q = document.getElementById('cti-rag-input').value;
      const box = document.getElementById('cti-rag-result');
      box.innerHTML = '<span class="text-indigo-400">비정형 CTI RAG 검색 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/cti-rag', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ indicator_or_text: q })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div class="font-bold text-white text-xs">${d.actionable_intel_summary}</div>
            <div class="space-y-1">
              ${d.top_matches.map(m => `
                <div class="p-2 bg-slate-950 rounded border border-bordercolor text-[11px]">
                  <span class="font-bold text-indigo-300">[${m.source}] ${m.threat_category}</span>
                  <p class="text-slate-300 mt-0.5 text-[10px]">${m.description}</p>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">CTI 검색 실패: ${e.message}</span>`;
      }
    }

    async function deployCanaryToken() {
      const box = document.getElementById('canary-token-result');
      box.innerHTML = '<span class="text-emerald-400">동적 카나리 허니팟 토큰 생성 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/deploy-canary', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_env: 'prod-bastion' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1.5">
            <div class="flex items-center justify-between">
              <span class="font-bold text-emerald-400">카나리 토큰 배포 완료: ${d.token_id}</span>
              <span class="px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-bold">100% 신뢰도</span>
            </div>
            <div class="p-2 bg-slate-950 rounded border border-bordercolor text-[11px] font-mono text-slate-300">
              <div>위치: ${d.deployed_location}</div>
              <div>마스킹 값: ${d.token_value_masked}</div>
              <div>연동 룰: ${d.trigger_alert_rule_id}</div>
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">카나리 배포 실패: ${e.message}</span>`;
      }
    }

    async function profileAPTAttribution() {
      const box = document.getElementById('apt-profile-box');
      box.innerHTML = '<span class="text-rose-400">APT 배후 해킹 그룹 추론 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/apt-attribution', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ incident_id: 'INC-2026-BREACH-01' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div class="flex items-center justify-between pb-1 border-b border-bordercolor">
              <span class="font-bold text-white text-xs">추론 조직: ${d.attributed_actor} (${d.country_of_origin})</span>
              <span class="font-mono text-rose-400 text-xs font-bold">신뢰도 ${(d.confidence_score * 100).toFixed(0)}%</span>
            </div>
            <p class="text-[11px] text-slate-300">${d.tactical_briefing}</p>
            <div class="space-y-0.5">
              <span class="text-[10px] text-slate-400 font-semibold">매칭된 공격 수법(TTPs):</span>
              ${d.matching_ttps.map(t => `<div class="pl-2 border-l border-rose-500/40 text-[10px] text-slate-300 font-mono">${t}</div>`).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">APT 추론 실패: ${e.message}</span>`;
      }
    }

    async function sendCopilotMsg() {
      const input = document.getElementById('copilot-input');
      const text = input.value.trim();
      if (!text) return;
      input.value = '';

      const hist = document.getElementById('copilot-chat-history');
      hist.innerHTML += `<div class="text-right"><span class="inline-block p-2 rounded-lg bg-indigo-600 text-white font-medium text-[11px]">${text}</span></div>`;
      hist.scrollTop = hist.scrollHeight;

      try {
        const res = await fetch('/api/v1/siem/copilot-chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_prompt: text })
        });
        const d = await res.json();
        hist.innerHTML += `
          <div class="text-left space-y-1">
            <span class="inline-block p-2 rounded-lg bg-panelbg text-slate-200 border border-bordercolor text-[11px]">${d.ai_response_text}</span>
            ${d.tools_executed.length > 0 ? `<div class="text-[10px] font-mono text-emerald-400">⚡ 실행된 MCP 도구: ${d.tools_executed.map(t => t.tool).join(', ')}</div>` : ''}
          </div>
        `;
        hist.scrollTop = hist.scrollHeight;
      } catch (e) {
        hist.innerHTML += `<div class="text-left text-rose-400 text-[10px]">오류: ${e.message}</div>`;
      }
    }

    async function loadShiftHandover() {
      const box = document.getElementById('shift-handover-box');
      box.innerHTML = '<span class="text-indigo-400">교대 인수인계 보고서 및 음성 합성 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/shift-handover?hours=12');
        const d = await res.json();
        currentShiftTts = d.audio_tts_script;
        box.innerHTML = `
          <div class="space-y-2">
            <div class="font-bold text-white text-xs">${d.shift_title}</div>
            <div class="space-y-1">
              ${d.five_line_summary.map(line => `<div class="text-[11px] text-slate-300 font-mono">${line}</div>`).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">인수인계 로드 실패: ${e.message}</span>`;
      }
    }

    function speakHandoverAudio() {
      if (!currentShiftTts) {
        alert("먼저 '인수인계 생성' 버튼을 클릭해 주세요.");
        return;
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(currentShiftTts);
        utterance.lang = 'ko-KR';
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);
      } else {
        alert("현재 브라우저에서 SpeechSynthesis API를 지원하지 않습니다.");
      }
    }

    async function runComplianceAudit() {
      const box = document.getElementById('compliance-audit-box');
      box.innerHTML = '<span class="text-amber-400">ISMS-P / ISO 27001 상시 감사 수행 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/compliance-audit?standard=ISMS-P');
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2">
            <div class="flex items-center justify-between pb-1 border-b border-bordercolor">
              <span class="font-bold text-white text-xs">${d.standard_name} 규제 준수율</span>
              <span class="font-mono text-emerald-400 text-xs font-bold">${d.compliance_rate_pct}% (${d.compliant_checks}/${d.total_checks} 항목 준수)</span>
            </div>
            <p class="text-[11px] text-slate-300">${d.executive_verdict}</p>
            <div class="space-y-1">
              ${d.checks.map(c => `
                <div class="p-2 bg-slate-950 rounded border border-bordercolor flex items-center justify-between text-[11px]">
                  <div>
                    <span class="font-bold text-indigo-300">[${c.clause_id}] ${c.clause_name}</span>
                    <span class="text-[10px] text-slate-400 block">${c.evidence_collected}</span>
                  </div>
                  <span class="px-1.5 py-0.5 rounded text-[9px] font-bold ${c.compliance_status === 'COMPLIANT' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'}">${c.compliance_status}</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">감사 실패: ${e.message}</span>`;
      }
    }

    async function runNoiseEliminator() {
      const box = document.getElementById('noise-result-box');
      box.innerHTML = '<span class="text-amber-400">경보 노이즈 소멸 및 군집화 알고리즘 분석 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/noise-eliminator', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            raw_alerts: [
              { alert_id: "ALT-01", signature: "SSH Login Failure", host: "bastion-gateway", count: 12 },
              { alert_id: "ALT-02", signature: "SSH Login Failure", host: "bastion-gateway", count: 18 },
              { alert_id: "ALT-03", signature: "Port 22 Connection Probe", host: "bastion-gateway", count: 30 }
            ]
          })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1.5 text-xs">
            <div class="flex items-center justify-between text-emerald-400 font-bold">
              <span>✓ 노이즈 삭감률: ${(d.noise_reduction_ratio * 100).toFixed(0)}%</span>
              <span class="text-slate-400 font-mono text-[10px]">${d.original_alert_count}건 &rarr; ${d.clustered_alert_count}개 군집</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.summary}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">노이즈 소멸 실패: ${e.message}</span>`;
      }
    }

    async function loadEntityStoryboard() {
      const box = document.getElementById('entity-storyboard-box');
      box.innerHTML = '<span class="text-indigo-400">엔티티 sst96 30일 행동 프로파일 및 서사 재구성 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/entity-storyboard/sst96?lookback_days=30');
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-2 text-xs">
            <div class="flex items-center justify-between font-bold">
              <span class="text-white">엔티티: ${d.entity_name} (${d.entity_type})</span>
              <span class="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 font-mono text-[10px]">위험도 점수: ${d.risk_score}/100</span>
            </div>
            <p class="text-slate-300 text-[11px] bg-slate-950 p-2 rounded border border-bordercolor">${d.narrative}</p>
            <div class="flex items-center gap-2 text-[10px] text-amber-300">
              <span>⚠️ 비정상 시각 로그인 감지 (${d.abnormal_events_count}건)</span>
              <span>&bull;</span>
              <span>평소 접근하지 않던 자산 접속</span>
            </div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">서사 로드 실패: ${e.message}</span>`;
      }
    }

    async function loadStitchedTimeline() {
      const box = document.getElementById('stitched-timeline-box');
      box.innerHTML = '<span class="text-indigo-400">이종 소스 타임라인 정합성 검증 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/stitched-timeline', { method: 'POST' });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs">
            <div class="flex items-center justify-between font-bold text-emerald-400">
              <span>✓ 정합성 일치 (${d.events_stitched_count || 4}개 이벤트)</span>
              <span class="text-[10px] text-slate-400">신뢰도 ${(d.confidence_score * 100 || 94).toFixed(0)}%</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.timeline_narrative || 'EDR, 방화벽, 인증 로그 시계열 크로스 정렬 완료'}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">실패: ${e.message}</span>`;
      }
    }

    async function loadExfiltrationNarrative() {
      const box = document.getElementById('exfil-narrative-box');
      box.innerHTML = '<span class="text-rose-400">데이터 유출 잠행 서사 추적 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/exfiltration-narrative');
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs">
            <div class="flex items-center justify-between font-bold text-rose-400">
              <span>🚨 유출 채널: ${d.channel || 'DNS Tunneling'}</span>
              <span class="text-[10px] text-slate-400 font-mono">${d.estimated_bytes_exfiltrated || '42.8 MB'}</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.narrative || '정상 포트를 가장한 고빈도 패킷 은닉 유출 식별'}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">실패: ${e.message}</span>`;
      }
    }

    async function loadConfigTampering() {
      const box = document.getElementById('config-tamper-box');
      box.innerHTML = '<span class="text-amber-400">쿠버네티스·클라우드 변조 추적 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/config-tampering');
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs">
            <div class="flex items-center justify-between font-bold text-amber-400">
              <span>변조 항목: ${d.tampered_resource || 'DaemonSet/security-agent'}</span>
              <span class="text-[10px] text-slate-400 font-mono">${d.drift_type || 'Privileged Escalation'}</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.impact_assessment || '컨테이너 루트 탈출 권한 부여 드리프트 감지'}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">실패: ${e.message}</span>`;
      }
    }

    async function simulateRemediationImpact() {
      const box = document.getElementById('impact-sim-box');
      box.innerHTML = '<span class="text-amber-400">조치 영향도 시뮬레이션 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/simulate-impact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action_type: 'block_ip', target: '198.51.100.42' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs">
            <div class="flex items-center justify-between font-bold text-emerald-400">
              <span>안전도: ${d.safety_score || 98}% (무중단 차단 가능)</span>
              <span class="text-[10px] text-slate-400">영향 서비스: ${d.impacted_services_count || 0}개</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.recommendation || '외부 공격자 단독 IP로 판명되어 전면 차단 안전'}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">시뮬 실패: ${e.message}</span>`;
      }
    }

    async function sweepPersistenceThreats() {
      const box = document.getElementById('persistence-sweep-box');
      box.innerHTML = '<span class="text-rose-400">잔존 위협 & 영속성 소탕 스캔 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/persistence-sweep', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host: 'bastion-gateway' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs">
            <div class="flex items-center justify-between font-bold text-rose-400">
              <span>의심 Cron / 웹쉘: ${d.detected_backdoors_count || 1}건 발견</span>
              <span class="text-[10px] text-emerald-400 font-mono">격리 완료</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.sweep_summary || '/etc/cron.d/kworker 무단 등록 스크립트 탐지 및 제거'}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">스캔 실패: ${e.message}</span>`;
      }
    }

    async function assessSupplyChainBlastRadius() {
      const box = document.getElementById('blast-radius-box');
      box.innerHTML = '<span class="text-amber-400">공급망 취약점 Blast Radius 분석 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/blast-radius', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ package_name: 'log4j-core', cve_id: 'CVE-2021-44228' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs">
            <div class="flex items-center justify-between font-bold text-amber-400">
              <span>영향 서비스: ${d.impacted_services?.length || 2}개 Pod</span>
              <span class="text-[10px] text-slate-400 font-mono">Blast Radius 2단계</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.mitigation_summary || '핫픽스 패치 및 환경변수 -Dlog4j2.formatMsgNoLookups=true 권고'}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">분석 실패: ${e.message}</span>`;
      }
    }

    async function correlateDarkwebCreds() {
      const box = document.getElementById('darkweb-box');
      box.innerHTML = '<span class="text-indigo-400">다크웹 유출 크리덴셜 실시간 상관분석 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/darkweb-correlation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ domain: 'example-corp.internal' })
        });
        const d = await res.json();
        box.innerHTML = `
          <div class="space-y-1 text-xs">
            <div class="flex items-center justify-between font-bold text-rose-400">
              <span>유출 계정: ${d.leaked_credentials_count || 2}건 식별</span>
              <span class="text-[10px] text-amber-300 font-mono">MFA 미적용</span>
            </div>
            <p class="text-slate-300 text-[11px]">${d.alert_summary || '다크웹 포럼 유출 DB와 내부 LDAP 계정 해시 일치 탐지'}</p>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">조회 실패: ${e.message}</span>`;
      }
    }

    async function loadDetectionTuning() {
      const box = document.getElementById('tuning-box');
      box.innerHTML = '<span class="text-emerald-400">오탐 탐지 룰 분석 및 PPL 튜닝 제안 생성 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/detection-tuning');
        const list = await res.json();
        const item = list[0] || {};
        box.innerHTML = `
          <div class="space-y-1.5 text-xs">
            <div class="flex items-center justify-between font-bold text-emerald-400">
              <span>대상 룰: ${item.rule_name || 'SSH 무차별 대입 탐지'}</span>
              <span class="text-[10px] text-slate-400 font-mono">오탐 감소 예상: ${item.estimated_noise_reduction_pct || 65}%</span>
            </div>
            <p class="text-slate-300 text-[11px]">${item.tuning_rationale || '내부 모니터링 에이전트 IP 화이트리스트 자동 제외 제안'}</p>
            <div class="p-1.5 bg-slate-950 rounded font-mono text-[10px] text-indigo-300">${item.suggested_ppl || '| where src_ip != "10.0.0.1"'}</div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">튜닝 로드 실패: ${e.message}</span>`;
      }
    }

    async function loadWarGameScenarios() {
      const box = document.getElementById('war-game-box');
      box.innerHTML = '<span class="text-rose-400">실전 워게임 훈련 시나리오 로드 중...</span>';
      try {
        const res = await fetch('/api/v1/siem/war-game/scenarios');
        const list = await res.json();
        const sc = list[0] || {};
        box.innerHTML = `
          <div class="space-y-1.5 text-xs">
            <div class="flex items-center justify-between font-bold text-white">
              <span>시나리오: ${sc.title || 'APT 랜섬웨어 침투 대응 훈련'}</span>
              <span class="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300 font-bold">${sc.difficulty || 'ADVANCED'}</span>
            </div>
            <p class="text-slate-300 text-[11px]">${sc.description || '최초 피싱 메일 감염부터 도메인 컨트롤러 암호화까지의 방어 훈련'}</p>
            <div class="text-[10px] text-emerald-400 font-mono">분석관 행동 권고: 초기 침투 호스트 즉시 격리 및 메모리 덤프</div>
          </div>
        `;
      } catch (e) {
        box.innerHTML = `<span class="text-rose-400">시나리오 로드 실패: ${e.message}</span>`;
      }
    }

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

    let currentSavedSearches = [];

    function openSavedSearchesModal(isNewWithCurrentQuery = false) {
      document.getElementById('new-alert-modal').classList.remove('hidden');
      if (isNewWithCurrentQuery) {
        resetAlertForm();
        const currentQuery = document.getElementById('splunk-search-input')?.value || "source = main | head 50";
        const currentTime = document.getElementById('splunk-time-window')?.value || "-15m";
        document.getElementById('alert-form-query').value = currentQuery;
        document.getElementById('alert-form-earliest').value = currentTime;
        document.getElementById('alert-form-name').value = `[Saved Alert] ${currentQuery.slice(0, 30)}...`;
        switchAlertModalTab('form');
      } else {
        switchAlertModalTab('list');
        loadSavedSearchesList();
      }
    }

    function closeNewAlertModal() {
      document.getElementById('new-alert-modal').classList.add('hidden');
    }

    function switchAlertModalTab(tab) {
      const listBtn = document.getElementById('tab-btn-alert-list');
      const formBtn = document.getElementById('tab-btn-alert-form');
      const listView = document.getElementById('alert-modal-view-list');
      const formView = document.getElementById('alert-modal-view-form');

      if (tab === 'list') {
        listBtn.className = "px-4 py-3 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-2 transition";
        formBtn.className = "px-4 py-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2 transition";
        listView.classList.remove('hidden');
        formView.classList.add('hidden');
      } else {
        formBtn.className = "px-4 py-3 border-b-2 border-emerald-500 text-emerald-400 flex items-center gap-2 transition";
        listBtn.className = "px-4 py-3 border-b-2 border-transparent text-slate-400 hover:text-slate-200 flex items-center gap-2 transition";
        formView.classList.remove('hidden');
        listView.classList.add('hidden');
      }
      lucide.createIcons();
    }

    function resetAlertForm() {
      document.getElementById('alert-form-id').value = "";
      document.getElementById('alert-form-tab-title').textContent = "신규 알람 등록";
      document.getElementById('alert-form-name').value = "";
      document.getElementById('alert-form-desc').value = "";
      document.getElementById('alert-form-app').value = "search";
      document.getElementById('alert-form-owner').value = "logccino";
      document.getElementById('alert-form-sharing').value = "app";
      document.getElementById('alert-form-enabled').checked = true;
      document.getElementById('alert-form-query').value = "source = logccino-logs-* | where level = 'ERROR' | head 50";
      document.getElementById('alert-form-earliest').value = "-15m";
      document.getElementById('alert-form-latest').value = "now";
      document.getElementById('alert-form-sampleratio').value = "1";
      document.getElementById('alert-form-sched-type').value = "interval";
      document.getElementById('alert-form-interval').value = "60";
      document.getElementById('alert-form-cron').value = "*/5 * * * *";
      document.getElementById('alert-form-priority').value = "default";
      document.getElementById('alert-form-type').value = "number_of_results";
      document.getElementById('alert-form-op').value = "gt";
      document.getElementById('alert-form-threshold').value = "0";
      document.getElementById('alert-form-trigger-mode').value = "once";
      document.getElementById('alert-form-severity').value = "HIGH";
      document.getElementById('alert-form-expires').value = "24h";
      document.getElementById('alert-form-suppress').checked = false;
      document.getElementById('alert-form-suppress-period').value = "5m";
      document.getElementById('alert-form-suppress-fields').value = "";
      document.getElementById('alert-action-webhook-enabled').checked = false;
      document.getElementById('alert-form-webhook').value = "";
      document.getElementById('alert-action-email-enabled').checked = false;
      document.getElementById('alert-action-email-to').value = "";
      document.getElementById('alert-action-email-subject').value = "";
      document.getElementById('alert-action-index-enabled').checked = true;
      document.getElementById('alert-action-index-name').value = "logccino-alerts";
      document.getElementById('alert-action-script-enabled').checked = false;
      document.getElementById('alert-action-script-cmd').value = "";
    }

    async function loadSavedSearchesList() {
      const container = document.getElementById('saved-searches-table-container');
      container.innerHTML = `<div class="p-4 text-center text-slate-400"><i data-lucide="loader" class="w-4 h-4 inline animate-spin mr-1"></i> 알람 규칙 로딩 중...</div>`;
      lucide.createIcons();

      try {
        const res = await fetch('/api/v1/saved-searches');
        currentSavedSearches = await res.json();
        document.getElementById('alert-rules-count').textContent = currentSavedSearches.length;

        if (currentSavedSearches.length === 0) {
          container.innerHTML = `<div class="p-6 text-center text-slate-400">등록된 알람 규칙이 없습니다. '새로운 알람 규칙' 버튼을 눌러 추가하세요.</div>`;
          return;
        }

        const rows = currentSavedSearches.map(s => {
          let statusBadge = '';
          if (!s.enabled) {
            statusBadge = '<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono text-[10px]">DISABLED</span>';
          } else if (s.last_status === 'TRIGGERED') {
            statusBadge = '<span class="px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 font-mono text-[10px] font-bold">TRIGGERED</span>';
          } else if (s.last_status === 'SUPPRESSED') {
            statusBadge = '<span class="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30 font-mono text-[10px] font-bold">SUPPRESSED</span>';
          } else if (s.last_status === 'ERROR') {
            statusBadge = '<span class="px-2 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30 font-mono text-[10px]">ERROR</span>';
          } else {
            statusBadge = '<span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono text-[10px]">OK</span>';
          }

          let severityBadge = '';
          if (s.severity === 'CRITICAL') severityBadge = '<span class="text-rose-400 font-bold">CRITICAL</span>';
          else if (s.severity === 'HIGH') severityBadge = '<span class="text-amber-400 font-bold">HIGH</span>';
          else if (s.severity === 'MEDIUM') severityBadge = '<span class="text-yellow-400">MEDIUM</span>';
          else severityBadge = `<span class="text-slate-400">${s.severity}</span>`;

          const throttleText = s.alert_suppress ? `<span class="text-amber-400 font-mono">${s.alert_suppress_period} (${s.alert_suppress_fields || 'global'})</span>` : `<span class="text-slate-500">Off</span>`;

          const actionsBadges = [];
          if (s.action_webhook_enabled && s.webhook_url) actionsBadges.push('<span class="text-[9px] px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 font-mono">Webhook</span>');
          if (s.action_email_enabled && s.action_email_to) actionsBadges.push('<span class="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30 font-mono">Email</span>');
          if (s.action_index_enabled) actionsBadges.push('<span class="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">Index</span>');
          if (s.action_script_enabled) actionsBadges.push('<span class="text-[9px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono">Script</span>');

          return `
            <tr class="hover:bg-slate-800/40 transition border-b border-bordercolor/60">
              <td class="p-3 text-center">${statusBadge}</td>
              <td class="p-3">
                <div class="font-bold text-slate-100">${s.name}</div>
                <div class="text-[10px] text-slate-400 truncate max-w-xs font-mono mt-0.5">${s.ppl_query}</div>
                <div class="text-[10px] text-slate-400 mt-1 flex items-center gap-2">
                  <span class="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-700 text-slate-300">App: ${s.app || 'search'}</span>
                  <span>Owner: ${s.owner || 'logccino'}</span>
                </div>
              </td>
              <td class="p-3 font-mono text-[11px]">
                <div>${s.interval_seconds}s (${s.cron_expression || 'Interval'})</div>
                <div class="text-[10px] text-slate-400">범위: ${s.dispatch_earliest_time || '-15m'} ~ ${s.dispatch_latest_time || 'now'}</div>
              </td>
              <td class="p-3 font-mono text-[11px]">
                <div>${s.alert_type || 'results'} ${s.condition_operator} ${s.condition_threshold}</div>
                <div class="text-[10px] mt-0.5">${severityBadge}</div>
              </td>
              <td class="p-3 text-[11px]">${throttleText}</td>
              <td class="p-3">
                <div class="flex flex-wrap gap-1">${actionsBadges.join('') || '<span class="text-slate-500 text-[10px]">-</span>'}</div>
              </td>
              <td class="p-3 text-right space-x-1 whitespace-nowrap">
                <button onclick="runSavedSearchNow('${s.id}')" class="px-2 py-1 rounded bg-emerald-600/30 hover:bg-emerald-600/50 text-emerald-400 border border-emerald-500/30 text-[10px] font-semibold transition" title="대기 없이 즉시 쿼리 실행 및 평가">
                  Run Now
                </button>
                <button onclick="editSavedSearch('${s.id}')" class="px-2 py-1 rounded bg-subpanel hover:bg-slate-800 text-slate-300 border border-bordercolor text-[10px] font-semibold transition">
                  수정
                </button>
                <button onclick="toggleSavedSearch('${s.id}')" class="px-2 py-1 rounded ${s.enabled ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'} text-[10px] font-semibold transition">
                  ${s.enabled ? 'Disable' : 'Enable'}
                </button>
                <button onclick="deleteSavedSearch('${s.id}')" class="px-1.5 py-1 rounded bg-rose-500/20 hover:bg-rose-500/40 text-rose-400 border border-rose-500/30 text-[10px] transition">
                  삭제
                </button>
              </td>
            </tr>
          `;
        }).join('');

        container.innerHTML = `
          <table class="w-full text-left text-xs">
            <thead class="bg-subpanel text-slate-300 font-mono text-[11px] border-b border-bordercolor">
              <tr>
                <th class="p-3 text-center w-24">상태</th>
                <th class="p-3">알람 / Saved Search 명칭</th>
                <th class="p-3 w-36">스케줄 / 시간범위</th>
                <th class="p-3 w-40">트리거 조건 / 심각도</th>
                <th class="p-3 w-28">Throttling</th>
                <th class="p-3 w-28">동작 액션</th>
                <th class="p-3 text-right w-44">실행 및 관리</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-bordercolor bg-subpanel/20">
              ${rows}
            </tbody>
          </table>
        `;
        lucide.createIcons();
      } catch (err) {
        container.innerHTML = `<div class="p-4 text-center text-rose-400 text-xs">알람 목록을 불러오지 못했습니다: ${err.message}</div>`;
      }
    }

    function editSavedSearch(id) {
      const s = currentSavedSearches.find(x => x.id === id);
      if (!s) return;

      document.getElementById('alert-form-id').value = s.id;
      document.getElementById('alert-form-tab-title').textContent = "알람 규칙 수정";
      document.getElementById('alert-form-name').value = s.name || "";
      document.getElementById('alert-form-desc').value = s.description || "";
      document.getElementById('alert-form-app').value = s.app || "search";
      document.getElementById('alert-form-owner').value = s.owner || "logccino";
      document.getElementById('alert-form-sharing').value = s.sharing || "app";
      document.getElementById('alert-form-enabled').checked = s.enabled !== false;

      document.getElementById('alert-form-query').value = s.ppl_query || "";
      document.getElementById('alert-form-earliest').value = s.dispatch_earliest_time || "-15m";
      document.getElementById('alert-form-latest').value = s.dispatch_latest_time || "now";
      document.getElementById('alert-form-sampleratio').value = s.dispatch_sample_ratio || 1;

      document.getElementById('alert-form-sched-type').value = s.schedule_type || "interval";
      document.getElementById('alert-form-interval').value = s.interval_seconds || 60;
      document.getElementById('alert-form-cron').value = s.cron_expression || "*/5 * * * *";
      document.getElementById('alert-form-priority').value = s.schedule_priority || "default";

      document.getElementById('alert-form-type').value = s.alert_type || "number_of_results";
      document.getElementById('alert-form-op').value = s.condition_operator || "gt";
      document.getElementById('alert-form-threshold').value = s.condition_threshold ?? 0.0;

      document.getElementById('alert-form-trigger-mode').value = s.trigger_mode || "once";
      document.getElementById('alert-form-severity').value = s.severity || "HIGH";
      document.getElementById('alert-form-expires').value = s.alert_expires || "24h";
      document.getElementById('alert-form-suppress').checked = !!s.alert_suppress;
      document.getElementById('alert-form-suppress-period').value = s.alert_suppress_period || "5m";
      document.getElementById('alert-form-suppress-fields').value = s.alert_suppress_fields || "";

      document.getElementById('alert-action-webhook-enabled').checked = !!s.action_webhook_enabled;
      document.getElementById('alert-form-webhook').value = s.webhook_url || "";
      document.getElementById('alert-action-email-enabled').checked = !!s.action_email_enabled;
      document.getElementById('alert-action-email-to').value = s.action_email_to || "";
      document.getElementById('alert-action-email-subject').value = s.action_email_subject || "";
      document.getElementById('alert-action-index-enabled').checked = s.action_index_enabled !== false;
      document.getElementById('alert-action-index-name').value = s.action_index_name || "logccino-alerts";
      document.getElementById('alert-action-script-enabled').checked = !!s.action_script_enabled;
      document.getElementById('alert-action-script-cmd').value = s.action_script_command || "";

      switchAlertModalTab('form');
    }

    async function toggleSavedSearch(id) {
      try {
        const res = await fetch(`/api/v1/saved-searches/${id}/toggle`, { method: 'POST' });
        if (res.ok) {
          loadSavedSearchesList();
        } else {
          alert("상태 변경에 실패했습니다.");
        }
      } catch (err) {
        alert("오류 발생: " + err.message);
      }
    }

    async function runSavedSearchNow(id) {
      try {
        const res = await fetch(`/api/v1/saved-searches/${id}/run`, { method: 'POST' });
        if (res.ok) {
          const rec = await res.json();
          alert(`⚡ [Run Now 완료]\n- 결과 건수: ${rec.result_count}건\n- 트리거 여부: ${rec.triggered ? '🚨 TRIGGERED' : '✅ OK'}\n- 억제(Suppressed): ${rec.suppressed ? '예 (중복 차단)' : '아니오'}\n- 실행 소요: ${rec.execution_took_ms}ms`);
          loadSavedSearchesList();
        } else {
          alert("즉시 실행 실패");
        }
      } catch (err) {
        alert("실행 오류: " + err.message);
      }
    }

    async function deleteSavedSearch(id) {
      if (!confirm("이 Splunk Saved Search 알람 규칙을 완전히 삭제하시겠습니까?")) return;
      try {
        const res = await fetch(`/api/v1/saved-searches/${id}`, { method: 'DELETE' });
        if (res.ok) {
          loadSavedSearchesList();
        } else {
          alert("삭제 실패");
        }
      } catch (err) {
        alert("삭제 오류: " + err.message);
      }
    }

    async function handleSaveAlert(e) {
      e.preventDefault();
      const searchId = document.getElementById('alert-form-id').value;

      const payload = {
        name: document.getElementById('alert-form-name').value,
        description: document.getElementById('alert-form-desc').value,
        app: document.getElementById('alert-form-app').value,
        owner: document.getElementById('alert-form-owner').value,
        sharing: document.getElementById('alert-form-sharing').value,
        enabled: document.getElementById('alert-form-enabled').checked,

        ppl_query: document.getElementById('alert-form-query').value,
        dispatch_earliest_time: document.getElementById('alert-form-earliest').value,
        dispatch_latest_time: document.getElementById('alert-form-latest').value,
        dispatch_sample_ratio: parseInt(document.getElementById('alert-form-sampleratio').value) || 1,

        schedule_type: document.getElementById('alert-form-sched-type').value,
        interval_seconds: parseInt(document.getElementById('alert-form-interval').value) || 60,
        cron_expression: document.getElementById('alert-form-cron').value,
        schedule_priority: document.getElementById('alert-form-priority').value,

        alert_type: document.getElementById('alert-form-type').value,
        condition_operator: document.getElementById('alert-form-op').value,
        condition_threshold: parseFloat(document.getElementById('alert-form-threshold').value) || 0.0,

        trigger_mode: document.getElementById('alert-form-trigger-mode').value,
        severity: document.getElementById('alert-form-severity').value,
        alert_expires: document.getElementById('alert-form-expires').value,
        alert_suppress: document.getElementById('alert-form-suppress').checked,
        alert_suppress_period: document.getElementById('alert-form-suppress-period').value,
        alert_suppress_fields: document.getElementById('alert-form-suppress-fields').value,

        action_webhook_enabled: document.getElementById('alert-action-webhook-enabled').checked,
        webhook_url: document.getElementById('alert-form-webhook').value || null,
        action_email_enabled: document.getElementById('alert-action-email-enabled').checked,
        action_email_to: document.getElementById('alert-action-email-to').value || null,
        action_email_subject: document.getElementById('alert-action-email-subject').value || null,
        action_index_enabled: document.getElementById('alert-action-index-enabled').checked,
        action_index_name: document.getElementById('alert-action-index-name').value || "logccino-alerts",
        action_script_enabled: document.getElementById('alert-action-script-enabled').checked,
        action_script_command: document.getElementById('alert-action-script-cmd').value || null
      };

      try {
        let res;
        if (searchId) {
          res = await fetch(`/api/v1/saved-searches/${searchId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
        } else {
          res = await fetch('/api/v1/saved-searches', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });
        }

        if (res.ok) {
          alert(searchId ? "알람 규칙이 성공적으로 수정되었습니다!" : "새로운 Splunk Saved Search & 알람 규칙이 등록되었습니다!");
          switchAlertModalTab('list');
          loadSavedSearchesList();
        } else {
          const err = await res.json();
          alert("저장 실패: " + (err.detail || JSON.stringify(err)));
        }
      } catch (err) {
        alert("오류 발생: " + err.message);
      }
    }

    async function testWebhookAction() {
      const url = document.getElementById('alert-form-webhook').value;
      if (!url) {
        alert("먼저 Webhook URL을 입력해주세요.");
        return;
      }
      try {
        const res = await fetch('/api/v1/saved-searches/test-webhook', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ webhook_url: url, message: "Logccino Splunk Alert Webhook Test" })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          alert("✅ 웹훅 전송 성공! (HTTP " + data.status_code + ")");
        } else {
          alert("❌ 웹훅 전송 실패: " + (data.detail || data.status_code));
        }
      } catch (err) {
        alert("❌ 웹훅 연결 실패: " + err.message);
      }
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
