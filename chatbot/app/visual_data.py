"""Visual asset extraction and Qdrant indexing for shared patent originals.

This module indexes only stable patent-original visuals: tables, figures,
diagram-like pages, and embedded images from ``data/patent/<patent_id>/patent.pdf``
or ``data/patent/<patent_id>/original.pdf``.
Reports are intentionally optional and not required for visual indexing.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import HTTPException

from .config import SHARED_PATENT_ROOT
from .qdrant_store import (
    collection_exists,
    collection_info,
    delete_documents,
    patent_visuals_collection,
    search_documents,
    search_visual_documents,
    upsert_documents,
    upsert_visual_documents,
    _is_named_vector_collection,
)
from .shared_data import list_shared_patent_ids


VISUAL_SOURCE_TYPES = frozenset({"ORIGINAL_VISUAL", "REPORT_VISUAL", "HTML_VISUAL"})
MANIFEST_NAME = "visual_index_manifest.json"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_patent_id(value: str) -> str:
    if not value or "/" in value or "\\" in value:
        raise HTTPException(status_code=400, detail="잘못된 patent_id입니다.")
    return value


def _patent_dir(patent_id: str) -> Path:
    safe_id = _safe_patent_id(patent_id)
    path = (SHARED_PATENT_ROOT / safe_id).resolve()
    try:
        path.relative_to(SHARED_PATENT_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="허용되지 않은 patent_id입니다.") from exc
    return path


def _manifest_path(patent_id: str) -> Path:
    return _patent_dir(patent_id) / "extracted" / MANIFEST_NAME


def _source_pdf_path(patent_id: str) -> Path:
    patent_dir = _patent_dir(patent_id)
    direct = patent_dir / "patent.pdf"
    if direct.exists():
        return direct
    original = patent_dir / "original.pdf"
    return original if original.exists() else direct


def _visual_candidate_ids() -> list[str]:
    ids = set(list_shared_patent_ids())
    if SHARED_PATENT_ROOT.exists():
        for path in SHARED_PATENT_ROOT.iterdir():
            if path.is_dir() and not path.name.startswith((".", "_")) and ((path / "patent.pdf").exists() or (path / "original.pdf").exists()):
                ids.add(path.name)
    return sorted(ids)


def _visual_url(patent_id: str, relative_asset_path: str) -> str:
    parts = [quote(part) for part in relative_asset_path.split("/") if part]
    return f"/files/shared/patent/{quote(patent_id)}/{'/'.join(parts)}"


def _source_pdf_url(patent_id: str, page_no: int | None = None, *, file_name: str = "patent.pdf") -> str:
    url = f"/files/shared/patent/{quote(patent_id)}/{quote(file_name)}"
    if page_no:
        url += f"#page={page_no}"
    return url


def _meta_from_shared_patent(patent_id: str) -> dict[str, Any]:
    parsed = _read_json(_patent_dir(patent_id) / "parsed.json")
    patent = parsed.get("normalized_patent") if isinstance(parsed.get("normalized_patent"), dict) else {}
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    return {
        "patent_id": patent_id,
        "title": meta.get("title") or patent.get("title") or patent_id,
        "application_number": meta.get("application_number"),
        "registration_number": meta.get("registration_number") or patent_id,
        "applicant": meta.get("applicant"),
        "inventor": meta.get("inventor"),
        "ipc_code": meta.get("ipc_code"),
        "cpc_code": meta.get("cpc_code"),
        "tech_field": meta.get("tech_field"),
        "business_field": meta.get("business_field"),
    }


def _document_to_qdrant_dict(document: Any, *, patent_id: str, patent_dir: Path, pdf_path: Path) -> dict[str, Any] | None:
    page_content = str(getattr(document, "page_content", "") or "").strip()
    metadata = dict(getattr(document, "metadata", {}) or {})
    if not page_content:
        return None
    relative_asset = str(metadata.get("asset_file_name") or "")
    asset_path = patent_dir / relative_asset if relative_asset else None
    page_no = metadata.get("page_no")
    pdf_file_name = pdf_path.name
    asset_url = _visual_url(patent_id, relative_asset) if relative_asset else None
    source_url = _source_pdf_url(patent_id, int(page_no), file_name=pdf_file_name) if isinstance(page_no, int) else _source_pdf_url(patent_id, file_name=pdf_file_name)
    if metadata.get("asset_url") and asset_url:
        page_content = page_content.replace(str(metadata.get("asset_url")), asset_url)
    if metadata.get("source_url"):
        page_content = page_content.replace(str(metadata.get("source_url")), source_url)
    metadata.update(
        {
            "patent_id": patent_id,
            "source_type": metadata.get("source_type") or "ORIGINAL_VISUAL",
            "content_type": "VISUAL_ASSET",
            "source_pdf_path": str(pdf_path),
            "source_path": str(asset_path) if asset_path else str(pdf_path),
            "relative_source_path": f"data/patent/{patent_id}/{relative_asset}" if relative_asset else f"data/patent/{patent_id}/{pdf_file_name}",
            "asset_path": str(asset_path) if asset_path else None,
            "asset_url": asset_url,
            "source_url": source_url,
            "file_name": Path(relative_asset).name if relative_asset else pdf_file_name,
            "visual_index_scope": "shared_patent_original",
        }
    )
    doc_id = metadata.get("chunk_id") or f"{patent_id}:ORIGINAL_VISUAL:{metadata.get('asset_kind')}:{metadata.get('text_hash')}"
    return {"doc_id": str(doc_id), "page_content": page_content, "metadata": metadata}


def build_patent_visual_index(
    patent_id: str,
    *,
    force: bool = False,
    recreate_collection: bool = False,
    max_assets: int | None = None,
) -> dict[str, Any]:
    """Extract and upsert one patent's original visual assets into Qdrant."""
    safe_id = _safe_patent_id(patent_id)
    patent_dir = _patent_dir(safe_id)
    pdf_path = _source_pdf_path(safe_id)
    manifest_path = _manifest_path(safe_id)
    if not pdf_path.exists():
        return {
            "status": "skipped",
            "reason": "missing_patent_pdf",
            "patent_id": safe_id,
            "pdf_path": str(pdf_path),
        }
    pdf_sha1 = _hash_file(pdf_path)
    old_manifest = _read_json(manifest_path)
    collection_ready = collection_exists(patent_visuals_collection())
    if (
        not force
        and collection_ready
        and old_manifest.get("source_pdf_sha1") == pdf_sha1
        and old_manifest.get("status") in {"indexed", "no_visuals"}
    ):
        return {
            "status": "skipped",
            "reason": "visual_index_already_current",
            "patent_id": safe_id,
            "manifest_path": str(manifest_path),
            "document_count": old_manifest.get("document_count", 0),
            "asset_count": old_manifest.get("asset_count", 0),
        }

    try:
        from .legacy.ingest import MAX_VISUAL_ASSETS_PER_DOCUMENT, extract_pdf_visual_documents

        docs = extract_pdf_visual_documents(
            pdf_path=pdf_path,
            patent_dir=patent_dir,
            patent_id=safe_id,
            source_document_type="ORIGINAL_PDF",
            public_file_base_url="/files/shared",
            file_name_for_url=pdf_path.name,
            meta=_meta_from_shared_patent(safe_id),
            max_assets=max_assets or MAX_VISUAL_ASSETS_PER_DOCUMENT,
        )
    except Exception as exc:
        manifest = {
            "status": "error",
            "patent_id": safe_id,
            "source_pdf_path": str(pdf_path),
            "source_pdf_sha1": pdf_sha1,
            "error": f"{type(exc).__name__}: {exc}",
            "refreshed_at": _now(),
        }
        _write_json(manifest_path, manifest)
        return {**manifest, "manifest_path": str(manifest_path)}

    qdrant_docs = [
        item
        for item in (
            _document_to_qdrant_dict(document, patent_id=safe_id, patent_dir=patent_dir, pdf_path=pdf_path)
            for document in docs
        )
        if item is not None
    ]
    asset_paths = sorted(
        {
            str((item.get("metadata") or {}).get("asset_path"))
            for item in qdrant_docs
            if (item.get("metadata") or {}).get("asset_path")
        }
    )
    delete_result = None
    qdrant = {"backend": "qdrant", "collection": patent_visuals_collection(), "document_count": 0}
    if qdrant_docs:
        from .clip_embedder import clip_status, IMAGE_VECTOR_SIZE
        cs = clip_status()
        collection_missing = not collection_exists(patent_visuals_collection())
        # 기존 컬렉션이 단일 벡터(non-named)면 CLIP 도입을 위해 재생성
        needs_recreate = (
            recreate_collection
            or collection_missing
            or (cs.get("available") and not _is_named_vector_collection(patent_visuals_collection()))
        )
        if not needs_recreate and collection_exists(patent_visuals_collection()):
            delete_result = delete_documents(patent_visuals_collection(), patent_id=safe_id)

        if cs.get("available"):
            # CLIP 사용 가능 → named vector (text + image) upsert
            qdrant = upsert_visual_documents(
                patent_visuals_collection(),
                qdrant_docs,
                collection_scope="shared_patent_visuals",
                recreate=needs_recreate,
                image_vector_size=IMAGE_VECTOR_SIZE,
                extra_payload={"index_scope": "shared_patent_visuals", "visual_index_scope": "shared_patent_original"},
            )
        else:
            # CLIP 없음 → 기존 단일 텍스트 벡터 upsert
            qdrant = upsert_documents(
                patent_visuals_collection(),
                qdrant_docs,
                collection_scope="shared_patent_visuals",
                recreate=needs_recreate,
                extra_payload={"index_scope": "shared_patent_visuals", "visual_index_scope": "shared_patent_original"},
            )
    manifest = {
        "status": "indexed" if qdrant_docs else "no_visuals",
        "patent_id": safe_id,
        "backend": "qdrant",
        "collection": patent_visuals_collection(),
        "source": "shared_patent_original_pdf",
        "source_pdf_path": str(pdf_path),
        "source_pdf_sha1": pdf_sha1,
        "document_count": len(qdrant_docs),
        "asset_count": len(asset_paths),
        "asset_paths": asset_paths[:300],
        "refreshed_at": _now(),
        "qdrant": qdrant,
        "delete_result": delete_result,
    }
    _write_json(manifest_path, manifest)
    return {**manifest, "manifest_path": str(manifest_path)}


