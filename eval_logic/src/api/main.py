"""Backward-compatible wrapper for the FastAPI app.

New code lives in ``apps.api.main``. This module keeps older commands such as
``uvicorn src.api.main:app`` working.
"""

from __future__ import annotations

import sys
from pathlib import Path


_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from apps.api.main import *  # noqa: F401,F403
