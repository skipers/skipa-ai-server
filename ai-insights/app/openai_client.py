"""Small dependency-light OpenAI Responses API client."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests


DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4.1-mini"


def load_env_value(key: str) -> str:
    value = os.environ.get(key)
    if value:
        return value.strip()
    for env_path in _env_paths():
        loaded = _read_env_file(env_path).get(key)
        if loaded:
            os.environ.setdefault(key, loaded)
            return loaded
    return ""


def portfolio_model() -> str:
    return (
        load_env_value("OPENAI_PORTFOLIO_INSIGHTS_MODEL")
        or load_env_value("OPENAI_MODEL")
        or DEFAULT_MODEL
    )


def call_openai_portfolio_insights(
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 30,
) -> dict[str, Any]:
    api_key = load_env_value("OPENAI_API_KEY")
    model = portfolio_model()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    base_url = load_env_value("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
        "temperature": 0.35,
        "max_output_tokens": 700,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "portfolio_insights",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "insights": {
                            "type": "array",
                            "minItems": 3,
                            "maxItems": 3,
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["insights"],
                },
            }
        },
    }
    response = requests.post(
        f"{base_url.rstrip('/')}/responses",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    text = _output_text(data)
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI response root is not an object")
    return {"model": model, "json": parsed, "raw": data}


def _output_text(data: dict[str, Any]) -> str:
    if data.get("output_text"):
        return str(data.get("output_text") or "").strip()
    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                chunks.append(str(content.get("text") or ""))
    text = "".join(chunks).strip()
    if not text:
        raise ValueError("OpenAI response text is empty")
    return text


def _env_paths() -> list[Path]:
    app_dir = Path(__file__).resolve().parents[1]
    repo_root = app_dir.parent
    return [
        app_dir / ".env",
        repo_root / ".env",
        repo_root / "chatbot" / ".env",
        repo_root / "eval_logic" / ".env",
    ]


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values