def build_missing_patent_visual_indexes(*, force: bool = False, max_patents: int | None = None) -> dict[str, Any]:
    """Index visuals for new/missing patents only, unless force=True."""
    started_at = _now()
    collection_ready = collection_exists(patent_visuals_collection())
    effective_force = force or not collection_ready
    results: list[dict[str, Any]] = []
    collection_recreated = False
    for patent_id in _visual_candidate_ids()[: max_patents or None]:
        recreate = bool(effective_force and not collection_recreated)
        result = build_patent_visual_index(patent_id, force=effective_force, recreate_collection=recreate)
        if result.get("qdrant", {}).get("document_count", 0) or recreate:
            collection_recreated = True
        results.append(result)
    processed = [item for item in results if item.get("status") in {"indexed", "no_visuals", "error"}]
    indexed = [item for item in results if item.get("status") == "indexed"]
    skipped = [item for item in results if item.get("status") == "skipped"]
    errors = [item for item in results if item.get("status") == "error"]
    return {
        "status": "completed",
        "workflow": "missing_patent_visual_index",
        "started_at": started_at,
        "finished_at": _now(),
        "force": force,
        "effective_force": effective_force,
        "collection": patent_visuals_collection(),
        "candidate_count": len(_visual_candidate_ids()),
        "processed_count": len(processed),
        "indexed_count": len(indexed),
        "skipped_count": len(skipped),
        "error_count": len(errors),
        "total_document_count": sum(int(item.get("document_count") or 0) for item in indexed),
        "results": results,
        "qdrant": collection_info(patent_visuals_collection()),
    }


