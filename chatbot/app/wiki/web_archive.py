"""Helpers for patent wiki archive files."""

from __future__ import annotations

from pathlib import Path

from ..config import PATENTS_ROOT


def list_wiki_files(patent_id: str) -> list[Path]:
    wiki_root = PATENTS_ROOT / patent_id / "wiki"
    if not wiki_root.exists():
        return []
    return [path for path in sorted(wiki_root.rglob("*")) if path.is_file()]
