# ☕ Logccino (로그치노)

> **"로컬 1대의 PC로는 불가능한 대용량(TB) & 실시간 분산 데이터 분석을 Claude가 즉시 수행할 수 있도록 지원하는 Agent-Native 빅데이터 인텔리전스 백엔드"**

---

## 🎯 왜 Logccino가 필요한가? (Problem & Solution)

- 🚫 **기존 로컬 AI 에이전트(Claude Desktop, Cursor 등)의 명확한 한계**:
  - 로컬 1대의 PC에서 실행되는 AI 에이전트는 소량의 CSV/로그 파일은 분석할 수 있습니다.
  - 하지만 **수십 GB~테라바이트(TB) 단위의 대규모 데이터**나 **초당 수만 건씩 쏟아지는 실시간 스트리밍 데이터**는 로컬 메모리와 컨텍스트 윈도우(Context Window) 한계로 인해 **절대 1대의 PC에서 분석할 수 없습니다.**
- 💡 **Logccino의 솔루션**:
  - **AWS 마켓플레이스** 또는 **사내 Kubernetes(k8s) 클러스터**에 1-클릭으로 배포하는 고성능 분산 로그/데이터 인텔리전스 백엔드입니다.
  - Claude 사용자는 배포된 Logccino의 원격 MCP(Server-Sent Events: SSE) 엔드포인트 URL만 등록하면 끝납니다.
  - 사용자가 평소처럼 Claude에게 자연어로 질문하면, Logccino 백엔드가 분산 클러스터에서 테라바이트급 로그를 병렬 집계하고 PPL/DSL 최적화를 거쳐 **Claude의 컨텍스트 한계 내에서 통계와 핵심 증거만을 압축 제공**합니다.

---

## 🏛️ 시스템 아키텍처

```
[사용자] 💬 ("어제 결제 모듈에서 발생한 타임아웃 에러 원인과 실시간 추세 알려줘")
   ⬇️
[Claude Desktop / Claude Code / AI Agents] (로컬 1대 PC)
   ↕️ (Remote MCP over SSE: https://logccino.company.internal/sse)
[Logccino Backend] (AWS Marketplace AMI / EKS / 사내 k8s 배포)
   ├── 🧠 NL-to-Query & PPL/DSL 엔진 (PPL 지원 시 PPL, 미지원 시 OpenSearch 기본 DSL 자동 폴백)
   ├── ⚡ Real-Time Stream Aggregator (초당 수만 건 스트림 실시간 요약)
   └── 📊 Big Data Downsampler (수억 건 로그의 통계적 압축 요약)
   ↕️
[OpenSearch 2.18 분산 클러스터 / 대규모 데이터 스토리지]
```

---

## 🚀 빠른 배포 가이드

### 1. 사내 Kubernetes (k8s) 플랫폼 배포
사내 프라이빗 k8s 또는 AWS EKS에 1-클릭으로 배포합니다:
```bash
kubectl apply -f deploy/k8s/logccino-all-in-one.yaml
```
- OpenSearch 클러스터와 Logccino Remote MCP 백엔드, Ingress가 자동으로 프로비저닝됩니다.
- Ingress 엔드포인트: `http://logccino.company.internal/sse`

### 2. AWS Marketplace / CloudFormation 배포
`deploy/aws/cloudformation-template.yaml`을 AWS 콘솔의 CloudFormation에서 실행하거나 CLI로 배포합니다:
```bash
aws cloudformation create-stack \
  --stack-name logccino-stack \
  --template-body file://deploy/aws/cloudformation-template.yaml \
  --parameters ParameterKey=KeyName,ParameterValue=my-key
```

### 3. 로컬 및 Docker 실행

#### 옵션 A. Docker Compose로 원클릭 전체 실행 (권장)
OpenSearch와 Logccino 백엔드 서비스를 모두 컨테이너로 즉시 실행합니다:
```bash
docker compose up -d --build
```
- Core API & Swagger: `http://localhost:8000/docs`
- Claude Remote MCP 엔드포인트: `http://localhost:8000/sse`

#### 옵션 B. 로컬 Python 직접 개발 환경 실행
OpenSearch 인프라만 컨테이너로 띄우고 호스트 환경에서 백엔드를 직접 개발/디버깅합니다:
```bash
# 1. OpenSearch 인프라 실행
docker compose up -d opensearch-node

# 2. 로컬 가상환경 및 백엔드 실행
source .venv/bin/activate
pip install -r requirements.txt
python -m core.main
```

---

## 🔌 Claude Desktop 연동 (원격 MCP 설정)

