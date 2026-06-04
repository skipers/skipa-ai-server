"""Small Ollama client used by the chatbot agent."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .config import LLM_TIMEOUT, OPENAI_API_KEY, OPENAI_BASE_URL, OLLAMA_BASE_URL, OLLAMA_TEMPERATURE


def call_ollama(
    prompt: str,
    *,
    model: str,
    num_predict: int,
    temperature: float = OLLAMA_TEMPERATURE,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Call Ollama generate API and return a normalized result.

    The function is intentionally dependency-light so the restored chatbot can
    run with only the existing FastAPI requirements.
    """
    if not model:
        return {"ok": False, "text": "", "error": "model is empty"}

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }
    request = Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout or LLM_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "text": "", "error": str(exc)}

    text = str(data.get("response") or "").strip()
    return {
        "ok": bool(text),
        "text": text,
        "error": None if text else "empty response",
        "model": model,
        "raw": data,
    }


def _openai_output_text(data: dict[str, Any]) -> str:
    if data.get("output_text"):
        return str(data.get("output_text") or "").strip()
    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                chunks.append(str(content.get("text") or ""))
    return "".join(chunks).strip()


def call_openai_json(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
    model: str,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Call OpenAI Responses API and require a JSON-schema-shaped answer."""
    if not OPENAI_API_KEY:
        return {"ok": False, "text": "", "error": "OPENAI_API_KEY is not configured", "model": model, "provider": "openai"}
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "intent_route",
                "schema": schema,
                "strict": True,
            }
        },
    }
    request = Request(
        f"{OPENAI_BASE_URL}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout or LLM_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "text": "", "error": str(exc), "model": model, "provider": "openai"}
    text = _openai_output_text(data)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "text": text,
            "error": f"OpenAI JSON parse failed: {exc}",
            "model": model,
            "provider": "openai",
            "raw": data,
        }
    if not isinstance(parsed, dict):
        return {
            "ok": False,
            "text": text,
            "error": "OpenAI JSON output root is not object",
            "model": model,
            "provider": "openai",
            "raw": data,
        }
    return {"ok": True, "text": json.dumps(parsed, ensure_ascii=False), "json": parsed, "error": None, "model": model, "provider": "openai", "raw": data}


def call_openai_messages(
    *,
    messages: list[dict[str, str]],
    model: str,
    timeout: int | None = None,
) -> dict[str, Any]:
    """Dependency-light OpenAI chat fallback for legacy JSON-only intent prompts."""
    if not OPENAI_API_KEY:
        return {"ok": False, "text": "", "error": "OPENAI_API_KEY is not configured", "model": model, "provider": "openai"}
    payload = {
        "model": model,
        "input": [
            {"role": item.get("role") or "user", "content": [{"type": "input_text", "text": str(item.get("content") or "")}]}
            for item in messages
        ],
    }
    request = Request(
        f"{OPENAI_BASE_URL}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout or LLM_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"ok": False, "text": "", "error": str(exc), "model": model, "provider": "openai"}
    text = _openai_output_text(data)
    return {"ok": bool(text), "text": text, "error": None if text else "empty response", "model": model, "provider": "openai", "raw": data}
