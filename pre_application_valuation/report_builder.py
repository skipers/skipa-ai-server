"""Report builder for pre-application valuation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .schemas import PreApplicationValuationRequest
from .text_normalizer import (
    normalize_grade,
    normalize_condition_list,
    normalize_report_prose,
    normalize_report_sentence,
    normalize_string_list,
    normalize_task_list,
)


REPORT_SCHEMA_VERSION = "pre-application-valuation-report/v3"
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
    "technology_readiness": 0.30,
    "claimability": 0.25,
    "business_hypothesis": 0.25,
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
    score_items = [
        normalize_score_item(item)
        for item in (evaluation.get("score_items") or [])
        if isinstance(item, dict)
    ]
    dimensions = summarize_dimensions(score_items)
    overall_score = weighted_overall_score(dimensions)
    weakest = min(dimensions, key=lambda item: item["average_score"]) if dimensions else None
    strongest = max(dimensions, key=lambda item: item["average_score"]) if dimensions else None
    next_actions = merge_next_actions(evaluation, score_items, diagnostics)
    key_risks = merge_risks(evaluation, score_items, diagnostics)
    overall_opinion = normalize_report_prose(evaluation.get("overall_opinion")) or default_overall_opinion(overall_score, weakest)

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "evaluation_id": evaluation_id,
        "evaluated_at": evaluated_at.isoformat(timespec="seconds"),
        "patent_title": request.patent_name,
        "metadata": {
            "report_type": "pre_application_valuation",
            "title": "사전가치평가 보고서",
            "assessment_mode": "early_stage_lightweight_check",
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
                {"key": "valuation_assessment", "title": "사전 가치평가"},
                {"key": "commercialization_assessment", "title": "사업화 가치"},
                {"key": "readiness", "title": "출원 준비도"},
                {"key": "evaluation", "title": "평가 기준별 상세 점수"},
                {"key": "claim_strategy", "title": "권리화 전략"},
                {"key": "filing_strategy", "title": "출원 전략"},
                {"key": "filing_investment_decision", "title": "출원 투자 판단"},
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
        "valuation_assessment": build_valuation_assessment(evaluation, overall_score, dimensions, diagnostics),
        "commercialization_assessment": build_commercialization_assessment(evaluation, request, diagnostics),
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
        "filing_investment_decision": build_filing_investment_decision(evaluation, overall_score, key_risks, next_actions),
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
            "value_grade": value_grade_for_score(overall_score),
            "investment_decision": investment_decision_label(overall_score),
        },
        "artifacts": {},
    }


def summarize_dimensions(score_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in score_items:
        grouped.setdefault(str(item.get("dimension") or "unknown"), []).append(normalize_score_item(item))
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
        action = normalize_report_sentence(action)
        reason = normalize_report_sentence(reason)
        if not action or action in seen:
            return
        seen.add(action)
        actions.append({"priority": priority, "action": action, "reason": reason})

    for item in evaluation.get("next_actions") or []:
        if isinstance(item, dict):
            add(str(item.get("priority") or "medium"), str(item.get("action") or ""), str(item.get("reason") or ""))
    for gap in diagnostics.get("gaps") or []:
        priority = "high" if gap.get("severity") == "high" else "medium"
        action, reason = action_for_diagnostic_gap(gap)
        add(priority, action, reason)
    low_items = sorted(score_items, key=lambda item: item.get("score", 5))[:4]
    for item in low_items:
        priority = "high" if int(item.get("score") or 3) <= 2 else "medium"
        for action in item.get("next_actions") or []:
            add(priority, str(action), f"{item.get('dimension_label')} / {item.get('item')} 보완")
    return actions[:8]


def action_for_diagnostic_gap(gap: dict[str, Any]) -> tuple[str, str]:
    gap_type = str(gap.get("type") or "")
    if gap_type == "business":
        return (
            "주요 고객군, 구매 의사결정자, 도입 환경, 예상 과금 방식을 한 장짜리 사업 가설 표로 정리하세요.",
            "사업 적용처가 구체화되어야 현재 아이디어의 잠재 가치와 우선 보완 방향을 함께 판단할 수 있습니다.",
        )
    if gap_type == "evidence":
        return (
            "성능 개선, 비용 절감, 불량률 감소처럼 가치 판단에 직접 연결되는 정량 지표와 검증 방법을 정의하세요.",
            "정량 근거가 있어야 기술 효과가 주장 수준에 머무르지 않고 명세서와 사업 검증 자료로 연결됩니다.",
        )
    if gap_type == "description":
        return (
            "기존 방식의 한계, 핵심 구성요소, 처리 흐름, 기대 효과를 각각 별도 문단으로 보강하세요.",
            "기술 설명이 구체적일수록 독립항 구성과 실시예 작성의 불확실성이 줄어듭니다.",
        )
    if gap_type == "claims":
        return (
            "독립항 1개와 종속항 3개 이상으로 청구항 초안을 재구성하고 각 항의 보호 목적을 표시하세요.",
            "청구항 구조가 잡혀야 권리범위, 회피설계 리스크, 명세서 보강 범위를 판단할 수 있습니다.",
        )
    if gap_type == "differentiation":
        return (
            "기존 기술 대비 다른 입력 데이터, 처리 방식, 출력 결과, 운영 효과를 비교표로 정리하세요.",
            "차별 포인트가 청구항 핵심 특징으로 전환되어야 선행기술 조사와 출원 전략이 선명해집니다.",
        )
    if gap_type == "filing_strategy":
        return (
            "국내 우선출원, PCT, 개별국 출원 중 어떤 경로가 사업 일정과 맞는지 국가별 우선순위를 정하세요.",
            "목표 국가와 사업 계획이 연결되어야 다음 검토 단계에서 출원 경로와 비용 우선순위를 합리적으로 정할 수 있습니다.",
        )
    message = str(gap.get("message") or "입력에서 부족한 근거를 보강하세요.")
    return (message, "입력 진단에서 확인된 보완 항목입니다.")


def merge_risks(
    evaluation: dict[str, Any],
    score_items: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> list[str]:
    risks: list[str] = []
    seen: set[str] = set()

    def add(text: str) -> None:
        text = normalize_report_sentence(text)
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
        "independent_claim_direction": normalize_report_prose(strategy.get("independent_claim_direction"))
        or "핵심 구성요소의 입력, 처리, 출력 관계를 독립항으로 구성하세요.",
        "dependent_claim_ideas": list_value(strategy.get("dependent_claim_ideas")) or normalize_string_list(diagnostics["claims"]["categories"]),
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
        f"{request.patent_name} 유사 기술 특허",
    ]
    return {
        "status": "not_performed",
        "purpose": "신규성/진보성 확정이 아니라 출원 전 리스크를 줄이기 위한 조사 계획입니다.",
        "recommended_queries": list(dict.fromkeys(query.strip() for query in queries if query.strip())),
        "focus_items": [
            {"item": item.get("item"), "score": item.get("score"), "reason": normalize_report_prose(item.get("reason"))}
            for item in risky_items
        ],
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
        "recommended_route": normalize_report_sentence(route),
        "country_notes": list_value(strategy.get("country_notes")) or countries,
        "target_country_count": diagnostics["strategy"]["target_country_count"],
        "has_overseas_target": diagnostics["strategy"]["has_overseas_target"],
    }


def build_valuation_assessment(
    evaluation: dict[str, Any],
    overall_score: float,
    dimensions: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    assessment = evaluation.get("valuation_assessment") if isinstance(evaluation.get("valuation_assessment"), dict) else {}
    value_grade = str(assessment.get("value_grade") or value_grade_for_score(overall_score))
    value_summary = normalize_report_prose(assessment.get("value_summary"))
    if not value_summary:
        value_summary = (
            f"현재 입력 기준 예상 특허 가치는 '{value_grade}'입니다. "
            f"종합 점수는 {score_to_100(overall_score)}/100이며, 초기 사전 점검에서 가치 판단의 핵심 변수는 "
            f"{value_driver_summary(dimensions)}입니다. 이 평가는 최종 출원 판정이 아니라 보완 우선순위를 정하기 위한 기준입니다."
        )
    return {
        "value_grade": value_grade,
        "value_score": score_to_100(overall_score),
        "value_summary": normalize_report_prose(value_summary),
        "positive_value_drivers": list_value(assessment.get("positive_value_drivers"))
        or default_positive_value_drivers(dimensions),
        "value_constraints": list_value(assessment.get("value_constraints"))
        or default_value_constraints(dimensions, diagnostics),
        "evidence_needed": list_value(assessment.get("evidence_needed"))
        or [
            "기존 기술 대비 성능, 비용, 시간 개선 폭을 정량 지표로 제시합니다.",
            "주요 적용 고객과 도입 시나리오를 2개 이상 구체화합니다.",
            "핵심 구성요소별 선행기술 검색 결과와 차별 포인트를 매핑합니다.",
        ],
    }


def build_commercialization_assessment(
    evaluation: dict[str, Any],
    request: PreApplicationValuationRequest,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    assessment = evaluation.get("commercialization_assessment") if isinstance(evaluation.get("commercialization_assessment"), dict) else {}
    business_text = request.related_business or "관련 사업 입력이 부족해 적용 시장을 넓게 추정했습니다."
    return {
        "target_market": normalize_report_sentence(assessment.get("target_market") or business_text),
        "expected_use_cases": list_value(assessment.get("expected_use_cases"))
        or [
            "현재 기술 설명과 관련 사업을 연결한 대표 적용 시나리오를 정의합니다.",
            "초기 도입 고객군과 구매 의사결정자를 분리해 검증합니다.",
        ],
        "monetization_paths": list_value(assessment.get("monetization_paths"))
        or ["제품/서비스 차별화 근거", "라이선스 또는 공동사업 협상 자산", "정부과제/투자 검토용 기술 근거"],
        "market_validation_gaps": list_value(assessment.get("market_validation_gaps"))
        or [
            gap["message"]
            for gap in diagnostics.get("gaps", [])
            if gap.get("type") in {"business", "evidence"}
        ],
    }


def build_filing_investment_decision(
    evaluation: dict[str, Any],
    overall_score: float,
    key_risks: list[str],
    next_actions: list[dict[str, str]],
) -> dict[str, Any]:
    decision = evaluation.get("filing_investment_decision") if isinstance(evaluation.get("filing_investment_decision"), dict) else {}
    label = str(decision.get("decision") or investment_decision_label(overall_score))
    return {
        "decision": label,
        "rationale": normalize_report_prose(decision.get("rationale") or investment_decision_rationale(overall_score)),
        "go_conditions": normalize_condition_list(
            decision.get("go_conditions"),
            outcome="출원 진행을 검토합니다.",
        )
        or normalize_condition_list(
            ["핵심 차별 포인트를 청구항 문장으로 고정", "선행기술 검색에서 직접 충돌 문헌 여부 확인"],
            outcome="출원 진행을 검토합니다.",
        ),
        "stop_or_hold_conditions": normalize_condition_list(
            decision.get("stop_or_hold_conditions"),
            outcome="보류 또는 중단을 검토합니다.",
        )
        or normalize_condition_list(key_risks[:3], outcome="보류 또는 중단을 검토합니다."),
        "recommended_next_sprint": normalize_task_list(decision.get("recommended_next_sprint"))
        or normalize_task_list([action["action"] for action in next_actions[:3] if action.get("action")]),
    }


def build_limitations(evaluation: dict[str, Any]) -> list[str]:
    limitations = list_value(evaluation.get("limitations"))
    defaults = [
        "본 보고서는 출원 전 입력 텍스트 기반 사전평가이며, 법적 효력 있는 특허성 의견서가 아닙니다.",
        "실제 선행기술 검색, 변리사 검토, 시장 데이터 검증 전까지 신규성/진보성 판단은 확정할 수 없습니다.",
    ]
    for item in defaults:
        normalized = normalize_report_sentence(item)
        if normalized not in limitations:
            limitations.append(normalized)
    return normalize_string_list(limitations)


def value_grade_for_score(score: float) -> str:
    if score >= 4.2:
        return "high_pre_filing_value"
    if score >= 3.4:
        return "promising_value_with_validation"
    if score >= 2.6:
        return "conditional_value"
    return "low_value_until_refined"


def investment_decision_label(score: float) -> str:
    if score >= 3.8:
        return "go_to_prior_art_search_and_drafting"
    if score >= 3.0:
        return "revise_then_file"
    if score >= 2.2:
        return "hold_for_value_validation"
    return "do_not_file_yet"


def investment_decision_rationale(score: float) -> str:
    if score >= 3.8:
        return "초기 점검 기준으로 기술 구성과 권리화 방향이 비교적 선명하므로, 간이 선행기술 검색과 청구항 초안 검토로 다음 단계를 진행할 수 있습니다."
    if score >= 3.0:
        return "아이디어의 방향성은 긍정적이지만 약한 항목을 먼저 보완하면 다음 검토의 신뢰도가 크게 올라갑니다."
    if score >= 2.2:
        return "잠재 가치는 일부 보이나 시장 근거, 차별 포인트, 청구항 구체성이 부족하므로 보완 스프린트 후 다시 평가하는 편이 좋습니다."
    return "현재 입력만으로는 다음 검토 단계로 넘기기 어렵기 때문에 문제 정의, 고객 가설, 핵심 구현 방식을 먼저 재정의해야 합니다."


def value_driver_summary(dimensions: list[dict[str, Any]]) -> str:
    if not dimensions:
        return "입력 구체성"
    ordered = sorted(dimensions, key=lambda item: item.get("average_score", 0), reverse=True)
    top = ordered[0]["label"]
    bottom = ordered[-1]["label"]
    return f"강점인 {top}과 보완이 필요한 {bottom}"


def default_positive_value_drivers(dimensions: list[dict[str, Any]]) -> list[str]:
    return normalize_string_list([
        f"{dimension['label']} 점수가 {dimension['score_out_of_100']}/100으로 상대적으로 높음"
        for dimension in dimensions
        if dimension.get("average_score", 0) >= 3.2
    ][:3] or ["입력된 기술 설명을 기준으로 출원 전 검토 가능한 최소 정보가 존재합니다."])


def default_value_constraints(dimensions: list[dict[str, Any]], diagnostics: dict[str, Any]) -> list[str]:
    constraints = [
        f"{dimension['label']} 점수가 {dimension['score_out_of_100']}/100으로 낮아 가치 판단 신뢰도를 제한함"
        for dimension in dimensions
        if dimension.get("average_score", 5) < 3.2
    ]
    constraints.extend(str(gap.get("message")) for gap in diagnostics.get("gaps", [])[:3])
    seen: set[str] = set()
    result: list[str] = []
    for item in constraints:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return normalize_string_list(result[:5])


def score_for_dimension(dimensions: list[dict[str, Any]], key: str) -> int:
    for dimension in dimensions:
        if dimension["key"] == key:
            return int(dimension["score_out_of_100"])
    return 0


def default_overall_opinion(score: float, weakest: dict[str, Any] | None) -> str:
    if weakest:
        return f"초기 사전 점검 점수는 {score}/5 수준이며, {weakest['label']} 보완이 우선입니다."
    return "평가 항목이 충분하지 않아 종합 의견을 산출하지 못했습니다."


def readiness_level(score: float) -> str:
    if score >= 3.8:
        return "ready_for_filing_review"
    if score >= 3.0:
        return "promising_with_targeted_revisions"
    if score >= 2.2:
        return "needs_substantial_preparation"
    return "not_ready"


def readiness_decision(score: float) -> str:
    if score >= 3.8:
        return "초기 점검 기준으로 다음 단계인 간이 선행기술 조사와 청구항 초안 검토로 넘겨볼 수 있습니다."
    if score >= 3.0:
        return "아이디어 방향은 긍정적이며, 약한 차원을 보완하면 다음 검토 단계로 진행하기 좋습니다."
    if score >= 2.2:
        return "아이디어 방향은 있으나 명세서/청구항/사업 근거를 보강한 뒤 다시 평가하는 것이 좋습니다."
    return "현 입력만으로는 출원 검토보다 문제 정의와 기술 구성 구체화가 먼저입니다."


def score_to_100(score: float | int | None) -> int:
    if not isinstance(score, (int, float)):
        return 0
    return round(max(0.0, min(100.0, float(score) * 20)))


def grade_for_score(score: float) -> str:
    if score >= 4.5:
        return normalize_grade("S", score)
    if score >= 4.0:
        return normalize_grade("A", score)
    if score >= 3.0:
        return normalize_grade("B", score)
    if score >= 2.0:
        return normalize_grade("C", score)
    return normalize_grade("D", score)


def list_value(value: Any) -> list[str]:
    return normalize_string_list(value)


def normalize_score_item(item: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(item)
    score = normalized.get("score")
    if "grade" in normalized:
        normalized["grade"] = normalize_grade(normalized.get("grade"), score)
    normalized["reason"] = normalize_report_prose(normalized.get("reason"))
    normalized["risks"] = normalize_string_list(normalized.get("risks"))
    normalized["next_actions"] = normalize_string_list(normalized.get("next_actions"))
    return normalized
