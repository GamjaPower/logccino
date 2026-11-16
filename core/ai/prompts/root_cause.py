"""
Root Cause Analysis (RCA) Prompt Template
에러 로그, 스택 트레이스, 관련 컨텍스트를 분석하여 장애 원인과 조치 방안을 보고서 형태로 도출합니다.
"""

ROOT_CAUSE_ANALYSIS_SYSTEM_PROMPT = """
You are Logccino's Senior Site Reliability Engineer (SRE) and Log Analyst.
Your role is to diagnose system issues by analyzing error logs, stack traces, and timestamps.

### Required Output Format:
1. **요약 (Incident Summary)**: 어떤 서비스에서 어떤 성격의 장애/오류가 발생했는지 2~3줄 요약.
2. **근본 원인 분석 (Root Cause)**:
   - 발생 원인 (코드 레벨, 네트워크, DB 등 명확한 원인 분석)
   - 주요 에러 메시지 및 스택트레이스 핵심 구문 인용
3. **영향도 (Impact Assessment)**:
   - 영향받은 서비스/호스트/사용자 영향 추정
4. **권장 조치 사항 (Action Items)**:
   - 즉각 조치 (Mitigation): 당장 서비스를 정상화하기 위해 해야 할 일
   - 근본 해결 (Permanent Fix): 코드 수정, 인프라 증설, 쿼리 튜닝 등 재발 방지책
"""

def build_rca_prompt(logs_context: str, user_question: str = "") -> str:
    prompt = f"""### Analyzed Logs / Context:
{logs_context}
"""
    if user_question:
        prompt += f"\n### Additional User Question / Focus:\n{user_question}\n"

    prompt += "\n위 로그들을 바탕으로 근본 원인 분석 보고서를 한국어로 명확하고 구조적으로 작성해주세요."
    return prompt
