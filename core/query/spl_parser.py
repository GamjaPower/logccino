import re

class SplunkToPPLTranslator:
    """
    Splunk SPL(Search Processing Language) 스타일 입력을 
    OpenSearch PPL(Piped Processing Language) 쿼리로 변환하는 트랜슬레이터
    """

    @staticmethod
    def translate(spl: str, default_index: str = "logccino-logs-*") -> str:
        query = spl.strip()
        
        # 1. 인덱스/소스 추출 또는 기본 소스 지정
        # 예: search index=app level=error -> source = app | where level = 'error'
        if query.startswith("search ") or query.startswith("| search "):
            query = re.sub(r"^\|?\s*search\s+", "", query)

        # 소스 지정이 없으면 기본 소스 추가
        if not query.startswith("source"):
            # 첫 번째 파이프(|) 이전의 필터 조건 추출
            parts = [p.strip() for p in query.split("|")]
            first_clause = parts[0]
            rest_clauses = parts[1:]

            transformed_first = f"source = {default_index}"
            if first_clause and first_clause != "*":
                # key=value 형태 처리
                transformed_first += f" | where {first_clause}"

            query = " | ".join([transformed_first] + rest_clauses)

        return query
