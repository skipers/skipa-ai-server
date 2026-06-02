"""RAG helpers for the chatbot agent."""

from __future__ import annotations

from typing import Any


def answer_question(*args: Any, **kwargs: Any) -> Any:
    from .pipeline import answer_question as _answer_question

    return _answer_question(*args, **kwargs)

__all__ = ["answer_question"]
