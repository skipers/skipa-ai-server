from __future__ import annotations

from datetime import datetime

from pre_application_valuation.diagnostics import build_diagnostics, estimate_ipc, keyword_summary
from pre_application_valuation.report_builder import build_report
from pre_application_valuation.schemas import PreApplicationValuationRequest


def test_build_report_produces_frontend_contract_sections() -> None:
    request = PreApplicationValuationRequest.model_validate(
        {
            "patentName": "AI 기반 제조 품질 예측 플랫폼",
            "technologyDescription": "센서와 이미지 데이터를 분석해 품질 문제를 예측하고 불량률을 10% 감소시킨다. "
            * 12,
            "claims": [
                "센서 데이터를 수집하는 장치",
                "품질 문제를 예측하는 방법",
                "컴퓨터가 상기 방법을 실행하는 프로그램 기록매체",
            ],
            "relatedBusiness": "스마트팩토리 품질 관리 플랫폼과 구독형 운영 서비스에 적용한다.",
            "targetCountries": ["KR", "US"],
        }
    )
    diagnostics = build_diagnostics(request)
    ipc = estimate_ipc(request)
    keywords = keyword_summary(request)
    evaluation = {
        "source": "test",
        "model": "rule-based",
        "overall_opinion": "출원 전 보완 후 검토 가능",
        "score_items": [
            {"dimension": "technology_readiness", "item": "기술 구체성", "score": 4, "reason": "구체성 높음"},
            {"dimension": "claimability", "item": "청구항 구조", "score": 3, "next_actions": ["독립항 보완"]},
            {"dimension": "business_hypothesis", "item": "사업 가설", "score": 3, "risks": ["고객 검증 부족"]},
            {"dimension": "filing_readiness", "item": "출원 준비", "score": 2, "risks": ["선행기술 조사 부족"]},
        ],
    }

    report = build_report(
        evaluation_id="eval-test",
        evaluated_at=datetime(2026, 6, 17, 12, 0, 0),
        request=request,
        diagnostics=diagnostics,
        ipc=ipc,
        keywords=keywords,
        evaluation=evaluation,
    )

    assert report["evaluation_id"] == "eval-test"
    assert report["evaluated_at"] == "2026-06-17T12:00:00"
    assert report["metadata"]["report_type"] == "pre_application_valuation"
    assert report["input_summary"]["claim_count"] == 3
    assert len(report["dimensions"]) == 4
    assert report["frontend_summary"]["overall_score"] == report["executive_summary"]["score_out_of_100"]
    assert report["filing_investment_decision"]["decision"] in {
        "go_to_prior_art_search_and_drafting",
        "revise_then_file",
        "hold_for_value_validation",
        "do_not_file_yet",
    }

