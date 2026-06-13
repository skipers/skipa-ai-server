"""Text and grade normalization helpers for pre-application reports."""

from __future__ import annotations

import re
from typing import Any


def normalize_grade(value: Any, score: float | int | None = None) -> str:
    grade = str(value or "").strip().upper()
    if grade.startswith("S"):
        return "S"
    if grade.startswith("A"):
        return "A"
    if grade.startswith("B"):
        return "B"
    if grade.startswith("C"):
        return "C"
    if grade.startswith("D"):
        return "D"
    if isinstance(score, (int, float)):
        numeric = float(score)
        if numeric > 5:
            numeric = numeric / 20
        if numeric >= 4.5:
            return "S"
        if numeric >= 4.0:
            return "A"
        if numeric >= 3.0:
            return "B"
        if numeric >= 2.0:
            return "C"
    return "D"


def normalize_report_sentence(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().rstrip(" ,;")
    if not text:
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
    text = re.sub(r"\.{2,}$", ".", text)

    replacements = {
        "포함하고 있다": "포함하고 있습니다",
        "제시하고 있다": "제시하고 있습니다",
        "기술하고 있다": "기술하고 있습니다",
        "가지고 있다": "가지고 있습니다",
        "수 있다": "수 있습니다",
        "있다": "있습니다",
        "이다": "입니다",
        "하다": "합니다",
        "한다": "합니다",
        "된다": "됩니다",
        "준다": "줍니다",
        "받는다": "받습니다",
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
        "평가했다": "평가했습니다",
        "평가하였다": "평가했습니다",
        "기재됐다": "기재됐습니다",
        "뚜렷하다": "뚜렷합니다",
        "제한적이다": "제한적입니다",
        "효과적이다": "효과적입니다",
        "넓다": "넓습니다",
        "존재함": "존재합니다",
        "갖춤": "갖추고 있습니다",
        "어려움": "어렵습니다",
        "포함": "포함됩니다",
        "기재됨": "기재됩니다",
        "작성됨": "작성됩니다",
        "구성됨": "구성됩니다",
        "포함됨": "포함됩니다",
        "가능": "가능합니다",
        "필요": "필요합니다",
        "함": "합니다",
    }
    for suffix, formal in replacements.items():
        if text.endswith(f"{suffix}."):
            sentence = f"{text[: -len(suffix) - 1]}{formal}"
            return sentence if sentence.endswith(".") else f"{sentence}."
        if text.endswith(suffix):
            return f"{text[: -len(suffix)]}{formal}."

    if text.endswith("없음."):
        return f"{text[:-3]}없습니다."
    if text.endswith("없음"):
        return f"{text[:-2]}없습니다."
    if text.endswith("낮음."):
        return f"{text[:-3]}낮습니다."
    if text.endswith("낮음"):
        return f"{text[:-2]}낮습니다."
    if text.endswith("높음."):
        return f"{text[:-3]}높습니다."
    if text.endswith("높음"):
        return f"{text[:-2]}높습니다."
    if text.endswith("임."):
        return f"{text[:-2]}입니다."
    if text.endswith("임"):
        return f"{text[:-1]}입니다."
    if text.endswith("음."):
        return f"{text[:-2]}으로 확인됩니다."
    if text.endswith("음"):
        return f"{text[:-1]}으로 확인됩니다."
    if text.endswith((").", "%.", "건.")):
        return f"{text[:-1]}입니다."
    if text.endswith((")", "%", "건")):
        return f"{text}입니다."
    if text.endswith(("니다.", "습니다.", "됩니다.", "합니다.", "입니다.", "보입니다.", "필요합니다.", "예상됩니다.")):
        return text
    if text.endswith(("니다", "습니다", "됩니다", "합니다", "입니다", "보입니다", "필요합니다", "예상됩니다")):
        return f"{text}."
    return f"{text}입니다."


def normalize_report_prose(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    chunks = [chunk.strip() for chunk in re.split(r"(?<=[.!?。])\s+", text) if chunk.strip()]
    if len(chunks) <= 1:
        return normalize_report_sentence(text)
    return " ".join(sentence for sentence in (normalize_report_sentence(chunk) for chunk in chunks) if sentence)


def normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [normalize_report_sentence(item) for item in value if str(item or "").strip()]