def patent_visual_index_status() -> dict[str, Any]:
    manifests = []
    missing = []
    pending = []
    errors = []
    for patent_id in _visual_candidate_ids():
        manifest_path = _manifest_path(patent_id)
        if manifest_path.exists():
            data = _read_json(manifest_path)
            item = {
                "patent_id": patent_id,
                "status": data.get("status"),
                "document_count": data.get("document_count", 0),
                "asset_count": data.get("asset_count", 0),
                "refreshed_at": data.get("refreshed_at"),
                "manifest_path": str(manifest_path),
                "error": data.get("error"),
            }
            manifests.append(item)
            if data.get("status") == "error":
                pending.append(patent_id)
                errors.append(item)
        else:
            missing.append(patent_id)
            pending.append(patent_id)
    qdrant = collection_info(patent_visuals_collection())
    if not qdrant.get("exists"):
        pending = _visual_candidate_ids()
    from .clip_embedder import clip_status
    return {
        "backend": "qdrant",
        "collection": patent_visuals_collection(),
        "named_vectors": _is_named_vector_collection(patent_visuals_collection()),
        "clip": clip_status(),
        "qdrant": qdrant,
        "candidate_count": len(_visual_candidate_ids()),
        "indexed_manifest_count": len(manifests),
        "missing_manifest_count": len(missing),
        "pending_reindex_count": len(pending),
        "missing_patents": missing[:100],
        "pending_patents": pending[:100],
        "error_count": len(errors),
        "errors": errors[:50],
        "manifests": manifests,
    }


def search_patent_visuals(
    query: str,
    *,
    patent_id: str | None = None,
    top_k: int = 6,
    use_clip: bool = True,
) -> dict[str, Any]:
    """Search visual assets. Uses CLIP cross-modal + text RRF when CLIP is available."""
    collection = patent_visuals_collection()
    if _is_named_vector_collection(collection):
        # Named vector collection: CLIP cross-modal + text RRF search
        result = search_visual_documents(
            collection,
            query,
            top_k=top_k,
            patent_id=patent_id,
            use_image_vector=use_clip,
        )
    else:
        # Legacy single-vector collection: text search only
        result = search_documents(
            collection,
            query,
            top_k=top_k,
            patent_id=patent_id,
            source_types=set(VISUAL_SOURCE_TYPES),
        )
    return {**result, "visual_collection": collection}
