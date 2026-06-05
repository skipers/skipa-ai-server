"""구조화된 JSON 보고서 빌더 (v2)

평가 결과와 유사 특허 분석 데이터를 받아 보고서 목차 6개 섹션을
그대로 반영한 구조화 JSON 보고서를 생성합니다.

목차:
  Section 1: 평가 요약
  Section 2: 평가 기준별 상세 점수
  Section 3: 사내 프로젝트 활용 현황
  Section 4: 유사 특허 분석
  Section 5: 추가 확인 필요 사항
  Section 6: 참고 문헌
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any


REPORT_SCHEMA_VERSION = "patent-valuation-report/v3"
DIMENSION_ORDER = ["기술성", "권리성", "시장성", "사업성"]


# ─────────────────────────────────────────────
# 등급 / 위험도 매핑
# ─────────────────────────────────────────────

_GRADE_STEPS: list[tuple[float, str]] = [
    (4.5, "S"),
    (4.0, "A"),
    (3.5, "B+"),
    (3.0, "B"),
    (2.5, "C+"),
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
        url = str(src.get("url") or "")
        if url and url not in seen:
            seen.add(url)
            result.append(src)
    return result


def _collect_all_sources(scores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for s in scores:
        sources.extend(s.get("sources") or [])
    return _dedup_sources(sources)


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
        "commercialization_status": biz_use.get("commercialization_status") or "미확인",
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
    all_scores = auto_scores + llm_scores
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
                    "strategy": s.get("strategy"),
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
            "자동 점수(규칙 기반 5개 항목) + LLM 점수(OpenAI GPT 기반 43개 항목). "
            "각 항목 1~5점 척도. 차원별 평균으로 종합 점수 산출."
        ),
        "all_sources": all_src,
    }


def _build_section3_project(evaluation_result: dict[str, Any]) -> dict[str, Any]:
    """3. 사내 프로젝트 활용 현황"""
    biz = (evaluation_result.get("evidence") or {}).get("business_use") or {}
    return {
        "title": "사내 프로젝트 활용 현황",
        "available": bool(biz),
        "data_source": "사내 프로젝트 문서 RAG 검색 결과",
        "commercialization_status": biz.get("commercialization_status") or "미확인",
        "query": biz.get("query") or "",
        "answer": biz.get("answer") or "",
        "applied_business_service": biz.get("applied_business_service") or "",
        "business_application_history": biz.get("business_application_history") or "",
        "customers_partners": biz.get("customers_partners") or "",
        "market_outlook": biz.get("market_outlook") or "",
        "commercialization_signals": biz.get("commercialization_signals") or [],
        "project_summary": biz.get("summary") or "",
        "sources": biz.get("sources") or [],
    }


def _build_section4_similar(similar_analysis: dict[str, Any] | None) -> dict[str, Any]:
    """4. 유사 특허 분석"""
    if not similar_analysis:
        return {
            "title": "유사 특허 분석",
            "available": False,
            "message": "유사 특허 분석 데이터가 없습니다.",
            "data_source": "KIPRIS 유사 특허 검색",
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
    for p in all_patents[:10]:  # 상위 10건
        sim = p.get("similarity") or {}
        src = p.get("source_detail") or {}
        patent_list.append({
            "application_number": p.get("application_number", ""),
            "patent_no": p.get("patent_no", ""),
            "title": p.get("title", ""),
            "applicant": p.get("applicant", ""),
            "application_year": src.get("application_date", "")[:4] if src.get("application_date") else "",
            "similarity_score": sim.get("overall", 0.0),
            "kipris_similarity_score": sim.get("kipris"),
            "citation_count": p.get("citation_count", 0),
            "legal_status": p.get("legal_status", ""),
        })

    interp = similar_analysis.get("interpretation") or {}
    return {
        "title": "유사 특허 분석",
        "available": True,
        "data_source": "KIPRIS 유사 특허 검색",
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
            "사업부 자체 자료 및 외부 근거와의 교차 검토",
        )
        reasons = []
        if score <= 3:
            reasons.append(f"평가 점수 {score}/5")
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


def _build_section6_references(
    evaluation_result: dict[str, Any],
    similar_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    """6. 참고 문헌"""
    # LLM 평가 출처
    llm_sources = evaluation_result.get("llm_sources") or []
    tech_market: list[dict] = []
    papers_reports: list[dict] = []
    for src in llm_sources:
        url = str(src.get("url") or "")
        if any(kw in url for kw in ("arxiv", "ieee", "scholar", "springer", "ncbi", "kci")):
            papers_reports.append(src)
        else:
            tech_market.append(src)

    # 사내 프로젝트 RAG 출처
    biz_sources = (evaluation_result.get("evidence") or {}).get("business_use", {})
    project_sources: list[dict] = []
    if isinstance(biz_sources, dict):
        project_sources = biz_sources.get("sources") or []

    # KIPRIS 유사 특허 출처
    kipris_sources: list[dict] = []
    if similar_analysis:
        for pat in (similar_analysis.get("similar_patents") or [])[:10]:
            entry = {
                "patent_no": pat.get("patent_no", ""),
                "title": pat.get("title", ""),
                "applicant": pat.get("applicant", ""),
                "legal_status": pat.get("legal_status", ""),
                "similarity_score": (pat.get("similarity") or {}).get("overall", 0.0),
            }
            kipris_sources.append(entry)

    # API/LLM 분석 참고
    api_llm_sources = [
        {
            "source": "OpenAI GPT-4o-mini",
            "usage": "43개 항목 LLM 기반 평가",
        },
        {
            "source": "KOSIS (통계청)",
            "usage": "산업 성장률 조회 (시장 성장성 점수)",
        },
        {
            "source": "Tavily Web Search",
            "usage": "LLM 평가 보조 웹 검색 증거 수집",
        },
    ]

    all_src = _dedup_sources(tech_market + papers_reports + project_sources)

    return {
        "title": "참고 문헌",
        "evaluation_standard": {
            "title": "IP가치평가 실무가이드 Chapter 4",
            "publisher": "특허청·한국발명진흥회·KISTI",
            "published_year": 2021,
        },
        "tech_market_sources": tech_market,
        "papers_and_reports": papers_reports,
        "project_rag_sources": project_sources,
        "kipris_similar_patent_sources": kipris_sources,
        "api_llm_sources": api_llm_sources,
        "all_sources_deduplicated": all_src,
    }


# ─────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────

def build_structured_report(
    evaluation_result: dict[str, Any],
    similar_analysis: dict[str, Any] | None = None,
    evaluation_analysis: str = "",
) -> dict[str, Any]:
    """모든 섹션을 담은 구조화 JSON 보고서를 생성합니다.

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
    all_scores = auto_scores + llm_scores

    dim_stats = _dim_stats(all_scores)
    dim_avgs = [d["average_score"] for d in dim_stats.values()]
    overall_score = round(sum(dim_avgs) / len(dim_avgs), 2) if dim_avgs else 0.0

    summary_steps = (evaluation_result.get("summary") or {}).get("steps") or []
    exec_time = (evaluation_result.get("summary") or {}).get("execution_time_seconds")

    return {
        "report_id": report_id,
        "generated_at": now.isoformat(),
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_metadata": {
            "title": "IP 가치 평가 보고서",
            "evaluation_date": evaluated_on.isoformat(),
            "score_display_scale": "0~100",
            "item_score_scale": "1~5",
            "table_of_contents": [
                {"section": 1, "key": "section_1_summary", "title": "평가 요약"},
                {"section": 2, "key": "section_2_detailed_scores", "title": "평가 기준별 상세 점수"},
                {"section": 3, "key": "section_3_project_utilization", "title": "사내 프로젝트 활용 현황"},
                {"section": 4, "key": "section_4_similar_patents", "title": "유사 특허 분석"},
                {"section": 5, "key": "section_5_review_items", "title": "추가 확인 필요 사항"},
                {"section": 6, "key": "section_6_references", "title": "참고 문헌"},
            ],
        },
        "patent": _build_patent_info(evaluation_result, evaluated_on),
        "section_1_summary": _build_section1_summary(
            evaluation_result, all_scores, dim_stats, overall_score,
            similar_analysis, evaluation_analysis,
        ),
        "section_2_detailed_scores": _build_section2_detailed_scores(auto_scores, llm_scores),
        "section_3_project_utilization": _build_section3_project(evaluation_result),
        "section_4_similar_patents": _build_section4_similar(similar_analysis),
        "section_5_review_items": _build_section5_review_items(all_scores),
        "section_6_references": _build_section6_references(evaluation_result, similar_analysis),
        "pipeline": {
            "steps": summary_steps,
            "execution_time_seconds": exec_time,
        },
    }
