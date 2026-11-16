# ☕ Logccino (로그치노)

> **AI 에이전트(Claude, Antigravity, Cursor)를 위한 Model Context Protocol (MCP) 기반 로그 인텔리전스 백엔드 & 관리 플랫폼**

Logccino는 사용자가 직접 복잡한 대시보드(Kibana 등)나 쿼리 문법(Lucene, SPL)을 다룰 필요 없이, **사용자가 사용하는 AI 에이전트(Claude, Antigravity 등)가 MCP 도구를 통해 OpenSearch 로그를 직접 탐색하고 원인을 진단할 수 있도록 지원하는 에이전트 네이티브 로그 플랫폼**입니다. 사용자와 운영자는 이를 관제하고 설정할 수 있는 **관리 대시보드(Management UI)**만 다루면 됩니다.

---

## 💡 핵심 컨셉

- 🤖 **AI 에이전트가 주 인터페이스 (Agent as Primary Interface)**: 사용자는 평소 쓰던 AI 에이전트(Claude, Antigravity 등)에게 말로 질문하고, 에이전트가 Logccino MCP 서버를 호출하여 로그를 분석합니다.
- 🔌 **표준 MCP (Model Context Protocol) 지원**: `search_logs`, `diagnose_service_errors`, `get_service_metrics`, `trace_transaction` 등 6가지 특화 도구 제공.
- 🎛️ **경량 관리 UI (Management UI)**: OpenSearch 클러스터 상태, 에이전트 연결용 MCP 설정 복사, 실시간 로그 스트림, 마이크로서비스 헬스 메트릭 관제.
- ⚡ **고성능 OpenSearch 2.18 기반**: 대규모 분산 로그 수집 및 고속 PPL/DSL 쿼리 실행.

---

## 🏛️ 시스템 구조 요약

```
[사용자] 💬 ("어제 결제 모듈 왜 죽었어?")
   ⬇️
[AI 에이전트 (Claude / Antigravity / Cursor)]
   ↕️ (Model Context Protocol - MCP)
[Logccino MCP Server] ➡️ [Query Engine] ➡️ [OpenSearch Cluster (9200)]
   ⬆️
[Logccino Management UI] (운영자 관리 대시보드: 클러스터 헬스, MCP 허브, 실시간 로그)
```

---

## 📁 프로젝트 디렉토리 구조

```
logccino/
├── docker-compose.yml              # OpenSearch 2.18 로컬 개발 컨테이너
├── requirements.txt                # Core Backend & MCP 의존성
├── .env.example                    # 환경설정 템플릿
├── configs/                        # 인덱스 템플릿 및 매핑 설정
│   └── index_template.json         # OpenSearch 인덱스 템플릿 (표준 로그 필드 매핑)
├── core/                           # Logccino 코어 엔진
│   ├── config.py                   # 환경설정 로더 (Pydantic Settings)
│   ├── main.py                     # API 서버 구동 진입점
│   ├── client/                     # OpenSearch 연결 클라이언트
│   │   └── opensearch_client.py
│   ├── mcp/                        # Model Context Protocol (MCP) 서버
│   │   ├── server.py               # FastMCP 서버 진입점 (Stdio / SSE)
│   │   ├── tools.py                # 6대 핵심 MCP 도구 로직
│   │   └── config_helper.py        # Claude/Antigravity/Cursor용 설정 생성기
│   ├── ingestion/                  # 로그 수집 및 정규화 파이프라인
│   │   ├── parser.py               # 공통 스키마 정규화 파서
│   │   └── pipeline.py             # OpenSearch Bulk 인덱싱
│   ├── query/                      # 검색 & 쿼리 엔진
│   │   ├── builder.py              # Query DSL 빌더
│   │   ├── spl_parser.py           # SPL -> OpenSearch PPL 변환기
│   │   └── executor.py             # OpenSearch 쿼리 실행기
│   ├── ai/                         # 자연어 질의 플래너 및 내부 분석 프롬프트
│   │   ├── assistant.py            # AI 질의/분석 오케스트레이터
│   │   └── prompts/                # 프롬프트 템플릿 (nl_to_query, analyst, chat)
│   └── api/                        # FastAPI REST API 서버
│       ├── app.py                  # API 앱 및 미들웨어
│       ├── models/                 # Request/Response DTO
│       └── routes/                 # admin(관리UI용), analyze, search, ingest 엔드포인트
├── frontend/                       # Logccino 관리 대시보드 (Management UI)
│   └── README.md
├── scripts/                        # 유틸리티 및 초기화 스크립트
│   └── init_opensearch.py          # 템플릿 적용 & 샘플 로그 주입
├── docs/                           # 상세 문서
│   ├── ARCHITECTURE.md             # 시스템 아키텍처 다이어그램 및 설계
│   ├── MCP_GUIDE.md                # AI 에이전트(Claude, Antigravity) 연동 가이드
│   └── PROMPT_GUIDE.md             # 내부 프롬프트 구조 및 개발 가이드
└── tests/                          # 단위/통합 테스트
```

---

## 🚀 빠른 시작 (Quick Start)

### 1. 로컬 OpenSearch 클러스터 실행
```bash
docker compose up -d
```
- OpenSearch: `http://localhost:9200`

### 2. 환경 설정 및 의존성 설치
```bash
cp .env.example .env
pip install -r requirements.txt
```

### 3. OpenSearch 인덱스 템플릿 & 샘플 데이터 등록
```bash
python scripts/init_opensearch.py
```

### 4. Core API & 관리 백엔드 서버 실행
```bash
python -m core.main
```
- 관리 API Swagger 문서: `http://localhost:8000/docs`
- 시스템 오버뷰 API: `http://localhost:8000/api/v1/admin/overview`
- MCP 설정 조회 API: `http://localhost:8000/api/v1/admin/mcp/status`

---

## 🔌 AI 에이전트 연동 (MCP 등록)

Claude Desktop, Google Antigravity, Cursor 등의 에이전트 설정 파일에 아래를 추가하면 즉시 Logccino 도구가 활성화됩니다:

```json
{
  "mcpServers": {
    "logccino": {
      "command": "python",
      "args": ["-m", "core.mcp.server"],
      "cwd": "/path/to/logccino",
      "env": {
        "PYTHONPATH": "/path/to/logccino"
      }
    }
  }
}
```
> 자세한 에이전트별 설정 및 대화 활용법은 [MCP_GUIDE.md](file:///home/sst96/Workspace/logccino/docs/MCP_GUIDE.md)를 참고하세요.

---

## 🎛️ 관리 UI (Management UI)
- 관리 대시보드 화면 및 컴포넌트 설계 가이드는 [frontend/README.md](file:///home/sst96/Workspace/logccino/frontend/README.md)를 참고하세요.
