"""Local retrieval over patent original/report/wiki vectorstores."""

from __future__ import annotations

import logging
from typing import Any

from ..store import search_chunks

logger = logging.getLogger(__name__)


def retrieve_local(
    query: str,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    top_k: int = 5,
    rerank: bool = False,
    use_query_expansion: bool = False,
) -> dict[str, Any]:
    if not use_query_expansion:
        return search_chunks(
            query,
            patent_id=patent_id,
            source_types=source_types,
            top_k=top_k,
            rerank=rerank,
        )

    # Multi-Query Expansion: 3개 변형 쿼리 생성 → 각각 검색 → 병합 → re-rank
    from .query_expansion import expand_query, merge_hits

    queries = expand_query(query)
    logger.debug("query_expansion: %d variants for %r", len(queries), query[:60])

    # 각 변형 쿼리로 top_k * 2 검색 (병합 후 top_k로 줄임)
    fetch_k = min(top_k * 2, 20)
    all_hits: list[list[dict[str, Any]]] = []
    base_result: dict[str, Any] = {}

    for i, q in enumerate(queries):
        result = search_chunks(
            q,
            patent_id=patent_id,
            source_types=source_types,
            top_k=fetch_k,
            rerank=False,  # 병합 후 한 번만 re-rank
        )
        if i == 0:
            base_result = result
        all_hits.append(list(result.get("hits") or []))

    merged = merge_hits(all_hits, top_k=fetch_k)

    # Re-rank merged hits
    if rerank and merged:
        try:
            from ..reranker import rerank_hits
            merged = rerank_hits(query, merged, top_k=top_k)
        except Exception as e:
            logger.warning("rerank failed after expansion: %s", e)
            merged = merged[:top_k]
    else:
        merged = merged[:top_k]

    return {
        **base_result,
        "hits": merged,
        "hit_count": len(merged),
        "mode": f"multi_query_expansion_{len(queries)}q" + ("_reranked" if rerank else ""),
        "expanded_queries": queries,
    }
