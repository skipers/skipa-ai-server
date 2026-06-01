"""Ingestion compatibility helpers for chatbot data."""

from __future__ import annotations

from typing import Any

from ..vectorstore import refresh_vectorstores


def refresh_indexes(*, use_reviewed: bool = True) -> dict[str, Any]:
    return refresh_vectorstores(use_reviewed=use_reviewed)
