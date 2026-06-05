"""Deterministic scoring logic for pre-application valuation.

The existing re-valuation pipeline scores registered patents with rich KIPRIS,
KOSIS, RAG, and LLM evidence. This module keeps the parts that make sense before
filing: claim breadth, disclosure completeness, business fit, and target country
coverage. It intentionally avoids network calls so CLI/API tests are stable.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .schemas import PreApplicationValuationRequest


@dataclass(frozen=True)
class ScoreSignal:
    item: str
    dimension: str
    score: int
    basis: str

    def to_dict(self) -> dict[str, object]:
        return {
            "item": self.item,
            "dimension": self.dimension,
            "score": self.score,
            "score_out_of_100": self.score * 20,
            "basis": self.basis,
            "method": "rule_based_pre_application",
        }


DIMENSION_LABELS = {
    "technology": "기술성",
    "rights": "권리성",
    "business": "사업성",
}

DIMENSION_WEIGHTS = {
    "technology": 0.36,
    "rights": 0.34,
    "business": 0.30,
}

_IPC_KEYWORDS: list[tuple[str, str, tuple[str, ...]]] = [
    ("H04L 29/08", "디지털 정보 전송/네트워크 서비스", ("5g", "네트워크", "통신", "전송", "압축", "지연", "패킷", "클라우드")),
    ("G06F 16/00", "정보 검색/데이터 처리", ("데이터", "검색", "분석", "인덱스", "저장", "처리", "추천")),
    ("G06N 20/00", "머신러닝/인공지능", ("ai", "인공지능", "학습", "모델", "예측", "딥러닝", "분류")),
    ("G06Q 10/06", "관리/사업 데이터 처리", ("업무", "관리", "품질", "공정", "사업", "운영", "리스크")),
    ("B60W 60/00", "자율주행/차량 제어", ("차량", "자율주행", "운전", "센서", "주행")),
    ("A61B 5/00", "의료 진단/생체 측정", ("의료", "환자", "진단", "생체", "헬스케어", "질병")),
    ("H01L 21/00", "반도체 제조 공정", ("반도체", "웨이퍼", "공정", "소재", "박막", "식각", "cmp")),
]


def estimate_ipc(request: PreApplicationValuationRequest) -> dict[str, object]:
    text = _joined_text(request).lower()
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


def calculate_scores(request: PreApplicationValuationRequest) -> dict[str, object]:
    signals = [
        *_technology_signals(request),
        *_rights_signals(request),
        *_business_signals(request),
    ]
    dimensions = _dimension_summary(signals)
    weighted_average = sum(
        dimensions[key]["average_score"] * DIMENSION_WEIGHTS[key]
        for key in DIMENSION_WEIGHTS
        if key in dimensions
    )
    overall_score = round(weighted_average, 2)
    return {
        "overall_score": overall_score,
        "overall_score_out_of_100": round(overall_score * 20),
        "overall_grade": grade_for_score(overall_score),
        "dimensions": list(dimensions.values()),
        "score_items": [signal.to_dict() for signal in signals],
    }


def grade_for_score(score: float) -> str:
    if score >= 4.5:
        return "A+"
    if score >= 4.0:
        return "A"
    if score >= 3.5:
        return "B+"
    if score >= 3.0:
        return "B"
    if score >= 2.5:
        return "C+"
    if score >= 2.0:
        return "C"
    return "D"


def _technology_signals(request: PreApplicationValuationRequest) -> list[ScoreSignal]:
    description = request.technology_description
    text = _joined_text(request)
    novelty_terms = _count_terms(text, ("차별", "신규", "고유", "실시간", "자동", "최적", "예측", "저지연", "효율", "정확"))
    mechanism_terms = _count_terms(text, ("단계", "모듈", "알고리즘", "모델", "서버", "센서", "학습", "압축", "분석", "제어"))
    effect_terms = _count_terms(text, ("감소", "향상", "개선", "절감", "방지", "최소화", "증가", "가속", "품질"))
    desc_len = len(description)
    return [
        ScoreSignal(
            "기술 구체성",
            "technology",
            _score_by_thresholds(desc_len, [700, 450, 220, 100]),
            f"기술 설명 {desc_len}자. 작동 방식과 활용 맥락의 상세도 기준",
        ),
        ScoreSignal(
            "차별 요소 명확성",
            "technology",
            _score_by_thresholds(novelty_terms, [5, 3, 2, 1]),
            f"차별/효과 관련 키워드 {novelty_terms}개 확인",
        ),
        ScoreSignal(
            "구현 가능성",
            "technology",
            _score_by_thresholds(mechanism_terms + effect_terms, [8, 5, 3, 1]),
            f"구성/효과 신호 {mechanism_terms + effect_terms}개 확인",
        ),
    ]


def _rights_signals(request: PreApplicationValuationRequest) -> list[ScoreSignal]:
    claim_count = len(request.claims)
    independent_like = sum(1 for claim in request.claims if not _looks_dependent(claim))
    category_count = len(_claim_categories(request.claims))
    avg_claim_len = round(sum(len(claim) for claim in request.claims) / claim_count) if claim_count else 0
    countries = request.target_countries
    overseas = [country for country in countries if country not in ("한국", "대한민국", "KR", "Korea")]
    return [
        ScoreSignal(
            "청구항 충실성",
            "rights",
            _score_claim_count(claim_count, avg_claim_len),
            f"청구항 {claim_count}개, 평균 길이 {avg_claim_len}자",
        ),
        ScoreSignal(
            "권리 범위 균형",
            "rights",
            _score_by_thresholds(independent_like + category_count, [5, 4, 3, 2]),
            f"독립항 추정 {independent_like}개, 발명 카테고리 {category_count}개",
        ),
        ScoreSignal(
            "출원 전략 확장성",
            "rights",
            _score_country_strategy(countries),
            f"출원 예정 국가 {len(countries)}개, 해외 권역 {len(overseas)}개",
        ),
    ]


def _business_signals(request: PreApplicationValuationRequest) -> list[ScoreSignal]:
    business = request.related_business
    text = _joined_text(request)
    monetization_terms = _count_terms(text, ("서비스", "플랫폼", "공정", "품질", "비용", "고객", "매출", "운영", "구독", "인프라"))
    adoption_terms = _count_terms(text, ("기존", "연동", "도입", "적용", "자동화", "현장", "클라우드", "모바일", "api"))
    countries = request.target_countries
    return [
        ScoreSignal(
            "사업 연계 명확성",
            "business",
            _score_by_thresholds(len(business), [120, 70, 30, 8]),
            f"관련 사업 설명 {len(business)}자",
        ),
        ScoreSignal(
            "수익/운영 임팩트",
            "business",
            _score_by_thresholds(monetization_terms + adoption_terms, [7, 5, 3, 1]),
            f"사업화/도입 신호 {monetization_terms + adoption_terms}개 확인",
        ),
        ScoreSignal(
            "시장 진입 준비도",
            "business",
            _score_by_thresholds(len(countries) + adoption_terms, [6, 4, 2, 1]),
            f"국가 수 {len(countries)}개와 도입 관련 신호 {adoption_terms}개 기준",
        ),
    ]


def _dimension_summary(signals: Iterable[ScoreSignal]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[ScoreSignal]] = {}
    for signal in signals:
        grouped.setdefault(signal.dimension, []).append(signal)
    result: dict[str, dict[str, object]] = {}
    for key in ("technology", "rights", "business"):
        items = grouped.get(key, [])
        average = round(sum(item.score for item in items) / len(items), 2) if items else 0.0
        result[key] = {
            "key": key,
            "label": DIMENSION_LABELS[key],
            "average_score": average,
            "score_out_of_100": round(average * 20),
            "grade": grade_for_score(average),
            "weight": DIMENSION_WEIGHTS[key],
            "items": [item.to_dict() for item in items],
        }
    return result


def _score_by_thresholds(raw: int, thresholds: list[int]) -> int:
    for index, threshold in enumerate(thresholds):
        if raw >= threshold:
            return 5 - index
    return 1


def _score_claim_count(count: int, avg_len: int) -> int:
    if count >= 8 and avg_len >= 80:
        return 5
    if count >= 5 and avg_len >= 50:
        return 4
    if count >= 2:
        return 3
    if count == 1:
        return 2
    return 1


def _score_country_strategy(countries: list[str]) -> int:
    normalized = {country.upper() for country in countries}
    if len(countries) >= 4 and {"미국", "US", "USA", "유럽", "EP", "EU"} & normalized:
        return 5
    if len(countries) >= 3:
        return 4
    if len(countries) >= 2:
        return 3
    if len(countries) == 1:
        return 2
    return 1


def _claim_categories(claims: list[str]) -> set[str]:
    categories: set[str] = set()
    for claim in claims:
        if any(keyword in claim for keyword in ("시스템", "장치", "서버", "단말", "디바이스")):
            categories.add("장치")
        if any(keyword in claim for keyword in ("방법", "단계", "수행", "프로세스")):
            categories.add("방법")
        if any(keyword in claim for keyword in ("기록매체", "프로그램", "컴퓨터")):
            categories.add("매체")
    return categories or ({"기타"} if claims else set())


def _looks_dependent(claim: str) -> bool:
    return bool(re.search(r"(제\s*\d+\s*항|청구항\s*\d+).*(있어서|따른|기재된)", claim))


def _count_terms(text: str, terms: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term.lower()) for term in terms)


def _joined_text(request: PreApplicationValuationRequest) -> str:
    return "\n".join([
        request.patent_name,
        request.technology_description,
        "\n".join(request.claims),
        request.related_business,
        ", ".join(request.target_countries),
    ])


def keyword_summary(request: PreApplicationValuationRequest, limit: int = 8) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9가-힣]{2,}", _joined_text(request).lower())
    stopwords = {"기반", "방법", "시스템", "장치", "있는", "하는", "및", "또는", "위한", "에서", "으로", "제공"}
    counter = Counter(token for token in tokens if token not in stopwords)
    return [token for token, _count in counter.most_common(limit)]
