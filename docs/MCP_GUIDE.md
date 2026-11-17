# 🏛️ Logccino Enterprise MCP 연동 가이드 (Enterprise Model Context Protocol Guide)

Logccino Enterprise는 업계 표준 **Model Context Protocol (MCP)**을 완전하게 구현합니다.
Anthropic Claude (Claude Desktop, Claude Code), Google Antigravity, Cursor IDE 등의 AI 에이전트와 원격 연결되어, 에이전트가 로컬 PC의 하드웨어 및 컨텍스트 윈도우 한계를 초과하는 **페타바이트급 분산 빅데이터 로그 및 초고속 실시간 스트림**을 즉각 조회·분석할 수 있도록 지원합니다.

---

## 🛠️ 엔터프라이즈 MCP 도구 목록 (Enterprise Tools)

| Tool 이름 | 엔터프라이즈 설명 | 주요 매개변수 |
| :--- | :--- | :--- |
| `search_natural` | 자연어 질문으로 OpenSearch 분산 클러스터 직접 검색 (PPL 엔진 우선, Query DSL 자동 폴백) | `prompt: str, size: int = 30` |
| `get_realtime_stream_summary` | 초당 대규모 스트림에서 최근 N분간 Throughput(eps), 에러 스파이크, 시계열 트렌드 실시간 요약 | `minutes: int = 15, service: Optional[str] = None` |
| `aggregate_bigdata_metrics` | 수백만~수억 건의 빅데이터 로그를 분산 사전 집계하여 상태(정상/주의/경고)가 포함된 압축 매트릭스 반환 | `time_window: str = "24h", group_by: str = "service", filter_query: Optional[str] = None` |
| `diagnose_service_errors` | 서비스별 최근 ERROR/FATAL 로그, 실패 빈도 및 예외 스택트레이스 수집 (RCA 지원) | `service: Optional[str] = None, time_window: str = "1h", limit: int = 10` |
| `get_service_metrics` | 전사 마이크로서비스 24시간 가용성, 총 로그 볼륨, 에러율(%), 상태 판정 집계 | `time_window: str = "24h"` |
| `trace_transaction` | 특정 `trace_id`의 마이크로서비스 전 구간 호출 타임라인 및 지연/장애 전파 추적 | `trace_id: str` |
| `search_ppl` | 엔터프라이즈 OpenSearch PPL 파이프라인 쿼리 직접 실행 | `ppl_query: str` |
| `search_logs` | 필터(서비스, 레벨, 키워드, 타임스탬프) 기반 정밀 로그 탐색 | `query: Optional[str], service: Optional[str], level: Optional[str], start_time: Optional[str], end_time: Optional[str], size: int = 30` |
| `get_cluster_health` | OpenSearch 클러스터 상태(Green/Yellow/Red), 노드 수, 샤드 및 총 인덱싱 볼륨 텔레메트리 | 없음 |
| `analyze_security_incidents` | SSH 무차별 대입, 비인가 Sudo 권한 상승, UFW 방화벽 차단 등 보안 침해사고 분석 | `time_window: str = "24h", limit: int = 50` |
| `get_syslog_collector_status` | Rust 고성능 Syslog 수집기 데몬 실행 상태, Throughput(EPS), 수집 카운터 조회 | 없음 |
| `list_saved_searches` | Splunk 스타일 PPL Saved Search 및 실시간 스케줄러 알람 규칙 목록 조회 | 없음 |
| `create_saved_search` | 새로운 PPL 조건부 알람 등록 (주기, 임계치, 심각도, Webhook URL) | `name, ppl_query, interval_seconds, condition_threshold, ...` |
| `run_saved_search` | 특정 Saved Search / Alert 즉시 실행(Run Now) 및 매칭 결과 검증 | `search_id: str` |
| `update_saved_search` | PPL 알람 스케줄러의 활성화 여부(ON/OFF), 실행 주기, 쿼리 수정 | `search_id: str, enabled, ppl_query, interval_seconds, ...` |
| `delete_saved_search` | Saved Search 알람 규칙 삭제 | `search_id: str` |
| `get_alert_history` | 스케줄러에 의해 트리거된 최근 알람 발송 타임라인 조회 | `limit: int = 20, triggered_only: bool = True` |
| `list_users` | Splunk 스타일 사용자 계정, 소속 롤(Role), 기본 인덱스('main') 및 허용 인덱스 목록 조회 | 없음 |
| `create_user` | 신규 사용자 생성 및 롤(admin, power, security_analyst, user) 할당 | `username, full_name, email, roles, default_index` |
| `list_roles` | Splunk 표준 롤 목록 및 세부 Capability 권한 매핑 조회 | 없음 |

