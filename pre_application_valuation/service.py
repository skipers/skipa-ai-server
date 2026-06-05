"""Service layer for pre-application valuation."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from .llm_comment import generate_llm_overall_comment
from .schemas import PreApplicationValuationRequest
from .scoring import calculate_scores, estimate_ipc, keyword_summary


SCHEMA_VERSION = "pre-application-valuation/v1"


def evaluate_pre_application(request: PreApplicationValuationRequest | dict[str, Any]) -> dict[str, Any]:
    parsed = request if isinstance(request, PreApplicationValuationRequest) else PreApplicationValuationRequest.model_validate(request)
    scoring = calculate_scores(parsed)
    ipc = estimate_ipc(parsed)
    dimensions = scoring["dimensions"]
    strongest = max(dimensions, key=lambda item: item["average_score"])
    weakest = min(dimensions, key=lambda item: item["average_score"])
    fallback_comment = _overall_comment(str(scoring["overall_grade"]), weakest["label"])
    llm_comment = generate_llm_overall_comment(parsed, scoring, ipc, fallback_comment)
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluation_id": f"preval-{uuid4().hex[:12]}",
        "evaluated_at": datetime.now().isoformat(timespec="seconds"),
        "patent_title": parsed.patent_name,
        "input": {
            "patent_name": parsed.patent_name,
            "technology_description": parsed.technology_description,
            "claims": parsed.claims,
            "related_business": parsed.related_business,
            "target_countries": parsed.target_countries,
        },
        "ai_classification": ipc,
        "keywords": keyword_summary(parsed),
        "overall": {
            "score": scoring["overall_score"],
            "score_out_of_100": scoring["overall_score_out_of_100"],
            "grade": scoring["overall_grade"],
            "comment": llm_comment["overall_comment"],
            "comment_source": llm_comment["source"],
            "comment_model": llm_comment["model"],
        },
        "llm_comment": llm_comment,
        "dimensions": dimensions,
        "score_items": scoring["score_items"],
        "comments": _dimension_comments(dimensions),
        "recommendations": _recommendations(parsed, weakest["key"]),
        "frontend_summary": {
            "title": parsed.patent_name,
            "ipc": ipc["ipc"],
            "overall_grade": scoring["overall_grade"],
            "technology_score": _score_for(dimensions, "technology"),
            "rights_score": _score_for(dimensions, "rights"),
            "business_score": _score_for(dimensions, "business"),
            "strongest_dimension": strongest["label"],
            "weakest_dimension": weakest["label"],
        },
    }


def _score_for(dimensions: list[dict[str, Any]], key: str) -> int:
    for dimension in dimensions:
        if dimension["key"] == key:
            return int(dimension["score_out_of_100"])
    return 0


def _overall_comment(grade: str, weakest_label: str) -> str:
    if grade in ("A+", "A"):
        return f"출원 전 사전 평가 기준으로 우수합니다. {weakest_label} 보완 시 강한 출원 패키지가 기대됩니다."
    if grade in ("B+", "B"):
        return f"출원 검토가 가능한 수준입니다. {weakest_label}을 먼저 보완하면 등급 개선 여지가 큽니다."
    if grade in ("C+", "C"):
        return f"아이디어 방향은 확인되지만 출원 전 보완이 필요합니다. {weakest_label} 근거를 구체화하세요."
    return f"현 입력만으로는 출원 타당성이 낮게 평가됩니다. {weakest_label}부터 재정리하는 것이 좋습니다."


def _dimension_comments(dimensions: list[dict[str, Any]]) -> list[dict[str, str]]:
    comments = []
    for dimension in dimensions:
        label = str(dimension["label"])
        score = float(dimension["average_score"])
        if score >= 4:
            message = f"{label}은 강점으로 보입니다. 현재 근거를 명세서와 청구항에 일관되게 반영하세요."
        elif score >= 3:
            message = f"{label}은 평균 이상입니다. 차별 요소와 정량 효과를 조금 더 명확히 적으면 좋습니다."
        else:
            message = f"{label}은 보완 필요성이 큽니다. 구체적 구성, 범위, 활용 근거를 추가하세요."
        comments.append({"dimension": label, "comment": message})
    return comments


def _recommendations(request: PreApplicationValuationRequest, weakest_key: str) -> list[str]:
    recommendations = [
        "독립항에는 핵심 구성요소와 데이터 흐름을 한 문장 안에서 분명히 연결하세요.",
        "기술 설명에는 기존 방식 대비 차별점과 기대 효과를 정량 표현으로 보강하세요.",
    ]
    if weakest_key == "rights":
        recommendations.insert(0, "청구항을 독립항/종속항으로 나누고 장치, 방법, 기록매체 관점을 함께 검토하세요.")
    elif weakest_key == "business":
        recommendations.insert(0, "관련 사업의 적용 고객, 수익 모델, 도입 환경을 더 구체적으로 작성하세요.")
    elif weakest_key == "technology":
        recommendations.insert(0, "핵심 알고리즘이나 시스템 구성의 입력, 처리, 출력 과정을 단계별로 보강하세요.")
    if not request.target_countries:
        recommendations.append("출원 예정 국가를 최소 1개 이상 지정하면 권리 전략 평가가 안정적입니다.")
    return recommendations[:4]
