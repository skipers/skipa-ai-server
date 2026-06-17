from __future__ import annotations

from pre_application_valuation.text_normalizer import (
    normalize_grade,
    normalize_report_sentence,
    normalize_string_list,
)


def test_normalize_grade_accepts_labels_and_scores() -> None:
    assert normalize_grade("a+") == "A"
    assert normalize_grade("", score=92) == "S"
    assert normalize_grade(None, score=3.2) == "B"
    assert normalize_grade("unknown") == "D"


def test_normalize_report_sentence_makes_formal_sentence() -> None:
    assert normalize_report_sentence("기술 차별성이 높다") == "기술 차별성이 높습니다."
    assert normalize_report_sentence("권리 범위 보완 필요") == "권리 범위 보완 필요합니다."


def test_normalize_string_list_filters_empty_items() -> None:
    assert normalize_string_list(["차별성 높음", "", "사업화 가능"]) == [
        "차별성 높습니다.",
        "사업화 가능합니다.",
    ]

