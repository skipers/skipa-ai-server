"""Configuration helpers for the chatbot Swagger API."""

from __future__ import annotations

import os
from pathlib import Path


os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

CHATBOT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CHATBOT_ROOT.parent
PROCESS_ENV_KEYS = set(os.environ)


OPEN_SOURCE_PROVIDER_ALIASES = {"opensource", "open_source", "openai_compatible", "vllm", "sglang"}


def _load_env_file(path: Path, *, override: bool = False, protected_keys: set[str] | None = None) -> None:
    if not path.exists():
        return
    protected = protected_keys or set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in protected and (override or key not in os.environ):
            os.environ[key] = value


def _sanitize_mode(value: str) -> str:
    return "".join(ch for ch in value.strip().lower() if ch.isalnum() or ch in {"_", "-"})


def _selected_ai_mode() -> str:
    for key in ("AI_PROVIDER", "AI_MODE", "AI_PROVIDER_PROFILE", "LLM_PROVIDER", "MODEL_PROVIDER"):
        value = os.getenv(key)
        if value:
            return _sanitize_mode(value)
    return ""


def _component_provider(name: str, *, fallback: str) -> str:
    value = os.getenv(name, "").strip().lower()
    if SELECTED_AI_MODE in OPEN_SOURCE_PROVIDER_ALIASES and (not value or value == "openai"):
        return "opensource"
    return value or fallback


def _resolve_path(raw: str | None, default: Path) -> Path:
    candidate = Path(raw).expanduser() if raw else default
    if not candidate.is_absolute():
        candidate = (CHATBOT_ROOT / candidate).resolve()
    return candidate


_load_env_file(CHATBOT_ROOT / ".env")
_load_env_file(PROJECT_ROOT / ".env")
SELECTED_AI_MODE = _selected_ai_mode()
if SELECTED_AI_MODE:
    _load_env_file(PROJECT_ROOT / "ai_runtime" / "modes" / f"{SELECTED_AI_MODE}.env", override=True, protected_keys=PROCESS_ENV_KEYS)
    SELECTED_AI_MODE = _selected_ai_mode()

DEFAULT_DATA_ROOT = CHATBOT_ROOT / "data" if (CHATBOT_ROOT / "data").exists() else PROJECT_ROOT / "data"
DATA_ROOT = _resolve_path(os.getenv("DATA_ROOT") or os.getenv("SKIPA_DATA_ROOT"), DEFAULT_DATA_ROOT)
PATENTS_ROOT = _resolve_path(os.getenv("PATENTS_ROOT"), DATA_ROOT / "mapped_patent_reports")
BUSINESS_ROOT = _resolve_path(os.getenv("BUSINESS_ROOT"), DATA_ROOT / "business")
LOG_ROOT = _resolve_path(os.getenv("LOG_ROOT"), CHATBOT_ROOT / "logs")
WIKI_AUDITOR_ROOT = _resolve_path(os.getenv("WIKI_AUDITOR_ROOT"), CHATBOT_ROOT / "logs" / "wiki_auditor")
# Shared project data root: PROJECT_ROOT/data (patent PDFs, reports, wiki)
SHARED_DATA_ROOT = _resolve_path(os.getenv("SHARED_DATA_ROOT"), PROJECT_ROOT / "data")
SHARED_PATENT_ROOT = _resolve_path(os.getenv("SHARED_PATENT_ROOT"), SHARED_DATA_ROOT / "patent")
WIKI_ROOT = _resolve_path(os.getenv("WIKI_ROOT"), SHARED_DATA_ROOT / "wiki")
PRE_EVAL_ROOT = _resolve_path(os.getenv("PRE_EVAL_ROOT"), SHARED_DATA_ROOT / "pre_application_cases")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "").rstrip("/")
MINIO_CONSOLE_URL = os.getenv("MINIO_CONSOLE_URL", "").rstrip("/")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "skipa")
MINIO_PATENT_PREFIX = os.getenv("MINIO_PATENT_PREFIX", "patents/").strip("/")
MINIO_WIKI_PREFIX = os.getenv("MINIO_WIKI_PREFIX", "wiki/").strip("/")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("1", "true", "yes")
MINIO_SYNC_ON_STARTUP = os.getenv("MINIO_SYNC_ON_STARTUP", "true").lower() in ("1", "true", "yes")
MINIO_REINDEX_AFTER_SYNC = os.getenv("MINIO_REINDEX_AFTER_SYNC", "true").lower() in ("1", "true", "yes")
MINIO_WIKI_SYNC_ON_STARTUP = os.getenv("MINIO_WIKI_SYNC_ON_STARTUP", "true").lower() in ("1", "true", "yes")
MINIO_WIKI_SYNC_BEFORE_REFRESH = os.getenv("MINIO_WIKI_SYNC_BEFORE_REFRESH", "true").lower() in ("1", "true", "yes")
MINIO_WIKI_UPLOAD_ON_WRITE = os.getenv("MINIO_WIKI_UPLOAD_ON_WRITE", "true").lower() in ("1", "true", "yes")

