from __future__ import annotations

from pathlib import Path

from chatbot.app.rag.sources import cards_from_hits, cards_from_web


def test_cards_from_hits_filters_unusable_hits_and_enriches_metadata(tmp_path) -> None:
    source_path = tmp_path / "report.json"
    source_path.write_text("{}", encoding="utf-8")
    hits = [
        {"excerpt": "검색 결과가 없습니다.", "metadata": {"source_type": "WIKI"}},
        {
            "excerpt": (
                "제조 공정 이미지와 센서 데이터를 함께 분석하여 불량 원인을 추정하고, "
                "품질 저하 위험을 조기에 감지해 현장 작업자에게 근거 정보를 제공합니다."
            ),
            "score": 0.82,
            "metadata": {
                "source_type": "REPORT_PDF",
                "title": "제조 품질 보고서",
                "section_title": "핵심 근거",
                "page": "5",
                "source_path": str(source_path),
            },
        },
    ]

    cards = cards_from_hits(hits, query="제조 공정 불량")

    assert len(cards) == 1
    assert cards[0]["label"] == "근거 1"
    assert cards[0]["source_type"] == "REPORT_PDF"
    assert cards[0]["page_no"] == 5
    assert cards[0]["metadata"]["retrieval_score"] == 0.82
    assert cards[0]["match_terms"] == ["제조", "공정", "불량"]


def test_cards_from_web_uses_web_labels_and_public_url() -> None:
    cards = cards_from_web(
        [
            {
                "title": "KIPO 안내",
                "url": "https://example.com/kipo",
                "snippet": "특허 출원 절차 안내입니다.",
                "source_type": "search",
            }
        ],
        start_index=3,
        query="특허 출원 절차",
    )

    assert cards[0]["label"] == "웹 근거 3"
    assert cards[0]["source_type"] == "WEB"
    assert cards[0]["url"] == "https://example.com/kipo"
    assert cards[0]["metadata"]["provider_source_type"] == "search"
