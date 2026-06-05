"""Restored rag.zip engine package.

Importing the current config first makes the legacy modules pick up the unified
data root and local ``.env`` values before their module-level settings load.
"""

from .. import config as _config  # noqa: F401
