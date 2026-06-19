"""서비스 화면용 재평가 보고서 JSON 빌더입니다."""

from __future__ import annotations

from datetime import date, datetime
import json
import re
from typing import Any

from core.report_text import normalize_local_source_markers, normalize_report_prose, normalize_report_sentence


REPORT_SCHEMA_VERSION = "patent-valuation-report/v4-frontend-compatible"
DIMENSION_ORDER = ["기술성", "권리성", "시장성", "사업성"]
SIMILAR_PATENT_MAX_AGE_YEARS = 20
KIPRIS_PLUS_URL = "https://plus.kipris.or.kr/portal/main.do"
KOSIS_URL = "https://kosis.kr/index/index.do"

TARGET_EVALUATION_ITEMS: tuple[dict[str, Any], ...] = (
    {
        "dim": "기술성",
        "item": "차별성 및 파급성",
        "sources": ("차별성", "파급 및 활용성"),
    },
    {
        "dim": "기술성",
        "item": "혁신성 및 개척성",
        "sources": ("혁신성", "기술의 개척성"),
    },
    {
        "dim": "기술성",
        "item": "대체기술 및 경쟁성",
        "sources": ("대체기술", "기술 경쟁성"),
    },
    {
        "dim": "기술성",
        "item": "기술 모방 및 회피설계 난이도",
        "sources": ("기술적 모방 난이도", "기술의 복잡성"),
    },
    {"dim": "권리성", "item": "IP 원천성", "sources": ("IP 원천성",)},
    {"dim": "권리성", "item": "권리의 충실성", "sources": ("권리의 충실성",)},
    {"dim": "권리성", "item": "권리행사 제한 가능성", "sources": ("권리행사 제한 가능성",)},
    {"dim": "권리성", "item": "무효 가능성", "sources": ("무효 가능성",)},
    {"dim": "권리성", "item": "회피설계 용이성", "sources": ("회피설계 용이성",)},
    {"dim": "권리성", "item": "권리범위 적절성", "sources": ("권리범위 적절성",)},
    {"dim": "권리성", "item": "권리의 구성요소", "sources": ("권리의 구성요소",)},
    {"dim": "권리성", "item": "권리의 추상성", "sources": ("권리의 추상성",)},
    {
        "dim": "권리성",
        "item": "IP 포트폴리오 구축 적절성",
        "sources": ("IP 포트폴리오 구축 적절성",),
    },
    {
        "dim": "권리성",
        "item": "침해 발견 및 입증 용이성",
        "sources": ("침해 발견 및 입증 용이성",),
    },
    {"dim": "시장성", "item": "특허출원 활성도", "sources": ("특허출원 활성도",)},
    {"dim": "시장성", "item": "고객에 미치는 영향", "sources": ("고객에 미치는 영향",)},
    {"dim": "사업성", "item": "매출 성장성", "sources": ("매출 성장성",)},
)

REPORT_ITEM_STRATEGY: dict[str, str] = {
    "차별성 및 파급성": "hybrid",
    "혁신성 및 개척성": "hybrid",
    "대체기술 및 경쟁성": "web_search",
    "기술 모방 및 회피설계 난이도": "claims_only",
    "IP 원천성": "web_search",
    "권리의 충실성": "claims_only",
    "권리행사 제한 가능성": "claims_only",
    "무효 가능성": "claims_only",
    "회피설계 용이성": "claims_only",
    "권리범위 적절성": "claims_only",
    "권리의 구성요소": "claims_only",
    "권리의 추상성": "claims_only",
    "IP 포트폴리오 구축 적절성": "claims_only",
    "침해 발견 및 입증 용이성": "claims_only",
    "특허출원 활성도": "web_search",
    "고객에 미치는 영향": "hybrid",
    "매출 성장성": "web_search",
}


# ─────────────────────────────────────────────
# 등급 / 위험도 매핑
# ─────────────────────────────────────────────

_GRADE_STEPS: list[tuple[float, str]] = [
    (4.5, "S"),
    (4.0, "A"),
    (3.0, "B"),
    (2.0, "C"),
    (0.0, "D"),
]

_RISK_STEPS: list[tuple[float, str]] = [
    (3.5, "low"),
    (2.5, "medium"),
    (0.0, "high"),
]


def _to_grade(score: float) -> str:
    for threshold, grade in _GRADE_STEPS:
        if score >= threshold:
            return grade
    return "D"


def _to_risk(score: float) -> str:
    for threshold, level in _RISK_STEPS:
        if score >= threshold:
            return level
    return "high"


def _score_to_100(score: float | int | None) -> int | None:
    """1~5점 평균을 기존 HTML 보고서의 0~100점 척도로 변환합니다."""
    if not isinstance(score, (int, float)):
        return None
    return round(max(0.0, min(100.0, float(score) / 5 * 100)))


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value if str(item).strip())
    return re.sub(r"\s+", " ", str(value)).strip()


def _remove_estimation_marker(value: Any) -> str:
    text = _clean_text(value)
    text = re.sub(r"\s*\(추정\)\s*", " ", text)
    text = re.sub(r"\s*추정\)\s*", " ", text)
    return _clean_text(text)


def _short_text(value: Any, limit: int = 50) -> str:
    """화면 표의 판단 요지에 맞게 짧고 끊기지 않는 문장을 만듭니다."""
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    for marker in ("다.", "니다.", "임.", "음.", ".", "이며,", ","):
        pos = text.find(marker)
        end = pos + len(marker)
        if 15 <= end <= limit:
            return text[:end]
    return text[:limit].rstrip()


def _ensure_sentence(value: Any) -> str:
    return normalize_report_sentence(value)


