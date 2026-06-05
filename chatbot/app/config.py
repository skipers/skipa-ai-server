"""Configuration helpers for the chatbot Swagger API."""

from __future__ import annotations

import os
from pathlib import Path


os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

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

DEFAULT_DATA_ROOT = CHATBOT_ROOT / "data" if (CHATBOT_ROOT / "data").exists() else PROJECT_ROOT / "data"
DATA_ROOT = _resolve_path(os.getenv("DATA_ROOT") or os.getenv("SKIPA_DATA_ROOT"), DEFAULT_DATA_ROOT)
PATENTS_ROOT = _resolve_path(os.getenv("PATENTS_ROOT"), DATA_ROOT / "mapped_patent_reports")
BUSINESS_ROOT = _resolve_path(os.getenv("BUSINESS_ROOT"), DATA_ROOT / "business")
DEFAULT_PATENT_APPLICATION_ROOT = (
    DATA_ROOT / "patent_application_official_pack"
    if (DATA_ROOT / "patent_application_official_pack").exists()
    else DATA_ROOT / "patent_application_official_pack(1)"
)
PATENT_APPLICATION_ROOT = _resolve_path(
    os.getenv("PATENT_APPLICATION_ROOT"),
    DEFAULT_PATENT_APPLICATION_ROOT,
)
LOG_ROOT = _resolve_path(os.getenv("LOG_ROOT"), CHATBOT_ROOT / "logs")
WIKI_AUDITOR_ROOT = _resolve_path(os.getenv("WIKI_AUDITOR_ROOT"), CHATBOT_ROOT / "logs" / "wiki_auditor")

PUBLIC_FILE_BASE_URL = os.getenv("PUBLIC_FILE_BASE_URL", "http://localhost:8000/files")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_INTENT_MODEL = os.getenv("OPENAI_INTENT_MODEL", "gpt-4.1-mini")
OPENAI_ANSWER_MODEL = os.getenv("OPENAI_ANSWER_MODEL", "gpt-4.1")
OPENAI_VLM_MODEL = os.getenv("OPENAI_VLM_MODEL", "gpt-4.1-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
INTENT_PROVIDER = os.getenv("INTENT_PROVIDER", "openai").lower()
ANSWER_PROVIDER = os.getenv("ANSWER_PROVIDER", "openai").lower()
ENABLE_OLLAMA_INTENT_FALLBACK = os.getenv("ENABLE_OLLAMA_INTENT_FALLBACK", "false").lower() in ("1", "true", "yes")
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai" if OPENAI_API_KEY else "huggingface").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL if EMBEDDING_PROVIDER == "openai" else "BAAI/bge-m3")
GEN_MODEL = os.getenv("GEN_MODEL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
INTENT_MODEL = os.getenv("INTENT_MODEL", OPENAI_INTENT_MODEL if INTENT_PROVIDER == "openai" else GEN_MODEL or "qwen2.5:1.5b")
ANSWER_MODEL = os.getenv("ANSWER_MODEL", OPENAI_ANSWER_MODEL if ANSWER_PROVIDER == "openai" else GEN_MODEL or "qwen2.5:1.5b")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.0"))
INTENT_NUM_PREDICT = int(os.getenv("INTENT_NUM_PREDICT", "220"))
ANSWER_NUM_PREDICT = int(os.getenv("ANSWER_NUM_PREDICT", "2000"))
LLM_TIMEOUT = min(int(os.getenv("CHATBOT_LLM_TIMEOUT", "45")), 180)
INTENT_LLM_TIMEOUT = min(int(os.getenv("INTENT_LLM_TIMEOUT", os.getenv("CHATBOT_LLM_TIMEOUT", "30"))), 180)
ANSWER_LLM_TIMEOUT = min(int(os.getenv("ANSWER_LLM_TIMEOUT", os.getenv("CHATBOT_LLM_TIMEOUT", "90"))), 240)
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
