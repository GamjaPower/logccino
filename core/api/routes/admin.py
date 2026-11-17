"""
Logccino Admin & Management API Router
AI 에이전트(Claude, Antigravity) 연동 상태, MCP 도구 관리,
OpenSearch 클러스터 및 로그 수집 현황을 관리하는 UI 전용 백엔드 API
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException
from core.client.opensearch_client import opensearch_service
from core.config import settings
from core.mcp.tools import mcp_tools
from core.mcp.config_helper import get_all_mcp_configs

router = APIRouter(prefix="/admin", tags=["Management UI"])

@router.get("/overview")
async def get_system_overview() -> Dict[str, Any]:
    """관리 UI 대시보드 요약 지표 (OpenSearch 헬스, 총 로그 수, 서비스 현황)"""
    try:
        cluster_status = mcp_tools.get_cluster_status()
        service_metrics = mcp_tools.get_service_metrics(time_window="24h")
        
        return {
            "status": "success",
            "cluster": cluster_status,
            "services_summary": service_metrics.get("services", []),
            "services_count": service_metrics.get("services_count", 0),
            "mcp_enabled": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mcp/status")
async def get_mcp_status_and_configs() -> Dict[str, Any]:
    """MCP 서버 상태, 등록된 도구(Tools) 메타데이터, 에이전트별 설정 JSON"""
    tools_metadata = [
        {
            "name": "search_natural",
            "description": "자연어 질의로 OpenSearch 대규모 분산 로그 직접 검색 (PPL 우선, DSL 자동 폴백)",
            "parameters": ["prompt", "size"]
        },
        {
            "name": "get_realtime_stream_summary",
            "description": "초당 대규모 실시간 스트림에서 최근 N분간 에러율 및 시계열 트렌드 요약",
            "parameters": ["minutes", "service"]
        },
        {
            "name": "aggregate_bigdata_metrics",
            "description": "수백만~수억 건의 빅데이터 로그를 분산 사전 집계하여 통계 요약표 반환",
            "parameters": ["time_window", "group_by", "filter_query"]
        },
        {
            "name": "search_logs",
            "description": "OpenSearch 로그 검색 (키워드, 서비스, 레벨, 시간 필터)",
            "parameters": ["query", "service", "level", "start_time", "end_time", "size"]
        },
        {
            "name": "search_ppl",
            "description": "OpenSearch PPL(Piped Processing Language) 쿼리 직접 실행",
            "parameters": ["ppl_query"]
        },
        {
            "name": "diagnose_service_errors",
            "description": "최근 ERROR/FATAL 로그 및 스택트레이스 수집 (RCA 장애 진단용)",
            "parameters": ["service", "time_window", "limit"]
        },
        {
            "name": "get_service_metrics",
            "description": "서비스별 총 로그 볼륨 및 에러율 집계",
            "parameters": ["time_window"]
        },
        {
            "name": "trace_transaction",
            "description": "특정 trace_id의 마이크로서비스 전 구간 이벤트 타임라인 추적",
            "parameters": ["trace_id"]
        },
        {
            "name": "get_cluster_health",
            "description": "OpenSearch 클러스터 및 Logccino 인덱스 상태 점검",
            "parameters": []
        }
    ]

    prompts_metadata = [
        {
            "name": "diagnose-incident",
            "description": "서비스별 장애 진단 및 근본 원인 분석 가이드",
            "parameters": ["service_name"]
        },
        {
            "name": "bigdata-overview",
            "description": "전사 서비스 대용량 로그 거시적 안정성 및 에러율 분석",
            "parameters": ["time_window"]
        },
        {
            "name": "deep-dive-analysis",
            "description": "자연어 심층 로그 분석 및 5단계 리포트 생성",
            "parameters": ["service_name", "issue_description"]
        },
        {
            "name": "chat-follow-up",
            "description": "멀티턴 대화형 후속 분석 및 구체적 세부사항 질의",
            "parameters": ["previous_context", "follow_up_question"]
        },
        {
            "name": "realtime-stream-anomaly",
            "description": "실시간 고속 스트림 이상 탐지 및 에러 스파이크 감지",
            "parameters": ["minutes", "service"]
        }
    ]

    configs = get_all_mcp_configs()

    return {
        "status": "active",
        "server_name": "Logccino Big Data & Real-Time Intelligence MCP",
        "transport": ["stdio", "sse"],
        "tools_count": len(tools_metadata),
        "tools": tools_metadata,
        "prompts_count": len(prompts_metadata),
        "prompts": prompts_metadata,
        "agent_configs": configs
    }

@router.get("/mcp/config")
async def get_mcp_config_only() -> Dict[str, Any]:
    """Claude Desktop 및 AI 에이전트 연동용 설정 JSON만 반환"""
    return get_all_mcp_configs()

@router.get("/logs/preview")
async def get_logs_preview(size: int = 30) -> Dict[str, Any]:
    """최근 수집된 로그 실시간 프리뷰"""
    try:
        res = mcp_tools.search_logs(size=min(size, 100))
        return {
            "status": "success",
            "total": res.get("total_matched", 0),
            "logs": res.get("hits", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services")
async def list_services() -> Dict[str, Any]:
    """현재 인덱싱된 모든 마이크로서비스 및 최근 통계"""
    try:
        metrics = mcp_tools.get_service_metrics(time_window="24h")
        return {
            "status": "success",
            "services": metrics.get("services", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
