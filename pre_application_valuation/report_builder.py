"""Report builder for pre-application valuation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .schemas import PreApplicationValuationRequest


REPORT_SCHEMA_VERSION = "pre-application-valuation-report/v2"
DIMENSION_ORDER = [
    "technology_readiness",
    "claimability",
    "business_hypothesis",
    "filing_readiness",
]
DIMENSION_LABELS = {
    "technology_readiness": "기술 구체성",
    "claimability": "권리화 가능성",
    "business_hypothesis": "시장/사업 가설",
    "filing_readiness": "출원 준비도",
}
DIMENSION_WEIGHTS = {
    "technology_readiness": 0.28,
    "claimability": 0.32,
    "business_hypothesis": 0.20,
    "filing_readiness": 0.20,
}


def build_report(
    *,
    evaluation_id: str,
    evaluated_at: datetime,
    request: PreApplicationValuationRequest,
    diagnostics: dict[str, Any],
    ipc: dict[str, Any],
    keywords: list[str],
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    score_items = list(evaluation.get("score_items") or [])
    dimensions = summarize_dimensions(score_items)
    overall_score = weighted_overall_score(dimensions)
    weakest = min(dimensions, key=lambda item: item["average_score"]) if dimensions else None
    strongest = max(dimensions, key=lambda item: item["average_score"]) if dimensions else None
    next_actions = merge_next_actions(evaluation, score_items, diagnostics)
    key_risks = merge_risks(evaluation, score_items, diagnostics)
    overall_opinion = str(evaluation.get("overall_opinion") or "").strip() or default_overall_opinion(overall_score, weakest)

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "evaluated_at": evaluated_at.isoformat(timespec="seconds"),
        "patent_title": request.patent_name,
        "metadata": {
            "report_type": "pre_application_valuation",
            "title": "사전가치평가 보고서",
            "schema_version": REPORT_SCHEMA_VERSION,
            "generated_at": evaluated_at.isoformat(timespec="seconds"),
            "score_display_scale": "0~100",
            "item_score_scale": "1~5",
            "storage_policy": "local_json_development",
            "evaluation_source": evaluation.get("source"),
            "model": evaluation.get("model"),
            "service_sections": [
                {"key": "input_summary", "title": "입력 요약"},
                {"key": "executive_summary", "title": "평가 요약"},
                {"key": "readiness", "title": "출원 준비도"},
                {"key": "evaluation", "title": "평가 기준별 상세 점수"},
                {"key": "claim_strategy", "title": "권리화 전략"},
                {"key": "filing_strategy", "title": "출원 전략"},
                {"key": "next_actions", "title": "보완 액션"},
                {"key": "limitations", "title": "평가 한계"},
            ],
        },
        "input": request.model_dump(),
        "input_summary": {
            "title": request.patent_name,
            "target_countries": request.target_countries,
            "claim_count": diagnostics["claims"]["count"],
            "independent_like_claims": diagnostics["claims"]["independent_like_count"],
            "related_business": request.related_business,
            "keywords": keywords,
            "estimated_ipc": ipc,
        },
        "executive_summary": {
            "overall_score": overall_score,
            "score_out_of_100": score_to_100(overall_score),
            "grade": grade_for_score(overall_score),
            "opinion": overall_opinion,
            "strongest_dimension": strongest["label"] if strongest else None,
            "weakest_dimension": weakest["label"] if weakest else None,
            "key_risks": key_risks[:5],
        },
        "readiness": {
            "level": readiness_level(overall_score),
            "decision": readiness_decision(overall_score),
            "weakest_dimension": weakest,
            "required_before_filing": [action for action in next_actions if action.get("priority") == "high"],
            "diagnostic_gaps": diagnostics.get("gaps") or [],
        },
        "dimensions": dimensions,
        "score_items": score_items,
        "claim_strategy": build_claim_strategy(evaluation, diagnostics),
        "prior_art_search_plan": build_prior_art_search_plan(request, ipc, score_items),
        "filing_strategy": build_filing_strategy(evaluation, request, diagnostics),
        "next_actions": next_actions,
        "limitations": build_limitations(evaluation),
        "diagnostics": diagnostics,
        "ai_classification": ipc,
        "keywords": keywords,
        "frontend_summary": {
            "title": request.patent_name,
            "ipc": ipc["ipc"],
            "overall_grade": grade_for_score(overall_score),
            "overall_score": score_to_100(overall_score),
            "technology_score": score_for_dimension(dimensions, "technology_readiness"),
            "rights_score": score_for_dimension(dimensions, "claimability"),
            "business_score": score_for_dimension(dimensions, "business_hypothesis"),
            "filing_readiness_score": score_for_dimension(dimensions, "filing_readiness"),
            "strongest_dimension": strongest["label"] if strongest else None,
            "weakest_dimension": weakest["label"] if weakest else None,
        },
        "artifacts": {},
    }


def summarize_dimensions(score_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in score_items:
        grouped.setdefault(str(item.get("dimension") or "unknown"), []).append(item)
    dimensions = []
    for key in DIMENSION_ORDER:
        items = grouped.get(key, [])
        values = [float(item.get("score")) for item in items if isinstance(item.get("score"), (int, float))]
        average = round(sum(values) / len(values), 2) if values else 0.0
        dimensions.append({
            "key": key,
            "label": DIMENSION_LABELS[key],
            "average_score": average,
            "score_out_of_100": score_to_100(average),
            "grade": grade_for_score(average),
            "weight": DIMENSION_WEIGHTS[key],
            "item_count": len(items),
            "items": items,
        })
    return dimensions


def weighted_overall_score(dimensions: list[dict[str, Any]]) -> float:
    if not dimensions:
        return 0.0
    weighted = sum(float(item["average_score"]) * DIMENSION_WEIGHTS.get(str(item["key"]), 0.0) for item in dimensions)
    return round(weighted, 2)


def merge_next_actions(
    evaluation: dict[str, Any],
    score_items: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(priority: str, action: str, reason: str = "") -> None:
        action = action.strip()
        if not action or action in seen:
            return
        seen.add(action)
        actions.append({"priority": priority, "action": action, "reason": reason})

    for item in evaluation.get("next_actions") or []:
        if isinstance(item, dict):
            add(str(item.get("priority") or "medium"), str(item.get("action") or ""), str(item.get("reason") or ""))
    for gap in diagnostics.get("gaps") or []:
        priority = "high" if gap.get("severity") == "high" else "medium"
        add(priority, str(gap.get("message") or ""), "로컬 진단에서 확인된 보완 항목입니다.")
    low_items = sorted(score_items, key=lambda item: item.get("score", 5))[:4]
    for item in low_items:
        priority = "high" if int(item.get("score") or 3) <= 2 else "medium"
        for action in item.get("next_actions") or []:
            add(priority, str(action), f"{item.get('dimension_label')} / {item.get('item')} 보완")
    return actions[:8]


def merge_risks(
    evaluation: dict[str, Any],
    score_items: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> list[str]:
    risks: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        text = text.strip()
        if text and text not in seen:
            seen.add(text)
            risks.append(text)

    for risk in evaluation.get("key_risks") or []:
        add(str(risk))
    for gap in diagnostics.get("gaps") or []:
        if gap.get("severity") == "high":
            add(str(gap.get("message") or ""))
    for item in score_items:
        if int(item.get("score") or 3) <= 2:
            for risk in item.get("risks") or []:
                add(str(risk))
    return risks


def build_claim_strategy(evaluation: dict[str, Any], diagnostics: dict[str, Any]) -> dict[str, Any]:
    strategy = evaluation.get("claim_strategy") if isinstance(evaluation.get("claim_strategy"), dict) else {}
    return {
        "independent_claim_direction": strategy.get("independent_claim_direction") or "핵심 구성요소의 입력, 처리, 출력 관계를 독립항으로 구성하세요.",
        "dependent_claim_ideas": list_value(strategy.get("dependent_claim_ideas")) or diagnostics["claims"]["categories"],
        "avoidance_design_notes": list_value(strategy.get("avoidance_design_notes")) or ["기능적 효과만 청구하지 말고 구현 수단과 조건을 함께 한정하세요."],
        "diagnostics": diagnostics["claims"],
    }


def build_prior_art_search_plan(
    request: PreApplicationValuationRequest,
    ipc: dict[str, Any],
    score_items: list[dict[str, Any]],
) -> dict[str, Any]:
    risky_items = [item for item in score_items if item.get("item") in {"차별 포인트 설득력", "선행기술 조사 필요도"}]
    queries = [
        f"{request.patent_name} {ipc.get('description', '')}",
        f"{request.patent_name} 기존 기술 문제점",
        f"{ipc.get('ipc', '')} {request.patent_name}",
    ]
    return {
        "status": "not_performed",
        "purpose": "신규성/진보성 확정이 아니라 출원 전 리스크를 줄이기 위한 조사 계획입니다.",
        "recommended_queries": [query.strip() for query in queries if query.strip()],
        "focus_items": [{"item": item.get("item"), "score": item.get("score"), "reason": item.get("reason")} for item in risky_items],
    }


def build_filing_strategy(
    evaluation: dict[str, Any],
    request: PreApplicationValuationRequest,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    strategy = evaluation.get("filing_strategy") if isinstance(evaluation.get("filing_strategy"), dict) else {}
    countries = request.target_countries
    route = strategy.get("recommended_route")
    if not route:
        route = "국내 우선출원 후 해외/PCT 전략 재검토" if countries else "목표 시장 확정 후 국내 우선출원 여부 검토"
    return {
        "recommended_route": route,
        "country_notes": list_value(strategy.get("country_notes")) or countries,
        "target_country_count": diagnostics["strategy"]["target_country_count"],
        "has_overseas_target": diagnostics["strategy"]["has_overseas_target"],
    }


def build_limitations(evaluation: dict[str, Any]) -> list[str]:
    limitations = list_value(evaluation.get("limitations"))
    defaults = [
        "본 보고서는 출원 전 입력 텍스트 기반 사전평가이며, 법적 효력 있는 특허성 의견서가 아닙니다.",
        "실제 선행기술 검색, 변리사 검토, 시장 데이터 검증 전까지 신규성/진보성 판단은 확정할 수 없습니다.",
    ]
    for item in defaults:
        if item not in limitations:
            limitations.append(item)
    return limitations


def score_for_dimension(dimensions: list[dict[str, Any]], key: str) -> int:
    for dimension in dimensions:
        if dimension["key"] == key:
            return int(dimension["score_out_of_100"])
    return 0


def default_overall_opinion(score: float, weakest: dict[str, Any] | None) -> str:
    if weakest:
        return f"종합 준비도는 {score}/5 수준이며, {weakest['label']} 보완이 우선입니다."
    return "평가 항목이 충분하지 않아 종합 의견을 산출하지 못했습니다."


def readiness_level(score: float) -> str:
    if score >= 4.0:
        return "ready_for_filing_review"
    if score >= 3.2:
        return "promising_with_targeted_revisions"
    if score >= 2.4:
        return "needs_substantial_preparation"
    return "not_ready"


def readiness_decision(score: float) -> str:
    if score >= 4.0:
        return "출원 검토 단계로 넘길 수 있으나 선행기술 검색과 청구항 정교화가 필요합니다."
    if score >= 3.2:
        return "출원 가능성은 있으나 약한 차원을 먼저 보완한 뒤 초안화하는 것이 좋습니다."
    if score >= 2.4:
        return "아이디어 방향은 있으나 명세서/청구항/사업 근거 보강 후 재평가가 필요합니다."
    return "현 입력만으로는 출원 검토보다 아이디어 구체화가 먼저입니다."


def score_to_100(score: float | int | None) -> int:
    if not isinstance(score, (int, float)):
        return 0
    return round(max(0.0, min(100.0, float(score) * 20)))


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


def list_value(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
