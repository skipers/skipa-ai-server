"""Local diagnostics for pre-application valuation.

These checks are intentionally deterministic. They do not decide the whole
valuation by themselves; they give the LLM and the local fallback evaluator a
shared factual baseline about input completeness and claim draft quality.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .schemas import PreApplicationValuationRequest


_IPC_KEYWORDS: list[tuple[str, str, tuple[str, ...]]] = [
    ("H04L 29/08", "디지털 정보 전송/네트워크 서비스", ("5g", "네트워크", "통신", "전송", "압축", "지연", "패킷", "클라우드")),
    ("G06F 16/00", "정보 검색/데이터 처리", ("데이터", "검색", "분석", "인덱스", "저장", "처리", "추천")),
    ("G06N 20/00", "머신러닝/인공지능", ("ai", "인공지능", "학습", "모델", "예측", "딥러닝", "분류")),
    ("G06Q 10/06", "관리/사업 데이터 처리", ("업무", "관리", "품질", "공정", "사업", "운영", "리스크")),
    ("B60W 60/00", "자율주행/차량 제어", ("차량", "자율주행", "운전", "센서", "주행")),
    ("A61B 5/00", "의료 진단/생체 측정", ("의료", "환자", "진단", "생체", "헬스케어", "질병")),
    ("H01L 21/00", "반도체 제조 공정", ("반도체", "웨이퍼", "공정", "소재", "박막", "식각", "cmp")),
]


def build_diagnostics(request: PreApplicationValuationRequest) -> dict[str, Any]:
    claims = request.claims
    joined = joined_text(request)
    independent_claims = [claim for claim in claims if not looks_dependent(claim)]
    dependent_claims = [claim for claim in claims if looks_dependent(claim)]
    categories = sorted(claim_categories(claims))
    diagnostics = {
        "text": {
            "technology_description_chars": len(request.technology_description),
            "related_business_chars": len(request.related_business),
            "total_input_chars": len(joined),
        },
        "claims": {
            "count": len(claims),
            "independent_like_count": len(independent_claims),
            "dependent_like_count": len(dependent_claims),
            "average_chars": _average_length(claims),
            "categories": categories,
            "has_method_claim": "방법" in categories,
            "has_device_claim": "장치" in categories,
            "has_media_claim": "매체" in categories,
        },
        "strategy": {
            "target_country_count": len(request.target_countries),
            "target_countries": request.target_countries,
            "has_overseas_target": any(not is_korea(country) for country in request.target_countries),
        },
        "signals": {
            "problem_terms": count_terms(joined, ("문제", "한계", "불편", "지연", "비효율", "오류", "위험", "부족")),
            "mechanism_terms": count_terms(joined, ("단계", "모듈", "알고리즘", "모델", "서버", "센서", "학습", "분석", "제어", "처리")),
            "differentiation_terms": count_terms(joined, ("차별", "신규", "고유", "개선", "최적", "저지연", "자동", "정확", "효율")),
            "effect_terms": count_terms(joined, ("감소", "향상", "개선", "절감", "방지", "최소화", "증가", "가속", "품질")),
            "quantitative_terms": count_terms(joined, ("%", "배", "초", "분", "건", "원", "비율", "정량", "수치")),
            "business_terms": count_terms(joined, ("서비스", "플랫폼", "공정", "품질", "비용", "고객", "매출", "운영", "구독", "인프라")),
            "adoption_terms": count_terms(joined, ("기존", "연동", "도입", "적용", "자동화", "현장", "클라우드", "모바일", "api")),
        },
        "gaps": [],
    }
    diagnostics["gaps"] = detect_gaps(diagnostics)
    return diagnostics


def estimate_ipc(request: PreApplicationValuationRequest) -> dict[str, object]:
    text = joined_text(request).lower()
    best_code, best_desc, best_hits = "G06F 17/00", "디지털 데이터 처리", 0
    matched_keywords: list[str] = []
    for code, desc, keywords in _IPC_KEYWORDS:
        hits = [keyword for keyword in keywords if keyword.lower() in text]
        if len(hits) > best_hits:
            best_code, best_desc, best_hits = code, desc, len(hits)
            matched_keywords = hits
    confidence = "high" if best_hits >= 3 else "medium" if best_hits >= 1 else "low"
    return {
        "ipc": best_code,
        "description": best_desc,
        "confidence": confidence,
        "matched_keywords": matched_keywords,
    }


def keyword_summary(request: PreApplicationValuationRequest, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9가-힣]{2,}", joined_text(request).lower())
    stopwords = {"기반", "방법", "시스템", "장치", "있는", "하는", "및", "또는", "위한", "에서", "으로", "제공"}
    counter = Counter(token for token in tokens if token not in stopwords)
    return [token for token, _count in counter.most_common(limit)]


def detect_gaps(diagnostics: dict[str, Any]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    text = diagnostics["text"]
    claims = diagnostics["claims"]
    strategy = diagnostics["strategy"]
    signals = diagnostics["signals"]
    if text["technology_description_chars"] < 300:
        gaps.append({"type": "description", "severity": "high", "message": "기술 설명이 짧아 문제, 구성, 효과를 더 구체화해야 합니다."})
    if claims["count"] < 3:
        gaps.append({"type": "claims", "severity": "high", "message": "청구항 수가 적어 독립항/종속항 전략을 보강해야 합니다."})
    if claims["independent_like_count"] == 0:
        gaps.append({"type": "claims", "severity": "high", "message": "독립항으로 볼 수 있는 청구항이 확인되지 않습니다."})
    if signals["differentiation_terms"] < 2:
        gaps.append({"type": "differentiation", "severity": "medium", "message": "기존 기술 대비 차별 포인트가 약하게 표현되어 있습니다."})
    if signals["quantitative_terms"] == 0:
        gaps.append({"type": "evidence", "severity": "medium", "message": "효과를 뒷받침할 정량 표현이나 검증 지표가 부족합니다."})
    if text["related_business_chars"] < 50:
        gaps.append({"type": "business", "severity": "medium", "message": "적용 고객, 수익 모델, 도입 환경 설명이 부족합니다."})
    if strategy["target_country_count"] == 0:
        gaps.append({"type": "filing_strategy", "severity": "medium", "message": "출원 예정 국가가 없어 권리화 전략 판단이 제한됩니다."})
    return gaps


def joined_text(request: PreApplicationValuationRequest) -> str:
    return "\n".join([
        request.patent_name,
        request.technology_description,
        "\n".join(request.claims),
        request.related_business,
        ", ".join(request.target_countries),
    ])


def looks_dependent(claim: str) -> bool:
    return bool(re.search(r"(제\s*\d+\s*항|청구항\s*\d+).*(있어서|따른|기재된)", claim))


def claim_categories(claims: list[str]) -> set[str]:
    categories: set[str] = set()
    for claim in claims:
        if any(keyword in claim for keyword in ("시스템", "장치", "서버", "단말", "디바이스")):
            categories.add("장치")
        if any(keyword in claim for keyword in ("방법", "단계", "수행", "프로세스")):
            categories.add("방법")
        if any(keyword in claim for keyword in ("기록매체", "프로그램", "컴퓨터")):
            categories.add("매체")
    return categories or ({"기타"} if claims else set())


def count_terms(text: str, terms: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term.lower()) for term in terms)


def is_korea(country: str) -> bool:
    return country.strip().upper() in {"한국", "대한민국", "KR", "KOREA", "SOUTH KOREA"}


def _average_length(items: list[str]) -> int:
    return round(sum(len(item) for item in items) / len(items)) if items else 0
