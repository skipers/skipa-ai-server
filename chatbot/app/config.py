"""Configuration helpers for the chatbot Swagger API."""

from __future__ import annotations

import os
from pathlib import Path


CHATBOT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CHATBOT_ROOT.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _resolve_path(raw: str | None, default: Path) -> Path:
    candidate = Path(raw).expanduser() if raw else default
    if not candidate.is_absolute():
        candidate = (CHATBOT_ROOT / candidate).resolve()
    return candidate


_load_env_file(CHATBOT_ROOT / ".env")

DATA_ROOT = _resolve_path(os.getenv("DATA_ROOT") or os.getenv("SKIPA_DATA_ROOT"), PROJECT_ROOT / "data")
PATENTS_ROOT = _resolve_path(os.getenv("PATENTS_ROOT"), DATA_ROOT / "mapped_patent_reports")
BUSINESS_ROOT = _resolve_path(os.getenv("BUSINESS_ROOT"), DATA_ROOT / "business")
LOG_ROOT = _resolve_path(os.getenv("LOG_ROOT"), CHATBOT_ROOT / "logs")
WIKI_AUDITOR_ROOT = _resolve_path(os.getenv("WIKI_AUDITOR_ROOT"), CHATBOT_ROOT / "logs" / "wiki_auditor")

PUBLIC_FILE_BASE_URL = os.getenv("PUBLIC_FILE_BASE_URL", "http://localhost:8000/files")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
GEN_MODEL = os.getenv("GEN_MODEL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
INTENT_MODEL = os.getenv("INTENT_MODEL", GEN_MODEL or "qwen2.5:1.5b")
ANSWER_MODEL = os.getenv("ANSWER_MODEL", GEN_MODEL or "qwen2.5:1.5b")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.0"))
INTENT_NUM_PREDICT = int(os.getenv("INTENT_NUM_PREDICT", "180"))
ANSWER_NUM_PREDICT = int(os.getenv("ANSWER_NUM_PREDICT", "520"))
LLM_TIMEOUT = min(int(os.getenv("CHATBOT_LLM_TIMEOUT", os.getenv("DYNAMIC_ANSWER_TIMEOUT", "30"))), 30)
TOP_K = int(os.getenv("TOP_K", "10"))

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
WEB_SEARCH_LIMIT = int(os.getenv("WEB_SEARCH_LIMIT", "5"))
WEB_SEARCH_TIMEOUT = min(int(os.getenv("WEB_SEARCH_TIMEOUT", "12")), 12)
WEB_SEARCH_API_URL = os.getenv("WEB_SEARCH_API_URL", "")
WEB_SEARCH_API_KEY = os.getenv("WEB_SEARCH_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_API_URL = os.getenv("TAVILY_API_URL", "https://api.tavily.com/search")
WEB_SEARCH_BLOCKLIST_DOMAINS = {
    item.strip().lower()
    for item in os.getenv("WEB_SEARCH_BLOCKLIST_DOMAINS", "").split(",")
    if item.strip()
}
