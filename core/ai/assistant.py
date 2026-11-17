import os
import re
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from core.config import settings
from core.query.builder import QueryBuilder
from core.query.executor import QueryExecutor
from core.ai.prompts.nl_to_query import (
    NL_QUERY_PLANNER_SYSTEM_PROMPT,
    build_nl_query_planner_prompt
)
from core.ai.prompts.natural_log_analyst import (
    NATURAL_LOG_ANALYST_SYSTEM_PROMPT,
    build_natural_log_analysis_prompt
)
from core.ai.prompts.chat_analyst import (
    CHAT_LOG_ANALYST_SYSTEM_PROMPT,
    build_chat_analysis_prompt
)
from core.ai.prompts.root_cause import (
    ROOT_CAUSE_ANALYSIS_SYSTEM_PROMPT,
    build_rca_prompt
)
from core.ai.prompts.log_summarize import (
    LOG_SUMMARIZE_SYSTEM_PROMPT,
    build_log_summarize_prompt
)

logger = logging.getLogger(__name__)

class AIAssistant:
    """Logccino 자연어 로그 분석 및 직결 AI 엔진"""

    def __init__(self):
        self.executor = QueryExecutor()

    @property
    def provider(self) -> str:
        return settings.llm_provider

    @property
    def model(self) -> str:
        return settings.llm_model or settings.default_model or "gpt-6-luna"

    def _resolve_relative_time(self, window_str: Optional[str]) -> Optional[str]:
        if not window_str:
            return None
        now = datetime.now(timezone.utc)
        unit = window_str[-1].lower()
        try:
            val = int(window_str[:-1])
            if unit == 'm':
                delta = timedelta(minutes=val)
            elif unit == 'h':
                delta = timedelta(hours=val)
            elif unit == 'd':
                delta = timedelta(days=val)
            else:
                return None
            return (now - delta).isoformat()
        except Exception:
            return None

    async def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """LLM 호출 공통 유틸리티 (Gemini & OpenAI 지원)"""
        # 1. Gemini
        if self.provider == "gemini" and settings.gemini_api_key:
            try:
                from google import genai
                client = genai.Client(api_key=settings.gemini_api_key)
                response = client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=genai.types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=temperature
                    )
                )
                return response.text.strip()
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                raise e

        # 2. OpenAI
        if (self.provider == "openai" or settings.openai_api_key) and settings.openai_api_key:
            try:
                import openai
                client_kwargs = {"api_key": settings.openai_api_key}
                if settings.openai_base_url:
                    client_kwargs["base_url"] = settings.openai_base_url
                client = openai.AsyncOpenAI(**client_kwargs)
                target_model = self.model or "gpt-6-luna"

                create_kwargs = {
                    "model": target_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                }
                # gpt-6, o1, o3 등은 temperature 1만 지원하거나 커스텀 temperature 미지원
                if any(k in target_model.lower() for k in ["gpt-6", "o1", "o3", "reasoning"]):
                    create_kwargs["temperature"] = 1
                else:
                    create_kwargs["temperature"] = temperature

                response = await client.chat.completions.create(**create_kwargs)
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"OpenAI API error ({target_model}): {e}")
                try:
                    if "temperature" in str(e).lower():
                        logger.info(f"Retrying {target_model} with default temperature...")
                        retry_kwargs = {
                            "model": target_model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 1
                        }
                        response = await client.chat.completions.create(**retry_kwargs)
                        return response.choices[0].message.content.strip()

                    if target_model != "gpt-4o-mini":
                        logger.info("Retrying with fallback model: gpt-4o-mini")
                        response = await client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=temperature
                        )
                        return response.choices[0].message.content.strip()
                except Exception as fallback_err:
                    logger.error(f"OpenAI fallback error: {fallback_err}")
                raise e

        # Fallback 메시지
        logger.warning("LLM API key not configured or provider unavailable.")
        return ""

    async def plan_query_from_natural_language(self, user_query: str) -> Dict[str, Any]:
        """자연어 질의로부터 검색 전략 및 PPL / OpenSearch 기본 Query DSL 플랜 생성"""
        prompt = build_nl_query_planner_prompt(user_query)
        plan: Optional[Dict[str, Any]] = None

        try:
            raw_response = await self._call_llm(
                system_prompt=NL_QUERY_PLANNER_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.1
            )

            if raw_response:
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_response, re.DOTALL)
                json_str = match.group(1).strip() if match else raw_response.strip()
                plan = json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to generate query plan via LLM: {e}, falling back to rule-based")

        if not plan:
            # 규칙 기반 Fallback 생성
            level_hint = "ERROR" if any(w in user_query.lower() for w in ["에러", "error", "fail", "실패", "오류", "exception"]) else None
            # 간단한 서비스명 추론
            service_hint = None
            for common_svc in ["payment", "auth", "order", "gateway", "user", "notification"]:
                if common_svc in user_query.lower():
                    service_hint = common_svc
                    break

            plan = {
                "intent": "ERROR_DIAGNOSIS" if level_hint else "EVENT_LOOKUP",
                "summary_of_intent": f"자연어 키워드 검색: {user_query}",
                "filters": {
                    "service": service_hint,
                    "level": level_hint,
                    "keywords": [user_query],
                    "time_relative": "24h"
                },
                "ppl_query": f"source = {settings.opensearch_index_prefix}-* | where match(message, '{user_query}') | head 50",
                "suggested_size": 50
            }

        # OpenSearch 원래 기능인 Query DSL 빌드 및 플랜에 첨부
        filters = plan.get("filters", {})
        keywords = filters.get("keywords") or []
        query_str = " ".join(keywords) if keywords else None
        time_rel = filters.get("time_relative")
        start_time = self._resolve_relative_time(time_rel)

        dsl_query = QueryBuilder.build_search_query(
            query_string=query_str,
            level=filters.get("level"),
            service=filters.get("service"),
            start_time=start_time,
            size=plan.get("suggested_size", 50)
        )
        plan["dsl_query"] = dsl_query

        return plan

    async def execute_natural_query(self, user_query: str, size: int = 50) -> Dict[str, Any]:
        """
        자연어 질의로부터 OpenSearch를 바로 호출:
        PPL이 사용 가능한 구조이면 PPL로 실행하고, 불가하거나 실패 시 OpenSearch 원래 기능(Query DSL)으로 자동 실행
        """
        plan = await self.plan_query_from_natural_language(user_query)
        ppl_query = plan.get("ppl_query")
        dsl_query = plan.get("dsl_query") or QueryBuilder.build_search_query(query_string=user_query, size=size)

        exec_res = self.executor.execute_with_fallback(
            ppl_query=ppl_query,
            dsl_query=dsl_query
        )

        return {
            "prompt": user_query,
            "query_plan": plan,
            "mode": exec_res.get("mode"),
            "executed_query": exec_res.get("executed_query"),
            "total": exec_res.get("total", 0),
            "count": exec_res.get("count", 0),
            "hits": exec_res.get("hits", []),
            "took_ms": exec_res.get("took_ms", 0),
            "fallback_reason": exec_res.get("fallback_reason")
        }

    async def translate_natural_language_to_ppl(self, user_query: str) -> str:
        """단일 PPL 쿼리 문자열 추출"""
        plan = await self.plan_query_from_natural_language(user_query)
        return plan.get("ppl_query", f"source = {settings.opensearch_index_prefix}-* | head 50")

    async def generate_natural_analysis_report(
        self,
        user_question: str,
        logs_data: str,
        query_used: str = "",
        total_matched: int = 0
    ) -> str:
        """수집된 로그 데이터를 기반으로 자연어 종합 분석 보고서 생성"""
        prompt = build_natural_log_analysis_prompt(
            user_question=user_question,
            logs_data=logs_data,
            query_used=query_used,
            total_matched=total_matched
        )

        try:
            report = await self._call_llm(
                system_prompt=NATURAL_LOG_ANALYST_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2
            )
            if report:
                return report
        except Exception as e:
            logger.error(f"Error generating natural log analysis: {e}")

        # LLM Key가 없을 때 Fallback
        return f"""# 🔍 로그 검색 및 간이 분석 결과 (LLM Fallback)

> 💡 **안내**: 상세한 AI 원인 진단 보고서를 생성하려면 `.env` 파일에 `GEMINI_API_KEY`를 설정해주세요.

### 1. 📌 검색 요약
- **질문**: "{user_question}"
- **실행된 쿼리**: `{query_used}`
- **조회된 로그 건수**: 총 {total_matched}건

### 2. 📋 수집된 로그 샘플
```text
{logs_data[:2000]}
```
"""

    async def chat_about_logs(
        self,
        conversation_history: List[Dict[str, str]],
        user_question: str,
        logs_context: str = ""
    ) -> str:
        """이전 대화 이력과 로그 컨텍스트를 고려한 멀티턴 대화형 답변 생성"""
        prompt = build_chat_analysis_prompt(
            conversation_history=conversation_history,
            user_question=user_question,
            logs_context=logs_context
        )

        try:
            reply = await self._call_llm(
                system_prompt=CHAT_LOG_ANALYST_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.3
            )
            if reply:
                return reply
        except Exception as e:
            logger.error(f"Error in chat_about_logs: {e}")

        return f"현재 LLM 서비스에 연결할 수 없어 질문('{user_question}')에 답변을 생성하지 못했습니다."

    async def analyze_root_cause(self, error_logs: str, context: Optional[str] = None) -> str:
        """단일 에러에 대한 빠른 원인 및 해결책 제시"""
        prompt = build_rca_prompt(error_logs, context)
        try:
            report = await self._call_llm(
                system_prompt=ROOT_CAUSE_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.1
            )
            if report:
                return report
        except Exception as e:
            logger.error(f"Error in analyze_root_cause: {e}")
        return "에러 분석을 수행할 수 없습니다. LLM 설정을 확인해주세요."

    async def summarize_logs(self, logs_sample: str) -> str:
        """수집된 로그 요약 브리핑 생성"""
        prompt = build_log_summarize_prompt(logs_sample)
        try:
            summary = await self._call_llm(
                system_prompt=LOG_SUMMARIZE_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2
            )
            if summary:
                return summary
        except Exception as e:
            logger.error(f"Error in summarize_logs: {e}")
        return "로그 요약을 생성할 수 없습니다."

ai_assistant = AIAssistant()
