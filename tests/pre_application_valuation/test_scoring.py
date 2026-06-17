from __future__ import annotations

from pre_application_valuation.schemas import PreApplicationValuationRequest
from pre_application_valuation.scoring import calculate_scores, estimate_ipc, grade_for_score, keyword_summary


def _strong_ai_request() -> PreApplicationValuationRequest:
    return PreApplicationValuationRequest.model_validate(
        {
            "patentName": "AI 기반 제조 품질 예측 플랫폼",
            "technologyDescription": (
                "제조 공정 이미지 데이터와 센서 데이터를 실시간으로 분석하고, "
                "인공지능 학습 모델이 결함 유형을 분류하며 품질 저하를 예측한다. "
                "기존 수동 검사 대비 불량률 감소, 검사 시간 절감, 공정 효율 향상을 목표로 한다. "
                "서버 모듈은 입력 데이터 전처리, 예측 알고리즘 실행, 경보 출력 단계를 자동으로 수행한다."
            ),
            "claims": [
                "이미지 데이터와 센서 데이터를 수집하는 시스템",
                "상기 시스템에 있어서 결함 유형을 분류하는 학습 모델",
                "제조 품질 예측 방법으로서 데이터 전처리 단계와 예측 점수 산출 단계를 포함하는 방법",
                "컴퓨터가 상기 방법을 실행하도록 하는 프로그램 기록매체",
                "품질 저하 예측 결과를 현장 단말에 제공하는 서버",
            ],
            "relatedBusiness": "스마트팩토리 품질 관리 서비스와 월 구독형 공정 운영 플랫폼에 적용한다.",
            "targetCountries": ["KR", "US", "EP"],
        }
    )


def test_estimate_ipc_detects_ai_keywords() -> None:
    ipc = estimate_ipc(_strong_ai_request())

    assert ipc["ipc"] == "G06N 20/00"
    assert ipc["confidence"] == "high"
    assert "인공지능" in ipc["matched_keywords"]


def test_calculate_scores_returns_weighted_dimensions_and_items() -> None:
    result = calculate_scores(_strong_ai_request())

    assert 1 <= result["overall_score"] <= 5
    assert result["overall_grade"] in {"S", "A", "B", "C", "D"}
    assert len(result["dimensions"]) == 3
    assert len(result["score_items"]) == 9
    assert {dimension["key"] for dimension in result["dimensions"]} == {"technology", "rights", "business"}


def test_grade_for_score_thresholds() -> None:
    assert grade_for_score(4.5) == "S"
    assert grade_for_score(4.0) == "A"
    assert grade_for_score(3.0) == "B"
    assert grade_for_score(2.0) == "C"
    assert grade_for_score(1.9) == "D"


def test_keyword_summary_excludes_common_stopwords() -> None:
    keywords = keyword_summary(_strong_ai_request(), limit=5)

    assert "시스템" not in keywords
    assert len(keywords) == 5

