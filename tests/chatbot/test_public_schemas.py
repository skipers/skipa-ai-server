from __future__ import annotations

from chatbot.app.schemas import AnswerSourceCard, PublicAnswerSourceCard, PublicChatResponse


def test_public_source_card_omits_internal_metadata() -> None:
    internal = AnswerSourceCard.model_validate(
        {
            "label": "근거 1",
            "display_title": "보고서 / 요약",
            "source_type": "REPORT_PDF",
            "snippet": "핵심 근거",
            "metadata": {"debug": "internal"},
        }
    )
    public = PublicAnswerSourceCard.model_validate(internal.model_dump())

    dumped = public.model_dump()
    assert "metadata" not in dumped
    assert dumped["label"] == "근거 1"
    assert dumped["snippet"] == "핵심 근거"


def test_public_chat_response_defaults_collections() -> None:
    response = PublicChatResponse.model_validate(
        {
            "query": "요약해줘",
            "patent_id": None,
            "answer": "답변",
        }
    )

    assert response.source_cards == []
    assert response.metrics == {}

