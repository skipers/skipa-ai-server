"""Test-only import helpers.

The production entrypoints currently adjust sys.path in a few places. Tests keep
that behavior local so application runtime code stays untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVAL_LOGIC_SRC = PROJECT_ROOT / "eval_logic" / "src"

for path in (PROJECT_ROOT, EVAL_LOGIC_SRC):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

