import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from core.api.models.query import (
    AnalysisRequest,
    NaturalAnalysisRequest,
    NaturalAnalysisResponse,
    ChatAnalysisRequest
)
from core.query.builder import QueryBuilder
from core.query.executor import QueryExecutor
from core.ai.assistant import ai_assistant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["AI Log Analysis"])
executor = QueryExecutor()

def _format_logs_for_prompt(logs: List[Dict[str, Any]], max_chars: int = 15000) -> str:
    """로그 목록을 LLM 프롬프트에 주입하기 좋게 압축 포맷팅"""
    lines = []
    for idx, item in enumerate(logs):
        ts = item.get("@timestamp", "")
        lvl = item.get("level", "INFO")
        svc = item.get("service", "unknown")
        msg = item.get("message", "")
        trace = item.get("trace_id", "")
        trace_str = f" [trace={trace}]" if trace else ""
        lines.append(f"[{idx+1}] [{ts}] [{lvl}] [{svc}]{trace_str} {msg}")

    result = "\n".join(lines)
    if len(result) > max_chars:
        return result[:max_chars] + f"\n... (총 {len(logs)}건 중 일부 길이 제한으로 축약됨)"
    return result

@router.post("/natural", response_model=NaturalAnalysisResponse)
async def analyze_logs_with_natural_language(req: NaturalAnalysisRequest):
    """
    자연어로 로그를 분석하는 통합 엔드포인트
    1. 자연어 의도 분석 및 검색 쿼리(PPL / OpenSearch Query DSL) 플래닝
    2. OpenSearch 대상 로그 검색 및 수집 (PPL 지원 시 PPL, 불가 시 OpenSearch 원래 기능 Query DSL 폴백)
    3. LLM 기반 원인 규명, 이상치 감지, 타임라인 및 해결책 종합 분석 리포트 생성
    """
    try:
        # 1. 자연어 질의 분석 및 검색 플랜 도출
        query_plan = await ai_assistant.plan_query_from_natural_language(req.prompt)
        ppl_query = query_plan.get("ppl_query", "")
        filters = query_plan.get("filters", {})

        # 요청 오버라이드 반영
        target_service = req.service or filters.get("service")
        target_level = filters.get("level")
        keywords = filters.get("keywords") or []
        query_str = " ".join(keywords) if keywords else None

        dsl_query = QueryBuilder.build_search_query(
            query_string=query_str,
            level=target_level,
            service=target_service,
            size=req.sample_size
        )

        # 2. OpenSearch 검색 수행 (PPL 시도 -> 실패/미지원 시 OpenSearch 원래 기능 DSL Fallback)
        search_res = executor.execute_with_fallback(
            ppl_query=ppl_query,
            dsl_query=dsl_query
        )

        logs = search_res.get("hits", [])
        total_matched = search_res.get("total", len(logs))
        executed_query = search_res.get("executed_query")
        mode = search_res.get("mode", "dsl")
        took_ms = search_res.get("took_ms", 0)

        # 3. 로그 텍스트화 및 LLM 심층 분석
        formatted_logs = _format_logs_for_prompt(logs[:req.sample_size])
        report = await ai_assistant.generate_natural_analysis_report(
            user_question=req.prompt,
            logs_data=formatted_logs,
            query_used=json.dumps(executed_query, ensure_ascii=False) if isinstance(executed_query, dict) else str(executed_query),
            total_matched=total_matched
        )

        return NaturalAnalysisResponse(
            status="success",
            prompt=req.prompt,
            query_plan=query_plan,
            executed_query=executed_query,
            mode=mode,
            total_matched=total_matched,
            analysis_report=report,
            evidence_logs=logs[:10],
            took_ms=took_ms
        )
    except Exception as e:
        logger.error(f"Error in natural language log analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_analysis(req: ChatAnalysisRequest):
    """멀티턴 로그 대화형 질의응답 엔드포인트"""
    try:
        reply = await ai_assistant.chat_about_logs(
            conversation_history=[turn.dict() for turn in req.conversation_history],
            user_question=req.question,
            logs_context=req.logs_context or ""
        )
        return {"response": reply}
    except Exception as e:
        logger.error(f"Error in chat analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
async def legacy_quick_analyze(req: AnalysisRequest):
    """빠른 RCA (Root Cause Analysis) 단일 엔드포인트"""
    try:
        if req.logs:
            logs_text = _format_logs_for_prompt(req.logs)
        elif req.query:
            dsl = QueryBuilder.build_search_query(query_string=req.query, size=30)
            res = executor.execute_dsl(dsl)
            logs_text = _format_logs_for_prompt(res.get("hits", []))
        else:
            raise HTTPException(status_code=400, detail="logs 또는 query 중 하나를 전달해야 합니다.")

        analysis = await ai_assistant.analyze_root_cause(
            error_logs=logs_text,
            context=req.question
        )
        return {"analysis": analysis}
    except Exception as e:
        logger.error(f"Error in quick analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
