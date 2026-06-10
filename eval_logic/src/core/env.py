"""Environment loading helpers shared by eval_logic modules."""

from __future__ import annotations

from pathlib import Path

from core.paths import ROOT_DIR

SERVER_ROOT = ROOT_DIR.parent


def load_runtime_env() -> list[Path]:
    """Load shared server env first, then legacy eval_logic env if present."""
    try:
        from dotenv import load_dotenv
    except Exception:
        return []

    loaded: list[Path] = []
    for env_path in (SERVER_ROOT / ".env", ROOT_DIR / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)
            loaded.append(env_path)
    return loaded
