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
WIKI_AUDITOR_ROOT = _resolve_path(os.getenv("WIKI_AUDITOR_ROOT"), CHATBOT_ROOT / "wiki_auditor")

PUBLIC_FILE_BASE_URL = os.getenv("PUBLIC_FILE_BASE_URL", "http://localhost:8000/files")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
GEN_MODEL = os.getenv("GEN_MODEL", "")
TOP_K = int(os.getenv("TOP_K", "10"))

