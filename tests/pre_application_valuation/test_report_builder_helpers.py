from __future__ import annotations

from pre_application_valuation.report_builder import (
    build_limitations,
    default_overall_opinion,
    investment_decision_label,
    readiness_level,
    score_to_100,
    summarize_dimensions,
    value_grade_for_score,
    weighted_overall_score,
)


def test_summarize_dimensions_normalizes_scores_and_grades() -> None:
    dimensions = summarize_dimensions(
            [
                {"dimension": "technology_readiness", "score": 5, "reason": "차별성 높음", "risks": ["없음"]},
                {"dimension": "technology_readiness", "score": 3, "reason": "구체성 보통"},
                {"dimension": "claimability", "score": 2, "next_actions": ["청구항 보완 필요"]},
            ]
        )

    technology = next(item for item in dimensions if item["key"] == "technology_readiness")
    rights = next(item for item in dimensions if item["key"] == "claimability")

    assert technology["average_score"] == 4.0
    assert technology["score_out_of_100"] == 80
    assert technology["grade"] == "A"
    assert rights["item_count"] == 1


def test_weighted_overall_score_uses_dimension_weights() -> None:
    dimensions = [
        {"key": "technology_readiness", "average_score": 5},
        {"key": "claimability", "average_score": 3},
        {"key": "business_hypothesis", "average_score": 1},
        {"key": "filing_readiness", "average_score": 2},
    ]

    assert weighted_overall_score(dimensions) == 2.9


def test_report_builder_threshold_helpers() -> None:
    assert score_to_100(4.7) == 94
    assert score_to_100(9) == 100
    assert score_to_100(-1) == 0
    assert value_grade_for_score(4.2) == "high_pre_filing_value"
    assert investment_decision_label(3.8) == "go_to_prior_art_search_and_drafting"
    assert readiness_level(2.2) == "needs_substantial_preparation"


def test_build_limitations_always_includes_default_disclaimers() -> None:
    limitations = build_limitations({"limitations": ["입력 정보가 제한적임"]})

    assert "입력 정보가 제한적입니다." in limitations
    assert any("법적 효력 있는 특허성 의견서가 아닙니다" in item for item in limitations)
    assert any("신규성/진보성 판단은 확정할 수 없습니다" in item for item in limitations)


def test_default_overall_opinion_mentions_weakest_dimension() -> None:
    opinion = default_overall_opinion(3.25, {"label": "권리성"})

    assert "3.25/5" in opinion
    assert "권리성" in opinion
