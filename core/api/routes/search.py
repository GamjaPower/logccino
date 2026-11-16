from fastapi import APIRouter, HTTPException
from core.api.models.query import SearchRequest, NaturalQueryRequest
from core.query.builder import QueryBuilder
from core.query.spl_parser import SplunkToPPLTranslator
from core.query.executor import QueryExecutor
from core.ai.assistant import ai_assistant

router = APIRouter(prefix="/search", tags=["Search"])
executor = QueryExecutor()

@router.post("")
async def search_logs(req: SearchRequest):
    try:
        # 1. SPL / PPL 파이프라인 형태의 쿼리가 제공된 경우
        if req.spl:
            translated_ppl = SplunkToPPLTranslator.translate(req.spl)
            try:
                ppl_result = executor.execute_ppl(translated_ppl)
                return {
                    "mode": "ppl",
                    "query": translated_ppl,
                    "result": ppl_result
                }
            except Exception as ppl_err:
                # OpenSearch PPL 플러그인이 없거나 실패할 경우 DSL fallback 안내
                return {
                    "mode": "ppl_fallback",
                    "error": str(ppl_err),
                    "query": translated_ppl
                }

        # 2. 일반 Query DSL 방식
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
    """자연어를 OpenSearch PPL로 변환하고 필요시 즉시 실행"""
    try:
        generated_ppl = await ai_assistant.translate_natural_language_to_ppl(req.prompt)
        
        response_data = {
            "prompt": req.prompt,
            "ppl_query": generated_ppl
        }

        if req.execute:
            try:
                result = executor.execute_ppl(generated_ppl)
                response_data["execution_result"] = result
            except Exception as exec_err:
                response_data["execution_error"] = str(exec_err)

        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
