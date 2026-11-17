---
name: logccino-soc-scenarios
description: >-
  클로드(Claude)가 MITRE ATT&CK 엔터프라이즈 매트릭스를 기반으로 Logccino 자율형 AI SIEM의 보안 관제 시나리오를
  전문적으로 설계, PPL 쿼리 합성, 임계치 산정, 중복 알람 억제(Throttling) 및 등록·튜닝·검증을 자율 수행하는 전문 운영 가이드입니다.
---

# Logccino Autonomous AI SOC Detection Scenarios Skill

이 스킬은 AI 에이전트(Claude)가 엔터프라이즈 보안관제센터(SOC)의 수석 탐지 엔지니어(Detection Engineer) 역할을 수행하여,
**시나리오 제작부터 실시간 탐지, LLM 기반 자율 분석(보안 오류 시 클로드 위임), 그리고 SOAR 단계별 해결(사람 수동 승인 및 유사 건 자동화)**까지 이어지는 **End-to-End 자율 관제 사이클**을 완벽히 지휘하는 전문 운영 지침입니다.

---

## 1. 🔄 4대 엔드-투-엔드 자율 관제 사이클

```
[1. 시나리오 제작] ────► [2. 실시간 탐지] ────► [3. 자율 분석] ────► [4. SOAR 해결 계획]
   클로드 스킬             스케줄러 PPL/DSL         .env LLM API          단계별 시각화 제시
(MITRE ATT&CK)           백그라운드 주기 실행      (보안오류 시 Claude위임)  사람 수동 승인 or 유사건 자동화
```

1. **시나리오 제작 (클로드 - Claude)**:
   - 분석가는 복잡한 쿼리를 직접 작성하지 않습니다. 클로드가 MITRE ATT&CK 프레임워크와 위협 인텔리전스를 분석하여 PPL/DSL 쿼리, 임계치, 억제(Throttle) 규칙을 자율 설계하고 등록합니다.
2. **실시간 탐지 (스케줄러 - Scheduler Engine)**:
   - 등록된 시나리오가 스케줄러를 통해 60초~300초 간격으로 PPL 쿼리를 주기 실행하여 이상 패턴을 0.1초 내 탐지합니다.
3. **자율 분석 (.env LLM API & Claude Fallback)**:
   - 위협 감지 즉시 `.env`에 등록된 LLM API(OpenAI/Gemini/vLLM)가 1차 자율 트리아지(오탐 분류, 공격 단계, 위험도, 원인 요약)를 수행합니다.
   - **보안 가드레일 제약 또는 호출 오류 발생 시**: 시스템은 결코 에러를 방치하지 않고 **`PENDING_CLAUDE_ANALYSIS`** 상태로 안전하게 보관하여, 클로드 수석 분석관이 직접 분석할 수 있도록 위임 대기열로 이관합니다.
4. **SOAR 해결 계획 제시 & 수동 승인 / 유사 건 자동화**:
   - AI는 전체 해결 절차를 SOAR 플레이북(방화벽 IP 차단 ➔ EDR 호스트 격리 ➔ IAM 세션 만료 ➔ 사후 보고서)처럼 **단계별로 시각화**하여 제시합니다.
   - 실제 수행은 **사람이 영향도를 검토한 후 수동 승인(Human-in-the-Loop)**으로 진행합니다.
   - 단, 검증된 시나리오에 대해 **`유사 건 자동 처리 정책(Auto-Remediate Policy)`**이 활성화된 경우, 다음 알람부터는 사람의 대기 없이 AI가 즉시 자동 해결 완료합니다.

---

## 2. 🛠️ 전체 관제 수명주기 제어 MCP 도구 목록

클로드는 다음 전용 MCP 도구들을 활용하여 관제 시나리오 및 인시던트 해결을 관리합니다:

도구 명 (Tool Name) | 주요 역할 | 핵심 매개변수
:---|:---|:---
`list_soc_detection_scenarios` | 현재 등록된 전체 관제 시나리오, MITRE 매핑, 실행 주기, 최근 트리거 현황 조회 | 없음
`register_soc_detection_scenario` | MITRE ATT&CK 기반 신규 관제 시나리오 자율 등록 (Splunk `savedsearches.conf` 호환) | `name`, `ppl_query`, `mitre_tactic`, `mitre_technique`, `severity`, `ai_rationale`, `interval_seconds`, `condition_threshold`, `alert_suppress_period`, `webhook_url`
`tune_soc_detection_scenario` | 오탐(False Positive) 방지 및 운영 환경에 맞춘 임계치, 주기, 중복 억제, 활성화 튜닝 | `scenario_id`, `enabled`, `condition_threshold`, `interval_seconds`, `alert_suppress_period`, `webhook_url`
`test_run_soc_detection_scenario` | 대기 시간 없이 시나리오를 즉시 실행(Run Now)하여 PPL 쿼리 매칭 건수, 트리거 및 억제(Suppressed) 동작 검증 | `scenario_id`
`get_mitre_attack_coverage` | 14대 MITRE ATT&CK 전술별 커버리지 비율(%), 기법 매핑 현황 및 미탐지 Gap 분석 보고서 반환 | 없음
`get_autonomous_incidents` | 자율 AI SIEM이 분석한 전체 인시던트 및 단계별 SOAR 조치 계획 조회 | 없음
`execute_soar_remediation_step` | 사람 또는 에이전트에 의한 특정 SOAR 조치 단계 승인 및 실행 | `incident_id`, `step_number`, `approved_by`
`execute_all_soar_remediation_steps` | 인시던트의 전체 SOAR 조치 단계 일괄 승인 및 즉시 실행 | `incident_id`, `approved_by`
`manage_auto_remediation_policy` | 시나리오별 유사 건 자동 처리 정책(Auto-Remediate) 조회 또는 활성화/비활성화 | `scenario_id`, `enabled`
`get_incidents_pending_claude_analysis` | LLM API 가드레일 오류 등으로 인해 클로드 수석 분석관에게 위임된 인시던트 대기열 조회 | 없음
`submit_claude_incident_analysis` | 클로드가 위임된 인시던트를 직접 분석하고 맞춤형 SOAR 조치 계획 제출 | `incident_id`, `is_false_positive`, `confidence_score`, `root_cause`, `adjusted_severity`, `remediation_steps`

