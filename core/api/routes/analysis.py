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
    1. 자연어 의도 분석 및 검색 쿼리(PPL/DSL) 플래닝
    2. OpenSearch 대상 로그 검색 및 수집
    3. LLM 기반 원인 규명, 이상치 감지, 타임라인 및 해결책 종합 분석 리포트 생성
    """
    try:
        # 1. 자연어 질의 분석 및 검색 플랜 도출
        query_plan = await ai_assistant.plan_query_from_natural_language(req.prompt)
        ppl_query = query_plan.get("ppl_query", "")
        filters = query_plan.get("filters", {})

        logs: List[Dict[str, Any]] = []
        total_matched = 0
        executed_query = ppl_query
        took_ms = 0

        # 2. OpenSearch 검색 수행 (PPL 시도 -> 실패 시 DSL Fallback)
        ppl_success = False
        if ppl_query:
            try:
                ppl_res = executor.execute_ppl(ppl_query)
                # PPL 결과 파싱 (OpenSearch PPL 응답 스키마)
                schema = ppl_res.get("schema", [])
                datarows = ppl_res.get("datarows", [])
                cols = [col["name"] for col in schema]
                for row in datarows:
                    logs.append(dict(zip(cols, row)))
                total_matched = len(logs)
                ppl_success = True
            except Exception as e:
                logger.warning(f"PPL execution failed, falling back to DSL: {e}")

        if not ppl_success:
            # DSL fallback 검색
            keywords = filters.get("keywords") or []
            query_str = " ".join(keywords) if keywords else None
            level = req.service or filters.get("level")
            service = req.service or filters.get("service")

            dsl = QueryBuilder.build_search_query(
                query_string=query_str,
                level=level,
                service=service,
                size=req.sample_size
            )
            dsl_res = executor.execute_dsl(dsl)
            logs = dsl_res.get("hits", [])
            total_matched = dsl_res.get("total", len(logs))
            took_ms = dsl_res.get("took_ms", 0)
            executed_query = json.dumps(dsl, ensure_ascii=False)

        # 3. 로그 텍스트화 및 LLM 심층 분석
        formatted_logs = _format_logs_for_prompt(logs[:req.sample_size])
        report = await ai_assistant.generate_natural_analysis_report(
            user_question=req.prompt,
            logs_data=formatted_logs,
            query_used=executed_query,
            total_matched=total_matched
        )

        return NaturalAnalysisResponse(
            status="success",
            prompt=req.prompt,
            query_plan=query_plan,
            executed_query=executed_query,
            total_matched=total_matched,
            analysis_report=report,
            evidence_logs=logs[:10],  # 상위 10개 핵심 근거 로그 첨부
            took_ms=took_ms
        )

    except Exception as e:
        logger.error(f"Failed in natural log analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def chat_about_logs(req: ChatAnalysisRequest):
    """
    이전 분석 결과를 바탕으로 대화형 후속 질의(Interactive Follow-up)를 수행합니다.
    """
    try:
        history = [turn.model_dump() for turn in req.conversation_history]
        reply = await ai_assistant.chat_about_logs(
            conversation_history=history,
            new_question=req.question,
            new_logs_context=req.logs_context or ""
        )
        return {
            "status": "success",
            "question": req.question,
            "answer": reply
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/root-cause")
async def analyze_root_cause(req: AnalysisRequest):
    """기존 로그 목록 또는 단순 검색 쿼리 기반 RCA 분석 호환"""
    try:
        logs_text = ""
        if req.logs:
            logs_text = json.dumps(req.logs, ensure_ascii=False, indent=2)
        elif req.query:
            dsl = QueryBuilder.build_search_query(query_string=req.query, level="ERROR", size=20)
            res = executor.execute_dsl(dsl)
            logs_text = json.dumps(res.get("hits", []), ensure_ascii=False, indent=2)
        else:
            raise HTTPException(status_code=400, detail="Either logs or query must be provided.")

        analysis = await ai_assistant.analyze_root_cause(logs_text, req.question or "")
        return {
            "status": "success",
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
