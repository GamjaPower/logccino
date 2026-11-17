"""
Splunk-Style Query Join Engine for Logccino & OpenSearch

OpenSearch는 네이티브 Cross-Index Subsearch Join을 지원하지 않으므로,
본 엔진이 Splunk 표준 문법(| join [type=inner|left|outer] <keys> [ subsearch ])을
파싱하여 분산 인덱스 간 백엔드 인메모리 해시 조인을 수행합니다.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class JoinSpec(BaseModel):
    left_query: str
    right_query: str
    join_type: str = "inner"  # inner, left, outer (full), right
    keys: List[str] = Field(default_factory=list)
    post_pipe: Optional[str] = None


class SplunkJoinEngine:
    """
    Splunk 스타일 | join 쿼리 파서 및 인메모리 해시 조인 엔진
    """

    # 정규식 패턴: | join [type=xxx] [keys] [ subquery ]
    # 예: | join type=left host [ source = logccino-logs-* | stats count() by host ]
    JOIN_REGEX = re.compile(
        r"\|\s*join\s+(?:type\s*=\s*(?P<type>inner|left|outer|right)\s+)?(?P<keys>[a-zA-Z0-9_,\s]+?)\s*\[\s*(?P<subquery>[\s\S]+?)\s*\](?:\s*\|\s*(?P<post_pipe>[\s\S]+))?$",
        re.IGNORECASE
    )

    @classmethod
    def is_join_query(cls, query: str) -> bool:
        """쿼리에 | join [ ... ] 구문이 포함되어 있는지 확인"""
        if not query:
            return False
        return bool(re.search(r"\|\s*join\b.*?\[.*?\]", query, re.IGNORECASE | re.DOTALL))

    @classmethod
    def parse_join_query(cls, query: str) -> Optional[JoinSpec]:
        """
        Splunk 스타일 join 쿼리 파싱
        반환: JoinSpec (left_query, right_query, join_type, keys, post_pipe)
        """
        # join 키워드 위치 검색
        join_match = re.search(r"\|\s*join\b", query, re.IGNORECASE)
        if not join_match:
            return None

        left_part = query[:join_match.start()].strip()
        join_and_right = query[join_match.start():].strip()

        # 대괄호 [ ... ] 파싱 (중첩 대괄호 처리)
        bracket_start = join_and_right.find("[")
        if bracket_start == -1:
            return None

        # 매칭되는 닫는 대괄호 탐색
        depth = 0
        bracket_end = -1
        for i in range(bracket_start, len(join_and_right)):
            if join_and_right[i] == "[":
                depth += 1
            elif join_and_right[i] == "]":
                depth -= 1
                if depth == 0:
                    bracket_end = i
                    break

        if bracket_end == -1:
            return None

        params_part = join_and_right[len(join_match.group(0)):bracket_start].strip()
        subquery = join_and_right[bracket_start + 1:bracket_end].strip()
        post_part = join_and_right[bracket_end + 1:].strip()

        # join type 추출
        join_type = "inner"
        type_match = re.search(r"type\s*=\s*(inner|left|outer|right)", params_part, re.IGNORECASE)
        if type_match:
            join_type = type_match.group(1).lower()
            params_part = params_part[:type_match.start()] + params_part[type_match.end():]

        # join keys 추출
        raw_keys = [k.strip() for k in params_part.replace(",", " ").split() if k.strip()]
        keys = raw_keys if raw_keys else ["_id"]

        # post_pipe (] 이후 파이프 명령어)
        post_pipe = None
        if post_part.startswith("|"):
            post_pipe = post_part[1:].strip()

        return JoinSpec(
            left_query=left_part,
            right_query=subquery,
            join_type=join_type,
            keys=keys,
            post_pipe=post_pipe
        )

    @classmethod
    def hash_join(
        cls,
        left_records: List[Dict[str, Any]],
        right_records: List[Dict[str, Any]],
        keys: List[str],
        how: str = "inner"
    ) -> List[Dict[str, Any]]:
        """
        두 데이터셋 간 인메모리 해시 조인 수행 (inner, left, outer, right)
        """
        how = how.lower()
        if how == "full":
            how = "outer"

        def get_key_tuple(record: Dict[str, Any]) -> Tuple:
            # 중첩 키 및 일반 키 탐색 (e.g. host.name or host)
            vals = []
            for k in keys:
                val = record.get(k)
                if val is None and "." in k:
                    parts = k.split(".")
                    cur = record
                    for p in parts:
                        if isinstance(cur, dict):
                            cur = cur.get(p)
                        else:
                            cur = None
                            break
                    val = cur
                vals.append(str(val) if val is not None else None)
            return tuple(vals)

        # Right 테이블의 해시 인덱스 생성
        right_hash: Dict[Tuple, List[Dict[str, Any]]] = {}
        for r_rec in right_records:
            kt = get_key_tuple(r_rec)
            # 키가 모두 None인 레코드는 조인 불가
            if any(v is not None for v in kt):
                right_hash.setdefault(kt, []).append(r_rec)

        joined_results: List[Dict[str, Any]] = []
        matched_right_indices = set()

        # Left 레코드 순회
        for l_rec in left_records:
            kt = get_key_tuple(l_rec)
            matched_r_list = right_hash.get(kt, [])

            if matched_r_list:
                for r_rec in matched_r_list:
                    matched_right_indices.add(id(r_rec))
                    # 레코드 병합 (left 우선, 충돌 시 right 속성에 접미사 또는 보존)
                    merged = dict(l_rec)
                    for rk, rv in r_rec.items():
                        if rk not in merged or merged[rk] is None:
                            merged[rk] = rv
                        elif rk not in keys and merged[rk] != rv:
                            merged[f"right_{rk}"] = rv
                    joined_results.append(merged)
            else:
                if how in ("left", "outer"):
                    # Right 필드를 None으로 채워서 추가
                    merged = dict(l_rec)
                    joined_results.append(merged)

        # Right 외부 조인 (outer or right)
        if how in ("outer", "right"):
            for r_rec in right_records:
                if id(r_rec) not in matched_right_indices:
                    merged = dict(r_rec)
                    joined_results.append(merged)

        return joined_results

    @classmethod
    def apply_post_pipe(cls, records: List[Dict[str, Any]], post_pipe: str) -> List[Dict[str, Any]]:
        """
        조인 완료 후 후속 파이프(| head N, | fields col1, col2, | sort -col) 간단 처리
        """
        if not post_pipe or not records:
            return records

        pipes = [p.strip() for p in post_pipe.split("|") if p.strip()]
        res = list(records)

        for pipe in pipes:
            parts = pipe.split()
            cmd = parts[0].lower()

            if cmd == "head" and len(parts) > 1:
                try:
                    limit = int(parts[1])
                    res = res[:limit]
                except ValueError:
                    pass

            elif cmd == "tail" and len(parts) > 1:
                try:
                    limit = int(parts[1])
                    res = res[-limit:]
                except ValueError:
                    pass

            elif cmd in ("fields", "table"):
                selected_fields = [f.strip(",") for f in parts[1:] if f.strip(",")]
                if selected_fields:
                    res = [
                        {k: r.get(k) for k in selected_fields if k in r}
                        for r in res
                    ]

            elif cmd == "sort":
                sort_spec = parts[1] if len(parts) > 1 else None
                if sort_spec:
                    desc = sort_spec.startswith("-") or (len(parts) > 2 and parts[1].lower() == "desc")
                    col = sort_spec.lstrip("+-") if not (len(parts) > 2 and parts[1].lower() == "desc") else parts[2]
                    res.sort(
                        key=lambda r: (r.get(col) is not None, r.get(col)),
                        reverse=desc
                    )

        return res
