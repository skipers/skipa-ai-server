"""Text normalization helpers for frontend report fields."""

from __future__ import annotations

import re
from typing import Any


def normalize_reference_markers(value: Any) -> str:
    """Normalize citation labels used inside report prose.

    All citations are rendered as local source markers: ``[출처1]``.
    """
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""

    text = re.sub(r"\[참고\s*(?:자료|문헌)\s*(\d+)\]", r"[출처\1]", text)
    text = re.sub(r"(?<!\[)참고\s*(?:자료|문헌)\s*(\d+)", r"[출처\1]", text)
    text = re.sub(r"\[출처\s*(\d+)\]", r"[출처\1]", text)
    text = re.sub(r"(?<!\[)출처\s*(\d+)", r"[출처\1]", text)

    def numeric_list(match: re.Match[str]) -> str:
        nums = re.findall(r"\d+", match.group(1))
        return ", ".join(f"[출처{num}]" for num in nums)

    text = re.sub(r"\[((?:\d+\s*,\s*)+\d+)\]", numeric_list, text)
    text = re.sub(r"\[(\d+)\]", r"[출처\1]", text)
    return text


def normalize_local_source_markers(value: Any, source_count: int = 0) -> str:
    """Normalize markers and renumber them within one item's source list."""
    text = normalize_reference_markers(value)
    if not text:
        return ""

    seen: dict[str, int] = {}

    def replace(match: re.Match[str]) -> str:
        original = match.group(1)
        if source_count <= 0:
            return ""
        if original not in seen:
            next_num = len(seen) + 1
            seen[original] = min(next_num, source_count)
        return f"[출처{seen[original]}]"

    text = re.sub(r"\[출처(\d+)\]", replace, text)
    return re.sub(r"\s+", " ", text).strip()
