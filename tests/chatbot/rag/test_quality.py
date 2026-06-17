from __future__ import annotations

from chatbot.app.rag.quality import evidence_quality, filter_usable_hits, preprocess_evidence_text


def test_preprocess_evidence_text_removes_low_value_lines_and_duplicates() -> None:
    text = """
    관련 근거를 찾지 못했습니다.
    제조 공정의 이미지 데이터를 분석해 결함 유형을 분류합니다.
    제조 공정의 이미지 데이터를 분석해 결함 유형을 분류합니다.
    """

    assert preprocess_evidence_text(text) == "제조 공정의 이미지 데이터를 분석해 결함 유형을 분류합니다."


def test_evidence_quality_flags_negative_placeholder() -> None:
    quality = evidence_quality("관련 근거를 찾지 못했습니다.")

    assert quality["usable"] is False
    assert "negative_placeholder" in quality["reasons"]


def test_filter_usable_hits_keeps_clean_evidence_and_adds_quality_metadata() -> None:
    hits = [
        {"excerpt": "검색 결과가 없습니다.", "metadata": {"source_type": "wiki"}},
        {
            "excerpt": "본 기술은 제조 이미지와 센서 신호를 함께 분석하여 불량 원인을 추정합니다.",
            "metadata": {"source_type": "report"},
        },
    ]

    filtered = filter_usable_hits(hits)

    assert len(filtered) == 1
    assert filtered[0]["metadata"]["source_type"] == "report"
    assert filtered[0]["metadata"]["evidence_quality"]["usable"] is True

