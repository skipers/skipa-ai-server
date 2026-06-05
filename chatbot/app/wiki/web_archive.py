"""Helpers for topic-based wiki archive files."""

from __future__ import annotations

from pathlib import Path

from .topics import get_patent_topic, topic_wiki_root


def list_wiki_files(patent_id: str) -> list[Path]:
    """Return wiki files for the topic that *patent_id* belongs to."""
    wiki_root = topic_wiki_root(get_patent_topic(patent_id))
    if not wiki_root.exists():
        return []
    return [path for path in sorted(wiki_root.rglob("*")) if path.is_file()]
