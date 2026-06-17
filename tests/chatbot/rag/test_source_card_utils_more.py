from __future__ import annotations

from chatbot.app.rag.source_card_utils import (
    compact_text,
    match_terms_from_query,
    normalize_match_terms,
    source_display_title,
    source_location_label,
)


def test_source_display_title_falls_back_to_clean_file_name() -> None:
    title = source_display_title(
        {"source_path": "data/reports/202606_report.final.pdf"},
        {},
    )

    assert title == "202606_report.final"


def test_source_location_label_combines_available_metadata() -> None:
    label = source_location_label(
        {},
        {
            "source_type": "REPORT_PDF",
            "page": 12,
            "section_title": "상세 점수",
            "chunk_id": "chunk-3",
            "file_name": "report.json",
        },
    )

    assert "REPORT_PDF" in label
    assert "p.12" in label
    assert "상세 점수" in label
    assert "report.json" in label


def test_match_terms_from_query_keeps_unique_terms_in_order() -> None:
    terms = match_terms_from_query(
        "AI 품질 품질 예측 비용",
        "AI 기반 품질 예측 시스템은 비용 절감을 지원한다.",
    )

    assert terms == ["AI", "품질", "예측", "비용"]


def test_normalize_match_terms_and_compact_text() -> None:
    assert normalize_match_terms("품질") == ["품질"]
    assert normalize_match_terms(["품질", "", "예측"]) == ["품질", "예측"]
    assert compact_text("abcdef", limit=5) == "ab..."

