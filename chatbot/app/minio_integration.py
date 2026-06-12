"""Integration flows that bridge MinIO vectorstore builds to backend status callbacks."""

from __future__ import annotations

from typing import Any

from .backend_callbacks import mark_pre_evaluation_embedding_complete, mark_report_embedding_complete
from .minio_vectorstore import build_patent_vectorstore_from_minio, build_pre_eval_vectorstore_from_minio


def _assert_index_built(result: dict[str, Any]) -> None:
    count = int(result.get("total_chunks") or result.get("document_count") or 0)
    if count <= 0:
        raise RuntimeError(f"Vectorstore build produced no chunks: {result}")


def build_patent_vectorstore_and_mark_embedding_complete(
    *,
    report_id: int | str,
    patent_id: int | str | None = None,
    minio_path: str | None = None,
) -> dict[str, Any]:
    """Build a patent vectorstore, then mark the backend report as EMBEDDING_COMPLETED."""
    if not minio_path and patent_id is None:
        raise ValueError("patent_id or minio_path is required")

    path = minio_path or f"patents/{patent_id}"
    index_result = build_patent_vectorstore_from_minio(path)
    _assert_index_built(index_result)
    callback_result = mark_report_embedding_complete(report_id)
    return {
        "status": "embedding_completed",
        "report_id": report_id,
        "patent_id": patent_id or index_result.get("patent_id"),
        "minio_path": path,
        "index": index_result,
        "backend_callback": callback_result,
    }


def build_pre_eval_vectorstore_and_mark_embedding_complete(
    *,
    pre_evaluation_id: int | str,
    minio_path: str | None = None,
) -> dict[str, Any]:
    """Build a pre-evaluation vectorstore, then mark it as EMBEDDING_COMPLETED."""
    path = minio_path or f"pre-evaluations/{pre_evaluation_id}"
    index_result = build_pre_eval_vectorstore_from_minio(path)
    _assert_index_built(index_result)
    callback_result = mark_pre_evaluation_embedding_complete(pre_evaluation_id)
    return {
        "status": "embedding_completed",
        "pre_evaluation_id": pre_evaluation_id,
        "minio_path": path,
        "index": index_result,
        "backend_callback": callback_result,
    }
