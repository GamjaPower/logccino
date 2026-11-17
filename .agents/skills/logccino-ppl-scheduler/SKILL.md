---
name: logccino-ppl-scheduler
description: >-
  Splunk 스타일 PPL(Piped Processing Language) 기반 스케줄러 및 실시간 알람 규칙(Splunk savedsearches.conf 완전 호환)을
  MCP 서버를 통해 등록, 조회, 즉시 실행(Run Now), 수정, 삭제 및 모니터링하는 전문 운영 가이드입니다.
---

# Logccino Splunk Saved Search & Alerting MCP Skill

이 스킬은 AI 에이전트(Claude, Antigravity, Cursor 등)가 Logccino의 **Splunk Saved Search & Alerting 엔진(savedsearches.conf 호환)**을 MCP 도구(Tools)를 통해 직접 등록하고 관리할 수 있도록 지원하는 가이드입니다.

---

## 1. 🛠️ 스케줄러 관리 MCP 도구 목록

Logccino MCP 서버는 Splunk Enterprise의 `savedsearches.conf`와 100% 동일한 매개변수를 지원합니다:

도구 이름 (Tool Name) | 주요 설명 | 핵심 매개변수
:---|:---|:---
`list_saved_searches` | 현재 등록된 모든 Splunk Saved Search 목록 및 최근 실행 상태(`OK`, `TRIGGERED`, `SUPPRESSED`, `ERROR`, `DISABLED`) 조회 | 없음
`create_saved_search` | Splunk savedsearches.conf 사양의 새로운 조건부 알람 및 스케줄러 등록 | `name`, `ppl_query`, `app`, `dispatch_earliest_time`, `dispatch_latest_time`, `schedule_type`, `cron_expression`, `interval_seconds`, `alert_type`, `condition_operator`, `condition_threshold`, `severity`, `alert_suppress`, `alert_suppress_period`, `alert_suppress_fields`, `webhook_url`, `action_email_to`, `action_index_name`
`run_saved_search` | 특정 알람을 대기 시간 없이 즉시 실행(Splunk 'Run Now')하여 매칭 건수, 트리거 및 억제(Suppressed) 여부 확인 | `search_id`
`update_saved_search` | 기존 알람의 디스패치 시간 범위, 주기, 임계치, 억제(Throttle), 이메일/웹훅 수신처 수정 및 ON/OFF 토글 | `search_id`, `enabled`, `ppl_query`, `interval_seconds`, `condition_threshold`, `severity`, `dispatch_earliest_time`, `alert_suppress`, `alert_suppress_period`, `action_email_to`, `webhook_url`
`delete_saved_search` | 불필요한 알람 규칙 영구 삭제 | `search_id`
`get_alert_history` | 스케줄러에 의해 최근 트리거된 알람 발송 타임라인 및 결과 로그 조회 | `limit` (기본 20), `triggered_only` (기본 True)

---

## 2. 📋 Splunk Saved Searches & Alert Engine 주요 옵션 체계

Logccino의 Saved Search 엔진은 다음 6가지 핵심 영역의 옵션을 완벽히 수용합니다:

### 1) 일반 및 소유권 (General & Ownership)
- `name`: 알람 명칭 (e.g. `[SEC-01] SSH 무차별 대입 급증`)
- `description`: 알람 목적 및 대응 절차(SOP)
- `app`: Splunk App Context (`search`, `enterprise_security`, `autonomous_sre`)
- `owner`: 소유자 계정 (e.g. `admin`, `logccino`)
- `sharing`: 공유 범위 (`app`, `global`, `private`)
- `enabled`: 활성화 여부 (`True` / `False`)

### 2) 검색 쿼리 및 디스패치 시간 범위 (Query & Dispatch Window)
- `ppl_query`: 실행할 PPL / Join 쿼리 파이프라인
- `dispatch_earliest_time`: 검색 시작 시간 범위 (`-15m`, `-30m`, `-1h`, `-4h`, `-24h`, `-7d`, `@d`, `0`)
- `dispatch_latest_time`: 검색 종료 시간 (기본 `now`)
- `dispatch_sample_ratio`: 샘플링 비율 (1 = 100% 전수 검사, 10 = 10% 샘플링)

### 3) 스케줄링 (Schedule Settings)
- `schedule_type`: 스케줄 방식 (`interval`, `cron`, `realtime`)
- `interval_seconds`: 실행 주기 초 (e.g. 60, 120, 300)
- `cron_expression`: 표준 크론 표현식 (e.g. `*/5 * * * *`, `0 * * * *`)
- `schedule_priority`: 스케줄 우선순위 (`default`, `higher`, `highest`)
- `schedule_window`: 실행 윈도우 지연 허용치 (`auto`, `0`)

### 4) 트리거 조건 (Alert Trigger Condition)
- `alert_type`:
  - `number_of_results`: 결과 레코드 건수
  - `number_of_events`: 원본 이벤트 수
  - `number_of_hosts`: 고유 호스트(`host`) 수
  - `number_of_sources`: 고유 소스/프로그램(`source`, `program`, `service`) 수
  - `custom`: 커스텀 조건식
  - `always`: 스케줄 시 무조건 트리거
- `condition_operator`: 비교 연산자 (`gt`, `gte`, `lt`, `lte`, `eq`, `neq`, `drops_by`, `rises_by`)
- `condition_threshold`: 트리거 기준 임계치 (숫자, e.g. 0.0, 5.0, 100)

