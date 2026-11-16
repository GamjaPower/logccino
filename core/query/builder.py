from typing import Dict, Any, Optional

class QueryBuilder:
    """OpenSearch Query DSL 빌더"""

    @staticmethod
    def build_search_query(
        query_string: Optional[str] = None,
        level: Optional[str] = None,
        service: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        size: int = 100,
        from_: int = 0
    ) -> Dict[str, Any]:
        must_clauses = []
        filter_clauses = []

        if query_string and query_string.strip():
            must_clauses.append({
                "query_string": {
                    "query": query_string,
                    "default_field": "message"
                }
            })
        else:
            must_clauses.append({"match_all": {}})

        if level:
            filter_clauses.append({"term": {"level": level.upper()}})

        if service:
            filter_clauses.append({"term": {"service": service}})

        if start_time or end_time:
            range_filter = {"@timestamp": {}}
            if start_time:
                range_filter["@timestamp"]["gte"] = start_time
            if end_time:
                range_filter["@timestamp"]["lte"] = end_time
            filter_clauses.append({"range": range_filter})

        body = {
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": filter_clauses
                }
            },
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ],
            "from": from_,
            "size": size
        }
        return body
