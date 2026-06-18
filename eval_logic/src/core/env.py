"""Environment loading helpers shared by eval_logic modules."""

from __future__ import annotations

import os
from pathlib import Path

from core.paths import ROOT_DIR

SERVER_ROOT = ROOT_DIR.parent


def load_runtime_env() -> list[Path]:
    """Load shared server env first, then legacy eval_logic env if present."""
    try:
        from dotenv import dotenv_values, load_dotenv
    except Exception:
        return []

    protected_keys = set(os.environ)
    loaded: list[Path] = []
    for env_path in (SERVER_ROOT / ".env", ROOT_DIR / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)
            loaded.append(env_path)
    mode = _selected_mode()
    if mode:
        profile_path = SERVER_ROOT / "ai_runtime" / "modes" / f"{mode}.env"
        if profile_path.exists():
            for key, value in dotenv_values(profile_path).items():
                if key and value is not None and key not in protected_keys:
                    os.environ[key] = str(value)
            loaded.append(profile_path)
    return loaded


def _selected_mode() -> str:
    value = os.environ.get("AI_PROVIDER_PROFILE") or os.environ.get("AI_MODE")
    if not value:
        return ""
    return "".join(ch for ch in value.strip().lower() if ch.isalnum() or ch in {"_", "-"})
