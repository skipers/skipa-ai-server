"""Admin API for vectorstore management."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── MinIO 기반 빌드 ──────────────────────────────────────────────────────────

class MinioVectorstoreRequest(BaseModel):
    minio_path: str  # e.g. 'patents/1', '1', 'pre-evaluations/2'


class PatentMinioVectorstoreNotifyRequest(BaseModel):
    report_id: int | str
    patent_id: int | str | None = None
    minio_path: str | None = None


class PreEvalMinioVectorstoreNotifyRequest(BaseModel):
    pre_evaluation_id: int | str
    minio_path: str | None = None


@router.post(
    "/vectorstore/minio/patent/build",
    summary="MinIO 특허 벡터스토어 빌드",
    description=(
        "MinIO 경로(`patents/1` 또는 `1`)를 받아 해당 특허의 per-patent 컬렉션을 재생성합니다.\n\n"
        "처리 순서: parsed.json → 최신 reports/{N}/report.json → original.pdf (시각 텍스트)\n"
        "기존 컬렉션이 있으면 삭제 후 재생성합니다."
    ),
)
def build_patent_from_minio(request: MinioVectorstoreRequest) -> dict:
    from ..minio_vectorstore import build_patent_vectorstore_from_minio
    return build_patent_vectorstore_from_minio(request.minio_path)


@router.post(
    "/vectorstore/minio/patent/build-and-notify",
    summary="MinIO 특허 벡터스토어 빌드 후 백엔드 임베딩 완료 콜백",
    description=(
        "MinIO 특허 per-patent 컬렉션을 재생성한 뒤, 성공 시 "
        "`PATCH /internal/reports/{reportId}/embedding-complete`를 호출합니다.\n\n"
        "`report-complete` 콜백이 먼저 성공해서 백엔드 상태가 `REPORT_COMPLETED`여야 합니다."
    ),
)
def build_patent_from_minio_and_notify(request: PatentMinioVectorstoreNotifyRequest) -> dict:
    from ..minio_integration import build_patent_vectorstore_and_mark_embedding_complete

    try:
        return build_patent_vectorstore_and_mark_embedding_complete(
            report_id=request.report_id,
            patent_id=request.patent_id,
            minio_path=request.minio_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/vectorstore/minio/pre-eval/build",
    summary="MinIO 사전평가 벡터스토어 빌드",
    description=(
        "MinIO 경로(`pre-evaluations/1` 또는 `1`)를 받아 사전평가 컬렉션을 재생성합니다.\n\n"
        "input.json은 인덱싱하지 않습니다."
    ),
)
def build_pre_eval_from_minio(request: MinioVectorstoreRequest) -> dict:
    from ..minio_vectorstore import build_pre_eval_vectorstore_from_minio
    return build_pre_eval_vectorstore_from_minio(request.minio_path)


@router.post(
    "/vectorstore/minio/pre-eval/build-and-notify",
    summary="MinIO 사전평가 벡터스토어 빌드 후 백엔드 임베딩 완료 콜백",
    description=(
        "MinIO 사전평가 컬렉션을 재생성한 뒤, 성공 시 "
        "`PATCH /internal/pre-evaluations/{preEvaluationId}/embedding-complete`를 호출합니다.\n\n"
        "`report-complete` 콜백이 먼저 성공해서 백엔드 상태가 `REPORT_COMPLETED`여야 합니다."
    ),
)
def build_pre_eval_from_minio_and_notify(request: PreEvalMinioVectorstoreNotifyRequest) -> dict:
    from ..minio_integration import build_pre_eval_vectorstore_and_mark_embedding_complete

    return build_pre_eval_vectorstore_and_mark_embedding_complete(
        pre_evaluation_id=request.pre_evaluation_id,
        minio_path=request.minio_path,
    )


@router.get(
    "/vectorstore/minio/list",
    summary="MinIO 특허/사전평가 목록 조회",
)
def list_minio_resources() -> dict:
    from ..minio_vectorstore import list_minio_patents, list_minio_pre_evals
    return {
        "patents": list_minio_patents(),
        "pre_evaluations": list_minio_pre_evals(),
    }


class PatentVectorstoreRebuildRequest(BaseModel):
    patent_id: str | None = None
    path: str | None = None
    rebuild_all: bool = False


@router.post(
    "/vectorstore/patent/rebuild",
    summary="특허 벡터스토어 재생성",
    description=(
        "특정 특허의 per-patent Qdrant 컬렉션을 재생성합니다.\n\n"
        "- `patent_id`: 재생성할 특허 ID (예: `10-1959619`)\n"
        "- `path`: 특허 폴더 경로 (patent_id 대신 사용 가능)\n"
        "- `rebuild_all=true`: 모든 특허 컬렉션 일괄 재생성\n\n"
        "기존 컬렉션은 삭제 후 새로 생성됩니다 (blue/green 없음)."
    ),
)
def rebuild_patent_vectorstore(request: PatentVectorstoreRebuildRequest) -> dict:
    from ..shared_data import (
        build_patent_vectorstore,
        build_patent_vectorstore_from_path,
        build_all_patent_vectorstores,
        list_shared_patent_ids,
    )

    if request.rebuild_all:
        return build_all_patent_vectorstores()

    # path가 주어진 경우: 경로에서 직접 빌드 (patent_id는 폴더명에서 추론)
    if request.path:
        return build_patent_vectorstore_from_path(request.path)

    if not request.patent_id:
        raise HTTPException(status_code=422, detail="patent_id or path is required unless rebuild_all=true")

    if request.patent_id not in list_shared_patent_ids():
        raise HTTPException(status_code=404, detail=f"Patent '{request.patent_id}' not found in data/patent/")

    return build_patent_vectorstore(request.patent_id)


@router.get(
    "/vectorstore/patent/status",
    summary="특허 벡터스토어 상태 조회",
    description="모든 특허의 per-patent Qdrant 컬렉션 존재 여부와 문서 수를 반환합니다.",
)
def get_patent_vectorstore_status() -> dict:
    from ..shared_data import list_shared_patent_ids, patent_vectorstore_status

    patent_ids = list_shared_patent_ids()
    results = {}
    for pid in patent_ids:
        try:
            results[pid] = patent_vectorstore_status(pid)
        except Exception as exc:
            results[pid] = {"patent_id": pid, "error": str(exc)}
    return {"patent_count": len(patent_ids), "patents": results}


@router.get(
    "/vectorstore/patent/{patent_id}/status",
    summary="단일 특허 벡터스토어 상태",
)
def get_single_patent_vectorstore_status(patent_id: str) -> dict:
    from ..shared_data import patent_vectorstore_status, list_shared_patent_ids

    if patent_id not in list_shared_patent_ids():
        raise HTTPException(status_code=404, detail=f"Patent '{patent_id}' not found")
    return patent_vectorstore_status(patent_id)