---

## 3. 🛡️ MITRE ATT&CK 전술별 표준 PPL 시나리오 템플릿

클로드가 시나리오를 합성할 때 사용하는 검증된 PPL 쿼리 패턴입니다:

### 1) Reconnaissance / Discovery (정찰 및 탐색)
- **기법**: `T1046 Network Service Scanning`
- **시나리오명**: `[SEC-03] 경계 방화벽(UFW) 비정상 포트 스캔 및 차단 감시`
- **PPL 파이프라인**:
  ```spl
  source = logccino-logs-* | where security.action = 'firewall_drop' or security.action = 'port_scan' | head 50
  ```
- **권장 임계치**: `condition_threshold: 0.0` (매칭 발생 즉시), `interval_seconds: 180`
- **중복 억제**: `alert_suppress: true`, `alert_suppress_period: 10m`

### 2) Credential Access (자격증명 탈취 및 살포)
- **기법**: `T1110.001 Password Guessing / Spraying`
- **시나리오명**: `[SEC-01] SSH 무차별 대입(Brute-Force) 및 로그인 실패 급증`
- **PPL 파이프라인**:
  ```spl
  source = logccino-logs-* | where security.action = 'ssh_login_failure' or security.action = 'ssh_login_failed' | head 50
  ```
- **권장 임계치**: `condition_threshold: 0.0`, `interval_seconds: 60`, `severity: CRITICAL`
- **중복 억제**: `alert_suppress: true`, `alert_suppress_period: 5m`, `alert_suppress_fields: host`

### 3) Privilege Escalation (권한 상승)
- **기법**: `T1548.003 Sudo and Sudo Caching`
- **시나리오명**: `[SEC-02] 의심스러운 비인가 Sudo 권한 상승 탐지`
- **PPL 파이프라인**:
  ```spl
  source = logccino-logs-* | where program = 'sudo' or security.action = 'sudo_escalation' | head 50
  ```
- **권장 임계치**: `condition_threshold: 0.0`, `interval_seconds: 120`, `severity: HIGH`

### 4) Exfiltration (데이터 유출)
- **기법**: `T1071.004 Application Layer Protocol - DNS Tunneling`
- **시나리오명**: `[SEC-05] DNS 터널링 및 비정상 TXT 레코드 대용량 은닉 유출`
- **PPL 파이프라인**:
  ```spl
  source = logccino-logs-* | where security.action = 'dns_tunneling' or length(query) > 100 | head 50
  ```
- **권장 임계치**: `condition_threshold: 0.0`, `interval_seconds: 120`, `severity: HIGH`
- **중복 억제**: `alert_suppress: true`, `alert_suppress_period: 10m`

### 5) Impact (랜섬웨어 및 파괴 행위)
- **기법**: `T1486 Data Encrypted for Impact`
- **시나리오명**: `[SEC-04] 랜섬웨어 카나리 파일 변조 및 대량 확장자 암호화`
- **PPL 파이프라인**:
  ```spl
  source = logccino-logs-* | where security.action = 'ransomware_canary_hit' or event_type = 'file_tamper' | head 50
  ```
- **권장 임계치**: `condition_threshold: 0.0`, `interval_seconds: 60`, `severity: CRITICAL`
- **중복 억제**: `alert_suppress: false` (카나리 변조는 억제 없이 즉각 전파)

---

## 4. 🚨 LLM 보안 가드레일 오류 시 클로드 Fallback 처리 가이드

만약 탐지된 로그의 바이너리 페이로드나 난독화된 Base64 스크립트로 인해 외부 LLM API(OpenAI/Gemini)가 안전성 정책(Content Safety Filter)으로 요청을 거부하거나 오류를 반환한 경우:
1. 클로드는 `get_incidents_pending_claude_analysis()`를 호출하여 대기열에 쌓인 인시던트 목록을 확인합니다.
2. 각 인시던트의 원본 로그(`raw_sample_logs`)와 탐지 컨텍스트를 직접 분석합니다.
3. 분석 결과를 `submit_claude_incident_analysis` 도구를 통해 제출합니다:
   - `incident_id`: 인시던트 ID
   - `is_false_positive`: 오탐 여부
   - `confidence_score`: 분석 신뢰도
   - `root_cause`: 원인 및 공격 기법 상세 설명
   - `remediation_steps`: 침해 격리 및 차단을 위한 맞춤형 SOAR 계획 단계
4. 제출 즉시 SIEM UI에 클로드의 분석 결과가 반영되며, 분석가는 단계별 승인 또는 자동 해결을 진행할 수 있습니다.
