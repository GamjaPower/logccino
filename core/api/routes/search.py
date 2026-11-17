from fastapi import APIRouter, HTTPException
from core.api.models.query import SearchRequest, NaturalQueryRequest
from core.query.builder import QueryBuilder
from core.query.executor import QueryExecutor
from core.ai.assistant import ai_assistant

router = APIRouter(prefix="/search", tags=["Search"])
executor = QueryExecutor()

@router.post("")
async def search_logs(req: SearchRequest):
    """
    로그 검색 엔드포인트
    1. natural_query 입력 시: 자연어 의도 분석 후 PPL(가능시) 또는 OpenSearch 기본 DSL로 자동 실행
    2. 일반 필터 입력 시: OpenSearch 표준 Query DSL로 실행
    """
    try:
        # 1. 자연어 질의가 직접 포함된 경우
        if req.natural_query and req.natural_query.strip():
            result = await ai_assistant.execute_natural_query(
                user_query=req.natural_query,
                size=req.size
            )
            return result

        # 2. 일반 Query DSL 방식 (키워드/필터)
        dsl = QueryBuilder.build_search_query(
            query_string=req.query,
            level=req.level,
            service=req.service,
            start_time=req.start_time,
            end_time=req.end_time,
            size=req.size,
            from_=req.from_
        )
        result = executor.execute_dsl(dsl)
        return {
            "mode": "dsl",
            "query": dsl,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/natural")
async def natural_language_search(req: NaturalQueryRequest):
    """
    자연어에서 바로 OpenSearch를 호출하는 엔드포인트
    - PPL이 사용 가능한 구조이면 PPL 쿼리로 실행
    - PPL이 미지원되거나 실패할 경우 OpenSearch 원래 기능(Query DSL)으로 자동 Fallback 실행
    """
    try:
        if req.execute:
            exec_result = await ai_assistant.execute_natural_query(
                user_query=req.prompt,
                size=req.size
            )
            return exec_result
        else:
            plan = await ai_assistant.plan_query_from_natural_language(req.prompt)
            return {
                "prompt": req.prompt,
                "query_plan": plan,
                "ppl_query": plan.get("ppl_query"),
                "dsl_query": plan.get("dsl_query")
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from pydantic import BaseModel, Field
from typing import List, Optional, Any, Union

class PPLSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 100

class JoinSearchRequest(BaseModel):
    query: Optional[str] = None
    left_query: Optional[str] = None
    right_query: Optional[str] = None
    on: Union[str, List[str]] = "host"
    how: str = "inner"

@router.post("/ppl")
async def search_ppl(req: PPLSearchRequest):
    """
    Splunk 스타일 PPL 및 Cross-Index Join 검색 실행기
    '| join [ ... ]' 구문 사용 시 백엔드 인메모리 해시 조인이 자동 수행됩니다.
    """
    try:
        raw_res = executor.execute_ppl(req.query)
        formatted_hits = executor.format_ppl_response(raw_res)
        return {
            "status": "success",
            "query": req.query,
            "total": len(formatted_hits),
            "schema": raw_res.get("schema", []),
            "hits": formatted_hits,
            "mode": raw_res.get("mode", "ppl")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PPL execution error: {str(e)}")

@router.post("/join")
async def search_join(req: JoinSearchRequest):
    """
    Splunk 스타일 Cross-Index Join 전용 엔드포인트
    단일 쿼리 문자열(| join [ ... ]) 또는 left/right 쿼리 분할 실행 지원
    """
    from core.query.join_engine import SplunkJoinEngine
    try:
        if req.query and req.query.strip():
            raw_res = executor.execute_ppl(req.query)
            formatted_hits = executor.format_ppl_response(raw_res)
            return {
                "status": "success",
                "query": req.query,
                "total": len(formatted_hits),
                "hits": formatted_hits,
                "schema": raw_res.get("schema", [])
            }

        if not req.left_query or not req.right_query:
            raise HTTPException(status_code=400, detail="Either 'query' or both 'left_query' and 'right_query' must be provided.")

        keys = [req.on] if isinstance(req.on, str) else req.on
        left_res = executor.execute_ppl(req.left_query)
        left_recs = executor.format_ppl_response(left_res)

        right_res = executor.execute_ppl(req.right_query)
        right_recs = executor.format_ppl_response(right_res)

        joined = SplunkJoinEngine.hash_join(left_recs, right_recs, keys=keys, how=req.how)
        return {
            "status": "success",
            "left_query": req.left_query,
            "right_query": req.right_query,
            "keys": keys,
            "how": req.how,
            "total": len(joined),
            "hits": joined
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
