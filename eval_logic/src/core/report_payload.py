"""Frontend-facing report.json payload helpers."""

from __future__ import annotations

from typing import Any

from core.report_text import normalize_local_source_markers


REPORT_CONTRACT_KEYS = (
    "report_id",
    "generated_at",
    "schema_version",
    "patent",
    "summary",
    "evaluation",
    "project_association",
    "similar_patents",
    "risks",
)


PATENT_KEYS = (
    "title",
    "registration_number",
    "application_number",
    "application_date",
    "registration_date",
    "publication_number",
    "publication_date",
    "ipc_codes",
    "cpc_codes",
    "assignee",
    "legal_status",
    "expiration_date",
    "remaining_years",
)

SUMMARY_KEYS = (
    "overall_score",
    "overall_score_out_of_100",
    "overall_grade",
    "risk_level",
    "overall_opinion",
    "dimension_cards",
    "similar_patents_brief",
    "evidence_limitations",
    "human_review_recommended",
)

DIMENSION_CARD_KEYS = (
    "key",
    "label",
    "score_out_of_100",
    "average_score",
    "grade",
    "item_count",
)

EVALUATION_KEYS = (
    "score_scale",
    "evaluation_standard",
    "score_calculation_method",
    "dimensions",
)

DIMENSION_KEYS = (
    "key",
    "label",
    "score_out_of_100",
    "average_score",
    "grade",
    "item_count",
    "summary",
    "items",
)

ITEM_KEYS = (
    "name",
    "score",
    "score_out_of_100",
    "grade",
    "method",
    "judgment_summary",
    "judgment_basis",
    "confidence",
    "sources",
)

PROJECT_KEYS = (
    "available",
    "status",
    "data_source",
    "applied_services",
    "application_history",
    "customers_partners",
    "market_outlook",
    "signals",
    "summary",
    "review_note",
    "sources",
)

SIMILAR_KEYS = (
    "available",
    "data_source",
    "collection_policy",
    "summary",
    "competitive_analysis",
    "patents",
)

SIMILAR_SUMMARY_KEYS = (
    "total_similar_patents",
    "active_count",
    "published_or_pending_count",
    "rejected_or_expired_count",
    "avg_citation_count",
    "max_citation_count",
    "application_year_range",
    "status_distribution",
)

STATUS_KEYS = ("등록", "공개", "심사중", "거절", "소멸", "취하")

SIMILAR_PATENT_KEYS = (
    "title",
    "application_number",
    "application_year",
    "applicant",
    "legal_status",
    "kipris_similarity_score",
    "similarity_score",
    "citation_count",
    "patent_no",
    "summary",
)

RISK_KEYS = ("selection_rule", "human_review_recommended", "items")
RISK_ITEM_KEYS = (
    "dimension",
    "name",
    "score",
    "priority",
    "reason",
    "judgment_basis",
    "required_evidence",
)

