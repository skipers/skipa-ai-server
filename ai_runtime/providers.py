"""Dependency-light model provider helpers.

Set ``AI_PROVIDER=openai`` for OpenAI or ``AI_PROVIDER=opensource`` for
vLLM/SGLang/OpenAI-compatible open-source serving.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests


OPENAI_BASE_URL = "https://api.openai.com/v1"
OPEN_SOURCE_BASE_URL = "http://localhost:8000/v1"
OPEN_SOURCE_LLM_MODEL = "Qwen/Qwen3-235B-A22B-Instruct-2507"
OPEN_SOURCE_EMBEDDING_MODEL = "Qwen/Qwen3-Embedding-8B"
OPEN_SOURCE_RERANKER_MODEL = "Qwen/Qwen3-Reranker-4B"


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


def provider() -> str:
    return (
        load_env_value("AI_PROVIDER")
        or load_env_value("AI_MODE")
        or load_env_value("AI_PROVIDER_PROFILE")
        or load_env_value("LLM_PROVIDER")
        or load_env_value("MODEL_PROVIDER")
        or "openai"
    ).strip().lower()


def is_open_source_provider() -> bool:
    return provider() in {"opensource", "open_source", "openai_compatible", "vllm", "sglang"}


def llm_configured() -> bool:
    if is_open_source_provider():
        return bool(_base_url("llm"))
    return bool(load_env_value("OPENAI_API_KEY"))


def embedding_configured() -> bool:
    if is_open_source_provider():
        return bool(_base_url("embedding"))
    return bool(load_env_value("OPENAI_API_KEY"))


def default_llm_model(*env_names: str) -> str:
    for name in env_names:
        value = load_env_value(name)
        if value:
            return value
    if is_open_source_provider():
        return (
            load_env_value("OPEN_SOURCE_LLM_MODEL")
            or load_env_value("OPEN_SOURCE_REPORT_MODEL")
            or OPEN_SOURCE_LLM_MODEL
        )
    return load_env_value("OPENAI_MODEL") or "gpt-4o-mini"


def default_embedding_model(*env_names: str) -> str:
    for name in env_names:
        value = load_env_value(name)
        if value:
            return value
    if is_open_source_provider():
        return load_env_value("OPEN_SOURCE_EMBEDDING_MODEL") or OPEN_SOURCE_EMBEDDING_MODEL
    return load_env_value("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"


def default_reranker_model(*env_names: str) -> str:
    for name in env_names:
        value = load_env_value(name)
        if value:
            return value
    return load_env_value("OPEN_SOURCE_RERANKER_MODEL") or OPEN_SOURCE_RERANKER_MODEL


def chat_text(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    model_env: tuple[str, ...] = (),
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int = 60,
    json_object: bool = False,
) -> dict[str, Any]:
    model_name = model or default_llm_model(*model_env)
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens:
        payload["max_tokens"] = max_tokens
    if json_object and _request_json_response_format():
        payload["response_format"] = {"type": "json_object"}

    response = requests.post(
        f"{_base_url('llm').rstrip('/')}/chat/completions",
        headers=_headers("llm"),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    text = _chat_output_text(data)
    if not text:
        raise ValueError("LLM response text is empty")
    return {"provider": provider(), "model": model_name, "text": text, "raw": data}


def chat_json(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    model_env: tuple[str, ...] = (),
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    result = chat_text(
        messages=messages,
        model=model,
        model_env=model_env,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        json_object=True,
    )
    parsed = parse_json_object(result["text"])
    return {**result, "json": parsed}


def embed_texts(
    texts: list[str],
    *,
    model: str | None = None,
    model_env: tuple[str, ...] = (),
    timeout: int = 60,
    dimensions: int | None = None,
) -> dict[str, Any]:
    model_name = model or default_embedding_model(*model_env)
    payload: dict[str, Any] = {"model": model_name, "input": texts}
    if dimensions and _request_embedding_dimensions():
        payload["dimensions"] = dimensions
    response = requests.post(
        f"{_base_url('embedding').rstrip('/')}/embeddings",
        headers=_headers("embedding"),
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    items = data.get("data") or []
    vectors = [item.get("embedding") for item in sorted(items, key=lambda item: item.get("index", 0))]
    if len(vectors) != len(texts) or not all(isinstance(vector, list) for vector in vectors):
        raise ValueError("Embedding response shape is invalid")
    return {
        "provider": provider(),
        "model": model_name,
        "embeddings": [[float(value) for value in vector] for vector in vectors],
        "raw": data,
    }


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = str(text or "").strip()
    if "```json" in cleaned:
        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in cleaned:
        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("LLM response root is not an object")
    return parsed


def _base_url(kind: str = "llm") -> str:
    if is_open_source_provider():
        if kind == "embedding":
            value = (
                load_env_value("OPEN_SOURCE_EMBEDDING_BASE_URL")
                or load_env_value("EMBEDDING_BASE_URL")
            )
            if value:
                return value
        return (
            load_env_value("OPEN_SOURCE_LLM_BASE_URL")
            or load_env_value("OPEN_SOURCE_BASE_URL")
            or load_env_value("VLLM_BASE_URL")
            or load_env_value("SGLANG_BASE_URL")
            or load_env_value("OPENAI_BASE_URL")
            or OPEN_SOURCE_BASE_URL
        )
    return load_env_value("OPENAI_BASE_URL") or OPENAI_BASE_URL


def _api_key(kind: str = "llm") -> str:
    if is_open_source_provider():
        if kind == "embedding":
            value = (
                load_env_value("OPEN_SOURCE_EMBEDDING_API_KEY")
                or load_env_value("EMBEDDING_API_KEY")
            )
            if value:
                return value
        return (
            load_env_value("OPEN_SOURCE_LLM_API_KEY")
            or load_env_value("OPEN_SOURCE_API_KEY")
            or load_env_value("VLLM_API_KEY")
            or load_env_value("SGLANG_API_KEY")
            or load_env_value("OPENAI_API_KEY")
            or "EMPTY"
        )
    return load_env_value("OPENAI_API_KEY")


def _headers(kind: str = "llm") -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = _api_key(kind)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _chat_output_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for choice in data.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                chunks.extend(str(item.get("text") or "") for item in content if isinstance(item, dict))
        elif choice.get("text"):
            chunks.append(str(choice.get("text") or ""))
    return "".join(chunks).strip()


def _request_embedding_dimensions() -> bool:
    return load_env_value("EMBEDDING_REQUEST_DIMENSIONS").lower() in {"1", "true", "yes"}


def _request_json_response_format() -> bool:
    value = load_env_value("LLM_REQUEST_JSON_RESPONSE_FORMAT").lower()
    return value not in {"0", "false", "no", "off"}


def _env_paths() -> list[Path]:
    cwd = Path.cwd()
    module_root = Path(__file__).resolve().parents[1]
    base_paths = [
        cwd / ".env",
        module_root / ".env",
        module_root / "chatbot" / ".env",
        module_root / "eval_logic" / ".env",
        module_root / "pre_application_valuation" / ".env",
        module_root / "ai-insights" / ".env",
        module_root / "ai-insights" / "app" / ".env",
    ]
    mode = _selected_mode(base_paths)
    mode_paths = _mode_env_paths(mode, cwd, module_root) if mode else []
    return mode_paths + base_paths


def _selected_mode(base_paths: list[Path]) -> str:
    for key in ("AI_PROVIDER_PROFILE", "AI_MODE"):
        value = os.environ.get(key)
        if value:
            return _sanitize_mode(value)
    for path in base_paths:
        values = _read_env_file(path)
        for key in ("AI_PROVIDER_PROFILE", "AI_MODE"):
            if values.get(key):
                return _sanitize_mode(values[key])
    return ""


def _sanitize_mode(value: str) -> str:
    return "".join(ch for ch in str(value).strip().lower() if ch.isalnum() or ch in {"_", "-"})


def _mode_env_paths(mode: str, cwd: Path, module_root: Path) -> list[Path]:
    filename = f"{mode}.env"
    return [
        cwd / "ai_runtime" / "modes" / filename,
        module_root / "ai_runtime" / "modes" / filename,
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
