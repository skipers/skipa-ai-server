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


def normalize_report_sentence(value: Any) -> str:
    """Normalize one Korean report sentence to a polite report style."""
    text = re.sub(r"\s+", " ", str(value or "")).strip().rstrip(" ,;")
    if not text:
        return ""
    if re.fullmatch(r"(?:\[출처\d+\]\s*)+(?:\.?입니다)?\.?", text):
        return ""

    text = text.replace("습니다로 확인됩니다", "습니다")
    text = text.replace("있다로 확인됩니다", "있습니다")
    text = text.replace("필요가 있다로 확인됩니다", "필요합니다")
    text = text.replace("없으로 확인됩니다", "없습니다")
    text = text.replace("낮으로 확인됩니다", "낮습니다")
    text = text.replace("높으로 확인됩니다", "높습니다")
    text = text.replace("있다입니다", "있습니다")
    text = text.replace("수준임을", "수준으로")
    text = text.replace(".입니다.", ".")
    text = text.replace(".입니다", ".")
    text = re.sub(
        r"(니다|습니다|됩니다|합니다|입니다|보입니다|필요합니다|예상됩니다|확인됩니다)\.입니다\.?",
        r"\1.",
        text,
    )
    malformed_endings = {
        "있다.입니다": "있습니다",
        "한다.입니다": "합니다",
        "된다.입니다": "됩니다",
        "준다.입니다": "줍니다",
        "높다.입니다": "높습니다",
        "낮다.입니다": "낮습니다",
        "어렵다.입니다": "어렵습니다",
        "같다.입니다": "같습니다",
        "상태다.입니다": "상태입니다",
        "수준이다.입니다": "수준입니다",
        "내렸다.입니다": "내렸습니다",
    }
    for bad, good in malformed_endings.items():
        if text.endswith(f"{bad}."):
            text = f"{text[: -len(bad) - 1]}{good}."
            break
        if text.endswith(bad):
            text = f"{text[: -len(bad)]}{good}."
            break
    text = re.sub(r"(\d+(?:\.\d+)?%?\s*\([^)]*\))\.입니다\.?", r"\1입니다.", text)
    text = re.sub(r"(\d+(?:\.\d+)?%?)\.입니다\.?", r"\1입니다.", text)
    text = re.sub(r"(\[출처\d+\])(?:\.?입니다)?\.?$", r"\1.", text)
    text = re.sub(r"\.{2,}$", ".", text)

    trailing_sources = ""
    source_match = re.match(r"^(.*?)(\s*(?:\[출처\d+\]\s*)+)\.?$", text)
    if source_match:
        text = source_match.group(1).rstrip(" ,;.")
        trailing_sources = source_match.group(2).strip()

    replacements = {
        "포함하고 있다": "포함하고 있습니다",
        "제시하고 있다": "제시하고 있습니다",
        "기술하고 있다": "기술하고 있습니다",
        "가지고 있다": "가지고 있습니다",
        "시사하고 있다": "시사하고 있습니다",
        "수 있다": "수 있습니다",
        "있다": "있습니다",
        "이다": "입니다",
        "하다": "합니다",
        "한다": "합니다",
        "된다": "됩니다",
        "준다": "줍니다",
        "다룬다": "다룹니다",
        "가진다": "가집니다",
        "갖는다": "갖습니다",
        "제공한다": "제공합니다",
        "도모한다": "도모합니다",
        "증대시킨다": "증대시킵니다",
        "향상시킨다": "향상시킵니다",
        "만든다": "만듭니다",
        "기여한다": "기여합니다",
        "개선한다": "개선합니다",
        "나타낸다": "나타냅니다",
        "여겨진다": "여겨집니다",
        "받는다": "받습니다",
        "평가했다": "평가했습니다",
        "평가하였다": "평가했습니다",
        "확인했다": "확인했습니다",
        "않는다": "않습니다",
        "기재됐다": "기재됐습니다",
        "뚜렷하다": "뚜렷합니다",
        "제한적이다": "제한적입니다",
        "효과적이다": "효과적입니다",
        "넓다": "넓습니다",
        "나타난다": "나타납니다",
        "판단된다": "판단됩니다",
        "판단됨": "판단됩니다",
        "확인됨": "확인됩니다",
        "확인된다": "확인됩니다",
        "확인하였다": "확인했습니다",
        "존재한다": "존재합니다",
        "보여준다": "보여줍니다",
        "보인다": "보입니다",
        "보임": "보입니다",
        "필요하다": "필요합니다",
        "필요하다.": "필요합니다.",
        "요구된다": "요구됩니다",
        "예상된다": "예상됩니다",
        "어렵다": "어렵습니다",
        "높다": "높습니다",
        "낮다": "낮습니다",
        "크다": "큽니다",
        "같다": "같습니다",
        "상태다": "상태입니다",
        "수준이다": "수준입니다",
        "내렸다": "내렸습니다",
        "존재함": "존재합니다",
        "갖춤": "갖추고 있습니다",
        "어려움": "어렵습니다",
        "포함": "포함됩니다",
        "기재됨": "기재됩니다",
        "작성됨": "작성됩니다",
        "구성됨": "구성됩니다",
        "포함됨": "포함됩니다",
        "존재": "존재합니다",
        "가능": "가능합니다",
        "필요": "필요합니다",
        "함": "합니다",
    }
    for suffix, formal in replacements.items():
        if text.endswith(f"{suffix}.입니다"):
            sentence = f"{text[: -len(suffix) - 4]}{formal}."
            return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
        if text.endswith(f"{suffix}.입니다."):
            sentence = f"{text[: -len(suffix) - 5]}{formal}."
            return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
        if text.endswith(f"{suffix}."):
            sentence = f"{text[: -len(suffix) - 1]}{formal}"
            if not sentence.endswith("."):
                sentence = f"{sentence}."
            return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
        if text.endswith(suffix):
            sentence = f"{text[: -len(suffix)]}{formal}."
            return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence

    if text.endswith("없음."):
        sentence = f"{text[:-3]}없습니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("없음"):
        sentence = f"{text[:-2]}없습니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("낮음."):
        sentence = f"{text[:-3]}낮습니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("낮음"):
        sentence = f"{text[:-2]}낮습니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("높음."):
        sentence = f"{text[:-3]}높습니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("높음"):
        sentence = f"{text[:-2]}높습니다."
        return f"{sentence[:-2]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("임."):
        sentence = f"{text[:-2]}입니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("임"):
        sentence = f"{text[:-1]}입니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("음."):
        sentence = f"{text[:-2]}으로 확인됩니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("음"):
        sentence = f"{text[:-1]}으로 확인됩니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("것으로 판단."):
        sentence = f"{text[:-7]}것으로 판단됩니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith("것으로 판단"):
        sentence = f"{text[:-6]}것으로 판단됩니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith((
        "니다.",
        "습니다.",
        "됩니다.",
        "합니다.",
        "입니다.",
        "보입니다.",
        "필요합니다.",
        "예상됩니다.",
    )):
        return f"{text[:-1]} {trailing_sources}.".strip() if trailing_sources else text
    if text.endswith((
        "니다",
        "습니다",
        "됩니다",
        "합니다",
        "입니다",
        "보입니다",
        "필요합니다",
        "예상됩니다",
    )):
        sentence = f"{text}."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith((").", "%.", "건.")):
        sentence = f"{text[:-1]}입니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    if text.endswith((")", "%", "건")):
        sentence = f"{text}입니다."
        return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence
    sentence = f"{text}입니다."
    return f"{sentence[:-1]} {trailing_sources}.".strip() if trailing_sources else sentence


def normalize_report_prose(value: Any) -> str:
    """Normalize sentence endings in report prose without changing citations."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[.!?。])\s+", text) if chunk.strip()]
    if len(chunks) <= 1:
        return normalize_report_sentence(text)
    normalized = []
    for chunk in chunks:
        sentence = normalize_report_sentence(chunk)
        if not sentence:
            continue
        if re.fullmatch(r"(?:\[출처\d+\]\s*)+\.?", sentence):
            continue
        normalized.append(sentence)
    return " ".join(normalized)
