"""JSON persistence helpers for pre-application valuation."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def save_result(result: dict[str, Any], output_dir: Path | str | None = None) -> Path:
    directory = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    directory.mkdir(parents=True, exist_ok=True)
    title = str(result.get("patent_title") or "pre_application")
    evaluation_id = str(result.get("evaluation_id") or datetime.now().strftime("%Y%m%d_%H%M%S"))
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_safe_name(title)}_{evaluation_id}.json"
    path = directory / filename
    result.setdefault("artifacts", {})
    result["artifacts"]["output_path"] = str(path)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path = directory / "latest.json"
    latest_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_json(path: Path | str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("JSON 최상위 값은 object여야 합니다.")
    return payload


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", value).strip("._")
    return cleaned[:80] or "pre_application"
