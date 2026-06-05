"""Backward-compatible wrapper for ``apps.api.job_store``."""

from __future__ import annotations

import sys
from pathlib import Path


_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from apps.api.job_store import *  # noqa: F401,F403