---

## 🧭 엔터프라이즈 MCP 프롬프트 프리셋 (Prompt Presets)

Claude Desktop의 프롬프트 메뉴(`/` 또는 📎)에서 원클릭으로 호출할 수 있는 표준 SRE 프롬프트입니다:

1. **`deep-dive-analysis`** (`service_name`, `issue_description`):
   - 대상 서비스의 증거 수집, 장애 전파 타임라인 분석, P0~P3 등급 판정 및 긴급/근본 조치를 포함하는 5단계 SRE 종합 보고서 자동 작성.
2. **`bigdata-overview`** (`time_window`):
   - 전사 마이크로서비스 대용량 로그의 거시적 안정성 감사 및 SLO 에러 버짓 소진 현황 브리핑.
3. **`diagnose-incident`** (`service_name`):
   - 특정 서비스의 긴급 장애(P0/P1) 발생 시 즉각적인 원인 규명 및 서킷 브레이커 트립 등 완화책 도출.
4. **`chat-follow-up`** (`previous_context`, `follow_up_question`):
   - 이전 대화 컨텍스트를 유지하며 특정 설정값, 영향받은 사용자 ID 등 세부 사항을 추적하는 멀티턴 대화.
5. **`realtime-stream-anomaly`** (`minutes`, `service`):
   - 실시간 고속 스트림의 초당 처리량(EPS) 급변 및 에러율 스파이크 감지.
6. **`security-soc-analyst`** (`time_window`):
   - SOC 침해사고 분석 (공격자 IP, SSH 무차별 대입, Sudo 권한 상승, 방화벽 차단 타임라인 종합 보고).
7. **`alert-triage-analyst`** (`search_id`):
   - PPL 스케줄러에 의해 트리거된 Splunk 스타일 실시간 알람 긴급 원인 규명 및 조치 가이드 도출.

---

## 🔌 AI 에이전트별 엔터프라이즈 연동 설정

### 1. Claude Desktop 원격 연동 (AWS / 사내 Kubernetes 클러스터) 🌟 [권장]
사내 Kubernetes 또는 AWS 환경에 배포된 Logccino 엔드포인트를 `~/.config/Claude/claude_desktop_config.json`에 등록합니다:

```json
{
  "mcpServers": {
    "logccino": {
      "url": "https://logccino.company.internal/sse"
    }
  }
}
```

### 2. Google Antigravity CLI (`agy`) 및 Cursor IDE 연동
개발자 워크스테이션 환경에서 로컬 파이프라인 또는 원격 SSE 엔드포인트로 연동합니다:

```json
{
  "mcpServers": {
    "logccino": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

---

## 🔒 엔터프라이즈 보안 및 규제 준수 (Security & Compliance)
- **전송 계층 암호화**: TLS 1.3 / HTTPS 전송 및 서버-전송 이벤트(SSE) 통신 보호.
- **기밀 정보 마스킹 (Data Redaction)**: 사용자 토큰, 비밀번호, 결제 카드 번호(PAN) 및 개인정보(PII)는 AI 프롬프트 주입 전 자동 마스킹 처리.
- **감사 추적성 (Audit Trail)**: 모든 자연어 검색 및 도구 호출 기록은 기업 보안 감사(SOC 2 Type II, ISO 27001) 요건에 부합하도록 구조화된 로그로 기록됩니다.