### 5) 빈도 및 Throttling 억제 (Frequency & Suppression)
- `trigger_mode`: 트리거 모드 (`once`: 조건 충족 시 1회 발송, `for_each_result`: 결과 행마다 개별 발송)
- `severity`: 알람 심각도 (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`)
- `alert_track`: Triggered Alerts에 추적/보관 여부
- `alert_expires`: 알람 보관 만료 기간 (`24h`, `7d`, `30d`)
- `alert_suppress`: 중복 알람 억제(Throttling) 활성화 여부
- `alert_suppress_period`: 억제 기간 (e.g. `5m`, `15m`, `1h`, `1d`)
- `alert_suppress_fields`: 억제 기준 필드 (쉼표 구분: `host`, `src_ip`, `service`)

### 6) 알람 동작 (Alert Actions)
- **Webhook Action**: `action_webhook_enabled`, `webhook_url` (Slack/Teams/Discord/사내 관제)
- **Email Action**: `action_email_enabled`, `action_email_to`, `action_email_subject`, `action_email_priority`
- **Indexing Action**: `action_index_enabled`, `action_index_name` (`logccino-alerts`, `notable`)
- **Script Action**: `action_script_enabled`, `action_script_command` (`/opt/scripts/remediate.sh`)

---

## 3. 🚀 MCP를 통한 스케줄러 관리 단계별 워크플로우

### 단계 1: 현재 알람 상태 점검
사용자가 "현재 등록된 알람 현황 보여줘"라고 요청할 때:
1. `list_saved_searches()`를 호출합니다.
2. 반환된 규칙의 `name`, `app`, `interval_seconds`, `last_status`, `last_result_count`, `last_suppressed`를 표 형태로 요약합니다.

### 단계 2: 신규 Splunk PPL 알람 등록 (Throttling 및 Dispatch Window 포함)
사용자가 "SSH 실패가 15분 동안 3개 이상의 호스트에서 발생하면 CRITICAL 알람을 보내고 10분간 호스트별로 중복 알람을 억제해줘"라고 요청할 때:
1. `create_saved_search`를 다음과 같이 호출합니다:
   - `name`: "[SEC] 분산 SSH 무차별 대입 공격 감시"
   - `ppl_query`: "source = logccino-logs-* | where security.action = 'ssh_login_failure' | head 50"
   - `app`: "enterprise_security"
   - `dispatch_earliest_time`: "-15m"
   - `interval_seconds`: 60
   - `alert_type`: "number_of_hosts"
   - `condition_operator`: "gte"
   - `condition_threshold`: 3.0
   - `severity`: "CRITICAL"
   - `alert_suppress`: True
   - `alert_suppress_period`: "10m"
   - `alert_suppress_fields`: "host"
   - `action_email_to`: "soc-lead@company.com"
2. 생성된 `id`와 설정 내용을 사용자에게 확인 보고합니다.

### 단계 3: 즉시 검증 (Run Now)
생성된 알람이 정상적으로 PPL을 실행하고 매칭하는지 즉시 확인할 때:
1. `run_saved_search(search_id='alert-xxxx')`를 호출합니다.
2. 실행 소요 시간(`execution_took_ms`), 매칭 건수(`result_count`), 트리거 여부(`triggered`), 억제 여부(`suppressed`)를 확인합니다.

---

## 4. 🔔 Webhook 및 알람 발송 JSON 페이로드 규격
알람이 트리거되면 Slack / Teams / Discord와 호환되는 풍부한 JSON 페이로드가 웹훅 수신처로 전송됩니다:
```

---

## 5. 🤖 연계 스킬: Logccino Autonomous AI SOC Detection Scenarios
보안관제(SIEM) 도메인의 공격 벡터(무차별 대입, 권한 상승, 정찰, 랜섬웨어 카나리, DNS 유출 등) 및 MITRE ATT&CK 엔터프라이즈 매트릭스 연계 관제 시나리오 관리는 자매 스킬인 **`logccino-soc-scenarios`**를 함께 활용하십시오.
사람이 직접 시나리오를 타이핑하지 않고 클로드가 자율적으로 PPL을 생성하고 튜닝합니다.json
{
  "text": "🚨 [Logccino Splunk Alert] [SEC-01] SSH 무차별 대입 및 로그인 실패 급증 (심각도: CRITICAL)",
  "saved_search_id": "alert-ssh-bruteforce",
  "alert_name": "[SEC-01] SSH 무차별 대입(Brute-Force) 및 로그인 실패 급증",
  "app": "enterprise_security",
  "severity": "CRITICAL",
  "matched_events": 5,
  "alert_type": "number_of_results",
  "condition": "number_of_results gt 0.0",
  "ppl_query": "source = logccino-logs-* | where security.action = 'ssh_login_failure' ...",
  "dispatch_window": "-15m ~ now",
  "timestamp": "2026-11-17T19:30:00Z",
  "sample_logs": [...]
}
```

---

## 5. 🤖 연계 스킬: Logccino Autonomous AI SOC Detection Scenarios
보안관제(SIEM) 도메인의 공격 벡터(무차별 대입, 권한 상승, 정찰, 랜섬웨어 카나리, DNS 유출 등) 및 MITRE ATT&CK 엔터프라이즈 매트릭스 연계 관제 시나리오 관리는 자매 스킬인 **`logccino-soc-scenarios`**를 함께 활용하십시오.
사람이 직접 시나리오를 타이핑하지 않고 클로드가 자율적으로 PPL을 생성하고 튜닝합니다.
