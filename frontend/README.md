# 🎛️ Logccino Management UI (Admin Dashboard)

AI 에이전트(Claude, Antigravity, Cursor 등)가 Logccino를 통해 로그를 효과적으로 탐색할 수 있도록, **OpenSearch 클러스터 헬스, MCP 서버 상태, 수집된 로그 및 마이크로서비스 상태를 모니터링하고 제어하는 관리자 전용 웹 대시보드**입니다.

---

## 🎯 주요 관리 기능

### 1. 📊 시스템 개요 (System Overview)
- OpenSearch 클러스터 상태 (`Green` / `Yellow` / `Red`), 연결 노드 수
- 총 인덱싱된 도큐먼트 수 및 실시간 로그 수집 볼륨
- 등록된 활성 마이크로서비스 개수

### 2. 🔌 AI 에이전트 & MCP 관리 센터 (Agent & MCP Hub)
- **MCP 서버 상태**: Stdio 및 SSE 전송 모드 상태 확인
- **제공 도구 (MCP Tools)**:
  - `search_logs`: 필터 기반 로그 검색
  - `search_ppl`: OpenSearch PPL 쿼리 실행
  - `diagnose_service_errors`: 최근 에러 및 스택트레이스 수집 (RCA용)
  - `get_service_metrics`: 서비스별 에러율 및 볼륨 통계
  - `trace_transaction`: 분산 트레이스 ID 타임라인 추적
  - `get_cluster_status`: 클러스터 헬스 체크
- **원클릭 설정 생성기**:
  - Claude Desktop (`claude_desktop_config.json`) 설정 복사
  - Google Antigravity CLI (`agy`) MCP 설정 복사
  - Cursor IDE 설정 복사

### 3. 📋 실시간 로그 모니터링 (Live Log Stream)
- 최근 수집된 로그 30~100건 프리뷰
- 서비스, 레벨(ERROR/WARN/INFO), 타임스탬프, 메시지 테이블
- JSON 원본 상세 보기 모달

### 4. 🩺 서비스 헬스 현황 (Microservice Health)
- 마이크로서비스별 24시간 로그 볼륨 및 에러 발생률(%)
- 주의가 필요한 비정상 서비스 하이라이트

---

## 🛠️ 권장 기술 스택
- **Framework**: Next.js 14+ (App Router) 또는 Vite + React 18
- **UI & Styling**: TailwindCSS + Shadcn/ui (깔끔한 엔터프라이즈 다크 모드)
- **Icons**: Lucide React
- **통신**: TanStack Query (React Query)
- **연동 엔드포인트**:
  - `GET /api/v1/admin/overview`: 대시보드 통계
  - `GET /api/v1/admin/mcp/status`: MCP 도구 및 설정 JSON
  - `GET /api/v1/admin/logs/preview`: 실시간 로그 프리뷰
  - `GET /api/v1/admin/services`: 서비스별 통계
