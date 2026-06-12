"""Optional chatbot vectorstore indexing hooks for worker completion flows."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from typing import Any, Callable

LOGGER = logging.getLogger(__name__)


def index_patent_report_from_minio(
    report_key: str,
    *,
    patent_id: int | str | None = None,
    enabled: bool = True,
    strict: bool = False,
) -> dict[str, Any] | None:
    """Trigger chatbot patent vectorstore rebuild for a completed report."""
    if not enabled:
        return None
    prefix = _patent_prefix_from_report_key(report_key) or (str(patent_id) if patent_id is not None else "")
    return _call_builder(
        "build_patent_vectorstore_from_minio",
        prefix,
        strict=strict,
        log_context={"kind": "patent", "report_key": report_key, "prefix": prefix},
    )


def index_pre_evaluation_report_from_minio(
    report_key: str,
    *,
    pre_evaluation_id: int | str | None = None,
    enabled: bool = True,
    strict: bool = False,
) -> dict[str, Any] | None:
    """Trigger chatbot pre-application vectorstore rebuild for a completed report."""
    if not enabled:
        return None
    prefix = _pre_evaluation_prefix_from_report_key(report_key) or (
        f"pre-evaluations/{pre_evaluation_id}" if pre_evaluation_id is not None else ""
    )
    return _call_builder(
        "build_pre_eval_vectorstore_from_minio",
        prefix,
        strict=strict,
        log_context={"kind": "pre_evaluation", "report_key": report_key, "prefix": prefix},
    )


def _call_builder(
    function_name: str,
    minio_prefix: str,
    *,
    strict: bool,
    log_context: dict[str, Any],
) -> dict[str, Any] | None:
    if not minio_prefix:
        message = f"Cannot trigger vectorstore indexing without MinIO prefix: {log_context}"
        if strict:
            raise RuntimeError(message)
        LOGGER.warning(message)
        return None

    try:
        builder = _load_builder(function_name)
        result = builder(minio_prefix)
        LOGGER.info(
            "Vectorstore indexing completed kind=%s prefix=%s result=%s",
            log_context.get("kind"),
            minio_prefix,
            _compact_result(result),
        )
        return result if isinstance(result, dict) else {"result": result}
    except Exception as exc:
        LOGGER.exception(
            "Vectorstore indexing failed kind=%s prefix=%s reportKey=%s",
            log_context.get("kind"),
            minio_prefix,
            log_context.get("report_key"),
        )
        if strict:
            raise
        return {"status": "failed", "error": str(exc), **log_context}


def _load_builder(function_name: str) -> Callable[[str], Any]:
    _ensure_chatbot_import_paths()
    errors: list[str] = []
    for module_name in ("app.minio_vectorstore", "chatbot.app.minio_vectorstore"):
        try:
            module = importlib.import_module(module_name)
            builder = getattr(module, function_name)
            if callable(builder):
                return builder
        except Exception as exc:
            errors.append(f"{module_name}: {type(exc).__name__}: {exc}")
    raise RuntimeError(f"Cannot import chatbot vectorstore builder {function_name}: {'; '.join(errors)}")


def _ensure_chatbot_import_paths() -> None:
    server_root = Path(__file__).resolve().parents[3]
    candidates = [server_root / "chatbot", server_root]
    for path in candidates:
        path_text = str(path)
        if path.exists() and path_text not in sys.path:
            sys.path.insert(0, path_text)


def _patent_prefix_from_report_key(report_key: str) -> str | None:
    key = str(report_key or "").strip().strip("/")
    marker = "/reports/"
    if marker in key and key.endswith("/report.json"):
        return key.split(marker, 1)[0]
    if key.endswith("/report.json"):
        return key[: -len("/report.json")]
    return None


def _pre_evaluation_prefix_from_report_key(report_key: str) -> str | None:
    key = str(report_key or "").strip().strip("/")
    if key.endswith("/report.json"):
        return key[: -len("/report.json")]
    return None


def _compact_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"result": str(result)}
    keys = ("status", "collection", "collection_id", "document_count", "counts", "errors")
    return {key: result.get(key) for key in keys if key in result}
