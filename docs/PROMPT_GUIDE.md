# Logccino 자연어 로그 분석 프롬프트 가이드 (Prompt Guide)

Logccino는 복잡한 검색 쿼리나 대시보드 조작 없이 **"사람이 말하듯 자연어로 질문하고, AI가 로그를 분석하여 원인과 해결책을 알려주는 시스템"**을 지향합니다.

이 문서는 Logccino 내부의 **AI 프롬프트 파이프라인 구조**와 **자체 웹 UI(챗봇 & 대시보드) 제작을 위한 개발 프롬프트**를 안내합니다.

---

## 1. 자연어 로그 분석 AI 프롬프트 체계

```mermaid
flowchart LR
    A["사용자 자연어 질문<br/>'어제 결제 오류 왜 났어?'"] --> B["[Stage 1] NL Query Planner<br/>(nl_to_query.py)"]
    B --> C["OpenSearch 로그 수집<br/>(PPL/DSL 실행)"]
    C --> D["[Stage 2] Deep-Dive Log Analyst<br/>(natural_log_analyst.py)"]
    D --> E["종합 분석 보고서 & 조치 방안<br/>(마크다운 + 근거 로그)"]
    E --> F["[Stage 3] Chat Engine<br/>(chat_analyst.py - 후속 질의)"]
```

---

### 1.1. [Stage 1] NL Query Planner (자연어 질의 플래너)
- **파일 경로**: [nl_to_query.py](file:///home/sst96/Workspace/logccino/core/ai/prompts/nl_to_query.py)
- **목적**: 사용자의 모호하거나 다양한 자연어 표현에서 검색 의도(Intent), 대상 서비스, 로그 레벨, 시간 범위, 검색 키워드를 추출하고 실행 가능한 PPL 쿼리를 생성합니다.
- **핵심 프롬프트 구성**:
  - **역할 정의**: OpenSearch 쿼리 최적화 및 로그 검색 전문가
  - **스키마 명시**: `@timestamp`, `service`, `host`, `level`, `message`, `trace_id`, `attributes.*`
  - **출력 규격**: 엄격한 JSON 구조 (`intent`, `summary_of_intent`, `filters`, `ppl_query`, `suggested_size`)

---

### 1.2. [Stage 2] Deep-Dive Log Analyst (자연어 로그 분석 전문가)
- **파일 경로**: [natural_log_analyst.py](file:///home/sst96/Workspace/logccino/core/ai/prompts/natural_log_analyst.py)
- **목적**: 실제 OpenSearch에서 검색된 로그 레코드와 에러 스택트레이스를 주입받아, 실질적인 원인 규명 및 SRE 관점의 조치 방안을 보고서 형태로 도출합니다.
- **핵심 프롬프트 구성**:
  - **원칙**: 두괄식 직접 답변, 실제 로그 및 에러 메시지 직접 인용, 시간순 전파 과정 파악, 긴급 완화책과 영구 해결책 분리
  - **출력 섹션**:
    1. 📌 **핵심 요약 (Executive Summary)**: 2~3줄 결론 및 심각도(CRITICAL / WARNING / INFO)
    2. 🔬 **상세 분석 및 원인 규명 (Root Cause & Diagnostics)**: 장애 원인 및 근거 로그 발췌
    3. ⏱️ **이벤트 타임라인 및 영향도 (Timeline & Impact)**: 발생 시점, 전파 과정, 영향 범위
    4. 🛠️ **권장 조치 방안 (Recommended Actions)**: 긴급 조치(Immediate) 및 근본 조치(Permanent)
    5. 💡 **추천 후속 질문 (Suggested Next Steps)**: 추가 파악할 만한 자연어 질문 추천

---

### 1.3. [Stage 3] Interactive Chat Engine (대화형 후속 분석)
- **파일 경로**: [chat_analyst.py](file:///home/sst96/Workspace/logccino/core/ai/prompts/chat_analyst.py)
- **목적**: 1차 분석 이후 사용자가 추가 질문(예: "그때 DB 커넥션 풀 설정값은 몇이었어?", "500 에러를 겪은 사용자 ID들 뽑아줘")을 던졌을 때, 이전 대화 및 로그 컨텍스트를 유지하여 자연스러운 대화형 분석을 제공합니다.

---

## 2. 자체 웹 UI 제작을 위한 프롬프트 (Kibana 대체용)

기존 Kibana(5601 포트) 대신 자체 제작할 프론트엔드(Next.js)를 AI와 함께 구축할 때 사용할 수 있는 단계별 개발 프롬프트입니다.

### [1단계: 대화형 분석 중심의 Next.js 챗봇 UI 뼈대 생성]
```text
frontend/ 디렉토리에 Next.js 14 (App Router, TailwindCSS, Lucide-React, Shadcn/ui)를 기반으로 Logccino의 자연어 로그 분석 전용 대시보드를 생성해줘.
1. 상단: 실시간 서비스 상태 인디케이터 (OpenSearch 연결 상태)
2. 중앙 좌측: 자연어 대화형 인터페이스 (Chat UI)
   - 입력창: 자연어로 로그 질문 입력 ("최근 1시간 결제 오류 원인 분석해줘")
   - 메시지창: AI의 마크다운 분석 보고서 렌더링 + 추천 후속 질문 칩(클릭 시 자동 입력)
3. 중앙 우측 / 하단: 근거 로그 뷰어 (Evidence Log Viewer)
   - AI 보고서와 함께 반환된 실제 OpenSearch 로그(JSON 상세 모달, 레벨별 배지 색상)
4. API 연동: Logccino Core Backend의 POST /api/v1/analyze/natural 및 POST /api/v1/analyze/chat 호출
```

### [2단계: 차트 및 시각화 컴포넌트 추가]
```text
분석 결과에 시계열 에러 발생 빈도나 서비스별 분포를 보여줄 수 있도록 Recharts 또는 ECharts를 연동해줘.
- 시간대별 로그 건수 히스토그램 (Bar / Area Chart)
- 로그 레벨(INFO, WARN, ERROR) 파이 차트
- AI 분석 결과와 연동되어 질문한 시점의 그래프 하이라이트 표시
```
