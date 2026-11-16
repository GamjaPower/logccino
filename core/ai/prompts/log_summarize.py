"""
Log Summarization Prompt Template
특정 시간대의 대량 로그 이벤트 타임라인을 파악하고 주요 이벤트 및 이상 징후를 요약합니다.
"""

LOG_SUMMARIZE_SYSTEM_PROMPT = """
You are an expert Log Pattern and Anomaly Analyst.
Your role is to summarize large volumes of structured and unstructured logs into high-level events, trends, and patterns.

### Guidelines:
- 단순 나열이 아닌 패턴별(예: HTTP 5xx 급증, 특정 API 레이턴시 증가, DB Connection Timeout 등) 그룹화.
- 타임라인 순으로 발생 양상을 서술.
- 특이 패턴 및 주의가 필요한 로그 강조.
"""

def build_log_summarize_prompt(logs: list[dict], time_window: str = "최근 1시간") -> str:
    log_samples = []
    for log in logs[:100]:  # 최대 100건 샘플링
        ts = log.get("@timestamp", "")
        lvl = log.get("level", "INFO")
        svc = log.get("service", "")
        msg = log.get("message", "")[:200]
        log_samples.append(f"[{ts}] [{lvl}] [{svc}] {msg}")

    logs_text = "\n".join(log_samples)

    return f"""### 로그 발생 기간: {time_window}
### 로그 샘플 (총 {len(logs)}건 중 주요 {len(log_samples)}건 추출):
{logs_text}

위 로그들을 분석하여 주요 이벤트 흐름, 이상 패턴, 서비스 상태 요약을 한국어로 작성해주세요."""
