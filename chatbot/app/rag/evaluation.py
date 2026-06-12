"""Lightweight answer quality metrics for Swagger/UI diagnostics.

지표 구성
─────────────────────────────────────────────────────────────────
composite_score (v1 — 호환 유지)
  = retrieval×0.50 + semantic×0.35 + kw_evidence×0.15

composite_v2 (6-way 종합)
  = retrieval×0.30 + faithfulness×0.22 + answer_relevance×0.20
    + semantic×0.15 + context_precision×0.08 + kw_evidence×0.05

신규 지표
  faithfulness          — 답변 토큰이 근거에 얼마나 뒷받침되나 (할루시네이션 역지표)
  answer_relevance      — 질문-답변 의미 유사도 (답변이 질문에 직접 답하는가)
  context_precision     — 검색된 청크 중 실제로 질문과 관련 있는 비율
  context_recall_approx — 질문 키워드가 전체 근거에서 얼마나 커버되나 (ground-truth 없는 근사)
─────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

from collections import Counter
import hashlib
import math
import re
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")
VECTOR_DIMENSIONS = 256

# 한국어 단음절 조사/어미 — 토큰 끝에서 제거해 형태소 정규화
_KO_TAIL = frozenset("이가은는을를의에과와도로")
# 평가 의미 없는 불용어
_STOPWORDS = frozenset([
    "이다", "있다", "하다", "된다", "없다", "것", "수", "등", "및",
    "또한", "그리고", "그러나", "하지만", "위해", "통해", "대해",
    "따라", "관련", "위한", "대한", "통한", "경우", "때", "이상",
    "이하", "위하여", "통하여", "의하여", "있는", "없는",
])


def _normalize(token: str) -> str:
    """한국어 단음절 조사를 제거하고 소문자로 정규화."""
    t = token.lower()
    if len(t) > 2 and t[-1] in _KO_TAIL:
        t = t[:-1]
    return t


def _tokens(text: Any) -> list[str]:
    raw = [_normalize(tok) for tok in TOKEN_RE.findall(str(text or ""))]
    return [t for t in raw if t not in _STOPWORDS and len(t) >= 2]


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
    if score >= 0.80:
        return "high"
    if score >= 0.60:
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


def _faithfulness(answer_tokens: list[str], evidence_tokens: list[str]) -> float:
    """답변 키워드 중 근거에 등장하는 비율 — 높을수록 할루시네이션 낮음."""
    return _coverage(answer_tokens, evidence_tokens)


def _answer_relevance(query_tokens: list[str], answer_tokens: list[str]) -> float:
    """질문-답변 의미 코사인 — 높을수록 답변이 질문에 직접 응답."""
    return _cosine(query_tokens, answer_tokens)


def _context_precision(query_tokens: list[str], source_cards: list[dict[str, Any]], threshold: float = 0.1) -> float:
    """검색된 청크 중 질문과 관련된 비율 (context precision).

    각 청크의 query-chunk 키워드 커버리지가 threshold를 넘으면 관련 있다고 판단.
    """
    if not source_cards:
        return 0.0
    relevant = 0
    for card in source_cards:
        if not isinstance(card, dict):
            continue
        chunk_text = str(card.get("snippet") or card.get("page_content") or "")
        chunk_tokens = _tokens(chunk_text)
        if _coverage(query_tokens, chunk_tokens) >= threshold:
            relevant += 1
    return round(relevant / len(source_cards), 4)


def _context_recall_approx(query_tokens: list[str], source_cards: list[dict[str, Any]]) -> float:
    """질문 키워드가 전체 청크에 걸쳐 얼마나 커버되나 (ground-truth 없는 근사).

    각 질문 토큰이 어느 청크에라도 등장하면 '회수됨'으로 처리.
    """
    if not query_tokens or not source_cards:
        return 0.0
    all_evidence_tokens: set[str] = set()
    for card in source_cards:
        if not isinstance(card, dict):
            continue
        chunk_text = str(card.get("snippet") or card.get("page_content") or "")
        all_evidence_tokens.update(_tokens(chunk_text))
    covered = sum(1 for t in set(query_tokens) if t in all_evidence_tokens)
    return round(covered / len(set(query_tokens)), 4)


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

    # source_cards 메타데이터에서 retrieval_score 추출 (caller가 안 넘겼을 때 fallback)
    source_scores = [float(score) for score in retrieval_scores or [] if isinstance(score, (int, float))]
    if not source_scores:
        source_scores = [
            float(c["metadata"]["retrieval_score"])
            for c in source_cards
            if isinstance(c, dict)
            and isinstance(c.get("metadata"), dict)
            and isinstance(c["metadata"].get("retrieval_score"), (int, float))
        ]

    semantic_score       = _cosine(answer_tokens, evidence_tokens)
    keyword_answer_score = _coverage(query_tokens, answer_tokens)
    keyword_evidence_score = _coverage(query_tokens, evidence_tokens)
    retrieval_score      = round(min(sum(source_scores) / len(source_scores), 1.0), 4) if source_scores else None

    # 신규 지표
    faithfulness         = _faithfulness(answer_tokens, evidence_tokens)
    answer_relevance     = _answer_relevance(query_tokens, answer_tokens)
    ctx_precision        = _context_precision(query_tokens, source_cards)
    ctx_recall           = _context_recall_approx(query_tokens, source_cards)

    # composite v1 (기존 — 호환 유지)
    if retrieval_score is not None:
        composite = round(
            retrieval_score * 0.50
            + semantic_score * 0.35
            + keyword_evidence_score * 0.15,
            4,
        )
    else:
        composite = round(semantic_score * 0.60 + keyword_evidence_score * 0.40, 4)

    # composite v2 (6-way 종합 점수)
    #   retrieval       0.30 — 벡터 검색 품질
    #   faithfulness    0.22 — 할루시네이션 역지표 (답변이 근거에 뒷받침되나)
    #   answer_relevance 0.20 — 질문-답변 정합성
    #   semantic        0.15 — 근거-답변 의미 일치
    #   context_precision 0.08 — 검색 정밀도
    #   kw_evidence     0.05 — 키워드 커버리지
    if retrieval_score is not None:
        composite_v2 = round(
            retrieval_score    * 0.30
            + faithfulness     * 0.22
            + answer_relevance * 0.20
            + semantic_score   * 0.15
            + ctx_precision    * 0.08
            + keyword_evidence_score * 0.05,
            4,
        )
    else:
        composite_v2 = round(
            faithfulness       * 0.30
            + answer_relevance * 0.28
            + semantic_score   * 0.22
            + ctx_precision    * 0.12
            + keyword_evidence_score * 0.08,
            4,
        )

    return {
        # ── 종합 점수 ──────────────────────────────────────────────
        "composite_score":    composite,
        "composite_v2":       composite_v2,
        "grade":              _score_grade(composite),
        "grade_v2":           _score_grade(composite_v2),
        # ── 기존 지표 ──────────────────────────────────────────────
        "retrieval_mean_score":            retrieval_score,
        "semantic_answer_evidence_score":  semantic_score,
        "keyword_evidence_coverage":       keyword_evidence_score,
        "keyword_answer_coverage":         keyword_answer_score,   # 진단용
        # ── 신규 지표 ──────────────────────────────────────────────
        "faithfulness":                    faithfulness,
        "answer_relevance":                answer_relevance,
        "context_precision":               ctx_precision,
        "context_recall_approx":           ctx_recall,
        # ── 부가 정보 ──────────────────────────────────────────────
        "source_count":       len(source_cards),
        "answer_token_count": len(answer_tokens),
        "query_token_count":  len(query_tokens),
        "bert_score":         _optional_bert_score(answer, evidence_text),
    }
