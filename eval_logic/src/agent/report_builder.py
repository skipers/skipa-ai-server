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

from datetime import datetime
from typing import Any


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
    for dim, items in by_dim.items():
        vals = [float(s["score"]) for s in items if isinstance(s.get("score"), (int, float))]
        avg = round(sum(vals) / len(vals), 2) if vals else 0.0
        result[dim] = {
            "average_score": avg,
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

def _build_patent_info(result: dict[str, Any]) -> dict[str, Any]:
    meta = result.get("meta") or {}
    legal = result.get("legal") or {}
    return {
        "id": result.get("patent_id", ""),
        "title": result.get("title", ""),
        "registration_number": meta.get("registration_number") or result.get("patent_id", ""),
        "application_date": meta.get("application_date"),
        "registration_date": meta.get("registration_date"),
        "ipc_codes": meta.get("ipc") or [],
        "cpc_codes": meta.get("cpc") or [],
        "assignee": meta.get("assignee") or [],
        "inventors": meta.get("inventors") or [],
        "total_claims": meta.get("total_claims"),
        "legal_status": legal.get("legal_status"),
        "remaining_years": legal.get("legal_remaining_years"),
    }


def _build_section1_summary(
    evaluation_result: dict[str, Any],
    all_scores: list[dict[str, Any]],
    dim_stats: dict[str, Any],
    overall_score: float,
    similar_analysis: dict[str, Any] | None,
    agent_analysis: str,
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
            "published_or_pending_count": eco.get("published_or_pending_count", 0),
            "rejected_or_expired_count": eco.get("rejected_or_expired_count", 0),
            "avg_similarity": round(sum(sim_scores) / len(sim_scores), 4) if sim_scores else 0.0,
        }

    return {
        "title": "평가 요약",
        "overall_score": overall_score,
        "overall_grade": _to_grade(overall_score),
        "risk_level": _to_risk(overall_score),
        "dimension_scores": {
            dim: {
                "average_score": data["average_score"],
                "grade": data["grade"],
                "item_count": data["item_count"],
            }
            for dim, data in dim_stats.items()
        },
        "project_utilization_brief": project_brief,
        "similar_patents_brief": similar_brief,
        "overall_opinion": agent_analysis,
    }


def _build_section2_detailed_scores(
    auto_scores: list[dict[str, Any]],
    llm_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    """2. 평가 기준별 상세 점수"""
    all_scores = auto_scores + llm_scores
    by_dim = _dim_items(all_scores)

    dim_detail: dict[str, Any] = {}
    for dim, items in by_dim.items():
        dim_detail[dim] = {
            "items": [
                {
                    "item": s.get("item", ""),
                    "score": s.get("score"),
                    "method": s.get("method", ""),
                    "judgment_basis": s.get("basis") or s.get("reason") or "",
                    "sources": s.get("sources") or [],
                }
                for s in items
            ]
        }

    all_src = _collect_all_sources(all_scores)
    return {
        "title": "평가 기준별 상세 점수",
        "dimensions": dim_detail,
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
        "commercialization_status": biz.get("commercialization_status") or "미확인",
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
            "title": item.get("title", ""),
            "applicant": item.get("applicant", ""),
            "legal_status": item.get("legal_status", ""),
            "citation_count": item.get("citation_count", 0),
            "similarity_score": sim.get("overall", 0.0),
            "common_points": comp.get("common_points") or [],
            "differences": comp.get("differences") or [],
            "analysis_summary": comp.get("summary", ""),
            "technical_analysis": {
                "technical_overlap": tech.get("technical_overlap", ""),
                "technical_difference": tech.get("technical_difference", ""),
                "scope_comparison": tech.get("scope_comparison", ""),
                "maintenance_implication": tech.get("maintenance_implication", ""),
            },
        })

    all_patents = similar_analysis.get("similar_patents") or []
    patent_list = []
    for p in all_patents[:10]:  # 상위 10건
        sim = p.get("similarity") or {}
        src = p.get("source_detail") or {}
        patent_list.append({
            "application_number": p.get("application_number", ""),
            "title": p.get("title", ""),
            "applicant": p.get("applicant", ""),
            "application_year": src.get("application_date", "")[:4] if src.get("application_date") else "",
            "similarity_score": sim.get("overall", 0.0),
            "citation_count": p.get("citation_count", 0),
            "legal_status": p.get("legal_status", ""),
        })

    interp = similar_analysis.get("interpretation") or {}
    return {
        "title": "유사 특허 분석",
        "available": True,
        "top_comparisons": top_list,
        "patent_list": patent_list,
        "competitive_analysis": {
            "maintenance_signal": interp.get("maintenance_signal", ""),
            "competition_intensity": interp.get("competition_intensity", ""),
            "differentiation_risk": interp.get("differentiation_risk", ""),
            "invalidity_or_designaround_risk": interp.get("invalidity_or_designaround_risk", ""),
            "decision_comment": interp.get("decision_comment", ""),
        },
    }


def _build_section5_review_items(all_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """5. 추가 확인 필요 사항 (점수 낮은 항목)"""
    review_map = {
        "특허활용 활성도": "특허출원 활성도 검토",
        "대체기술": "대체기술 및 경쟁성 검토",
        "IP 원천성": "IP 확보성 검토",
        "권리의 충실성": "권리 충실성 검토",
        "차별성": "차별성 및 파급성 검토",
        "무효 가능성": "무효 가능성 검토",
    }

    items = []
    for s in all_scores:
        score = s.get("score", 5)
        if not isinstance(score, (int, float)):
            continue
        if score > 3:
            continue
        priority = "urgent" if score <= 1 else ("high" if score == 2 else "medium")
        item_name = s.get("item", "")
        category = next(
            (label for key, label in review_map.items() if key in item_name),
            f"{s.get('dim', '')} - {item_name}",
        )
        items.append({
            "category": category,
            "item": item_name,
            "dim": s.get("dim", ""),
            "score": score,
            "reason": s.get("basis") or s.get("reason") or "",
            "review_priority": priority,
        })
    items.sort(key=lambda x: x["score"])

    return {
        "title": "추가 확인 필요 사항",
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
    agent_analysis: str = "",
) -> dict[str, Any]:
    """모든 섹션을 담은 구조화 JSON 보고서를 생성합니다.

    Args:
        evaluation_result: PatentEvaluationOutput.to_dict() 결과
        similar_analysis:  similar_patent_analyzer.analyze_similar_patents() 결과
        agent_analysis:    에이전트가 작성한 종합 분석 텍스트
    """
    patent_id = evaluation_result.get("patent_id") or "unknown"
    now = datetime.now()
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
        "schema_version": "2.0",
        "patent": _build_patent_info(evaluation_result),
        "section_1_summary": _build_section1_summary(
            evaluation_result, all_scores, dim_stats, overall_score,
            similar_analysis, agent_analysis,
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
