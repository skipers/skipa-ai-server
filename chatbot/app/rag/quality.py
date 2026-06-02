"""Evidence quality helpers for chatbot retrieval and answer grounding."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")
ERROR_RE = re.compile(
    r"(?i)(traceback|exception|stack trace|jsondecodeerror|internal server error|"
    r"undefined|nonetype|nan|llm 답변 생성에 실패|모델 상태:)"
)
NEGATIVE_PLACEHOLDER_RE = re.compile(
    r"(관련 근거를 찾지 못했습니다|근거를 찾지 못했습니다|찾을 수 없습니다|"
    r"찾을 수 없음|검색 결과가 없습니다|no local evidence|no web evidence|"
    r"데이터가 없습니다|자료가 없습니다)"
)
REPEATED_CHAR_RE = re.compile(r"(.)\1{12,}")


def compact_text(value: Any, limit: int = 1000) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def evidence_quality(text: str) -> dict[str, Any]:
    value = str(text or "")
    compact = "".join(value.split())
    signal = sum(1 for char in compact if char.isalnum() or ("가" <= char <= "힣"))
    tokens = [token.lower() for token in TOKEN_RE.findall(value)]
    counts = Counter(tokens)
    most_common_ratio = counts.most_common(1)[0][1] / max(len(tokens), 1) if tokens else 0.0
    reasons: list[str] = []
    if len(compact) < 30:
        reasons.append("too_short")
    if compact and signal / max(len(compact), 1) < 0.35:
        reasons.append("low_signal_ratio")
    if ERROR_RE.search(value):
        reasons.append("error_text")
    if NEGATIVE_PLACEHOLDER_RE.search(value):
        reasons.append("negative_placeholder")
    if REPEATED_CHAR_RE.search(value):
        reasons.append("repeated_char")
    if len(tokens) >= 12 and most_common_ratio >= 0.45:
        reasons.append("repeated_token")
    return {
        "usable": not reasons,
        "reasons": reasons,
        "char_count": len(value),
        "compact_char_count": len(compact),
        "token_count": len(tokens),
        "signal_ratio": round(signal / max(len(compact), 1), 4) if compact else 0.0,
        "most_common_token_ratio": round(most_common_ratio, 4),
    }


def is_usable_evidence(text: Any) -> bool:
    return bool(evidence_quality(str(text or "")).get("usable"))


def filter_usable_hits(hits: list[dict[str, Any]], *, limit: int | None = None) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for hit in hits:
        text = str(hit.get("excerpt") or hit.get("page_content") or "")
        quality = evidence_quality(text)
        if not quality["usable"]:
            continue
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        metadata = {**metadata, "evidence_quality": quality}
        filtered.append({**hit, "metadata": metadata})
        if limit is not None and len(filtered) >= limit:
            break
    return filtered
