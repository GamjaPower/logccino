# 🏛️ Logccino Enterprise 시스템 아키텍처 (Enterprise Architecture Overview)

Logccino Enterprise는 로컬 1대의 PC에서 구동되는 Claude, Antigravity 등의 AI 에이전트가 단독으로 처리할 수 없는 **대용량(TB~PB) 분산 데이터 및 초고속 실시간 스트림 데이터를 AWS 마켓플레이스 또는 사내 Kubernetes(k8s) 분산 클러스터에서 전담 집계·다운샘플링하여 원격 MCP(SSE)를 통해 전달하는 엔터프라이즈급 Agent-Native 빅데이터 인텔리전스 & 자율형 SRE 관제 백엔드**입니다.

---

## 🏛️ 엔터프라이즈 시스템 아키텍처 다이어그램

```mermaid
flowchart TD
    subgraph ClientTier ["엔터프라이즈 클라이언트 계층 (Tier 1)"]
        User["SRE / DevOps 엔지니어"]
        Claude["Claude Desktop / Claude Code<br/>(AI 에이전트 인터페이스)"]
        WebUI["Logccino Enterprise Web Console<br/>(/dashboard - Kibana 대체 UI)"]
    end

    subgraph EnterprisePlatform ["엔터프라이즈 플랫폼 계층 (AWS Marketplace / 사내 Kubernetes)"]
        subgraph GatewayTier ["1. API Gateway & Ingress Tier"]
            Ingress["K8s Ingress Controller / AWS ALB<br/>(TLS 1.3 / SSE Streaming / WAF)"]
        end

        subgraph MCPServerTier ["2. Remote MCP Intelligence Tier"]
            MCPServer["Logccino MCP Engine<br/>(Model Context Protocol over SSE)"]
            
            subgraph ToolMatrix ["빅데이터 & 실시간 MCP 도구 매트릭스"]
                ToolSearchNat["search_natural<br/>(PPL 컴파일러 / DSL Fallback)"]
                ToolStream["get_realtime_stream_summary<br/>(실시간 스트림 스파이크 집계)"]
                ToolBigData["aggregate_bigdata_metrics<br/>(수천만건 사전 집계 & 상태 판정)"]
                ToolDiag["diagnose_service_errors<br/>(RCA 장애 분석 & 스택트레이스)"]
                ToolTrace["trace_transaction<br/>(분산 W3C 트레이스 추적)"]
                ToolHealth["get_cluster_health<br/>(클러스터 노드 & 볼륨 텔레메트리)"]
            end
        end

        subgraph CoreBackendTier ["3. Logccino Core Services Tier (FastAPI)"]
            AdminAPI["Admin & Config Engine<br/>(/api/v1/admin/*)"]
            IngestAPI["High-Throughput Ingestion<br/>(/api/v1/ingest)"]
            AIPlanner["AI Query Planner & Analyst<br/>(OpenAI gpt-6-luna / Gemini)"]
            QExecutor["Distributed Query Executor<br/>(PPL 우선 & Native DSL 자동 폴백)"]
        end

        subgraph StorageClusterTier ["4. Distributed Storage Cluster Tier (OpenSearch 2.18)"]
            OSNodes["OpenSearch Distributed Hot/Warm Nodes<br/>(Index Shards & Replica Tier)"]
            PPLPlugin["PPL Engine (Piped Processing)"]
            Indices["logccino-logs-* Indices"]
        end
    end

    %% 상호 작용 흐름
    User -->|"자연어 질의 ('결제 장애 원인 분석해줘')"| Claude
    User -->|"브라우저 관리 및 관제"| WebUI
    Claude <-->|"Remote MCP over SSE<br/>(https://logccino.company.internal/sse)"| Ingress
    WebUI <-->|"REST API"| Ingress
    Ingress <--> MCPServer
    MCPServer --- ToolMatrix
    ToolMatrix --> AIPlanner
    ToolMatrix --> QExecutor
    QExecutor --> PPLPlugin
    QExecutor --> OSNodes
```

---

## 🚀 대용량 & 실시간 데이터 파이프라인 원칙

1. **로컬 에이전트 자원 및 컨텍스트 한계 극복**:
   - 로컬 Claude Desktop은 수 테라바이트의 원시 로그를 직접 다운로드하거나 탐색하지 않습니다.
   - 모든 대규모 필터링, 정렬, 시계열 버킷팅, 상위 에러 시그니처 추출 연산은 서버사이드 분산 클러스터에서 수행됩니다.
2. **지능형 다운샘플링 & 컨텍스트 보호**:
   - 수백만 건의 원시 로그를 Claude의 컨텍스트 윈도우(200k 토큰)에 쏟아붓지 않고, 압축된 통계 매트릭스, 시계열 트렌드, 대표 스택트레이스 샘플로 요약하여 전송합니다.
3. **PPL 파이프라인 가속 및 무중단 DSL 폴백**:
   - OpenSearch PPL 엔진 지원 시 파이프라인 쿼리(`source = ... | where ... | stats ...`)를 통해 초고속 연산을 수행합니다.
   - PPL 플러그인이 비활성화된 환경에서도 기본 OpenSearch Query DSL로 100% 무중단 자동 전환됩니다.
4. **엔터프라이즈급 배포 편의성**:
   - AWS Marketplace AMI 또는 사내 프라이빗 Kubernetes 클러스터에 1-클릭으로 배포되며, OS systemd 사용자 서비스로 무중단 백그라운드 구동됩니다.
