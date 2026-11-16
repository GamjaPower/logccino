import os
import re
import json
import logging
from typing import Optional, Dict, Any, List
from core.config import settings
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
    """Logccino 자연어 로그 분석 AI 엔진"""

    def __init__(self):
        self.provider = settings.llm_provider
        self.model = settings.llm_model

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
        if self.provider == "openai" and settings.openai_api_key:
            try:
                import openai
                client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                response = await client.chat.completions.create(
                    model=self.model or "gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                raise e

        # Fallback 메시지
        logger.warning("LLM API key not configured or provider unavailable.")
        return ""

    async def plan_query_from_natural_language(self, user_query: str) -> Dict[str, Any]:
        """자연어 질의로부터 검색 전략 및 PPL/DSL 쿼리 플랜 생성"""
        prompt = build_nl_query_planner_prompt(user_query)

        try:
            raw_response = await self._call_llm(
                system_prompt=NL_QUERY_PLANNER_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.1
            )

            if raw_response:
                # json 블록 추출
                match = re.search(r"```(?:json)?\s*(.*?)\s*```", raw_response, re.DOTALL)
                json_str = match.group(1).strip() if match else raw_response.strip()
                return json.loads(json_str)
        except Exception as e:
            logger.warning(f"Failed to generate query plan via LLM: {e}, falling back to rule-based")

        # 규칙 기반 Fallback 생성
        level_hint = "ERROR" if any(w in user_query.lower() for w in ["에러", "error", "fail", "실패", "오류", "exception"]) else None
        return {
            "intent": "ERROR_DIAGNOSIS" if level_hint else "EVENT_LOOKUP",
            "summary_of_intent": f"자연어 키워드 검색: {user_query}",
            "filters": {
                "service": None,
                "level": level_hint,
                "keywords": [user_query],
                "time_relative": "24h"
            },
            "ppl_query": f"source = {settings.opensearch_index_prefix}-* | where match(message, '{user_query}') | head 50",
            "suggested_size": 50
        }

    async def translate_natural_language_to_ppl(self, user_query: str) -> str:
        """하위 호환성을 위한 단일 PPL 쿼리 추출"""
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
        new_question: str,
        new_logs_context: str = ""
    ) -> str:
        """로그 분석 대화형 후속 질의 처리"""
        prompt = build_chat_analysis_prompt(
            conversation_history=conversation_history,
            new_question=new_question,
            new_logs_context=new_logs_context
        )

        try:
            answer = await self._call_llm(
                system_prompt=CHAT_LOG_ANALYST_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2
            )
            if answer:
                return answer
        except Exception as e:
            logger.error(f"Error in chat analysis: {e}")

        return "AI 응답을 생성하지 못했습니다. LLM API Key 및 설정을 확인해주세요."

    async def analyze_root_cause(self, logs_text: str, user_question: str = "") -> str:
        """기존 RCA 호환 메서드"""
        prompt = build_rca_prompt(logs_text, user_question)
        try:
            res = await self._call_llm(
                system_prompt=ROOT_CAUSE_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=prompt,
                temperature=0.2
            )
            if res:
                return res
        except Exception as e:
            logger.error(f"Gemini RCA error: {e}")
            raise e
        return "LLM API Key가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY를 등록해주세요."

ai_assistant = AIAssistant()
