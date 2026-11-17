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