def _dimension_summary(dim: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return f"{dim} 평가 항목의 근거 보강이 필요합니다."

    scored = [item for item in items if isinstance(item.get("score"), (int, float))]
    values = [float(item["score"]) for item in scored]
    average = round(sum(values) / len(values), 2) if values else 0.0
    strongest = max(scored, key=lambda item: item.get("score", 0), default=None)
    weakest = min(scored, key=lambda item: item.get("score", 0), default=None)

    def item_name(item: dict[str, Any] | None) -> str:
        return str((item or {}).get("name") or (item or {}).get("item") or "").strip()

    def evidence(item: dict[str, Any] | None, limit: int = 140) -> str:
        text = _clean_text(
            (item or {}).get("judgment_summary")
            or (item or {}).get("summary")
            or (item or {}).get("judgment_basis")
            or (item or {}).get("basis")
            or (item or {}).get("reason")
        )
        text = _short_text(text, limit) if text else ""
        return _ensure_sentence(text)

    def score_phrase(value: int) -> str:
        if value >= 80:
            return "우수한 편"
        if value >= 70:
            return "양호한 편"
        if value >= 60:
            return "보통 수준"
        return "보완 검토가 필요한 수준"

    intro_by_dim = {
        "기술성": "기술 구현의 차별성과 파급 가능성은 확인되지만 대체기술과 실제 구현 성능을 함께 보아야 하는 상태",
        "권리성": "등록 상태와 청구항 구성을 출발점으로 권리 범위·무효 가능성·포트폴리오 근거를 함께 확인해야 하는 상태",
        "시장성": "관련 출원 활성도와 고객 효익을 함께 보며 시장 수요의 강약을 균형 있게 판단해야 하는 상태",
        "사업성": "매출 성장성과 사내 적용 가능성을 중심으로 실제 사업화 여지를 판단할 수 있는 상태",
    }

    score_100 = _score_to_100(average)
    intro = intro_by_dim.get(dim, "세부 평가 항목의 강점과 보완점을 함께 검토해야 하는 상태")
    sentences = [
        f"{dim}은 {score_100}점으로 {score_phrase(score_100)}이며, {intro}입니다."
    ]
    if strongest:
        name = item_name(strongest)
        basis = evidence(strongest)
        if name and basis:
            sentences.append(f"상대적으로 강한 항목은 {name}이며, {basis}")
    if weakest and weakest is not strongest:
        name = item_name(weakest)
        basis = evidence(weakest)
        if name and basis:
            sentences.append(f"보완이 필요한 항목은 {name}으로, {basis}")
    return " ".join(sentences[:3])


def _market_business_summary(dimensions: dict[str, dict[str, Any]]) -> str:
    market_items = (dimensions.get("시장성") or {}).get("items") or []
    business_items = (dimensions.get("사업성") or {}).get("items") or []
    items = [*market_items, *business_items]
    if not items:
        return "시장성 및 사업성 평가 항목의 근거 보강이 필요합니다."

    patent_activity = next((item for item in items if item.get("name") == "특허출원 활성도"), None)
    customer = next((item for item in items if item.get("name") == "고객에 미치는 영향"), None)
    revenue = next((item for item in items if item.get("name") == "매출 성장성"), None)

    if patent_activity and customer and revenue:
        return (
            "시장성 및 사업성은 관련 출원 추세, 고객 효익, 매출 성장성을 함께 놓고 판단해야 합니다. "
            f"{_dimension_summary('시장성', market_items)} "
            f"{_dimension_summary('사업성', business_items)}"
        )

    parts = []
    if patent_activity:
        parts.append("특허출원 활성도 근거")
    if customer:
        parts.append("고객 영향")
    if revenue:
        parts.append("매출 성장성")
    if parts:
        return f"{', '.join(parts)}를 종합하면 시장성 및 사업성은 추가 근거와 함께 판단해야 합니다."
    return _dimension_summary("시장성 및 사업성", items)


def _parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip().replace(".", "-")
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _patent_expiration(application_date: Any) -> date | None:
    """대한민국 특허의 일반적인 출원일 기준 20년 만료일을 계산합니다."""
    parsed = _parse_iso_date(application_date)
    if not parsed:
        return None
    try:
        return parsed.replace(year=parsed.year + 20)
    except ValueError:
        return parsed.replace(year=parsed.year + 20, day=28)


def _remaining_years(expiration_date: date | None, evaluated_on: date) -> float | None:
    if not expiration_date:
        return None
    return round(max(0, (expiration_date - evaluated_on).days) / 365.25, 1)


def _confidence_for_score(score: dict[str, Any]) -> tuple[str, str]:
    """명시적 확신도가 없을 때 산출 방식과 근거 존재 여부로 표시값을 보완합니다."""
    explicit = str(score.get("confidence") or "").strip()
    if explicit:
        return explicit, "provided"
    method = str(score.get("method") or "")
    if method.startswith("auto"):
        return "높음", "inferred_from_rule_based_method"
    if score.get("sources"):
        return "보통", "inferred_from_llm_sources"
    return "낮음", "inferred_from_missing_supporting_sources"


def _score_summary(score: dict[str, Any]) -> str:
    return str(score.get("summary") or score.get("basis") or score.get("reason") or "")


def _score_basis(score: dict[str, Any]) -> str:
    return str(score.get("reason") or score.get("basis") or "")


# ─────────────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────────────

def _dim_stats(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """점수 목록을 차원별로 집계해 {dim: {average_score, grade, item_count, items}} 반환."""
    by_dim: dict[str, list[dict]] = {}
    for s in scores:
        dim = s.get("dim") or "unknown"
        by_dim.setdefault(dim, []).append(s)

    result: dict[str, Any] = {}
    for dim in [*DIMENSION_ORDER, *sorted(set(by_dim) - set(DIMENSION_ORDER))]:
        items = by_dim.get(dim, [])
        if not items:
            continue
        vals = [float(s["score"]) for s in items if isinstance(s.get("score"), (int, float))]
        avg = round(sum(vals) / len(vals), 2) if vals else 0.0
        result[dim] = {
            "average_score": avg,
            "score_out_of_100": _score_to_100(avg),
            "grade": _to_grade(avg),
            "item_count": len(items),
        }
    return result


def _dim_items(scores: list[dict[str, Any]]) -> dict[str, list[dict]]:
    """점수 목록을 차원별 항목 리스트로 분류."""
    by_dim: dict[str, list[dict]] = {}
    for s in scores:
        dim = s.get("dim") or "unknown"
        by_dim.setdefault(dim, []).append(s)
    return by_dim


def _dedup_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result = []
    for src in sources:
        if not isinstance(src, dict):
            continue
        key = str(src.get("url") or src.get("patent_no") or src.get("title") or src.get("source") or "")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(src)
    return result


def _collect_all_sources(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for s in scores:
        sources.extend(s.get("sources") or [])
    return _dedup_sources(sources)


def _merge_methods(items: list[dict[str, Any]]) -> str:
    methods = [str(item.get("method") or "").strip() for item in items if str(item.get("method") or "").strip()]
    unique = list(dict.fromkeys(methods))
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    if all(method.startswith("auto") for method in unique):
        return "auto"
    return "mixed"


def _strategy_for_item(item_name: Any) -> str | None:
    return REPORT_ITEM_STRATEGY.get(str(item_name or "").strip())


def _merge_strategy(target: dict[str, Any], items: list[dict[str, Any]]) -> str | None:
    for item in items:
        strategy = str(item.get("strategy") or "").strip()
        if strategy:
            return strategy
    return _strategy_for_item(target.get("item"))


def _merge_confidence(items: list[dict[str, Any]]) -> str:
    order = {"낮음": 0, "보통": 1, "높음": 2}
    confidences = [_confidence_for_score(item)[0] for item in items]
    if not confidences:
        return ""
    return min(confidences, key=lambda value: order.get(value, 1))


def _merge_score_items(target: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(item["score"]) for item in items if isinstance(item.get("score"), (int, float))]
    score = round(sum(values) / len(values), 2) if values else None
    summaries = [normalize_report_sentence(_score_summary(item)) for item in items if _clean_text(_score_summary(item))]
    bases = list(dict.fromkeys(normalize_report_prose(_score_basis(item)) for item in items if _clean_text(_score_basis(item))))
    merged_sources = _collect_all_sources(items)
    if target["item"] == "매출 성장성" and not merged_sources:
        merged_sources = [
            {
                "source": "KOSIS",
                "title": "KOSIS 국가통계포털",
                "url": KOSIS_URL,
            }
        ]
    merged = {
        "item": target["item"],
        "dim": target["dim"],
        "score": score,
        "summary": normalize_report_sentence(_short_text(" / ".join(summaries), 90)) if summaries else "",
        "basis": normalize_report_prose(" ".join(bases)),
        "reason": normalize_report_prose(" ".join(bases)),
        "sources": merged_sources,
        "method": _merge_methods(items),
        "strategy": _merge_strategy(target, items),
        "confidence": _merge_confidence(items),
        "merged_from": [item.get("item") for item in items if item.get("item")],
    }
    for key in ("kipris_evidence", "evidence"):
        value = next((item.get(key) for item in items if item.get(key)), None)
        if value:
            merged[key] = value
    return merged


def _canonical_evaluation_scores(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Report-facing scores normalized to the approved evaluation item set."""
    by_item: dict[str, list[dict[str, Any]]] = {}
    for score in scores:
        item_name = str(score.get("item") or "").strip()
        if not item_name:
            continue
        by_item.setdefault(item_name, []).append(score)

    normalized: list[dict[str, Any]] = []
    for target in TARGET_EVALUATION_ITEMS:
        source_items: list[dict[str, Any]] = []
        seen_source_ids: set[int] = set()
        for item in by_item.get(target["item"], []):
            source_items.append(item)
            seen_source_ids.add(id(item))
        for source_name in target["sources"]:
            for item in by_item.get(source_name, []):
                if id(item) in seen_source_ids:
                    continue
                source_items.append(item)
                seen_source_ids.add(id(item))
        if not source_items:
            continue
        normalized.append(_merge_score_items(target, source_items))
    return normalized


def _years_from_similar_analysis(similar_analysis: dict[str, Any] | None) -> list[int]:
    years: list[int] = []
    if not similar_analysis:
        return years
    for patent in similar_analysis.get("similar_patents") or []:
        if not isinstance(patent, dict):
            continue
        detail = patent.get("source_detail") if isinstance(patent.get("source_detail"), dict) else {}
        raw = detail.get("application_date") or patent.get("application_year") or patent.get("application_date") or ""
        year = _application_year(raw)
        if year is not None:
            years.append(year)
    return years


def _growth_rate_from_year_counts(year_counts: dict[int, int]) -> float | None:
    nonzero = [(year, count) for year, count in sorted(year_counts.items()) if count > 0]
    if len(nonzero) < 2:
        return None
    first = nonzero[0][1]
    last = nonzero[-1][1]
    if first <= 0:
        return None
    return round(((last - first) / first) * 100, 2)


def _filing_activity_score(rate: float | None, sample_count: int) -> int:
    if rate is None:
        return 3 if sample_count else 3
    if rate >= 80:
        return 5
    if rate >= 20:
        return 4
    if rate >= 0:
        return 3
    if rate >= -20:
        return 2
    return 1


def _enrich_canonical_filing_activity(
    scores: list[dict[str, Any]],
    similar_analysis: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    existing = next((item for item in scores if item.get("item") == "특허출원 활성도"), None)
    existing_evidence = existing.get("kipris_evidence") if isinstance(existing, dict) else None
    if isinstance(existing_evidence, dict) and not existing_evidence.get("fallback"):
        source = str(existing_evidence.get("source") or "")
        if "IPC" in source or existing_evidence.get("ipc_codes"):
            return scores

    years = _years_from_similar_analysis(similar_analysis)
    if not years:
        return scores

    current_year = max(years)
    window_years = list(range(current_year - 4, current_year + 1))
    counts = {year: years.count(year) for year in window_years}
    sample_count = sum(counts.values())
    rate = _growth_rate_from_year_counts(counts)
    score = _filing_activity_score(rate, sample_count)
    if rate is None:
        basis = (
            "KIPRIS 유사특허 후보 연도 분포는 확인되나 최근 5년 표본이 적어 증가율 산출은 제한적입니다. "
            f"연도별 건수: {', '.join(f'{year}년 {counts[year]}건' for year in window_years)}."
        )
        summary = "유사특허 연도 분포는 확인되나 증가율 표본은 제한적임."
    else:
        basis = (
            f"KIPRIS 유사특허 후보 최근 5년 출원 증가율은 {rate}%입니다. "
            f"연도별 건수: {', '.join(f'{year}년 {counts[year]}건' for year in window_years)}."
        )
        summary = f"유사특허 후보 기준 최근 5년 출원 증가율은 {rate}%임."
    evidence = {
        "source": "KIPRIS 유사특허 후보 연도 분포",
        "growth_rate": rate,
        "years": window_years,
        "yearly_counts": [{"year": year, "count": counts[year]} for year in window_years],
        "sample_count": sample_count,
        "fallback": False,
        "note": "IPC 전체 출원 통계가 아닌 KIPRIS 유사특허 후보 기반 보강 지표입니다.",
    }

    enriched = []
    for item in scores:
        if item.get("item") == "특허출원 활성도":
            updated = dict(item)
            updated.update({
                "score": score,
                "summary": summary,
                "basis": basis,
                "reason": basis,
                "confidence": "보통" if sample_count >= 2 else "낮음",
                "kipris_evidence": evidence,
                "sources": [
                    {
                        "source": "KIPRIS",
                        "title": "KIPRIS 유사특허 후보 연도 분포",
                        "url": KIPRIS_PLUS_URL,
                    }
                ],
            })
            enriched.append(updated)
        else:
            enriched.append(item)
    return enriched


# ─────────────────────────────────────────────
# 섹션 빌더
# ─────────────────────────────────────────────

def _build_patent_info(result: dict[str, Any], evaluated_on: date) -> dict[str, Any]:
    meta = result.get("meta") or {}
    legal = result.get("legal") or {}
    application_date = meta.get("application_date")
    expiration = (
        _parse_iso_date(legal.get("expiration_date") or legal.get("expiry_date"))
        or _patent_expiration(application_date)
    )
    legal_remaining_years = legal.get("legal_remaining_years")
    return {
        "id": result.get("patent_id", ""),
        "title": result.get("title", ""),
        "registration_number": meta.get("registration_number") or result.get("patent_id", ""),
        "application_number": meta.get("application_number"),
        "application_date": application_date,
        "registration_date": meta.get("registration_date"),
        "publication_number": meta.get("publication_number"),
        "publication_date": meta.get("publication_date"),
        "ipc_codes": meta.get("ipc") or [],
        "cpc_codes": meta.get("cpc") or [],
        "assignee": meta.get("assignee") or [],
        "inventors": meta.get("inventors") or [],
        "total_claims": meta.get("total_claims"),
        "legal_status": meta.get("legal_status") or legal.get("legal_status"),
        "expiration_date": expiration.isoformat() if expiration else None,
        "expiration_basis": "출원일 기준 20년 일반 만료일. 연장등록 등 개별 법적 사정은 별도 확인 필요",
        "remaining_years": (
            legal_remaining_years
            if isinstance(legal_remaining_years, (int, float))
            else _remaining_years(expiration, evaluated_on)
        ),
    }


def _build_metadata(report_id: str, generated_at: datetime, evaluated_on: date) -> dict[str, Any]:
    return {
        "report_type": "patent_reevaluation",
        "title": "재평가 보고서",
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "evaluation_date": evaluated_on.isoformat(),
        "score_display_scale": "0~100",
        "item_score_scale": "1~5",
        "service_sections": [
            {"key": "patent", "title": "특허 기본정보"},
            {"key": "summary", "title": "평가 요약"},
            {"key": "evaluation", "title": "평가 기준별 상세 점수"},
            {"key": "analysis", "title": "종합 평가 의견"},
            {"key": "risks", "title": "리스크 및 추가 확인 필요 사항"},
            {"key": "similar_patents", "title": "유사 특허"},
            {"key": "project_association", "title": "사내 프로젝트 연관 정보"},
        ],
        "storage_policy": "prebuilt_json_read_only",
        "report_id": report_id,
    }


def _default_overall_opinion(overall_score: float, dim_stats: dict[str, Any]) -> str:
    if not dim_stats:
        return "평가 점수 데이터가 없어 종합 의견을 산출하지 못했습니다."
    weakest_dim, weakest_data = min(dim_stats.items(), key=lambda item: item[1].get("average_score", 0))
    strongest_dim, strongest_data = max(dim_stats.items(), key=lambda item: item[1].get("average_score", 0))
    return (
        f"종합 점수는 {overall_score}/5이며, {strongest_dim}({strongest_data.get('score_out_of_100')}점)이 "
        f"상대적으로 강하고 {weakest_dim}({weakest_data.get('score_out_of_100')}점)은 추가 검토가 필요합니다."
    )


def _missing_dimensions(dim_stats: dict[str, Any]) -> list[str]:
    return [dim for dim in DIMENSION_ORDER if dim not in dim_stats]


def _source_count(scores: list[dict[str, Any]]) -> int:
    seen: set[str] = set()
    for score in scores:
        for source in score.get("sources") or []:
            if not isinstance(source, dict):
                continue
            key = str(source.get("url") or source.get("title") or source)
            seen.add(key)
    return len(seen)


def _evidence_limitations(
    all_scores: list[dict[str, Any]],
    dim_stats: dict[str, Any],
    project_available: bool,
    project_source_count: int,
) -> list[str]:
    limitations: list[str] = []
    missing_dims = _missing_dimensions(dim_stats)
    if missing_dims:
        limitations.append(
            f"{', '.join(missing_dims)} 평가는 현재 저장 보고서에 충분한 항목이 없어 정량 판단 범위가 제한됩니다."
        )
    if len(all_scores) < 20:
        limitations.append(
            "세부 평가 항목 수가 제한적이므로 점수는 예비 판단으로 보고 추가 근거 검토가 필요합니다."
        )
    if _source_count(all_scores) == 0:
        limitations.append(
            "외부 기술·시장 출처가 충분히 연결되지 않아 고점/저점 판단의 근거 확인이 필요합니다."
        )
    if not project_available or project_source_count == 0:
        limitations.append(
            "사내 프로젝트 연관 정보는 확인된 RAG 근거가 없거나 부족하여 미확인 상태로 표시합니다."
        )
    return limitations


def _compose_overall_opinion(
    overall_score: float,
    dim_stats: dict[str, Any],
    evaluation_analysis: str,
    limitations: list[str],
    dimension_summaries: dict[str, str] | None = None,
    similar_analysis: dict[str, Any] | None = None,
) -> str:
    if not dim_stats:
        return "평가 점수 데이터가 없어 종합 의견을 산출하지 못했습니다."

    dimension_summaries = dimension_summaries or {}
    strongest_dim, strongest_data = max(dim_stats.items(), key=lambda item: item[1].get("average_score", 0))
    weakest_dim, weakest_data = min(dim_stats.items(), key=lambda item: item[1].get("average_score", 0))
    score_100 = _score_to_100(overall_score)
    grade = _to_grade(overall_score)
    risk_phrase = {
        "low": "전반적으로 유지 및 활용 검토가 가능한",
        "medium": "일부 근거 보강을 전제로 활용성을 판단할",
        "high": "핵심 근거 재검토가 필요한",
    }.get(_to_risk(overall_score), "추가 검토가 필요한")

    sentences = [
        f"종합 평가는 {score_100}점({grade}등급)으로, {risk_phrase} 수준입니다."
    ]

    def opinion_text(value: str | None) -> str:
        return _clean_text(value or "").rstrip(" ,.;")

    def score_out(data: dict[str, Any]) -> int:
        value = data.get("score_out_of_100")
        if isinstance(value, (int, float)):
            return int(round(float(value)))
        return _score_to_100(float(data.get("average_score") or 0)) or 0

    def first_sentence(value: str | None) -> str:
        text = _clean_text(value or "")
        if not text:
            return ""
        for marker in ("다.", "요.", "임.", "음.", "."):
            pos = text.find(marker)
            if pos >= 0:
                return text[:pos + len(marker)]
        return _ensure_sentence(_short_text(text, 160))

    tech = dimension_summaries.get("기술성")
    rights = dimension_summaries.get("권리성")
    sentences.append(
        f"가장 강한 축은 {strongest_dim}({score_out(strongest_data)}점)이고, "
        f"보완이 필요한 축은 {weakest_dim}({score_out(weakest_data)}점)입니다."
    )
    tech_rights = " ".join(
        text for text in (first_sentence(tech), first_sentence(rights)) if text
    )
    if tech_rights:
        sentences.append(tech_rights)

    market = dimension_summaries.get("시장성")
    business = dimension_summaries.get("사업성")
    similar_summary = (similar_analysis or {}).get("ecosystem_summary") or {}
    similar_total = similar_summary.get("total_similar_patents")
    similar_active = similar_summary.get("active_count")
    similar_text = ""
    if isinstance(similar_total, (int, float)):
        similar_text = f" 최근 20년 유사특허는 {int(similar_total)}건"
        if isinstance(similar_active, (int, float)):
            similar_text += f", 활성 특허는 {int(similar_active)}건"
        similar_text += "으로 확인됩니다."
    if market or business or similar_text:
        market_business = " ".join(
            text for text in (first_sentence(market), first_sentence(business)) if text
        )
        if market_business:
            sentences.append(f"{market_business}{similar_text}")
        else:
            sentences.append(f"시장성·사업성은 시장 자료와 사업 적용 근거를 함께 검토해야 합니다.{similar_text}")

    if limitations:
        sentences.append(f"다만 {' '.join(_ensure_sentence(opinion_text(item)) for item in limitations[:2])}")

    sentences.append(
        "따라서 이 보고서는 단순 등급보다 기술 구현의 명확성, 권리 유지 가능성, 시장 출원 추세, 사내 적용 근거를 함께 읽는 방식으로 해석하는 것이 적절합니다."
    )
    return " ".join(sentences[:6])


def _build_summary(
    dim_stats: dict[str, Any],
    overall_score: float,
    evaluation_analysis: str,
    similar_analysis: dict[str, Any] | None,
    dimension_summaries: dict[str, str] | None = None,
    evidence_limitations: list[str] | None = None,
) -> dict[str, Any]:
    limitations = evidence_limitations or []
    dimension_summaries = dimension_summaries or {}
    similar_brief: dict[str, Any] = {"available": False}
    if similar_analysis:
        eco = similar_analysis.get("ecosystem_summary") or {}
        similar_brief = {
            "available": True,
            "total_count": eco.get("total_similar_patents", 0),
            "active_count": eco.get("active_count", 0),
            "enforceable_count": eco.get("enforceable_count", 0),
            "enforceable_ratio": eco.get("enforceable_ratio"),
            "average_citation_count": eco.get("avg_citation_count"),
        }

    return {
        "overall_score": overall_score,
        "overall_score_out_of_100": _score_to_100(overall_score),
        "overall_grade": _to_grade(overall_score),
        "risk_level": _to_risk(overall_score),
        "dimension_cards": [
            {
                "key": dim,
                "label": dim,
                "average_score": data["average_score"],
                "score_out_of_100": data["score_out_of_100"],
                "grade": data["grade"],
                "item_count": data["item_count"],
            }
            for dim, data in dim_stats.items()
        ],
        "similar_patents_brief": similar_brief,
        "overall_opinion": _compose_overall_opinion(
            overall_score,
            dim_stats,
            evaluation_analysis,
            limitations,
            dimension_summaries,
            similar_analysis,
        ),
        "evidence_limitations": limitations,
        "human_review_recommended": bool(limitations),
    }


def _build_evaluation(auto_scores: list[dict[str, Any]], llm_scores: list[dict[str, Any]]) -> dict[str, Any]:
    detailed = _build_section2_detailed_scores(auto_scores, llm_scores)
    dimensions = []
    for dim, data in (detailed.get("dimensions") or {}).items():
        items = [
            {
                "name": item.get("item", ""),
                "score": item.get("score"),
                "score_out_of_100": item.get("score_out_of_100"),
                "grade": _to_grade(float(item.get("score") or 0)) if isinstance(item.get("score"), (int, float)) else None,
                "method": item.get("method", ""),
                "strategy": item.get("strategy") or _strategy_for_item(item.get("item")),
                "confidence": item.get("confidence"),
                "judgment_summary": normalize_report_sentence(
                    _short_text(item.get("judgment_summary") or item.get("judgment_basis"), 50)
                ),
                "judgment_basis": normalize_local_source_markers(
                    normalize_report_prose(item.get("judgment_basis") or item.get("judgment_summary")),
                    len(item.get("sources") or []),
                ),
                "evidence": item.get("kipris_evidence") or item.get("evidence") or "",
                "sources": item.get("sources") or [],
            }
            for item in data.get("items") or []
        ]
        dimensions.append({
            "key": dim,
            "label": dim,
            "score_out_of_100": data.get("score_out_of_100"),
            "average_score": data.get("average_score"),
            "grade": _to_grade(float(data.get("average_score") or 0)),
            "item_count": data.get("item_count", 0),
            "items": items,
            "summary": _dimension_summary(dim, items),
        })

    return {
        "score_scale": {"item": "1~5", "display": "0~100"},
        "evaluation_standard": detailed.get("evaluation_standard"),
        "score_calculation_method": detailed.get("score_calculation_method"),
        "dimensions": dimensions,
    }


def _dimension_summaries_from_evaluation(evaluation: dict[str, Any]) -> dict[str, str]:
    summaries: dict[str, str] = {}
    for dim in evaluation.get("dimensions") or []:
        if not isinstance(dim, dict):
            continue
        key = str(dim.get("key") or dim.get("label") or "")
        if not key:
            continue
        summaries[key] = _dimension_summary(key, dim.get("items") or [])
    return summaries


def _build_analysis(
    evaluation_result: dict[str, Any],
    dim_stats: dict[str, Any],
    overall_score: float,
    evaluation_analysis: str,
    evidence_limitations: list[str] | None = None,
) -> dict[str, Any]:
    limitations = evidence_limitations or []
    strongest = sorted(
        dim_stats.items(),
        key=lambda item: item[1].get("average_score", 0),
        reverse=True,
    )
    weakest = sorted(dim_stats.items(), key=lambda item: item[1].get("average_score", 0))
    return {
        "overall": _compose_overall_opinion(overall_score, dim_stats, evaluation_analysis, limitations),
        "grade": _to_grade(overall_score),
        "strength_dimensions": [
            {"dimension": dim, "score_out_of_100": data.get("score_out_of_100")}
            for dim, data in strongest[:2]
        ],
        "watch_dimensions": [
            {"dimension": dim, "score_out_of_100": data.get("score_out_of_100")}
            for dim, data in weakest[:2]
        ],
        "market_sector": (evaluation_result.get("market") or {}).get("sector"),
        "evidence_limitations": limitations,
        "review_note": (
            "근거가 부족한 항목은 사람이 원문, 사업 적용 자료, 외부 시장 근거를 추가 확인한 뒤 최종 판단해야 합니다."
            if limitations
            else "현재 저장된 근거 기준으로 자동 보고서 구조를 구성했습니다."
        ),
        "human_review_recommended": bool(limitations),
    }


def _build_project_association(evaluation_result: dict[str, Any]) -> dict[str, Any]:
    project = _build_section3_project(evaluation_result)
    available = bool(project.get("available"))
    sources = project.get("sources") or []
    parsed = _parse_project_answer(project.get("answer") or project.get("project_summary") or "")
    if not available or not sources:
        return {
            "available": False,
            "status": "not_found",
            "data_source": project.get("data_source") or "사내 프로젝트 문서 RAG 검색 결과",
            "applied_services": "",
            "application_history": "",
            "customers_partners": "",
            "market_outlook": "",
            "summary": "현재 저장된 사내 프로젝트 RAG 결과에서 명확한 적용 현황은 확인되지 않았습니다.",
            "review_note": "연관 프로젝트가 없을 수도 있으므로 오류로 보지 않고 미확인 상태로 표시합니다. 필요 시 담당자가 프로젝트명, 제품명, 고객 사례를 추가 확인하면 됩니다.",
            "signals": [],
            "sources": [],
        }
    applied_services = _remove_estimation_marker(
        project.get("applied_business_service") or parsed.get("applied_services") or ""
    )
    application_history = _remove_estimation_marker(
        project.get("business_application_history") or parsed.get("application_history") or ""
    )
    customers_partners = _remove_estimation_marker(
        project.get("customers_partners") or parsed.get("customers_partners") or ""
    )
    market_outlook = _remove_estimation_marker(project.get("market_outlook") or parsed.get("market_outlook") or "")
    raw_summary = _remove_estimation_marker(
        parsed.get("summary") or project.get("project_summary") or _strip_markdown(project.get("answer") or "")
    )
    return {
        "available": available,
        "status": "found",
        "data_source": project.get("data_source"),
        "applied_services": applied_services,
        "application_history": application_history,
        "customers_partners": customers_partners,
        "market_outlook": market_outlook,
        "summary": _compose_project_summary(
            raw_summary,
            applied_services,
            application_history,
            customers_partners,
            market_outlook,
            sources,
        ),
        "signals": project.get("commercialization_signals") or parsed.get("commercialization_signals") or [],
        "review_note": "사내 프로젝트 RAG 근거가 확인되어 연관 정보로 표시합니다.",
        "sources": sources,
    }


def _compose_project_summary(
    raw_summary: Any,
    applied_services: Any,
    application_history: Any,
    customers_partners: Any,
    market_outlook: Any,
    sources: list[dict[str, Any]],
) -> str:
    base = _clean_text(raw_summary)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。])\s+|(?<=다\.)\s+", base) if s.strip()]

    service = _clean_text(applied_services)
    history = _clean_text(application_history)
    customers = _clean_text(customers_partners)
    outlook = _clean_text(market_outlook)
    source_titles = [
        _clean_text(src.get("title"))
        for src in sources[:2]
        if isinstance(src, dict) and _clean_text(src.get("title"))
    ]

    def topic_particle(text: str) -> str:
        if not text:
            return "와"
        code = ord(text[-1])
        if 0xAC00 <= code <= 0xD7A3:
            return "과" if (code - 0xAC00) % 28 else "와"
        return "와"

    def project_sentence(text: str) -> str:
        cleaned = _clean_text(text).rstrip(" ,;")
        if not cleaned:
            return ""
        cleaned = cleaned.replace("필요가 있다로 확인됩니다", "필요합니다.")
        cleaned = cleaned.replace("습니다로 확인됩니다", "습니다.")
        cleaned = cleaned.replace("있다로 확인됩니다", "있습니다.")
        cleaned = re.sub(r"\.{2,}$", ".", cleaned)
        cleaned = re.sub(r"필요하다\.$", "필요합니다.", cleaned)
        cleaned = re.sub(r"요구된다\.$", "요구됩니다.", cleaned)
        cleaned = re.sub(r"크다\.$", "큽니다.", cleaned)
        if cleaned.endswith((
            "입니다.",
            "합니다.",
            "됩니다.",
            "확인됩니다.",
            "필요합니다.",
            "예상됩니다.",
            "있습니다.",
            "보입니다.",
            "습니다.",
        )):
            return cleaned
        if cleaned.endswith((
            "입니다",
            "합니다",
            "됩니다",
            "확인됩니다",
            "필요합니다",
            "예상됩니다",
            "있습니다",
            "보입니다",
            "습니다",
        )):
            return f"{cleaned}."
        prefix = ""
        body = cleaned
        if "측면에서는 " in cleaned:
            prefix, body = cleaned.split("측면에서는 ", 1)
            prefix = f"{prefix}측면에서는 "
        body = body.rstrip(" .")
        if body.endswith(("되고 있음", "하고 있음")):
            return f"{prefix}{body[:-3].rstrip()} 있는 것으로 확인됩니다."
        if body.endswith("중임"):
            return f"{prefix}{body[:-2].rstrip()} 중인 것으로 확인됩니다."
        if body.endswith("확인되지 않음"):
            return f"{prefix}{body[:-7].rstrip()} 확인되지 않습니다."
        if body.endswith("되지 않음"):
            return f"{prefix}{body[:-5].rstrip()}되지 않는 것으로 확인됩니다."
        if body.endswith("없음"):
            return f"{prefix}{body[:-2].rstrip()} 없는 것으로 확인됩니다."
        if body.endswith("적용 시작"):
            return f"{prefix}{body[:-5].rstrip()} 적용이 시작된 것으로 확인됩니다."
        if body.endswith(("시작", "도입", "적용", "진행", "확대", "검토", "탐색", "확인")):
            return f"{prefix}{body}이 확인됩니다."
        return f"{prefix}{body}로 확인됩니다."

    if service:
        sentences.append(f"사내 적용 관점에서는 {service}{topic_particle(service)}의 연계 가능성이 우선 검토 대상입니다.")
    if history:
        sentences.append(project_sentence(f"적용 이력 측면에서는 {history}"))
    if customers:
        sentences.append(f"고객·파트너 관점에서는 {customers} 영역과의 관련성이 확인됩니다.")
    if outlook:
        sentences.append(project_sentence(outlook))
    if source_titles:
        sentences.append(f"주요 근거 문서는 {'; '.join(source_titles)} 등이며, 실제 적용 여부는 담당 조직의 프로젝트 이력 확인이 필요합니다.")

    deduped: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        cleaned = project_sentence(sentence)
        if "사업화 여부" in cleaned or "사업화 상태" in cleaned:
            continue
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return " ".join(deduped[:6])


def _strip_markdown(text: Any) -> str:
    lines = []
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line == "---" or line.startswith("|") or set(line) <= {"-", "|", " "}:
            continue
        line = re.sub(r"^#+\s*", "", line)
        lines.append(line)
    return _clean_text(" ".join(lines))


def _parse_project_answer(answer: Any) -> dict[str, str]:
    text = str(answer or "")
    parsed: dict[str, Any] = {}

    def from_json_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "applied_services": payload.get("applied_services") or payload.get("applied_business_service") or "",
            "application_history": payload.get("application_history") or payload.get("business_application_history") or "",
            "customers_partners": payload.get("customers_partners") or "",
            "market_outlook": payload.get("market_outlook") or "",
            "summary": payload.get("summary") or "",
            "commercialization_signals": payload.get("commercialization_signals") or payload.get("signals") or [],
        }

    stripped = text.strip()
    json_candidates = [stripped]
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        json_candidates.append(match.group(0))
    for candidate in json_candidates:
        if not candidate.startswith("{"):
            continue
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            parsed.update({key: value for key, value in from_json_payload(loaded).items() if value not in ("", [], None)})
            if parsed.get("summary"):
                return parsed

    field_map = {
        "적용 사업·서비스": "applied_services",
        "적용 사업/서비스": "applied_services",
        "사업 적용 이력": "application_history",
        "고객·파트너": "customers_partners",
        "고객/파트너": "customers_partners",
    }
    for raw in text.splitlines():
        line = raw.strip()
        if not (line.startswith("|") and line.endswith("|")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] in {"항목", "------"} or set(cells[0]) <= {"-"}:
            continue
        key = field_map.get(cells[0])
        if key:
            parsed[key] = cells[1]

    summary = ""
    outlook = ""
    if "## 요약 설명" in text:
        tail = text.split("## 요약 설명", 1)[1]
        if "## 시장 전망" in tail:
            summary, outlook = tail.split("## 시장 전망", 1)
        else:
            summary = tail
    parsed["summary"] = _strip_markdown(summary) or _strip_markdown(text)
    parsed["market_outlook"] = _strip_markdown(outlook)
    return parsed


def _build_similar_patents(similar_analysis: dict[str, Any] | None) -> dict[str, Any]:
    similar = _build_section4_similar(similar_analysis)
    patent_list = similar.get("patent_list") or []
    filtered_patents, excluded_count = _filter_recent_similar_patents(patent_list)
    summary = dict(similar.get("ecosystem_summary") or {})
    summary.update(_similar_summary_from_patents(filtered_patents, summary))
    return {
        "available": similar.get("available", False),
        "data_source": similar.get("data_source"),
        "collection_policy": {
            "source": similar.get("data_source") or "KIPRIS",
            "max_age_years": SIMILAR_PATENT_MAX_AGE_YEARS,
            "excluded_over_20_years_count": excluded_count,
            "candidate_pool_count": len(patent_list),
            "display_limit": 10,
            "sorted_by": "kipris_similarity_score_desc",
        },
        "summary": summary,
        "target_position": similar.get("target_position") or {},
        "top_comparisons": similar.get("top_comparisons") or [],
        "patents": filtered_patents,
        "competitive_analysis": similar.get("competitive_analysis") or {},
    }


def _application_year(value: Any) -> int | None:
    text = str(value or "").strip()
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    return int(match.group(0))


def _filter_recent_similar_patents(patents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    cutoff = date.today().year - SIMILAR_PATENT_MAX_AGE_YEARS + 1
    kept: list[dict[str, Any]] = []
    excluded = 0
    for patent in patents:
        year = _application_year(patent.get("application_year") or patent.get("application_date"))
        if year is not None and year < cutoff:
            excluded += 1
            continue
        normalized = dict(patent)
        if year is not None:
            normalized["application_year"] = year
        kept.append(normalized)
    kept.sort(key=lambda item: item.get("kipris_similarity_score") or item.get("similarity_score") or 0, reverse=True)
    return kept[:10], excluded


def _similar_summary_from_patents(
    patents: list[dict[str, Any]],
    existing: dict[str, Any],
) -> dict[str, Any]:
    if not patents:
        return {
            "total_similar_patents": 0,
            "active_count": 0,
            "published_or_pending_count": 0,
            "rejected_or_expired_count": 0,
            "avg_citation_count": 0,
            "max_citation_count": 0,
            "application_year_range": existing.get("application_year_range") or {},
            "status_distribution": {},
        }
    statuses: dict[str, int] = {}
    active = pending = rejected = 0
    citations: list[float] = []
    years: list[int] = []
    for patent in patents:
        status = str(patent.get("legal_status") or "미확인")
        statuses[status] = statuses.get(status, 0) + 1
        if any(token in status for token in ("등록", "유지")):
            active += 1
        elif any(token in status for token in ("공개", "심사", "출원")):
            pending += 1
        else:
            rejected += 1
        if isinstance(patent.get("citation_count"), (int, float)):
            citations.append(float(patent.get("citation_count")))
        year = _application_year(patent.get("application_year"))
        if year:
            years.append(year)
    range_existing = existing.get("application_year_range") if isinstance(existing.get("application_year_range"), dict) else {}
    return {
        "total_similar_patents": len(patents),
        "active_count": active,
        "published_or_pending_count": pending,
        "rejected_or_expired_count": rejected,
        "avg_citation_count": round(sum(citations) / len(citations), 1) if citations else 0,
        "max_citation_count": int(max(citations)) if citations else 0,
        "application_year_range": {
            "min": min(years) if years else range_existing.get("min"),
            "max": max(years) if years else range_existing.get("max"),
            "target": range_existing.get("target"),
        },
        "status_distribution": statuses,
    }


def _similar_patent_report_summary(patent: dict[str, Any]) -> str:
    comp = patent.get("comparison") if isinstance(patent.get("comparison"), dict) else {}
    summary = _clean_text(comp.get("summary") or patent.get("summary"))
    if summary:
        return summary

    common_points = comp.get("common_points") if isinstance(comp.get("common_points"), list) else []
    differences = comp.get("differences") if isinstance(comp.get("differences"), list) else []
    common = _clean_text(common_points[0]) if common_points else "결함 검출·분석 흐름"
    difference = _clean_text(differences[0]) if differences else "구체 구현 범위와 권리 상태"
    title = _clean_text(patent.get("title")) or "해당 유사 특허"
    return (
        f"{title}는 대상 특허와 {common} 측면에서 비교 가능하며, "
        f"{difference}에서 차이가 확인됩니다."
    )


def _build_risks(
    all_scores: list[dict[str, Any]],
    evidence_limitations: list[str] | None = None,
) -> dict[str, Any]:
    review = _build_section5_review_items(all_scores)
    limitations = evidence_limitations or []
    limitation_items = [
        {
            "dimension": "근거",
            "name": "근거 보강 필요",
            "score": None,
            "confidence": "낮음",
            "priority": "medium",
            "reason": limitation,
            "judgment_basis": normalize_local_source_markers(limitation, 0),
            "required_evidence": "특허 등록정보와 청구항, 사내 프로젝트 자료, 외부 기술·시장 근거 추가 확인",
        }
        for limitation in limitations
    ]
    return {
        "selection_rule": review.get("selection_rule"),
        "items": [
            {
                "dimension": item.get("dim", ""),
                "name": item.get("item", ""),
                "score": item.get("score"),
                "confidence": item.get("confidence"),
                "priority": item.get("review_priority"),
                "reason": item.get("selection_reason"),
                "judgment_basis": normalize_local_source_markers(item.get("judgment_basis"), 0),
                "required_evidence": item.get("required_evidence"),
            }
            for item in review.get("items") or []
        ] + limitation_items,
        "human_review_recommended": bool((review.get("items") or []) or limitations),
    }


def _build_section1_summary(
    evaluation_result: dict[str, Any],
    all_scores: list[dict[str, Any]],
    dim_stats: dict[str, Any],
    overall_score: float,
    similar_analysis: dict[str, Any] | None,
    evaluation_analysis: str,
) -> dict[str, Any]:
    """1. 평가 요약"""
    # 1.2 사내 프로젝트 활용 현황 (brief)
    biz_use = (evaluation_result.get("evidence") or {}).get("business_use") or {}
    project_brief: dict[str, Any] = {
        "applied_business_service": biz_use.get("applied_business_service") or "",
        "brief_summary": biz_use.get("summary") or "",
    }

    # 1.3 유사 특허 현황 (brief)
    eco: dict[str, Any] = {}
    similar_brief: dict[str, Any] = {"available": False}
    if similar_analysis:
        eco = similar_analysis.get("ecosystem_summary") or {}
        all_sims = similar_analysis.get("similar_patents") or []
        sim_scores = [
            s.get("similarity", {}).get("overall", 0.0)
            for s in all_sims
            if isinstance(s.get("similarity"), dict)
        ]
        similar_brief = {
            "available": True,
            "total": eco.get("total_similar_patents", 0),
            "active_count": eco.get("active_count", 0),
            "enforceable_count": eco.get("enforceable_count", 0),
            "published_or_pending_count": eco.get("published_or_pending_count", 0),
            "rejected_or_expired_count": eco.get("rejected_or_expired_count", 0),
            "enforceable_ratio": eco.get("enforceable_ratio"),
            "avg_citation_count": eco.get("avg_citation_count"),
            "avg_similarity": round(sum(sim_scores) / len(sim_scores), 4) if sim_scores else 0.0,
        }

    return {
        "title": "평가 요약",
        "overall_score": overall_score,
        "overall_score_out_of_100": _score_to_100(overall_score),
        "overall_grade": _to_grade(overall_score),
        "risk_level": _to_risk(overall_score),
        "score_scale": {
            "item": "1~5",
            "display": "0~100",
        },
        "dimension_scores": {
            dim: {
                "average_score": data["average_score"],
                "score_out_of_100": data["score_out_of_100"],
                "grade": data["grade"],
                "item_count": data["item_count"],
            }
            for dim, data in dim_stats.items()
        },
        "project_utilization_brief": project_brief,
        "similar_patents_brief": similar_brief,
        "overall_opinion": evaluation_analysis,
    }


def _build_section2_detailed_scores(
    auto_scores: list[dict[str, Any]],
    llm_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """2. 평가 기준별 상세 점수"""
    all_scores = _canonical_evaluation_scores(auto_scores + llm_scores)
    by_dim = _dim_items(all_scores)

    dim_detail: dict[str, Any] = {}
    for dim in [*DIMENSION_ORDER, *sorted(set(by_dim) - set(DIMENSION_ORDER))]:
        items = by_dim.get(dim, [])
        if not items:
            continue
        values = [float(s["score"]) for s in items if isinstance(s.get("score"), (int, float))]
        average = round(sum(values) / len(values), 2) if values else 0.0
        dim_detail[dim] = {
            "average_score": average,
            "score_out_of_100": _score_to_100(average),
            "item_count": len(items),
            "items": [
                {
                    "item": s.get("item", ""),
                    "score": s.get("score"),
                    "score_out_of_100": _score_to_100(s.get("score")),
                    "method": s.get("method", ""),
                    "strategy": s.get("strategy") or _strategy_for_item(s.get("item")),
                    "confidence": _confidence_for_score(s)[0],
                    "confidence_source": _confidence_for_score(s)[1],
                    "judgment_summary": _score_summary(s),
                    "judgment_basis": _score_basis(s),
                    "kipris_evidence": s.get("kipris_evidence") or "",
                    "sources": s.get("sources") or [],
                }
                for s in items
            ]
        }

    all_src = _collect_all_sources(all_scores)
    return {
        "title": "평가 기준별 상세 점수",
        "dimensions": dim_detail,
        "evaluation_standard": "IP가치평가 실무가이드 Chapter 4 (특허청·한국발명진흥회·KISTI, 2021)",
        "score_calculation_method": (
            "승인된 17개 평가 항목 기준으로 자동 점수와 LLM 점수를 병합합니다. "
            "각 항목 1~5점 척도이며, 차원별 평균으로 종합 점수를 산출합니다."
        ),
        "all_sources": all_src,
    }


def _build_section3_project(evaluation_result: dict[str, Any]) -> dict[str, Any]:
    """3. 사내 프로젝트 활용 현황"""
    biz = (evaluation_result.get("evidence") or {}).get("business_use") or {}
    raw = biz.get("raw") if isinstance(biz.get("raw"), dict) else {}
    return {
        "title": "사내 프로젝트 활용 현황",
        "available": bool(biz),
        "data_source": "사내 프로젝트 문서 RAG 검색 결과",
        "query": biz.get("query") or "",
        "answer": biz.get("answer") or "",
        "applied_business_service": biz.get("applied_business_service") or raw.get("applied_business_service") or "",
        "business_application_history": biz.get("business_application_history")
        or raw.get("business_application_history")
        or "",
        "customers_partners": biz.get("customers_partners") or raw.get("customers_partners") or "",
        "market_outlook": biz.get("market_outlook") or raw.get("market_outlook") or "",
        "commercialization_signals": biz.get("commercialization_signals")
        or raw.get("commercialization_signals")
        or [],
        "project_summary": biz.get("summary") or raw.get("summary") or "",
        "sources": biz.get("sources") or [],
    }


def _build_section4_similar(similar_analysis: dict[str, Any] | None) -> dict[str, Any]:
    """4. 유사 특허 분석"""
    source_search = (similar_analysis or {}).get("meta", {}).get("source_search", {}) if similar_analysis else {}
    data_source = (
        "KIPRIS 특화검색 유사도 크롤러 결과"
        if source_search.get("method") == "legacy_kipris_crawler"
        else "KIPRIS 유사 특허 검색"
    )
    if not similar_analysis:
        return {
            "title": "유사 특허 분석",
            "available": False,
            "message": "유사 특허 분석 데이터가 없습니다.",
            "data_source": data_source,
            "ecosystem_summary": {},
            "top_comparisons": [],
            "patent_list": [],
            "competitive_analysis": {},
        }

    top_raw = similar_analysis.get("top_comparisons") or []
    top_list = []
    for item in top_raw:
        comp = item.get("comparison") or {}
        tech = comp.get("technical_analysis") or {}
        sim = item.get("similarity") or {}
        top_list.append({
            "rank": item.get("rank"),
            "patent_no": item.get("patent_no", ""),
            "application_number": item.get("application_number", ""),
            "application_date": item.get("application_date", ""),
            "title": item.get("title", ""),
            "applicant": item.get("applicant", ""),
            "legal_status": item.get("legal_status", ""),
            "citation_count": item.get("citation_count", 0),
            "similarity_score": sim.get("overall", 0.0),
            "kipris_similarity_score": sim.get("kipris"),
            "common_points": comp.get("common_points") or [],
            "differences": comp.get("differences") or [],
            "analysis_summary": comp.get("summary", ""),
            "technical_analysis": {
                "technical_overlap": tech.get("technical_overlap", ""),
                "technical_difference": tech.get("technical_difference", ""),
                "scope_comparison": tech.get("scope_comparison", ""),
                "technical_review_point": tech.get("technical_review_point", ""),
            },
        })

    all_patents = similar_analysis.get("similar_patents") or []
    patent_list = []
    for p in all_patents:
        sim = p.get("similarity") or {}
        src = p.get("source_detail") or {}
        candidate = src.get("source_candidate") if isinstance(src.get("source_candidate"), dict) else {}
        application_year = (
            _application_year(src.get("application_date"))
            or _application_year(candidate.get("application_year"))
            or _application_year(candidate.get("application_date"))
        )
        patent_list.append({
            "application_number": p.get("application_number", ""),
            "patent_no": p.get("patent_no", ""),
            "title": p.get("title", ""),
            "applicant": p.get("applicant", ""),
            "application_year": application_year or "",
            "similarity_score": sim.get("overall", 0.0),
            "kipris_similarity_score": sim.get("kipris"),
            "citation_count": p.get("citation_count", 0),
            "legal_status": p.get("legal_status", ""),
            "summary": _similar_patent_report_summary(p),
        })

    interp = similar_analysis.get("interpretation") or {}
    return {
        "title": "유사 특허 분석",
        "available": True,
        "data_source": data_source,
        "source_search": source_search,
        "ecosystem_summary": similar_analysis.get("ecosystem_summary") or {},
        "target_position": similar_analysis.get("target_position") or {},
        "top_comparisons": top_list,
        "patent_list": patent_list,
        "competitive_analysis": {
            "competition_intensity": interp.get("competition_intensity", ""),
            "differentiation_risk": interp.get("differentiation_risk", ""),
            "invalidity_or_designaround_risk": interp.get("invalidity_or_designaround_risk", ""),
            "analysis_summary": interp.get("analysis_summary", ""),
        },
    }


def _build_section5_review_items(all_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """5. 추가 확인 필요 사항 (낮은 점수 또는 낮은 확신도 항목)"""
    review_map = {
        "기술 경쟁성": "경쟁·대체기술 현황 / 동일·유사 특허 및 논문 조사 / 시장 내 유사 솔루션 현황",
        "기술적 모방 난이도": "모방 방지 설계·알고리즘 차별성 설명 / 오픈소스·공개자료와의 차별성",
        "타제품에 미치는 영향": "시장 내 기존 상품·서비스와의 관계 분석",
        "특별한 인정": "산업 내 평판 / 수상·인증 / 시장조사 자료",
        "대체기술": "시장 내 대체기술 조사",
        "진부화 가능성": "기술수명주기 분석",
        "IP 포트폴리오 구축 적절성": "관련 기술군 특허 포트폴리오 / 해외·국내 개량 특허 보유 현황",
        "기타 요인 무효 가능성": "기재불비 검토 자료 / 무효심판 청구 이력",
        "권리행사 제한 가능성": "저촉권리 / 실시권 설정 / 공유권리 여부",
        "분쟁 및 라이선스 활성도": "관련 분쟁·라이선스 사례 / 동일 기술분야 통계",
        "시장 지배력": "시장점유율 자료 / 주요 경쟁사·시장구조 분석",
        "시장 경쟁성": "경쟁기업·제품 수 / 시장경쟁구조 분석",
        "예상 시장 점유율": "시장점유율 예측 자료 / 사업화 계획서",
        "시장 진입성": "시장 진입장벽 / 규제·정책 자료",
        "수요성": "수요 조사 / 시장 수요 변동성 자료",
        "고객의 지불의지": "고객 WTP 조사 / 경쟁 서비스 가격 자료",
        "영업 이익성": "업종 평균 영업이익률 / 비용 구조 자료",
        "예상매출": "시장 규모·점유율 가정 / 사업 계획 자료",
    }

    items = []
    for s in all_scores:
        score = s.get("score", 5)
        if not isinstance(score, (int, float)):
            continue
        confidence, confidence_source = _confidence_for_score(s)
        if score > 3 and confidence != "낮음":
            continue
        priority = "urgent" if score <= 1 else ("high" if score == 2 else "medium")
        item_name = s.get("item", "")
        required_evidence = next(
            (label for key, label in review_map.items() if key in item_name),
            "내부 프로젝트 자료 및 외부 근거와의 교차 검토",
        )
        reasons = []
        if score <= 3:
            reasons.append(f"평가 점수 {_score_to_100(score)}점")
        if confidence == "낮음":
            reasons.append("근거 확신도 낮음")
        items.append({
            "item": item_name,
            "dim": s.get("dim", ""),
            "score": score,
            "confidence": confidence,
            "confidence_source": confidence_source,
            "selection_reason": ", ".join(reasons),
            "judgment_basis": _score_basis(s),
            "required_evidence": required_evidence,
            "review_priority": priority,
        })
    items.sort(key=lambda x: (x["score"], x["confidence"] != "낮음"))

    return {
        "title": "추가 확인 필요 사항",
        "selection_rule": "평가 점수 3점 이하 또는 근거 확신도 낮음 항목",
        "items": items,
    }


# ─────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────

def build_structured_report(
    evaluation_result: dict[str, Any],
    similar_analysis: dict[str, Any] | None = None,
    evaluation_analysis: str = "",
) -> dict[str, Any]:
    """서비스 화면과 저장 DB 계약에 맞는 재평가 보고서 JSON을 생성합니다.

    Args:
        evaluation_result: PatentEvaluationOutput.to_dict() 결과
        similar_analysis:  similar_patent_analyzer.analyze_similar_patents() 결과
        evaluation_analysis: 평가 점수와 추가 확인 항목을 요약한 텍스트
    """
    patent_id = evaluation_result.get("patent_id") or "unknown"
    now = datetime.now()
    evaluated_on = now.date()
    report_id = f"{patent_id}_{now.strftime('%Y%m%d_%H%M%S')}"

    auto_scores: list[dict] = evaluation_result.get("auto_scores") or []
    llm_scores: list[dict] = evaluation_result.get("llm_scores") or []
    all_scores = _enrich_canonical_filing_activity(
        _canonical_evaluation_scores(auto_scores + llm_scores),
        similar_analysis,
    )

    dim_stats = _dim_stats(all_scores)
    dim_avgs = [d["average_score"] for d in dim_stats.values()]
    overall_score = round(sum(dim_avgs) / len(dim_avgs), 2) if dim_avgs else 0.0

    project_association = _build_project_association(evaluation_result)
    evidence_limitations = _evidence_limitations(
        all_scores,
        dim_stats,
        bool(project_association.get("available")),
        len(project_association.get("sources") or []),
    )
    evaluation_scores = _enrich_canonical_filing_activity(
        _canonical_evaluation_scores(auto_scores + llm_scores),
        similar_analysis,
    )
    evaluation = _build_evaluation(evaluation_scores, [])
    dimension_summaries = _dimension_summaries_from_evaluation(evaluation)

    return {
        "report_id": report_id,
        "generated_at": now.isoformat(),
        "schema_version": REPORT_SCHEMA_VERSION,
        "patent": _build_patent_info(evaluation_result, evaluated_on),
        "summary": _build_summary(
            dim_stats,
            overall_score,
            evaluation_analysis,
            similar_analysis,
            dimension_summaries,
            evidence_limitations,
        ),
        "evaluation": evaluation,
        "project_association": project_association,
        "similar_patents": _build_similar_patents(similar_analysis),
        "risks": _build_risks(all_scores, evidence_limitations),
    }
