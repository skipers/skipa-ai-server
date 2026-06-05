"""Topical filtering for external web evidence."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")
STOP_TERMS = {
    "특허",
    "기술",
    "시스템",
    "방법",
    "장치",
    "시장",
    "동향",
    "최근",
    "현재",
    "외부",
    "내부",
    "근거",
    "자료",
    "보고서",
    "가능성",
    "정리",
    "알려줘",
    "설명",
    "관련",
    "그리고",
    "with",
    "from",
    "market",
    "trend",
    "trends",
    "analysis",
    "report",
    "system",
    "method",
}
SYNONYMS = {
    "nf3": ["nf3", "nitrogen trifluoride", "trifluoride"],
    "반도체": ["semiconductor", "chip", "wafer"],
    "물류": ["logistics", "supply chain", "warehouse"],
    "가스": ["gas"],
    "이물질": ["contaminant", "particle", "foreign matter", "impurity"],
    "제거": ["removal", "cleaning", "filter"],
    "생산": ["production", "manufacturing"],
    "cmp": ["cmp", "chemical mechanical planarization", "chemical mechanical polishing"],
    "pad": ["pad"],
    "특허": ["patent"],
}
TRUSTED_PROVIDERS = {"KOSIS", "KIPRIS"}


def _tokens(value: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(value or "")]


def _topic_terms(query: str, patent_meta: dict[str, Any] | None = None) -> list[str]:
    meta = patent_meta or {}
    seed = " ".join(
        str(part or "")
        for part in [
            query,
            meta.get("title"),
            meta.get("registration_number"),
            meta.get("application_number"),
            meta.get("ipc_code"),
            meta.get("tech_field"),
            meta.get("business_field"),
        ]
    )
    terms: list[str] = []
    for token in _tokens(seed):
        if token in STOP_TERMS:
            continue
        if token.isdigit() and len(token) < 6:
            continue
        if token not in terms:
            terms.append(token)
    return terms[:24]


def web_result_relevance(
    *,
    query: str,
    title: str,
    snippet: str,
    url: str | None = None,
    patent_meta: dict[str, Any] | None = None,
    provider: str | None = None,
) -> dict[str, Any]:
    if provider and provider.upper() in TRUSTED_PROVIDERS:
        return {"relevant": True, "matched_terms": [provider], "score": 1.0, "reason": "trusted_provider"}

    haystack = " ".join([title or "", snippet or "", urlparse(url or "").netloc]).lower()
    terms = _topic_terms(query, patent_meta)
    matched: list[str] = []
    for term in terms:
        variants = [term, *SYNONYMS.get(term, [])]
        if any(variant and variant.lower() in haystack for variant in variants):
            matched.append(term)

    if "nf3" in terms and "nitrogen trifluoride" in haystack and "nf3" not in matched:
        matched.append("nf3")
    if {"cmp", "pad"} <= set(terms) and "cmp" in haystack and "pad" in haystack:
        for term in ("cmp", "pad"):
            if term not in matched:
                matched.append(term)

    return {
        "relevant": bool(matched),
        "matched_terms": matched[:8],
        "score": round(min(1.0, len(matched) / max(min(len(terms), 6), 1)), 4),
        "reason": "topic_overlap" if matched else "no_topic_overlap",
    }


def is_relevant_web_result(
    *,
    query: str,
    title: str,
    snippet: str,
    url: str | None = None,
    patent_meta: dict[str, Any] | None = None,
    provider: str | None = None,
) -> bool:
    return bool(
        web_result_relevance(
            query=query,
            title=title,
            snippet=snippet,
            url=url,
            patent_meta=patent_meta,
            provider=provider,
        ).get("relevant")
    )
