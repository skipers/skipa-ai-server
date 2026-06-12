"""Multi-Query Expansion for patent RAG retrieval.

원본 질문을 GPT-4.1로 3개의 다른 표현으로 확장한 뒤
각각 검색해 결과를 병합합니다.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_EXPAND_PROMPT = """특허 검색 시스템에서 사용할 다양한 검색 쿼리를 생성하세요.
원본 질문과 의미는 같지만 다른 단어·표현을 사용해 3개의 검색 쿼리를 만드세요.
각 쿼리는 벡터 검색에 최적화된 짧고 핵심적인 표현이어야 합니다.

원본 질문: {query}

JSON 배열로만 반환하세요: ["쿼리1", "쿼리2", "쿼리3"]"""


def expand_query(query: str) -> list[str]:
    """원본 쿼리 포함 최대 4개 쿼리 반환. 실패 시 원본만 반환."""
    if not query.strip():
        return [query]
    try:
        from openai import OpenAI
        from .config import ANSWER_MODEL
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=ANSWER_MODEL,
            messages=[{"role": "user", "content": _EXPAND_PROMPT.format(query=query[:500])}],
            temperature=0.4,
            max_tokens=200,
            timeout=10,
        )
        text = resp.choices[0].message.content.strip()
        # JSON 배열 파싱 시도
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # 배열만 추출
            import re
            m = re.search(r'\[.*?\]', text, re.DOTALL)
            parsed = json.loads(m.group()) if m else []

        if isinstance(parsed, list):
            variants = [str(q).strip() for q in parsed if str(q).strip()]
        else:
            variants = [str(q).strip() for v in parsed.values() if isinstance(v, list) for q in v]

        all_queries = [query] + variants[:3]
        return list(dict.fromkeys(all_queries))  # 중복 제거, 순서 유지
    except Exception as e:
        logger.debug("query_expansion failed: %s", e)
        return [query]


def merge_hits(hits_list: list[list[dict[str, Any]]], top_k: int) -> list[dict[str, Any]]:
    """여러 쿼리의 hit 목록을 병합하고 중복 제거.

    동일 내용의 청크가 여러 쿼리에서 검색됐을 때 하나만 남깁니다.
    출현 빈도(여러 쿼리에서 검색된 경우)를 score에 반영합니다.
    """
    seen: dict[str, dict[str, Any]] = {}
    freq: dict[str, int] = {}

    for hits in hits_list:
        for hit in hits:
            key = _hit_key(hit)
            if key not in seen:
                seen[key] = dict(hit)
                freq[key] = 1
            else:
                freq[key] += 1
                # 더 높은 score 유지
                if float(hit.get("score") or 0) > float(seen[key].get("score") or 0):
                    seen[key] = dict(hit)

    # 출현 빈도로 score 보정 (RRF: Reciprocal Rank Fusion 대신 간단한 frequency boost)
    for key, hit in seen.items():
        base_score = float(hit.get("score") or 0)
        hit["score"] = round(base_score * (1 + 0.1 * (freq[key] - 1)), 4)

    merged = sorted(seen.values(), key=lambda h: h.get("score") or 0, reverse=True)
    return merged[:top_k]


def _hit_key(hit: dict[str, Any]) -> str:
    """청크 고유 키: Qdrant ID 우선, 없으면 내용 앞 100자."""
    meta = hit.get("metadata") or {}
    uid = str(meta.get("id") or hit.get("id") or "")
    if uid:
        return uid
    content = str(hit.get("page_content") or "")
    return content[:120]
