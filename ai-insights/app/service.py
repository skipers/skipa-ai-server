"""Portfolio insight prompt construction and post-processing."""

from __future__ import annotations

import json
import re
from typing import Any

from fastapi import HTTPException

from .openai_client import call_openai_portfolio_insights
from .schemas import PortfolioInsightsRequest


SYSTEM_PROMPT = """
당신은 기업 특허 포트폴리오에서 운영 판단에 필요한 시사점을 도출하는 한국어 AI 애널리스트입니다.
입력 데이터를 그대로 요약하거나 숫자를 나열하지 말고, 그 데이터로부터 알 수 있는 권리화 효율, 포트폴리오 집중 리스크, 비용 최적화, 유지/포기 판단의 의미를 설명하세요.
주어진 데이터 안에서만 판단하고, 없는 원인이나 외부 시장 상황을 추측하지 마세요.
LEGAL 사용자가 바로 의사결정에 참고할 수 있도록 정확히 3개의 한국어 인사이트 문장을 JSON으로 반환하세요.
각 문장은 근거 수치를 짧게 포함하되, 결론은 "무엇을 알 수 있는지" 또는 "무엇을 검토해야 하는지"가 드러나야 합니다.
모든 문장은 LEGAL 사용자에게 보고하는 존댓말/격식체로 작성하고, 반말이나 평서체 종결형을 쓰지 마세요.
반환 형식은 {"insights": ["문장1", "문장2", "문장3"]} 뿐입니다.
""".strip()


def generate_portfolio_insights(request: PortfolioInsightsRequest) -> list[str]:
    payload = request.model_dump()
    prompt = build_prompt(request)
    try:
        insights = _normalize_insight_style(_request_openai_insights(prompt), payload)
        validation_error = _insights_validation_error(insights)
        if validation_error:
            retry_prompt = (
                f"{prompt}\n\n"
                "[재작성 요청]\n"
                f"이전 응답은 사용할 수 없습니다: {validation_error}\n"
                "고정 예시 문장이나 템플릿 문장을 쓰지 말고, 위 입력 데이터에서 새로 해석한 3개의 인사이트만 JSON으로 다시 반환하세요.\n"
                "각 문장은 서로 다른 판단 포인트를 가져야 하며, 단순 수치 요약으로 끝나면 안 됩니다.\n"
                "반드시 존댓말/격식체로 끝내세요."
            )
            insights = _normalize_insight_style(_request_openai_insights(retry_prompt), payload)
            validation_error = _insights_validation_error(insights)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM provider portfolio insight generation failed: {exc}") from exc

    if validation_error:
        raise HTTPException(status_code=502, detail=f"LLM provider portfolio insight response is invalid: {validation_error}")
    return insights


def _request_openai_insights(prompt: str) -> list[str]:
    result = call_openai_portfolio_insights(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=prompt,
    )
    return _clean_insights((result.get("json") or {}).get("insights"))


