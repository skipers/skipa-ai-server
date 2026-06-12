"""Cross-encoder reranker for patent retrieval.

Uses mmarco-mMiniLMv2 (multilingual MS MARCO cross-encoder) to rerank
Qdrant bi-encoder hits. Replaces cosine similarity scores with
cross-encoder relevance scores (0-1 via sigmoid normalization).
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_MAX_CHUNK_CHARS = 512  # trim chunk to avoid slow inference on huge texts


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(_MODEL_NAME)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def rerank_hits(
    query: str,
    hits: list[dict[str, Any]],
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    """Rerank hits using cross-encoder.

    Replaces ``hit["score"]`` and ``hit["metadata"]["retrieval_score"]``
    with sigmoid-normalized cross-encoder relevance scores.
    Returns hits sorted by cross-encoder score, truncated to top_k.
    """
    if not hits:
        return hits

    model = _get_model()
    texts = [str(h.get("page_content") or "")[:_MAX_CHUNK_CHARS] for h in hits]
    pairs = [(query, t) for t in texts]
    raw_scores = model.predict(pairs)

    reranked = []
    for hit, raw in zip(hits, raw_scores):
        norm = round(_sigmoid(float(raw)), 4)
        hit = dict(hit)
        hit["score"] = norm
        meta = dict(hit.get("metadata") or {})
        meta["retrieval_score"] = norm
        meta["reranked"] = True
        hit["metadata"] = meta
        reranked.append(hit)

    reranked.sort(key=lambda h: h["score"], reverse=True)
    return reranked[:top_k] if top_k else reranked
