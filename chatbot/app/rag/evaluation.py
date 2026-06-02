"""Lightweight answer quality metrics for Swagger/UI diagnostics."""

from __future__ import annotations

from collections import Counter
import hashlib
import math
import re
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")
VECTOR_DIMENSIONS = 256


def _tokens(text: Any) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(str(text or ""))]


def _coverage(source_tokens: list[str], target_tokens: list[str]) -> float:
    source = set(source_tokens)
    target = set(target_tokens)
    if not source:
        return 0.0
    return round(len(source & target) / len(source), 4)


def _vectorize(tokens: list[str]) -> dict[int, float]:
    counts: Counter[int] = Counter()
    for token in tokens:
        bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % VECTOR_DIMENSIONS
        counts[bucket] += 1
    norm = math.sqrt(sum(value * value for value in counts.values()))
    if not norm:
        return {}
    return {bucket: value / norm for bucket, value in counts.items()}


def _cosine(left_tokens: list[str], right_tokens: list[str]) -> float:
    left = _vectorize(left_tokens)
    right = _vectorize(right_tokens)
    if len(left) > len(right):
        left, right = right, left
    return round(sum(value * right.get(key, 0.0) for key, value in left.items()), 4)


def _score_grade(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.45:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _optional_bert_score(answer: str, evidence_text: str) -> dict[str, Any]:
    if not answer.strip() or not evidence_text.strip():
        return {
            "available": False,
            "reason": "answer or evidence text is empty",
            "fallback_metric": "semantic_answer_evidence_score",
        }
    try:
        from bert_score import score as bert_score
    except Exception as exc:
        return {
            "available": False,
            "reason": f"bert_score package is not available: {exc}",
            "fallback_metric": "semantic_answer_evidence_score",
        }
    try:
        precision, recall, f1 = bert_score(
            [answer[:5000]],
            [evidence_text[:5000]],
            lang="ko",
            verbose=False,
            rescale_with_baseline=False,
        )
        return {
            "available": True,
            "precision": round(float(precision[0]), 4),
            "recall": round(float(recall[0]), 4),
            "f1": round(float(f1[0]), 4),
            "reference": "retrieved evidence snippets",
        }
    except Exception as exc:
        return {
            "available": False,
            "reason": f"bert_score failed: {type(exc).__name__}: {exc}",
            "fallback_metric": "semantic_answer_evidence_score",
        }


def answer_quality_metrics(
    *,
    query: str,
    answer: str,
    source_cards: list[dict[str, Any]],
    retrieval_scores: list[float] | None = None,
) -> dict[str, Any]:
    query_tokens = _tokens(query)
    answer_tokens = _tokens(answer)
    evidence_text = " ".join(str(card.get("snippet") or "") for card in source_cards if isinstance(card, dict))
    evidence_tokens = _tokens(evidence_text)
    source_scores = [float(score) for score in retrieval_scores or [] if isinstance(score, (int, float))]
    semantic_score = _cosine(answer_tokens, evidence_tokens)
    keyword_score = _coverage(query_tokens, answer_tokens)
    evidence_keyword_score = _coverage(query_tokens, evidence_tokens)
    retrieval_score = round(sum(source_scores) / len(source_scores), 4) if source_scores else None
    composite_parts = [semantic_score, keyword_score, evidence_keyword_score]
    if retrieval_score is not None:
        composite_parts.append(min(retrieval_score, 1.0))
    composite = round(sum(composite_parts) / len(composite_parts), 4) if composite_parts else 0.0
    return {
        "composite_score": composite,
        "grade": _score_grade(composite),
        "semantic_answer_evidence_score": semantic_score,
        "keyword_answer_coverage": keyword_score,
        "keyword_evidence_coverage": evidence_keyword_score,
        "retrieval_mean_score": retrieval_score,
        "source_count": len(source_cards),
        "answer_token_count": len(answer_tokens),
        "query_token_count": len(query_tokens),
        "bert_score": _optional_bert_score(answer, evidence_text),
    }