REFERENCE_SOURCE_KEYS = ("title", "publisher", "published_date", "url")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _pick(source: dict[str, Any], keys: tuple[str, ...], defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = defaults or {}
    return {key: source.get(key, defaults.get(key)) for key in keys}


def _source_item(source: Any) -> dict[str, Any]:
    item = _as_dict(source)
    return {
        "title": item.get("title") or item.get("source") or "",
        "publisher": item.get("publisher") or item.get("source") or "",
        "published_date": item.get("published_date") or item.get("date") or "",
        "url": item.get("url") or "",
    }


def _evaluation_source(source: Any) -> dict[str, Any]:
    item = _as_dict(source)
    return {
        "title": item.get("title") or item.get("source") or "",
        "url": item.get("url") or "",
    }


def _canonical_evaluation_item(item: Any) -> dict[str, Any]:
    source = _as_dict(item)
    normalized = _pick(source, ITEM_KEYS, {"sources": []})
    normalized["sources"] = [_evaluation_source(src) for src in _as_list(source.get("sources"))]
    normalized["judgment_basis"] = normalize_local_source_markers(
        normalized.get("judgment_basis"),
        len(normalized["sources"]),
    )
    return normalized


def _canonical_patent(report: dict[str, Any]) -> dict[str, Any]:
    patent = _as_dict(report.get("patent"))
    defaults = {"ipc_codes": [], "cpc_codes": [], "assignee": []}
    normalized = _pick(patent, PATENT_KEYS, defaults)
    normalized["ipc_codes"] = _as_list(normalized.get("ipc_codes"))
    normalized["cpc_codes"] = _as_list(normalized.get("cpc_codes"))
    normalized["assignee"] = _as_list(normalized.get("assignee"))
    return normalized


def _canonical_summary(report: dict[str, Any]) -> dict[str, Any]:
    summary = _as_dict(report.get("summary"))
    normalized = _pick(
        summary,
        SUMMARY_KEYS,
        {
            "dimension_cards": [],
            "similar_patents_brief": {},
            "evidence_limitations": [],
            "human_review_recommended": False,
        },
    )
    normalized["dimension_cards"] = [
        _pick(_as_dict(item), DIMENSION_CARD_KEYS)
        for item in _as_list(normalized.get("dimension_cards"))
    ]
    brief = _as_dict(normalized.get("similar_patents_brief"))
    normalized["similar_patents_brief"] = {
        "available": brief.get("available", False),
        "total_count": brief.get("total_count", 0),
        "active_count": brief.get("active_count", 0),
        "average_citation_count": brief.get("average_citation_count", 0),
    }
    normalized["evidence_limitations"] = _as_list(normalized.get("evidence_limitations"))
    return normalized


def _canonical_evaluation(report: dict[str, Any]) -> dict[str, Any]:
    evaluation = _as_dict(report.get("evaluation"))
    dimensions = []
    for dimension in _as_list(evaluation.get("dimensions")):
        dim = _as_dict(dimension)
        normalized_dim = _pick(dim, DIMENSION_KEYS, {"items": []})
        normalized_dim["items"] = [_canonical_evaluation_item(item) for item in _as_list(dim.get("items"))]
        dimensions.append(normalized_dim)
    return {
        "score_scale": {
            "min": _as_dict(evaluation.get("score_scale")).get("min", 1),
            "max": _as_dict(evaluation.get("score_scale")).get("max", 5),
        },
        "evaluation_standard": evaluation.get("evaluation_standard"),
        "score_calculation_method": evaluation.get("score_calculation_method"),
        "dimensions": dimensions,
    }


def _canonical_project(report: dict[str, Any]) -> dict[str, Any]:
    project = _as_dict(report.get("project_association"))
    normalized = _pick(project, PROJECT_KEYS, {"signals": [], "sources": []})
    normalized["signals"] = _as_list(normalized.get("signals"))
    normalized["sources"] = [
        _pick(_as_dict(source), ("rank", "title", "url", "score"))
        for source in _as_list(normalized.get("sources"))
    ]
    return normalized


def _canonical_similar(report: dict[str, Any]) -> dict[str, Any]:
    similar = _as_dict(report.get("similar_patents"))
    summary = _as_dict(similar.get("summary"))
    application_year_range = _as_dict(summary.get("application_year_range"))
    status_distribution = _as_dict(summary.get("status_distribution"))
    competitive = _as_dict(similar.get("competitive_analysis"))
    return {
        "available": similar.get("available", False),
        "data_source": similar.get("data_source"),
        "collection_policy": {
            "max_age_years": _as_dict(similar.get("collection_policy")).get("max_age_years", 20),
            "excluded_over_20_years_count": _as_dict(similar.get("collection_policy")).get(
                "excluded_over_20_years_count", 0
            ),
            "sorted_by": _as_dict(similar.get("collection_policy")).get("sorted_by"),
        },
        "summary": {
            **_pick(summary, SIMILAR_SUMMARY_KEYS),
            "application_year_range": {
                "min": application_year_range.get("min"),
                "max": application_year_range.get("max"),
                "target": application_year_range.get("target"),
            },
            "status_distribution": {key: status_distribution.get(key, 0) for key in STATUS_KEYS},
        },
        "competitive_analysis": {
            "analysis_summary": competitive.get("analysis_summary"),
            "competition_intensity": competitive.get("competition_intensity"),
            "differentiation_risk": competitive.get("differentiation_risk"),
            "invalidity_or_designaround_risk": competitive.get("invalidity_or_designaround_risk"),
        },
        "patents": [
            _pick(_as_dict(patent), SIMILAR_PATENT_KEYS, {"summary": ""})
            for patent in _as_list(similar.get("patents"))
        ],
    }


def _canonical_risks(report: dict[str, Any]) -> dict[str, Any]:
    risks = _as_dict(report.get("risks"))
    return {
        "selection_rule": risks.get("selection_rule"),
        "human_review_recommended": risks.get("human_review_recommended", False),
        "items": [
            _pick(_as_dict(item), RISK_ITEM_KEYS)
            for item in _as_list(risks.get("items"))
        ],
    }


def frontend_report_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Return the exact report.json shape consumed by the frontend."""
    report = result.get("report") if isinstance(result.get("report"), dict) else result
    cleaned_report = {
        "report_id": report.get("report_id"),
        "generated_at": report.get("generated_at"),
        "schema_version": report.get("schema_version"),
        "patent": _canonical_patent(report),
        "summary": _canonical_summary(report),
        "evaluation": _canonical_evaluation(report),
        "project_association": _canonical_project(report),
        "similar_patents": _canonical_similar(report),
        "risks": _canonical_risks(report),
    }
    return {"report": cleaned_report}
