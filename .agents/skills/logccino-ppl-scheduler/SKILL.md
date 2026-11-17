---
name: logccino-ppl-scheduler
description: >-
  Splunk 스타일 PPL(Piped Processing Language) 기반 스케줄러 및 실시간 알람 규칙을 MCP 서버를 통해
  등록, 조회, 즉시 실행(Run Now), 수정, 삭제 및 모니터링하는 전문 운영 가이드입니다.
---

# Logccino PPL Scheduler & Alerting MCP Skill

이 스킬은 AI 에이전트(Claude, Antigravity, Cursor 등)가 Logccino의 **Splunk Saved Search & Alerting 엔진**을 MCP 도구(Tools)를 통해 직접 등록하고 관리할 수 있도록 지원하는 절차 가이드입니다.

---

## 1. 🛠️ 스케줄러 관리 MCP 도구 목록

Logccino MCP 서버는 다음 도구들을 제공합니다:

도구 이름 (Tool Name) | 주요 설명 | 핵심 매개변수
:---|:---|:---
`list_saved_searches` | 현재 등록된 모든 PPL 알람 스케줄러 목록 및 최근 실행 상태(`OK`, `TRIGGERED`, `ERROR`, `DISABLED`) 조회 | 없음
`create_saved_search` | 새로운 Splunk 스타일 PPL 조건부 알람 생성 및 스케줄러 자동 등록 | `name`, `ppl_query`, `interval_seconds`, `condition_operator`, `condition_threshold`, `severity`, `webhook_url`
`run_saved_search` | 특정 알람을 대기 시간 없이 즉시 실행(Splunk 'Run Now')하여 매칭 건수 및 샘플 로그 확인 | `search_id`
`update_saved_search` | 기존 알람의 실행 주기, PPL 쿼리, 임계치, 웹훅 URL 수정 및 ON/OFF 토글 | `search_id`, `enabled`, `ppl_query`, `interval_seconds`, `condition_threshold`, `webhook_url`
`delete_saved_search` | 불필요한 알람 규칙 영구 삭제 | `search_id`
`get_alert_history` | 스케줄러에 의해 최근 트리거된 알람 발송 타임라인 및 결과 로그 조회 | `limit` (기본 20), `triggered_only` (기본 True)

---

## 2. 📋 PPL 쿼리 작성 가이드 및 베스트 프랙티스

PPL(Piped Processing Language)은 OpenSearch 및 Splunk 사용자가 직관적인 파이프라인(`|`) 형태로 작성할 수 있습니다.

### 주요 권장 템플릿:
1. **보안: SSH 무차별 대입 및 로그인 실패 감시**
   ```sql
   source = logccino-logs-* | where security.action = 'ssh_login_failure' or security.action = 'ssh_login_failed' | head 50
   ```
2. **보안: 비인가 Sudo 권한 상승 감시**
   ```sql
   source = logccino-logs-* | where program = 'sudo' or security.action = 'sudo_escalation' | head 50
   ```
3. **SRE: 마이크로서비스 5xx 심각 장애 감시**
   ```sql
   source = logccino-logs-* | where level = 'ERROR' | head 50
   ```
4. **보안: 경계 방화벽 UFW 포트 스캔 차단 감시**
   ```sql
   source = logccino-logs-* | where security.action = 'firewall_drop' | head 50
   ```

> [!NOTE]
> PPL 작성 시 괄호 `(a or b)` 중첩보다는 `where condition1 or condition2` 형태의 선형 표현식이 가장 안정적으로 파싱됩니다.

---

## 3. 🚀 MCP를 통한 스케줄러 관리 단계별 워크플로우

### 단계 1: 현재 알람 상태 점검
사용자가 "현재 등록된 알람 현황 보여줘"라고 요청할 때:
1. `list_saved_searches()`를 호출합니다.
2. 반환된 규칙의 `name`, `interval_seconds`, `last_status`, `last_result_count`를 표 형태로 요약합니다.

### 단계 2: 신규 PPL 알람 등록
사용자가 "결제 서비스에서 타임아웃 에러가 1분 동안 3건 이상 나오면 알람을 보내줘"라고 요청할 때:
1. `create_saved_search`를 다음과 같이 호출합니다:
   - `name`: "[SRE] 결제 서비스 타임아웃 급증 감시"
   - `ppl_query`: "source = logccino-logs-* | where service = 'payment-service' and match(message, 'timeout') | head 50"
   - `interval_seconds`: 60
   - `condition_operator`: "gte"
   - `condition_threshold`: 3.0
   - `severity`: "CRITICAL"
   - `webhook_url`: (사용자 지정 웹훅 또는 None)
2. 생성된 `id`와 설정 내용을 사용자에게 확인 보고합니다.

### 단계 3: 즉시 검증 (Run Now)
생성된 알람이 정상적으로 PPL을 실행하고 매칭하는지 즉시 확인할 때:
1. `run_saved_search(search_id='alert-xxxx')`를 호출합니다.
2. 실행 소요 시간(`execution_took_ms`), 매칭 건수(`result_count`), 트리거 여부(`triggered`)를 확인합니다.

### 단계 4: 알람 일시 중지 및 설정 변경
1. 비활성화 시: `update_saved_search(search_id='alert-xxxx', enabled=False)`
2. 주기 변경 시: `update_saved_search(search_id='alert-xxxx', interval_seconds=300)`

---

## 4. 🔔 Webhook 연동 규격
알람이 트리거되면 Slack / Teams / Discord와 호환되는 JSON 페이로드가 웹훅 수신처로 전송됩니다:
```json
{
  "text": "🚨 [Logccino Splunk Alert] [SEC-01] SSH 무차별 대입 및 로그인 실패 급증 (심각도: CRITICAL)",
  "saved_search_id": "alert-ssh-bruteforce",
  "matched_events": 5,
  "condition": "count gt 0.0",
  "ppl_query": "source = logccino-logs-* | where security.action = 'ssh_login_failure' ...",
  "timestamp": "2026-11-17T19:30:00Z",
  "sample_logs": [...]
}
```
