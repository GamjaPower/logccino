"""
Interactive Log Chat & Follow-up Prompt Template
이전 로그 분석 결과 및 대화 맥락을 기반으로 사용자의 추가 자연어 질문에 연속해서 답변합니다.
"""

CHAT_LOG_ANALYST_SYSTEM_PROMPT = """
You are Logccino's Interactive Log Intelligence Assistant.
You assist developers, DevOps, and SREs in investigating system logs through natural conversation.
You maintain conversation context, refer back to previously analyzed logs, and examine new log details whenever needed.

### Guidelines:
- 이전 대화에서 논의된 로그, 원인, 서비스를 일관되게 기억하고 답변하세요.
- 사용자가 구체적인 세부 정보(예: "그때 DB 커넥션 풀 설정이 어땠어?", "500 에러 난 사용자 ID 목록 알려줘")를 요구하면 제공된 로그 컨텍스트에서 찾아 답변하세요.
- 친절하고 전문적인 엔지니어 톤으로 한국어로 답변하세요.
"""

def build_chat_analysis_prompt(
    conversation_history: list[dict],
    user_question: str = "",
    new_question: str = "",
    logs_context: str = "",
    new_logs_context: str = ""
) -> str:
    question = user_question or new_question
    context = logs_context or new_logs_context

    history_lines = []
    for turn in conversation_history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        role_label = "사용자" if role == "user" else "Logccino AI"
        history_lines.append(f"**{role_label}**: {content}")

    history_text = "\n\n".join(history_lines)

    prompt = f"""### 이전 대화 내역 (Conversation History):
{history_text}

### 추가 수집된 로그 컨텍스트 (필요시):
{context if context else "(추가 로그 없음 - 이전 맥락 기반 질의)"}

### 사용자의 새로운 질문:
"{question}"

이전 대화 맥락과 로그 데이터를 종합하여 명확하고 실용적인 답변을 한국어로 작성해주세요."""
    return prompt
