from __future__ import annotations

from chatbot.app.rag.source_card_utils import enrich_source_card, replace_answer_citation_labels


def test_enrich_source_card_builds_display_fields_from_metadata() -> None:
    card = {
        "label": "근거 1",
        "snippet": "청구항은 이미지 수집과 결함 분류를 포함합니다.",
        "metadata": {
            "title": "AI 기반 불량 검출 시스템",
            "section_title": "청구항 분석",
            "page_no": 3,
            "source_path": "reports/patent_report.pdf",
        },
    }

    enriched = enrich_source_card(card, query="이미지 결함 분류")

    assert enriched["display_title"] == "AI 기반 불량 검출 시스템 / 청구항 분석"
    assert "p.3" in enriched["location_label"]
    assert enriched["source_path"] == "reports/patent_report.pdf"
    assert enriched["match_terms"] == ["이미지", "결함", "분류"]


def test_replace_answer_citation_labels_uses_short_titles() -> None:
    cards = [
        {
            "label": "근거 1",
            "display_title": "AI 기반 불량 검출 시스템 / 청구항 분석",
            "metadata": {"citation_label": "근거 1"},
        }
    ]

    answer = replace_answer_citation_labels("해당 내용은 [근거 1]에서 확인됩니다.", cards)

    assert "[근거 1]" not in answer
    assert "AI 기반 불량 검출 시스템" in answer

