---
name: logccino-soc-scenarios
description: >-
  클로드(Claude)가 MITRE ATT&CK 엔터프라이즈 매트릭스를 기반으로 Logccino 자율형 AI SIEM의 보안 관제 시나리오를
  전문적으로 설계, PPL 쿼리 합성, 임계치 산정, 중복 알람 억제(Throttling) 및 등록·튜닝·검증을 자율 수행하는 전문 운영 가이드입니다.
---

# Logccino Autonomous AI SOC Detection Scenarios Skill

이 스킬은 AI 에이전트(Claude)가 엔터프라이즈 보안관제센터(SOC)의 수석 탐지 엔지니어(Detection Engineer) 역할을 수행하여,
**사람이 복잡한 쿼리를 일일이 수동 입력하지 않고도** 최신 사이버 위협 및 MITRE ATT&CK 프레임워크에 기반한 **보안 관제 시나리오(Detection Scenarios)를 자율적으로 생성, 배포, 튜닝 및 모니터링**할 수 있도록 하는 전문 운영 지침입니다.

---

## 1. 🎯 관제 시나리오 자율 관리 원칙

1. **사람의 수동 입력 배제**:
   - 보안관제 분석가는 복잡한 PPL 쿼리 문법, 시간 범위(`-15m ~ now`), 정규식(Rex), 중복 억제 해시 필드 등을 직접 타이핑하지 않습니다.
   - 모든 탐지 시나리오는 클로드 스킬이 로그 원천 스키마(ECS/Syslog/DB/SNMP)와 위협 인텔리전스(CTI)를 분석하여 자율적으로 합성하고 등록합니다.

2. **분석가는 현황 조회 및 경량 튜닝(Micro-Tuning)만 수행**:
   - Web UI에서는 시나리오 상태(Active/Disabled 토글), 임계값(Threshold), 알람 주기, 웹훅 수신처만 원클릭으로 조정합니다.
   - 새로운 탐지 룰이 필요한 경우, 분석가는 코파일럿에게 *"MITRE ATT&CK T1059 기반 의심스러운 파워쉘 스크립트 실행 탐지 시나리오 만들어줘"* 라고 자연어로 요청합니다.

3. **MITRE ATT&CK 전술 및 기법 전수 매핑**:
   - 모든 관제 시나리오는 공식 MITRE ATT&CK Tactic(전술) 및 Technique(기법 ID, 예: `T1110.001`, `T1548.003`, `T1046`, `T1486`, `T1071.004`)과 필수 연계됩니다.
   - 등록 시 탐지 근거(AI Rationale)와 오탐 최소화를 위한 억제(Throttling) 설정을 함께 정의합니다.

---

## 2. 🛠️ 관제 시나리오 제어 MCP 도구 목록

클로드는 다음 전용 MCP 도구들을 활용하여 관제 시나리오의 전체 생명주기를 관리합니다:

도구 명 (Tool Name) | 주요 역할 | 핵심 매개변수
:---|:---|:---
`list_soc_detection_scenarios` | 현재 등록된 전체 관제 시나리오, MITRE 매핑, 실행 주기, 최근 트리거 현황 조회 | 없음
`register_soc_detection_scenario` | MITRE ATT&CK 기반 신규 관제 시나리오 자율 등록 (Splunk `savedsearches.conf` 호환) | `name`, `ppl_query`, `mitre_tactic`, `mitre_technique`, `severity`, `ai_rationale`, `interval_seconds`, `condition_threshold`, `alert_suppress_period`, `webhook_url`
`tune_soc_detection_scenario` | 오탐(False Positive) 방지 및 운영 환경에 맞춘 임계치, 주기, 중복 억제, 활성화 튜닝 | `scenario_id`, `enabled`, `condition_threshold`, `interval_seconds`, `alert_suppress_period`, `webhook_url`
`test_run_soc_detection_scenario` | 대기 시간 없이 시나리오를 즉시 실행(Run Now)하여 PPL 쿼리 매칭 건수, 트리거 및 억제(Suppressed) 동작 검증 | `scenario_id`
`get_mitre_attack_coverage` | 14대 MITRE ATT&CK 전술별 커버리지 비율(%), 기법 매핑 현황 및 미탐지 Gap 분석 보고서 반환 | 없음

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

## 4. 🔄 클로드의 자율 시나리오 관리 표준 절차 (SOP)

### STEP 1: 관제 커버리지 Gap 분석
1. 사용자가 *"새로운 보안 시나리오 추천해줘"* 또는 *"미탐지 구역 찾아줘"* 라고 질문할 때:
2. `get_mitre_attack_coverage()`를 호출하여 `uncovered_tactics` 목록을 확인합니다.
3. 아직 룰이 없는 전술(예: Lateral Movement, Persistence 등)을 식별합니다.

### STEP 2: 시나리오 설계 및 PPL 합성
1. 식별된 위협에 대해 ECS 필드(`security.action`, `event_type`, `process.name`, `src_ip`, `dst_port`)를 조합하여 PPL 쿼리를 생성합니다.
2. 실시간 운영에 지장이 없도록 디스패치 시간 범위(`-15m ~ now`)와 적정 실행 주기(60초~300초)를 결정합니다.
3. 경보 피로(Alert Fatigue)를 막기 위해 `alert_suppress_period`를 최소 5분 이상으로 설정합니다.

### STEP 3: 자율 등록 (`register_soc_detection_scenario`)
1. `register_soc_detection_scenario` 도구를 호출하여 SIEM 엔진에 즉시 등록합니다.
2. 시스템은 즉시 `data/saved_searches.json` 및 스케줄러 큐에 반영하며, Web UI의 "AI 자율 관리 관제 시나리오 센터"에 실시간 노출됩니다.

### STEP 4: 시뮬레이션 및 즉시 검증 (`test_run_soc_detection_scenario`)
1. 등록 직후 `test_run_soc_detection_scenario(scenario_id)`를 실행하여 PPL 문법 오류가 없는지, 결과 건수(`result_count`) 및 실행 소요 시간(`execution_took_ms`)이 정상인지 검증합니다.
2. 분석가에게 시나리오 ID, MITRE 매핑, 탐지 원리를 브리핑합니다.

### STEP 5: 오탐 피드백 튜닝 (`tune_soc_detection_scenario`)
1. 분석가가 *"너무 자주 울려", "임계치를 5건 이상으로 올려줘"* 라고 피드백할 때:
2. `tune_soc_detection_scenario(scenario_id=..., condition_threshold=5.0, alert_suppress_period='15m')`를 호출하여 원클릭 튜닝을 완료합니다.
