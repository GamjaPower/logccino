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