배포된 Logccino 엔드포인트를 Claude Desktop의 설정 파일(`~/.config/Claude/claude_desktop_config.json` 또는 `%APPDATA%\Claude\claude_desktop_config.json`)에 추가합니다:

```json
{
  "mcpServers": {
    "logccino": {
      "url": "http://<YOUR_LOGCCINO_HOST>:8000/sse"
    }
  }
}
```

이제 Claude에게 바로 질문할 수 있습니다:
- *"최근 15분간 실시간 스트림에서 이상 에러 급증 구간 요약해줘"* (`get_realtime_stream_summary` 호출)
- *"어제 하루 동안 발생한 수천만 건의 결제 에러를 서비스별로 집계 분석해줘"* (`aggregate_bigdata_metrics` 호출)
- *"auth 서비스에서 500 에러 발생 원인과 연관된 트레이스 타임라인 추적해줘"* (`search_natural` 및 `trace_transaction` 호출)

---

## 🛠️ 대용량 & 실시간 데이터 분석 MCP 도구 목록

| 도구명 | 설명 |
| :--- | :--- |
| `search_natural` | 자연어 질문으로 OpenSearch 대규모 분산 로그 직접 검색 (PPL 우선, DSL 자동 폴백) |
| `get_realtime_stream_summary` | 초당 대규모로 쏟아지는 실시간 로그 스트림에서 최근 N분간의 에러 스파이크 및 트렌드 실시간 요약 |
| `aggregate_bigdata_metrics` | 수백만~수억 건의 빅데이터 로그를 분산 클러스터에서 사전 집계하여 Claude 컨텍스트 한계를 초과하지 않는 압축 통계 테이블 반환 |
| `diagnose_service_errors` | 분산 환경에서 발생하는 장애의 상위 에러 패턴 및 스택트레이스 수집 (RCA 지원) |
| `trace_transaction` | 마이크로서비스 전 구간을 관통하는 분산 트랜잭션(`trace_id`) 타임라인 추적 |
| `search_ppl` | OpenSearch PPL (Piped Processing Language) 파이프라인 쿼리 직접 실행 |
| `get_cluster_health` | 대규모 클러스터 노드 헬스 및 총 인덱싱 데이터 용량/건수 조회 |

---

## 📂 프로젝트 디렉토리 구조

```
logccino/
├── deploy/                         # 클라우드 & k8s 배포 매니페스트
│   ├── k8s/
│   │   └── logccino-all-in-one.yaml # Kubernetes 원터치 배포 (StatefulSet, Deployment, Ingress)
│   └── aws/
│       └── cloudformation-template.yaml # AWS 마켓플레이스/CloudFormation 템플릿
├── Dockerfile                      # 컨테이너 빌드 파일
├── docker-compose.yml              # 로컬 개발용 컨테이너 구성
├── core/                           # Logccino 코어 엔진
│   ├── mcp/                        # Model Context Protocol 서버 (Stdio & Remote SSE 지원)
│   │   ├── server.py               # MCP 서버 진입점 (FastMCP / MCPServer 호환)
│   │   ├── tools.py                # 대용량/실시간 특화 MCP 도구 구현체
│   │   └── config_helper.py        # Claude Desktop 원격/로컬 설정 생성기
│   ├── query/                      # 검색 & 분산 쿼리 엔진
│   │   ├── builder.py              # OpenSearch Query DSL 빌더
│   │   └── executor.py             # PPL 우선 실행 및 OpenSearch 원래 기능(Query DSL) 자동 폴백 실행기
│   ├── ai/                         # 자연어 질의 플래너 및 심층 분석기
│   │   └── assistant.py            # 자연어 -> PPL/DSL 직결 오케스트레이터
│   └── api/                        # FastAPI REST & SSE 관리 서버
├── docs/                           # 상세 문서
│   ├── PRODUCT_MASTER_PROMPT.md    # 제품 제작 및 고도화 마스터 시스템 프롬프트
│   ├── ARCHITECTURE.md             # 분산 아키텍처 및 클라우드 배포 설계
│   └── MCP_GUIDE.md                # Claude Desktop 원격 연동 가이드
└── tests/                          # 단위 및 통합 테스트 (자연어 검색, Fallback 등)
```

---

## 📜 라이선스 (License)

본 프로젝트는 **"Meal & Drinks License (밥과 술 라이선스)"**를 따릅니다:

> 🍚🍺 **원저작자에게 맛있는 밥 한 끼와 기분 좋은 술 한 잔을 정성껏 사야만 본 소프트웨어의 수정 및 배포 권한이 정식으로 부여됩니다.**  
> 상세한 조항은 [LICENSE](file:///home/sst96/Workspace/logccino/LICENSE) 파일을 참고하세요.