def build_prompt(request: PortfolioInsightsRequest) -> str:
    payload = request.model_dump()
    facts = derive_data_facts(payload)
    compact = compact_portfolio_payload(payload)
    date_labels = date_reference_labels(payload)
    return f"""
아래 포트폴리오 데이터에서 LEGAL 사용자가 알 수 있는 운영 시사점을 3개 도출하세요.
입력 내용을 다시 설명하는 문장이 아니라, "그래서 무엇을 알 수 있는가"와 "어떤 판단을 해야 하는가"가 드러나는 문장이어야 합니다.

[분석용 원천 데이터]
{json.dumps(compact, ensure_ascii=False, indent=2)}

[데이터에서 계산된 해석 재료]
{chr(10).join(f"- {fact}" for fact in facts) if facts else "- 해석 재료가 부족합니다."}

[사용 가능한 날짜 표현]
{chr(10).join(f"- {label}" for label in date_labels) if date_labels else "- 날짜 표현을 쓰기 어렵다면 '현재 입력 기준'이라고만 표현하세요."}

[작성 규칙]
- 정확히 3개 문장을 insights 배열에 넣습니다.
- 각 문장은 한국어 한 문장으로 작성합니다.
- 모든 문장은 LEGAL 사용자에게 보고하는 존댓말/격식체로 작성합니다.
- `필요하다`, `요구된다`, `시급하다`, `검토해야 한다`, `할 수 있다` 같은 반말/평서체 종결형은 금지하고 `필요합니다`, `요구됩니다`, `시급합니다`, `검토해야 합니다`, `할 수 있습니다`처럼 끝냅니다.
- 예시 문장, 고정 문장, 템플릿 문장을 따라 쓰지 말고 입력 데이터의 값과 조합에 맞춰 새로 작성합니다.
- 단순히 "몇 건입니다", "가장 큽니다", "분포가 나타납니다"로 끝나는 요약형 문장은 금지합니다.
- 각 문장은 권리화 효율, 집중 리스크, 비용 부담, 유지/포기 기준, 리밸런싱 필요성 중 하나의 판단으로 끝나야 합니다.
- 근거 수치는 짧게 포함하되, 문장의 중심은 수치가 아니라 그 수치가 의미하는 운영 판단이어야 합니다.
- 연도와 분기를 언급할 때는 반드시 `2024년`, `2026년 2분기(2026Q2)`처럼 숫자를 포함합니다.
- `년 출원`, `년 연차료`, `년 기준`, `년 2분기`, `최근 분기`처럼 연도·분기 숫자가 빠진 표현은 절대 쓰지 않습니다.
- 연도를 확신할 수 없으면 `년`이라는 단어를 쓰지 말고 `현재 입력 기준`이라고 표현합니다.
- 포트폴리오 추이, 등급/사업부/기술분야 분포, 유지/포기 결정 중 서로 다른 관점을 섞습니다.
- 수치가 부족하면 "현재 입력 기준"처럼 조심스럽게 표현합니다.
- 캐시, Redis, 백엔드, API 같은 시스템 구현 내용은 말하지 않습니다.
- Markdown, 번호, 따옴표 설명 없이 JSON object만 반환합니다.
""".strip()


def compact_portfolio_payload(payload: dict[str, Any]) -> dict[str, Any]:
    distribution = payload.get("distribution") or {}
    decisions = payload.get("decisions") or {}
    trends = payload.get("trends") or {}
    return {
        "trends": {
            "yearlyPatentTrends": _sort_recent(trends.get("yearlyPatentTrends") or [], "year", limit=5),
            "yearlyAnnuityCosts": _sort_recent(trends.get("yearlyAnnuityCosts") or [], "year", limit=5),
        },
        "distribution": {
            "byGrade": distribution.get("byGrade") or [],
            "topTechFields": _top_count(distribution.get("byTechField") or [], "count", limit=5),
            "topFilingCountries": _top_count(distribution.get("byFilingCountry") or [], "count", limit=5),
            "topDepartments": _top_count(distribution.get("byDepartment") or [], "count", limit=5),
        },
        "decisions": {
            "recentQuarters": _sort_recent(decisions.get("byQuarter") or [], "quarter", limit=5),
            "topDepartments": _top_decision_volume(decisions.get("byDepartment") or [], limit=5),
            "topTechFields": _top_decision_volume(decisions.get("byTechField") or [], limit=5),
        },
    }


