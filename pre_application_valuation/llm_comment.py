"""LLM-generated overall comment for pre-application valuation."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from .schemas import PreApplicationValuationRequest


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"


def generate_llm_overall_comment(
    request: PreApplicationValuationRequest,
    scoring: dict[str, Any],
    ipc: dict[str, Any],
    fallback_comment: str,
) -> dict[str, Any]:
    """Generate an overall evaluation comment with OpenAI, falling back safely."""
    api_key = _load_env_value("OPENAI_API_KEY")
    model = _load_env_value("OPENAI_REPORT_MODEL") or _load_env_value("OPENAI_MODEL") or DEFAULT_MODEL
    if not api_key:
        return _fallback("OPENAI_API_KEY가 없어 규칙 기반 코멘트를 사용했습니다.", fallback_comment, model)

    prompt = _build_prompt(request, scoring, ipc)
    try:
        response = requests.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model,
                "temperature": 0.2,
                "max_tokens": 700,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a Korean patent valuation analyst. "
                            "Return only one valid JSON object."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = _parse_json_object(content)
        comment = str(parsed.get("overall_comment") or "").strip()
        if not comment:
            return _fallback("LLM 응답에 overall_comment가 없어 규칙 기반 코멘트를 사용했습니다.", fallback_comment, model)
        return {
            "source": "llm",
            "model": model,
            "overall_comment": comment,
            "strengths": _string_list(parsed.get("strengths")),
            "risks": _string_list(parsed.get("risks")),
            "next_actions": _string_list(parsed.get("next_actions")),
            "raw": parsed,
        }
    except Exception as exc:
        return _fallback(f"LLM 코멘트 생성 실패: {exc}", fallback_comment, model)


def _build_prompt(
    request: PreApplicationValuationRequest,
    scoring: dict[str, Any],
    ipc: dict[str, Any],
) -> str:
    dimensions = scoring.get("dimensions") or []
    compact_dimensions = [
        {
            "dimension": item.get("label"),
            "score": item.get("score_out_of_100"),
            "grade": item.get("grade"),
        }
        for item in dimensions
    ]
    claims_text = "\n".join(f"- {claim}" for claim in request.claims[:8]) or "- 청구항 미입력"
    return f"""
아래 출원 전 특허/아이디어를 평가하고, 프론트 화면의 '종합 코멘트'에 넣을 내용을 작성하세요.

[입력]
특허명: {request.patent_name}
기술 설명: {request.technology_description}
청구항:
{claims_text}
관련 사업: {request.related_business or "미입력"}
출원 예정 국가: {", ".join(request.target_countries) or "미입력"}

[규칙 기반 사전 평가 요약]
종합 등급: {scoring.get("overall_grade")}
종합 점수: {scoring.get("overall_score_out_of_100")}/100
차원별 점수: {json.dumps(compact_dimensions, ensure_ascii=False)}
추정 IPC: {ipc.get("ipc")} ({ipc.get("description")})

[작성 기준]
- 한국어로 작성합니다.
- 단순히 점수를 반복하지 말고, 이 특허가 왜 출원 검토 가치가 있는지 또는 무엇이 약한지 평가자 관점으로 설명합니다.
- 기술성, 권리성, 사업성을 모두 한 번씩 언급합니다.
- 실제 선행기술 검색은 수행하지 않았으므로 "선행기술 조사 결과"처럼 확정적으로 말하지 않습니다.
- 전체 코멘트는 2~4문장, 프론트 카드에 바로 넣을 수 있게 자연스럽게 작성합니다.
- JSON 형식만 반환합니다.

반환 형식:
{{
  "overall_comment": "2~4문장 종합 평가 코멘트",
  "strengths": ["강점 1", "강점 2"],
  "risks": ["리스크 1", "리스크 2"],
  "next_actions": ["다음 액션 1", "다음 액션 2"]
}}
""".strip()


def _load_env_value(key: str) -> str:
    value = os.environ.get(key)
    if value:
        return value.strip()
    for env_path in _env_paths():
        loaded = _read_env_file(env_path).get(key)
        if loaded:
            os.environ.setdefault(key, loaded)
            return loaded
    return ""


def _env_paths() -> list[Path]:
    module_dir = Path(__file__).resolve().parent
    server_root = module_dir.parent
    return [
        server_root / ".env",
        server_root / "eval_logic" / ".env",
        server_root / "chatbot" / ".env",
    ]


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object")
    return parsed


def _fallback(reason: str, comment: str, model: str) -> dict[str, Any]:
    return {
        "source": "fallback",
        "model": model,
        "overall_comment": comment,
        "strengths": [],
        "risks": [reason],
        "next_actions": [],
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
