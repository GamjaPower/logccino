# Changelog

이 문서는 **Logccino** 프로젝트의 주요 릴리즈 변경 이력을 기록합니다.

## [v1.0.0] - 2026-11-27

### 주요 기능 (Features)

- **엔터프라이즈 SIEM AI Agent 플랫폼 초기 정식 릴리즈**
  - Splunk Enterprise Docker(`splunk/splunk`) 연동 및 `TCP 5090` 웹 콘솔·REST API 서버(`cmd/server`)
  - Go 1.26 기반 단일 정적 바이너리 빌드 및 CGO-free SQLite(`modernc.org/sqlite`) 저장소 지원
- **Detection as Code (DaC) 엔진 (`cmd/dacctl`, `internal/compiler`, `internal/validator`, `internal/deployer`)**
  - YAML 탐지 규칙을 Splunk Saved Search 배포 JSON으로 결정론적 컴파일
  - 문법·계약(contract)·픽스처(fixture) 3중 검증 파이프라인 및 Splunk 자동 배포·드리프트 탐지
  - 전용 규칙 Git 저장소(`DAC_GIT_*`) 연동, 초기 구조 자동 시드 및 주기적 동기화
- **멀티 에이전트 SOC 트리아지 파이프라인 (`internal/alerts`, `internal/triage`)**
  - `soc_alerts` 인덱스 실시간 폴러(`Poller`) 및 동일 티켓 중복 처리 방지(`inFlight` 보호)
  - `Collector`: SPL Guard·`escapeSPLValue` 인젝션 방어·허용 인덱스 제한 및 Splunk 룩업(`asset_inventory.csv`, `domain_policy.csv`, `ti_ioc.csv`) 연동
  - `Judge` + 대항형 `Rebuttal Agent` + 환각 검증기(`Verifier`) 기반 다단계 판정 및 근거 저장(`evidence`)
- **정보유출(DLP) 탐지 및 테스트 데이터 파이프라인 (`internal/dlp`, `cmd/loggen`, `cmd/loaddata`)**
  - 일일 유입 데이터 기반 비인가 외부 클라우드·웹 업로드 및 이상 대량 전송 탐지 시나리오
  - 매일 `06:00 KST` 자동 테스트 데이터 생성 스케줄러 및 수동 실행 API
- **애널리스트 지원·평가·기업용 웹 UI (`internal/assist`, `internal/eval`, `internal/coverage`, `internal/web`)**
  - `net/http` + `html/template` + 내장 htmx 기반 SOC 대시보드(최근 인시던트 한 줄 레이아웃, 규칙/커버리지/티켓 관리)
  - Analyst Assist(난독화 해제·태깅), ATT&CK/내부자/로그 커버리지 매트릭스 및 Eval Harness(`cmd/eval`)

### 보안 및 컴플라이언스 (Security & Hardening)

- **OpenAI API 전용 연동 및 PII 마스킹/복원 (`internal/llm/redact`)**
  - `LLM_REDACT_FIELDS` 기반 민감 필드 토큰 치환(`RedactText`), prefix-safe 복원(`Restore`), SHA-256 `InputHash` 감사 추적
  - `llm_calls` 감사 로그 기록 및 `GET /api/llm/calls` API 제공
- **프롬프트 버전 관리 및 검증 정합성 강화 (`internal/prompts`, `prompts/*.md`)**
  - `prompts/` 디렉터리에서 버전별 Markdown 프롬프트를 중앙 로드하고 `rebuttal_v1.md` 스키마 정합성 확보
- **동시성·메트릭·HTTP 서버 하드닝 (`internal/metrics`, `cmd/server`)**
  - 분석가 일치율(`concordance_rate`) 계산 SQL 버그 수정 및 LLM 텔레메트리(`TotalLLMCalls`, `TotalTokensUsed`, `AvgLatencyMs`) 추가
  - `Server` 공유 상태 `sync.RWMutex` 보호 및 `http.Server` 타임아웃(`ReadHeaderTimeout`, `IdleTimeout`, `MaxHeaderBytes`) 적용