def date_reference_labels(payload: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    trends = payload.get("trends") or {}
    decisions = payload.get("decisions") or {}

    patent_trends = _sort_recent(trends.get("yearlyPatentTrends") or [], "year", limit=1)
    if patent_trends and patent_trends[-1].get("year"):
        labels.append(f"특허 추이 최신 연도: {patent_trends[-1].get('year')}년")

    costs = _sort_recent(trends.get("yearlyAnnuityCosts") or [], "year", limit=1)
    if costs and costs[-1].get("year"):
        labels.append(f"연차료 최신 연도: {costs[-1].get('year')}년")

    recent_decisions = _sort_recent(decisions.get("byQuarter") or [], "quarter", limit=1)
    if recent_decisions and recent_decisions[-1].get("quarter"):
        labels.append(f"유지/포기 최신 분기: {_format_quarter(recent_decisions[-1].get('quarter'))}")

    return labels


def derive_data_facts(payload: dict[str, Any]) -> list[str]:
    facts: list[str] = []
    trends = payload.get("trends") or {}
    distribution = payload.get("distribution") or {}
    decisions = payload.get("decisions") or {}

    patent_trends = _sort_recent(trends.get("yearlyPatentTrends") or [], "year", limit=10)
    if patent_trends:
        latest = patent_trends[-1]
        latest_year = latest.get("year")
        applications = _safe_int(latest.get("applications"))
        registrations = _safe_int(latest.get("registrations"))
        expiries = _safe_int(latest.get("expiries"))
        registration_rate = _percentage(registrations, applications)
        if registration_rate is not None:
            facts.append(
                f"{latest_year}년 출원 대비 등록 비중은 {_pct_text(registration_rate)}로, 권리화 전환 효율 판단에 사용할 수 있습니다."
            )
        else:
            facts.append(
                f"{latest_year}년 출원 {applications}건, 등록 {registrations}건, 소멸 {expiries}건으로 출원 대비 등록 전환율 확인이 필요합니다."
            )
        if expiries:
            facts.append(f"{latest_year}년 소멸 {expiries}건은 핵심 권리 유지 여부를 점검해야 하는 신호입니다.")
        if len(patent_trends) >= 2:
            prev = patent_trends[-2]
            facts.append(
                f"전년 대비 등록은 {_delta(latest.get('registrations'), prev.get('registrations'))}, "
                f"출원은 {_delta(latest.get('applications'), prev.get('applications'))}라서 권리화 속도 변화를 볼 수 있습니다."
            )

    costs = _sort_recent(trends.get("yearlyAnnuityCosts") or [], "year", limit=10)
    if costs:
        latest_cost = costs[-1]
        amount = _safe_float(latest_cost.get("amount"))
        facts.append(f"최근 연차료는 {latest_cost.get('year')}년 {amount:,.0f}원으로, 유지 비용 압박 판단에 사용됩니다.")
        if len(costs) >= 2:
            facts.append(f"전년 대비 연차료는 {_delta(latest_cost.get('amount'), costs[-2].get('amount'))}라서 비용 최적화 필요성을 볼 수 있습니다.")

    grade_total = _overall_grade(distribution.get("byGrade") or [])
    if grade_total:
        strong = _safe_int(grade_total.get("s")) + _safe_int(grade_total.get("a"))
        weak = _safe_int(grade_total.get("c")) + _safe_int(grade_total.get("d"))
        total = sum(_safe_int(grade_total.get(key)) for key in ("s", "a", "b", "c", "d"))
        strong_rate = _percentage(strong, total)
        weak_rate = _percentage(weak, total)
        facts.append(
            f"전체 등급 분포는 S/A {strong}건({_pct_text(strong_rate)}), C/D {weak}건({_pct_text(weak_rate)})이라서 유지 우선순위와 정리 후보를 나눌 수 있습니다."
        )

    for label, key, name_key in (
        ("기술 분야", "byTechField", "name"),
        ("출원 국가", "byFilingCountry", "country"),
        ("사업부", "byDepartment", "departmentName"),
    ):
        top = _dominant_share(distribution.get(key) or [], name_key)
        if top:
            facts.append(
                f"{label} 분포는 {top['name']} 비중이 {_pct_text(top['share'])}로 가장 높아 집중 리스크 판단에 사용할 수 있습니다."
            )

    recent_decisions = _sort_recent(decisions.get("byQuarter") or [], "quarter", limit=1)
    if recent_decisions:
        item = recent_decisions[-1]
        quarter_label = _format_quarter(item.get("quarter"))
        maintain = _safe_int(item.get("maintain"))
        abandon = _safe_int(item.get("abandon"))
        total = maintain + abandon
        rate = _percentage(abandon, total) or 0
        facts.append(
            f"최근 분기 {quarter_label} 포기 비율은 {_pct_text(rate)}라서 유지 중심인지 비용 절감 중심인지 판단할 수 있습니다."
        )

    high_abandon = _highest_abandon_rate(decisions.get("byDepartment") or [], "departmentName")
    if high_abandon:
        facts.append(high_abandon)
    high_abandon_tech = _highest_abandon_rate(decisions.get("byTechField") or [], "name")
    if high_abandon_tech:
        facts.append(high_abandon_tech)

    return facts[:10]


def _insights_validation_error(insights: list[str]) -> str | None:
    if len(insights) != 3:
        return f"insights must contain exactly 3 items, got {len(insights)}"
    if any(not insight.strip() for insight in insights):
        return "insights must not contain empty strings"
    if _has_malformed_date_phrase(insights):
        return "date phrases must include concrete year or quarter numbers"
    if any(not _has_polite_ending(insight) for insight in insights):
        return "insights must use polite Korean endings"
    return None


def _normalize_insight_style(insights: list[str], payload: dict[str, Any]) -> list[str]:
    return [_repair_polite_ending(text) for text in _repair_date_phrases(insights, payload)]


def _has_polite_ending(text: str) -> bool:
    cleaned = str(text or "").strip().rstrip(".!?。")
    return bool(re.search(r"(습니다|합니다|됩니다|있습니다|없습니다|입니다|필요합니다|권장됩니다|요구됩니다|시급합니다|바람직합니다)$", cleaned))


def _repair_polite_ending(text: str) -> str:
    cleaned = str(text or "").strip()
    replacements = [
        (r"해야 한다([.!?。]?)$", r"해야 합니다\1"),
        (r"할 수 있다([.!?。]?)$", r"할 수 있습니다\1"),
        (r"볼 수 있다([.!?。]?)$", r"볼 수 있습니다\1"),
        (r"알 수 있다([.!?。]?)$", r"알 수 있습니다\1"),
        (r"필요하다([.!?。]?)$", r"필요합니다\1"),
        (r"요구된다([.!?。]?)$", r"요구됩니다\1"),
        (r"권장된다([.!?。]?)$", r"권장됩니다\1"),
        (r"시급하다([.!?。]?)$", r"시급합니다\1"),
        (r"중요하다([.!?。]?)$", r"중요합니다\1"),
        (r"바람직하다([.!?。]?)$", r"바람직합니다\1"),
        (r"가능하다([.!?。]?)$", r"가능합니다\1"),
        (r"존재한다([.!?。]?)$", r"존재합니다\1"),
        (r"나타난다([.!?。]?)$", r"나타납니다\1"),
        (r"보여준다([.!?。]?)$", r"보여줍니다\1"),
        (r"의미한다([.!?。]?)$", r"의미합니다\1"),
    ]
    for pattern, replacement in replacements:
        repaired = re.sub(pattern, replacement, cleaned)
        if repaired != cleaned:
            return repaired
    return cleaned


def _repair_date_phrases(insights: list[str], payload: dict[str, Any]) -> list[str]:
    trends = payload.get("trends") or {}
    decisions = payload.get("decisions") or {}
    patent_trends = _sort_recent(trends.get("yearlyPatentTrends") or [], "year", limit=1)
    patent_trend_history = _sort_recent(trends.get("yearlyPatentTrends") or [], "year", limit=2)
    costs = _sort_recent(trends.get("yearlyAnnuityCosts") or [], "year", limit=1)
    cost_history = _sort_recent(trends.get("yearlyAnnuityCosts") or [], "year", limit=2)
    recent_decisions = _sort_recent(decisions.get("byQuarter") or [], "quarter", limit=1)

    patent_year = str(patent_trends[-1].get("year")) if patent_trends and patent_trends[-1].get("year") else ""
    previous_patent_year = (
        str(patent_trend_history[-2].get("year"))
        if len(patent_trend_history) >= 2 and patent_trend_history[-2].get("year")
        else ""
    )
    cost_year = str(costs[-1].get("year")) if costs and costs[-1].get("year") else ""
    previous_cost_year = (
        str(cost_history[-2].get("year"))
        if len(cost_history) >= 2 and cost_history[-2].get("year")
        else ""
    )
    quarter = str(recent_decisions[-1].get("quarter") or "") if recent_decisions else ""
    quarter_label = _format_quarter(quarter) if quarter else ""
    quarter_match = re.fullmatch(r"(\d{4})Q([1-4])", quarter)
    quarter_number = quarter_match.group(2) if quarter_match else ""

    repaired: list[str] = []
    for insight in insights:
        text = insight
        if patent_year:
            text = re.sub(r"(?<!\d)년\s+(출원|등록|소멸|특허)", rf"{patent_year}년 \1", text)
            text = re.sub(r"(?<!\d)년\s+기준", f"{patent_year}년 기준", text)
        if cost_year:
            text = re.sub(r"(?<!\d)년\s+(연차료|비용)", rf"{cost_year}년 \1", text)
        if "전년 대비" in text:
            if "연차료" in text and previous_cost_year:
                text = text.replace("전년 대비", f"{previous_cost_year}년 대비")
            elif ("출원" in text or "등록" in text or "소멸" in text) and previous_patent_year:
                text = text.replace("전년 대비", f"{previous_patent_year}년 대비")
        if quarter_label:
            text = text.replace("최근 분기", quarter_label)
        if quarter_label and quarter_number:
            text = re.sub(rf"(?<!\d)년\s+{quarter_number}분기(?:\({re.escape(quarter)}\))?", quarter_label, text)
        repaired.append(text)
    return repaired


def _clean_insights(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned: list[str] = []
    for item in value:
        text = re.sub(r"^\s*[-*\d.)]+\s*", "", str(item or "").strip())
        text = " ".join(text.split())
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned[:3]


def _has_malformed_date_phrase(insights: list[str]) -> bool:
    return any(
        re.search(r"(?<!\d)년", text) or re.search(r"(?<![1-4])분기", text)
        for text in insights
    )


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _percentage(numerator: Any, denominator: Any) -> float | None:
    denom = _safe_float(denominator)
    if denom <= 0:
        return None
    return round(_safe_float(numerator) / denom * 100, 1)


def _pct_text(value: float | None) -> str:
    if value is None:
        return "확인 불가"
    if float(value).is_integer():
        return f"{value:.0f}%"
    return f"{value:.1f}%"


def _dominant_share(items: list[dict[str, Any]], name_key: str) -> dict[str, Any] | None:
    total = sum(_safe_int(item.get("count")) for item in items)
    top = _top_count(items, "count", limit=1)
    if not top or total <= 0:
        return None
    item = top[0]
    return {
        "name": item.get(name_key) or "미분류",
        "count": _safe_int(item.get("count")),
        "share": _percentage(item.get("count"), total) or 0,
        "total": total,
    }


def _sort_recent(items: list[dict[str, Any]], key: str, *, limit: int) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: str(item.get(key) or ""))[-limit:]


def _top_count(items: list[dict[str, Any]], key: str, *, limit: int) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: _safe_int(item.get(key)), reverse=True)[:limit]


