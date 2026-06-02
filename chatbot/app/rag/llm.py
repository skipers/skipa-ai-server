"""Small Ollama client used by the chatbot agent."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .config import LLM_TIMEOUT, OLLAMA_BASE_URL, OLLAMA_TEMPERATURE


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
