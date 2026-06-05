"""Path helpers for shared chatbot data."""

from __future__ import annotations

from pathlib import Path

from ..config import DATA_ROOT, PATENTS_ROOT


def data_path(*parts: str) -> Path:
    return DATA_ROOT.joinpath(*parts)


def patent_path(patent_id: str, *parts: str) -> Path:
    return PATENTS_ROOT.joinpath(patent_id, *parts)