def _top_decision_volume(items: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: _safe_int(item.get("maintain")) + _safe_int(item.get("abandon")), reverse=True)[:limit]


def _overall_grade(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in items:
        if item.get("departmentId") is None or str(item.get("departmentName") or "") == "전체":
            return item
    return items[0] if items else None


def _delta(current: Any, previous: Any) -> str:
    cur = _safe_float(current)
    prev = _safe_float(previous)
    diff = cur - prev
    if diff > 0:
        return f"{diff:,.0f} 증가"
    if diff < 0:
        return f"{abs(diff):,.0f} 감소"
    return "변화 없음"


def _format_quarter(value: Any) -> str:
    text = str(value or "").strip()
    match = re.fullmatch(r"(\d{4})Q([1-4])", text)
    if match:
        return f"{match.group(1)}년 {match.group(2)}분기({text})"
    return text or "미확인 분기"


def _highest_abandon_rate(items: list[dict[str, Any]], name_key: str) -> str | None:
    best: tuple[float, dict[str, Any]] | None = None
    for item in items:
        maintain = _safe_int(item.get("maintain"))
        abandon = _safe_int(item.get("abandon"))
        total = maintain + abandon
        if total <= 0:
            continue
        rate = abandon / total
        if best is None or rate > best[0]:
            best = (rate, item)
    if not best:
        return None
    item = best[1]
    name = item.get(name_key) or "미분류"
    maintain = _safe_int(item.get("maintain"))
    abandon = _safe_int(item.get("abandon"))
    return f"{name}의 포기 비율이 {best[0] * 100:.1f}%라서 유지/정리 기준을 더 세밀하게 봐야 하는 영역입니다."