BACKEND_INTERNAL_BASE_URL = os.getenv("BACKEND_INTERNAL_BASE_URL", "").rstrip("/")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
BACKEND_CALLBACK_TIMEOUT = min(int(os.getenv("BACKEND_CALLBACK_TIMEOUT", "15")), 120)

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION_PREFIX = os.getenv("QDRANT_COLLECTION_PREFIX", "skipa")
QDRANT_VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "3072"))
QDRANT_DISTANCE = os.getenv("QDRANT_DISTANCE", "Cosine")
QDRANT_TIMEOUT = min(int(os.getenv("QDRANT_TIMEOUT", "30")), 120)

PUBLIC_FILE_BASE_URL = os.getenv("PUBLIC_FILE_BASE_URL", "http://localhost:8000/files")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_INTENT_MODEL = os.getenv("OPENAI_INTENT_MODEL", "gpt-4.1-mini")
OPENAI_ANSWER_MODEL = os.getenv("OPENAI_ANSWER_MODEL", "gpt-4.1")
OPENAI_VLM_MODEL = os.getenv("OPENAI_VLM_MODEL", "gpt-4.1-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
INTENT_PROVIDER = _component_provider("INTENT_PROVIDER", fallback="openai")
ANSWER_PROVIDER = _component_provider("ANSWER_PROVIDER", fallback="openai")
ENABLE_OLLAMA_INTENT_FALLBACK = os.getenv("ENABLE_OLLAMA_INTENT_FALLBACK", "false").lower() in ("1", "true", "yes")
EMBEDDING_PROVIDER = _component_provider("EMBEDDING_PROVIDER", fallback="openai" if OPENAI_API_KEY else "huggingface")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL if EMBEDDING_PROVIDER == "openai" else "BAAI/bge-m3")
GEN_MODEL = os.getenv("GEN_MODEL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OPEN_SOURCE_LLM_MODEL = os.getenv("OPEN_SOURCE_LLM_MODEL") or os.getenv("OPEN_SOURCE_REPORT_MODEL") or GEN_MODEL
INTENT_MODEL = os.getenv("INTENT_MODEL", OPENAI_INTENT_MODEL if INTENT_PROVIDER == "openai" else OPEN_SOURCE_LLM_MODEL or "qwen2.5:1.5b")
ANSWER_MODEL = os.getenv("ANSWER_MODEL", OPENAI_ANSWER_MODEL if ANSWER_PROVIDER == "openai" else OPEN_SOURCE_LLM_MODEL or "qwen2.5:1.5b")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.0"))
INTENT_NUM_PREDICT = int(os.getenv("INTENT_NUM_PREDICT", "220"))
ANSWER_NUM_PREDICT = int(os.getenv("ANSWER_NUM_PREDICT", "2000"))
LLM_TIMEOUT = min(int(os.getenv("CHATBOT_LLM_TIMEOUT", "45")), 180)
INTENT_LLM_TIMEOUT = min(int(os.getenv("INTENT_LLM_TIMEOUT", os.getenv("CHATBOT_LLM_TIMEOUT", "30"))), 180)
ANSWER_LLM_TIMEOUT = min(int(os.getenv("ANSWER_LLM_TIMEOUT", os.getenv("CHATBOT_LLM_TIMEOUT", "90"))), 240)
TOP_K = int(os.getenv("TOP_K", "10"))

ENABLE_WEB_SEARCH = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
ENABLE_RERANK = os.getenv("ENABLE_RERANK", "true").lower() == "true"
ENABLE_QUERY_EXPANSION = os.getenv("ENABLE_QUERY_EXPANSION", "true").lower() == "true"
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
