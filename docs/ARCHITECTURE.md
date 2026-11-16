# Logccino Architecture Overview

Logccino는 로컬 1대의 PC에서 동작하는 Claude 같은 AI 에이전트가 단독으로 처리할 수 없는 **대용량(TB) 데이터 및 초고속 실시간 스트림 데이터를 AWS 마켓플레이스 또는 사내 Kubernetes(k8s) 분산 클러스터에서 전담 집계·다운샘플링하여 원격 MCP(SSE)를 통해 Claude에게 전달하는 Agent-Native 빅데이터 인텔리전스 백엔드**입니다.

---

## 🏛️ 시스템 아키텍처 다이어그램

```mermaid
flowchart TD
    subgraph ClientPC ["로컬 개발자 PC (1대)"]
        User["사용자"]
        Claude["Claude Desktop / Claude Code<br/>(로컬 AI 에이전트)"]
    end

    subgraph CloudK8sPlatform ["AWS Marketplace / 사내 Kubernetes 클러스터"]
        subgraph IngressLayer ["Ingress & Gateway"]
            Ingress["K8s Ingress / ALB<br/>(SSE & HTTP Streaming 지원)"]
        end

        subgraph MCPLayer ["1. Remote MCP Interface"]
            MCPServer["Logccino MCP Server<br/>(MCPServer / FastMCP over SSE)"]
            
            subgraph MCPTools ["빅데이터 & 실시간 MCP 도구 모음"]
                ToolSearchNat["search_natural<br/>(자연어 직결 검색: PPL / DSL Fallback)"]
                ToolStream["get_realtime_stream_summary<br/>(실시간 스트림 스파이크 요약)"]
                ToolBigData["aggregate_bigdata_metrics<br/>(수천만건 분산 사전 집계)"]
                ToolDiag["diagnose_service_errors<br/>(장애/RCA 에러 분석)"]
                ToolTrace["trace_transaction<br/>(분산 트레이스 타임라인 추적)"]
                ToolHealth["get_cluster_health<br/>(클러스터 노드 & 용량 헬스)"]
            end
        end

        subgraph CoreBackend ["2. Logccino Core Backend (FastAPI)"]
            AdminAPI["Admin & Config API<br/>(/api/v1/admin/*)"]
            IngestAPI["Log Ingestion API<br/>(/api/v1/ingest)"]
            QExecutor["Query Executor Engine<br/>(PPL 우선 & DSL 자동 폴백)"]
        end

        subgraph StorageLayer ["3. OpenSearch 2.18 Distributed Cluster"]
            OSNodes["OpenSearch Distributed Nodes<br/>(Hot/Warm Data Tier)"]
            PPLPlugin["PPL Engine & DSL"]
            IndexPattern["logccino-logs-*"]
        end
    end

    %% 사용자 상호작용
    User -->|"자연어 질문 ('결제 모듈 대규모 타임아웃 분석해줘')"| Claude
    Claude <-->|"Remote MCP over SSE<br/>(https://logccino.company.internal/sse)"| Ingress
    Ingress <--> MCPServer
    MCPServer --- MCPTools
    MCPTools --> QExecutor
    QExecutor --> PPLPlugin
    QExecutor --> OSNodes
```

---

## 🚀 대용량 & 실시간 데이터 처리 흐름 (Big Data & Real-Time Workflow)

1. **로컬 PC의 한계 극복**:
   - 로컬 Claude Desktop은 수 테라바이트 로그를 다운로드할 필요가 없습니다.
   - 자연어 질문을 원격 MCP를 통해 Logccino 백엔드로 전송합니다.
2. **분산 클러스터에서의 고속 병렬 연산**:
   - **PPL 지원 시**: OpenSearch PPL 엔진을 통해 파이프라인 집계 쿼리를 초고속 병렬 실행합니다.
   - **PPL 미지원 시**: OpenSearch 기본 Query DSL(bool, filter, terms aggregation, date_histogram)로 자동 전환하여 안전하게 실행합니다.
3. **지능형 다운샘플링 & 컨텍스트 보호**:
   - 수백만 건의 원시 로그를 Claude에게 그대로 보내지 않고, 시계열 트렌드, 이상치 비율, 대표 스택트레이스 샘플로 서버사이드에서 압축하여 전달합니다.
   - Claude는 컨텍스트 윈도우 한계에 걸리지 않고 초정밀 분석 리포트를 생성할 수 있습니다.
4. **엔터프라이즈 배포 간소화**:
   - AWS Marketplace AMI 또는 사내 Kubernetes의 Helm / `kubectl apply -f deploy/k8s/logccino-all-in-one.yaml` 한 방으로 클러스터와 원격 MCP가 즉시 준비됩니다.
