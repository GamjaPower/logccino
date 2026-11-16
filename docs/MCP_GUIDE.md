# Logccino MCP 연동 가이드 (Model Context Protocol Guide)

Logccino는 표준 **Model Context Protocol (MCP)**를 지원합니다.
Claude Code / Desktop, Google Antigravity, Cursor IDE 등의 AI 에이전트 설정에 Logccino를 등록하면, 에이전트가 사용자의 자연어 질문에 맞춰 OpenSearch 로그를 직접 검색하고 분석할 수 있습니다.

---

## 🛠️ 제공되는 MCP 도구 목록 (Tools)

| Tool 이름 | 설명 | 주요 매개변수 |
| :--- | :--- | :--- |
| `search_natural` | 자연어 질문으로 OpenSearch 대규모 분산 로그 직접 검색 (PPL 우선, DSL 자동 폴백) | `prompt`, `size` |
| `get_realtime_stream_summary` | 초당 대규모로 유입되는 실시간 로그 스트림의 최근 N분간 에러율 및 시계열 트렌드 요약 | `minutes`, `service` |
| `aggregate_bigdata_metrics` | 수백만~수억 건의 빅데이터 로그를 분산 사전 집계하여 Claude 컨텍스트 친화적 통계 요약 반환 | `time_window`, `group_by`, `filter_query` |
| `search_logs` | 필터 및 키워드 기반 로그 검색 | `query`, `service`, `level`, `start_time`, `end_time`, `size` |
| `search_ppl` | OpenSearch PPL 파이프라인 쿼리 실행 | `ppl_query` |
| `diagnose_service_errors` | 최근 에러 로그 및 스택트레이스 수집 (RCA용) | `service`, `time_window` (예: '1h', '24h'), `limit` |
| `get_service_metrics` | 서비스별 로그 볼륨 및 에러율(%) 통계 | `time_window` |
| `trace_transaction` | 특정 `trace_id`의 마이크로서비스 전 구간 타임라인 추적 | `trace_id` |
| `get_cluster_health` | OpenSearch 클러스터 및 Logccino 인덱스 상태 점검 | 없음 |

---

## 🔌 AI 에이전트별 연동 설정

### 1. Claude Desktop 원격 연동 (AWS Marketplace / 사내 k8s 배포 환경) 🌟 [권장]
사내 Kubernetes 또는 AWS에 Logccino가 배포된 경우, 로컬 Claude Desktop 설정 파일(`~/.config/Claude/claude_desktop_config.json`)에 원격 SSE URL만 지정하면 됩니다:

```json
{
  "mcpServers": {
    "logccino": {
      "url": "http://<YOUR_LOGCCINO_HOST>:8000/sse"
    }
  }
}
```

### 2. Claude Desktop 로컬 Stdio 연동 (로컬 단일 PC 개발 환경)
`~/.config/Claude/claude_desktop_config.json` (Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`) 파일에 다음을 추가합니다:

```json
{
  "mcpServers": {
    "logccino": {
      "command": "python",
      "args": ["-m", "core.mcp.server"],
      "cwd": "/absolute/path/to/logccino",
      "env": {
        "PYTHONPATH": "/absolute/path/to/logccino"
      }
    }
  }
}
```

### 3. Cursor IDE 연동
Cursor `Settings > Features > MCP Servers`에서 새로운 서버를 추가합니다:
- **Name**: `logccino`
- **Type**: `command`
- **Command**: `python -m core.mcp.server`

---

## 💬 AI 에이전트 활용 대화 예시

설정이 완료되면 사용자는 에이전트에게 일상적인 언어로 질문할 수 있으며, 에이전트가 Logccino 도구를 호출하여 답변합니다:

1. **장애 진단 질문**:
   > **사용자**: "오늘 오전부터 auth-service에서 발생한 로그인 오류 원인 좀 찾아줘."  
   > **에이전트**: `diagnose_service_errors(service="auth-service", time_window="6h")` 호출 ➡️ 에러 스택트레이스 및 원인 보고

2. **시스템 헬스 및 이상 탐지**:
   > **사용자**: "현재 우리 서비스 중에 에러율이 비정상적으로 높은 곳이 있어?"  
   > **에이전트**: `get_service_metrics(time_window="1h")` 호출 ➡️ 서비스별 에러율 비교 및 이상 서비스 보고

3. **분산 트레이스 추적**:
   > **사용자**: "트레이스 ID `tr-90218`에서 어느 서비스에서 타임아웃이 났는지 시간 순서대로 보여줘."  
   > **에이전트**: `trace_transaction(trace_id="tr-90218")` 호출 ➡️ 마이크로서비스 간 호출 타임라인 시각화
