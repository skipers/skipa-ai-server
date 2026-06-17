from __future__ import annotations

from pre_application_valuation.diagnostics import build_diagnostics, claim_categories, is_korea, looks_dependent
from pre_application_valuation.schemas import PreApplicationValuationRequest


def test_build_diagnostics_detects_gaps_for_sparse_input() -> None:
    request = PreApplicationValuationRequest.model_validate(
        {
            "patentName": "간단 아이디어",
            "technologyDescription": "AI로 처리한다.",
            "claims": ["AI 처리 시스템"],
            "relatedBusiness": "",
            "targetCountries": [],
        }
    )

    diagnostics = build_diagnostics(request)

    gap_types = {gap["type"] for gap in diagnostics["gaps"]}
    assert diagnostics["claims"]["count"] == 1
    assert diagnostics["claims"]["has_device_claim"] is True
    assert "description" in gap_types
    assert "claims" in gap_types
    assert "business" in gap_types
    assert "filing_strategy" in gap_types


def test_build_diagnostics_recognizes_claim_categories_and_overseas_strategy() -> None:
    request = PreApplicationValuationRequest.model_validate(
        {
            "patentName": "제조 진단 플랫폼",
            "technologyDescription": "센서 데이터와 이미지 데이터를 분석하여 공정 문제와 품질 위험을 예측한다. "
            * 20,
            "claims": [
                "센서 데이터를 분석하는 장치",
                "제1항에 있어서 이미지 데이터를 더 분석하는 방법",
                "컴퓨터가 상기 방법을 실행하도록 하는 프로그램 기록매체",
            ],
            "relatedBusiness": "스마트팩토리 품질 관리 플랫폼을 구독형 서비스로 제공한다. 현장 설비와 연동한다.",
            "targetCountries": ["KR", "US"],
        }
    )

    diagnostics = build_diagnostics(request)

    assert diagnostics["claims"]["has_device_claim"] is True
    assert diagnostics["claims"]["has_method_claim"] is True
    assert diagnostics["claims"]["has_media_claim"] is True
    assert diagnostics["claims"]["dependent_like_count"] == 1
    assert diagnostics["strategy"]["has_overseas_target"] is True


def test_claim_helpers_classify_common_patterns() -> None:
    assert looks_dependent("제1항에 있어서 추가 센서를 더 포함하는 시스템") is True
    assert looks_dependent("센서 데이터를 수집하는 시스템") is False
    assert claim_categories(["처리 방법", "분석 서버", "프로그램 기록매체"]) == {"방법", "장치", "매체"}
    assert is_korea("KR") is True
    assert is_korea("US") is False

