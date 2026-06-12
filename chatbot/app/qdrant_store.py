"""Qdrant-backed vectorstore for chatbot, wiki, and application assistants."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
import uuid

from .config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_EMBEDDING_MODEL,
    QDRANT_API_KEY,
    QDRANT_COLLECTION_PREFIX,
    QDRANT_DISTANCE,
    QDRANT_TIMEOUT,
    QDRANT_URL,
    QDRANT_VECTOR_SIZE,
)


TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")
MAX_EMBED_TEXT_CHARS = 6000
UPSERT_BATCH_SIZE = 64
EMBED_BATCH_SIZE = 32


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _json_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: int | None = None,
) -> dict[str, Any]:
    if not QDRANT_URL:
        raise RuntimeError("QDRANT_URL is not configured")
    url = f"{QDRANT_URL}{path}"
    data = json.dumps(payload or {}, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if QDRANT_API_KEY:
        headers["api-key"] = QDRANT_API_KEY
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout or QDRANT_TIMEOUT) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Qdrant {method} {path} failed: HTTP {exc.code} {detail}") from exc
    except (OSError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Qdrant {method} {path} failed: {exc}") from exc
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}
    return parsed if isinstance(parsed, dict) else {"result": parsed}


def qdrant_dashboard_url() -> str | None:
    if not QDRANT_URL:
        return None
    return f"{QDRANT_URL}/dashboard"


def qdrant_status() -> dict[str, Any]:
    status = {
        "backend": "qdrant",
        "configured": bool(QDRANT_URL),
        "url": QDRANT_URL,
        "dashboard_url": qdrant_dashboard_url(),
        "collection_prefix": QDRANT_COLLECTION_PREFIX,
        "vector_size": QDRANT_VECTOR_SIZE,
        "distance": QDRANT_DISTANCE,
        "api_key_configured": bool(QDRANT_API_KEY),
        "embedding_model": OPENAI_EMBEDDING_MODEL,
        "embedding_provider": "openai" if OPENAI_API_KEY else "local_hash_fallback",
    }
    try:
        response = _json_request("GET", "/collections", None)
        collections = response.get("result", {}).get("collections") or []
        status.update(
            {
                "connected": True,
                "collection_count": len(collections),
                "collections": [item.get("name") for item in collections[:50] if isinstance(item, dict)],
            }
        )
    except Exception as exc:
        status.update({"connected": False, "error": str(exc)})
    return status


def _sanitize(value: Any) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z가-힣_]+", "_", str(value or "")).strip("_")
    return cleaned or "default"


def collection_name(kind: str, identifier: Any | None = None) -> str:
    parts = [_sanitize(QDRANT_COLLECTION_PREFIX), _sanitize(kind)]
    if identifier not in (None, ""):
        parts.append(_sanitize(identifier))
    name = "_".join(parts)
    if len(name) <= 255:
        return name
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:12]
    return f"{name[:240]}_{digest}"


# ---------------------------------------------------------------------------
# Qdrant 컬렉션 이름 레지스트리
#
# 실제 생성되는 이름은 prefix(skipa) + kind 조합.
# PREFIX=skipa 기준 전체 목록:
#
#  skipa_patent_docs          ← parsed.json / report.json 텍스트 검색 (메인 특허 DB)
#  skipa_patent_docs_global   ← 전체 특허 통합 텍스트 검색 (재평가 특허 선택 없을 때)
#  skipa_patent_visual_clip   ← CLIP 이미지(512-dim) + 텍스트(3072-dim) named vectors
#  skipa_wiki_docs_global     ← 전체 wiki 통합 텍스트
#  skipa_wiki_topic_<topic>   ← 분야별(반도체_전자 / 소프트웨어_IT / ...) wiki 텍스트
#  skipa_application_docs     ← 특허 출원 공식팩 절차 텍스트
#  skipa_failed_patent_<id>   ← 실패특허 케이스별 텍스트
#  skipa_preeval_case_<id>    ← 사전평가 케이스별 텍스트
# ---------------------------------------------------------------------------

def shared_patents_collection() -> str:
    """메인 특허 텍스트 검색 컬렉션 — parsed.json / report.json."""
    return collection_name("patent_docs")


def patent_visuals_collection() -> str:
    """CLIP 이미지(512) + OpenAI 텍스트(3072) named vectors."""
    return collection_name("patent_visual_clip")


def patent_collection(patent_id: str | None = None) -> str:
    """전체(global) 또는 특허별 텍스트 컬렉션."""
    return collection_name("patent_docs_global" if not patent_id else "patent_doc", patent_id)


def wiki_collection(topic_slug: str | None = None) -> str:
    """전체(global) 또는 토픽별 wiki 텍스트 컬렉션."""
    return collection_name("wiki_docs_global" if not topic_slug else "wiki_topic", topic_slug)


def application_collection() -> str:
    """특허 출원 공식팩 절차 텍스트 컬렉션."""
    return collection_name("application_docs")


def failed_case_collection(case_id: str) -> str:
    """실패특허 케이스별 텍스트 컬렉션."""
    return collection_name("failed_patent", case_id)


def pre_eval_collection(case_id: str) -> str:
    """사전평가 케이스별 텍스트 컬렉션."""
    return collection_name("preeval_case", case_id)


def pre_application_collection(patent_id: str) -> str:
    """사전 출원 특허 보고서 전용 벡터스토어 — 컬렉션 이름은 'pre-{patent_id}'.

    MinIO 보고서 완료 웹훅으로 트리거되며, blue-green 없이 단순 upsert 방식으로
    하나씩 누적 생성됩니다.
    """
    safe = re.sub(r"[^0-9A-Za-z가-힣]", "_", str(patent_id or "")).strip("_")
    safe = safe[:80] or "unknown"
    return f"pre-{safe}"


def _text_for_embedding(text: Any) -> str:
    return " ".join(str(text or "").split())[:MAX_EMBED_TEXT_CHARS]


def _hash_embedding(text: str, size: int = QDRANT_VECTOR_SIZE) -> list[float]:
    counts: dict[int, float] = {}
    for token in TOKEN_RE.findall(text.lower()):
        bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % size
        counts[bucket] = counts.get(bucket, 0.0) + 1.0
    norm = sum(value * value for value in counts.values()) ** 0.5
    vector = [0.0] * size
    if not norm:
        return vector
    for index, value in counts.items():
        vector[index] = round(value / norm, 6)
    return vector


def _openai_embeddings(texts: list[str]) -> list[list[float]]:
    payload: dict[str, Any] = {
        "model": OPENAI_EMBEDDING_MODEL,
        "input": texts,
    }
    if QDRANT_VECTOR_SIZE:
        payload["dimensions"] = QDRANT_VECTOR_SIZE
    request = Request(
        f"{OPENAI_BASE_URL}/embeddings",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {OPENAI_API_KEY}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=QDRANT_TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenAI embedding failed: HTTP {exc.code} {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"OpenAI embedding failed: {exc}") from exc
    items = data.get("data") or []
    vectors = [item.get("embedding") for item in sorted(items, key=lambda item: item.get("index", 0))]
    if len(vectors) != len(texts) or not all(isinstance(vector, list) for vector in vectors):
        raise RuntimeError("OpenAI embedding response shape is invalid")
    return [[float(value) for value in vector] for vector in vectors]


def embed_texts(texts: list[str]) -> tuple[list[list[float]], str, str | None]:
    normalized = [_text_for_embedding(text) for text in texts]
    if OPENAI_API_KEY:
        try:
            return _openai_embeddings(normalized), "openai", None
        except Exception as exc:
            fallback = [_hash_embedding(text) for text in normalized]
            return fallback, "local_hash_fallback", str(exc)
    return [_hash_embedding(text) for text in normalized], "local_hash_fallback", None


def _point_id(doc: dict[str, Any]) -> str:
    raw = str(doc.get("doc_id") or hashlib.sha1(str(doc).encode("utf-8")).hexdigest())
    return str(uuid.uuid5(uuid.NAMESPACE_URL, raw))


def _payload_from_doc(doc: dict[str, Any], *, collection_scope: str, extra_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    text = str(doc.get("page_content") or "")
    payload = {
        "doc_id": str(doc.get("doc_id") or ""),
        "page_content": text,
        "metadata": metadata,
        "collection_scope": collection_scope,
        "patent_id": str(metadata.get("patent_id") or ""),
        "source_type": str(metadata.get("source_type") or ""),
        "case_id": str(metadata.get("case_id") or ""),
        "topic": str(metadata.get("topic") or ""),
        "section_title": str(metadata.get("section_title") or ""),
        "file_name": str(metadata.get("file_name") or ""),
        "source_path": str(metadata.get("source_path") or ""),
        "relative_source_path": str(metadata.get("relative_source_path") or ""),
    }
    payload.update(extra_payload or {})
    return payload


def _ensure_collection(collection: str, *, recreate: bool) -> None:
    encoded = quote(collection, safe="")
    if recreate:
        try:
            _json_request("DELETE", f"/collections/{encoded}", None)
        except Exception:
            pass
    payload = {"vectors": {"size": QDRANT_VECTOR_SIZE, "distance": QDRANT_DISTANCE}}
    try:
        _json_request("PUT", f"/collections/{encoded}", payload)
    except RuntimeError as exc:
        if "already exists" not in str(exc).lower():
            raise


def _ensure_visual_collection(collection: str, *, recreate: bool, image_vector_size: int) -> None:
    """Create/recreate the visual collection with named vectors (text + image)."""
    encoded = quote(collection, safe="")
    if recreate:
        try:
            _json_request("DELETE", f"/collections/{encoded}", None)
        except Exception:
            pass
    # named vectors: text (OpenAI) + image (CLIP)
    payload = {
        "vectors": {
            "text": {"size": QDRANT_VECTOR_SIZE, "distance": QDRANT_DISTANCE},
            "image": {"size": image_vector_size, "distance": "Cosine"},
        }
    }
    try:
        _json_request("PUT", f"/collections/{encoded}", payload)
    except RuntimeError as exc:
        if "already exists" not in str(exc).lower():
            raise


def _is_named_vector_collection(collection: str) -> bool:
    """Return True if the collection uses named vectors (text/image)."""
    info = collection_info(collection)
    config = info.get("config") or {}
    vectors_cfg = config.get("params", {}).get("vectors") or {}
    # named vectors → dict of dicts with keys like "text", "image"
    return isinstance(vectors_cfg, dict) and "text" in vectors_cfg


def upsert_visual_documents(
    collection: str,
    docs: list[dict[str, Any]],
    *,
    collection_scope: str,
    recreate: bool = False,
    image_vector_size: int = 512,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Upsert visual documents with dual text+image named vectors.

    Each point stores:
      vector.text  → OpenAI text-embedding-3-large of the caption/context
      vector.image → CLIP ViT-B/32 embedding of the PNG asset (or zero if missing)
    """
    from .clip_embedder import embed_images_batch, IMAGE_VECTOR_SIZE as CLIP_DIM

    effective_img_size = image_vector_size or CLIP_DIM
    _ensure_visual_collection(collection, recreate=recreate, image_vector_size=effective_img_size)

    # Collect asset paths for batch image embedding
    asset_paths: list[str | None] = [
        str((doc.get("metadata") or {}).get("asset_path") or "")
        for doc in docs
    ]
    valid_asset_paths: list[str] = [p for p in asset_paths if p]

    # Batch-embed all images at once
    image_vec_map: dict[str, list[float]] = {}
    if valid_asset_paths:
        vecs = embed_images_batch(valid_asset_paths)
        for path, vec in zip(valid_asset_paths, vecs):
            if vec is not None:
                image_vec_map[path] = vec

    zero_image_vec = [0.0] * effective_img_size
    embedding_error: str | None = None
    embedding_provider = "unknown"
    encoded = quote(collection, safe="")
    total = 0

    for start in range(0, len(docs), UPSERT_BATCH_SIZE):
        batch = docs[start : start + UPSERT_BATCH_SIZE]
        texts = [str(doc.get("embed_text") or doc.get("page_content") or "") for doc in batch]

        # Text embeddings via OpenAI
        text_vectors, provider, error = embed_texts(texts)
        embedding_provider = provider
        if error and not embedding_error:
            embedding_error = error

        points = []
        for doc, text_vec in zip(batch, text_vectors):
            asset_path = str((doc.get("metadata") or {}).get("asset_path") or "")
            image_vec = image_vec_map.get(asset_path, zero_image_vec)
            if not str(doc.get("page_content") or "").strip():
                continue
            points.append({
                "id": _point_id(doc),
                "vector": {"text": text_vec, "image": image_vec},
                "payload": _payload_from_doc(doc, collection_scope=collection_scope, extra_payload=extra_payload),
            })

        if not points:
            continue
        _json_request("PUT", f"/collections/{encoded}/points?wait=true", {"points": points})
        total += len(points)

    from .clip_embedder import clip_status
    cs = clip_status()
    return {
        "backend": "qdrant",
        "collection": collection,
        "collection_scope": collection_scope,
        "document_count": total,
        "refreshed_at": now_iso(),
        "embedding_provider": embedding_provider,
        "embedding_model": OPENAI_EMBEDDING_MODEL if embedding_provider == "openai" else "local_hash_fallback",
        "image_embedding_provider": cs.get("provider"),
        "image_embedding_available": cs.get("available"),
        "image_vector_size": effective_img_size,
        "embedding_error": embedding_error,
        "dashboard_url": qdrant_dashboard_url(),
    }


def search_visual_documents(
    collection: str,
    query: str,
    *,
    top_k: int = 6,
    patent_id: str | None = None,
    use_image_vector: bool = True,
) -> dict[str, Any]:
    """Search visual collection using CLIP cross-modal + text vectors.

    Strategy:
    1. If CLIP available: embed query with CLIP text encoder → search image vector
       (cross-modal: natural language → visual embedding space)
    2. Always: embed query with OpenAI → search text vector (caption search)
    3. Merge both result lists by RRF and return top_k.
    """
    if not collection_exists(collection):
        return {"query": query, "mode": "visual_search", "collection": collection, "hit_count": 0, "hits": []}

    named = _is_named_vector_collection(collection)
    query_filter = _filter_conditions(patent_id=patent_id, source_types=None)
    encoded = quote(collection, safe="")

    # ── Text vector search (caption/context) ──────────────────────────────
    text_vectors, provider, emb_error = embed_texts([query])
    text_payload: dict[str, Any] = {
        "limit": top_k,
        "with_payload": True,
        "with_vector": False,
    }
    if named:
        text_payload["vector"] = {"name": "text", "vector": text_vectors[0]}
    else:
        text_payload["vector"] = text_vectors[0]
    if query_filter:
        text_payload["filter"] = query_filter

    text_points: list[dict[str, Any]] = []
    try:
        resp = _json_request("POST", f"/collections/{encoded}/points/search", text_payload)
        text_points = resp.get("result") or []
    except Exception:
        pass

    # ── Image vector search (CLIP cross-modal) ────────────────────────────
    image_points: list[dict[str, Any]] = []
    clip_provider: str = "unavailable"
    if named and use_image_vector:
        from .clip_embedder import embed_text as clip_embed_text, clip_status
        cs = clip_status()
        clip_provider = cs.get("provider", "unavailable")
        if cs.get("available"):
            clip_vec = clip_embed_text(query)
            if clip_vec:
                img_payload: dict[str, Any] = {
                    "vector": {"name": "image", "vector": clip_vec},
                    "limit": top_k,
                    "with_payload": True,
                    "with_vector": False,
                }
                if query_filter:
                    img_payload["filter"] = query_filter
                try:
                    resp = _json_request("POST", f"/collections/{encoded}/points/search", img_payload)
                    image_points = resp.get("result") or []
                except Exception:
                    pass

    # ── RRF merge (Reciprocal Rank Fusion) ────────────────────────────────
    def rrf_score(rank: int, k: int = 60) -> float:
        return 1.0 / (k + rank + 1)

    scores: dict[str, float] = {}
    raw_points: dict[str, dict[str, Any]] = {}

    for rank, pt in enumerate(text_points):
        pid = str(pt.get("id") or "")
        scores[pid] = scores.get(pid, 0.0) + rrf_score(rank)
        raw_points[pid] = pt

    for rank, pt in enumerate(image_points):
        pid = str(pt.get("id") or "")
        scores[pid] = scores.get(pid, 0.0) + rrf_score(rank)
        if pid not in raw_points:
            raw_points[pid] = pt

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)[:top_k]
    merged_hits = []
    for pid in sorted_ids:
        pt = raw_points[pid]
        hit = _hit_from_point(pt, query)
        hit["rrf_score"] = round(scores[pid], 6)
        merged_hits.append(hit)

    return {
        "query": query,
        "mode": "visual_rrf_search" if image_points else "visual_text_search",
        "collection": collection,
        "top_k": top_k,
        "patent_id": patent_id,
        "hit_count": len(merged_hits),
        "hits": merged_hits,
        "text_hit_count": len(text_points),
        "image_hit_count": len(image_points),
        "embedding_provider": provider,
        "clip_provider": clip_provider,
        "named_vectors": named,
        "embedding_error": emb_error,
    }


def upsert_documents(
    collection: str,
    docs: list[dict[str, Any]],
    *,
    collection_scope: str,
    recreate: bool = True,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    _ensure_collection(collection, recreate=recreate)
    embedding_error: str | None = None
    embedding_provider = "unknown"
    encoded = quote(collection, safe="")
    total = 0
    for start in range(0, len(docs), UPSERT_BATCH_SIZE):
        batch = docs[start : start + UPSERT_BATCH_SIZE]
        texts = [str(doc.get("embed_text") or doc.get("page_content") or "") for doc in batch]
        vectors: list[list[float]] = []
        providers: set[str] = set()
        for embed_start in range(0, len(texts), EMBED_BATCH_SIZE):
            chunk = texts[embed_start : embed_start + EMBED_BATCH_SIZE]
            chunk_vectors, provider, error = embed_texts(chunk)
            providers.add(provider)
            if error and not embedding_error:
                embedding_error = error
            vectors.extend(chunk_vectors)
        embedding_provider = ",".join(sorted(providers)) if providers else embedding_provider
        points = [
            {
                "id": _point_id(doc),
                "vector": vector,
                "payload": _payload_from_doc(doc, collection_scope=collection_scope, extra_payload=extra_payload),
            }
            for doc, vector in zip(batch, vectors)
            if str(doc.get("page_content") or "").strip()
        ]
        if not points:
            continue
        _json_request("PUT", f"/collections/{encoded}/points?wait=true", {"points": points})
        total += len(points)
    return {
        "backend": "qdrant",
        "collection": collection,
        "collection_scope": collection_scope,
        "document_count": total,
        "refreshed_at": now_iso(),
        "embedding_provider": embedding_provider,
        "embedding_model": OPENAI_EMBEDDING_MODEL if embedding_provider == "openai" else "local_hash_fallback",
        "embedding_error": embedding_error,
        "dashboard_url": qdrant_dashboard_url(),
    }


def delete_documents(
    collection: str,
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    case_id: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    if not collection_exists(collection):
        return {"backend": "qdrant", "collection": collection, "deleted": False, "reason": "collection_missing"}
    query_filter = _filter_conditions(patent_id=patent_id, source_types=source_types, case_id=case_id, topic=topic)
    if not query_filter:
        raise ValueError("delete_documents requires at least one filter")
    encoded = quote(collection, safe="")
    response = _json_request("POST", f"/collections/{encoded}/points/delete?wait=true", {"filter": query_filter})
    return {"backend": "qdrant", "collection": collection, "deleted": True, "response": response}


def collection_info(collection: str) -> dict[str, Any]:
    encoded = quote(collection, safe="")
    try:
        response = _json_request("GET", f"/collections/{encoded}", None)
    except Exception as exc:
        return {
            "backend": "qdrant",
            "collection": collection,
            "exists": False,
            "error": str(exc),
            "dashboard_url": qdrant_dashboard_url(),
        }
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    return {
        "backend": "qdrant",
        "collection": collection,
        "exists": True,
        "status": result.get("status"),
        "points_count": result.get("points_count"),
        "vectors_count": result.get("vectors_count"),
        "indexed_vectors_count": result.get("indexed_vectors_count"),
        "config": result.get("config"),
        "dashboard_url": qdrant_dashboard_url(),
    }


def collection_exists(collection: str) -> bool:
    return bool(collection_info(collection).get("exists"))


def drop_collection(collection: str) -> dict[str, Any]:
    """Delete a Qdrant collection entirely. Safe to call even if it doesn't exist."""
    encoded = quote(collection, safe="")
    try:
        _json_request("DELETE", f"/collections/{encoded}", None)
        return {"backend": "qdrant", "collection": collection, "dropped": True}
    except Exception as exc:
        return {"backend": "qdrant", "collection": collection, "dropped": False, "error": str(exc)}


def _filter_conditions(
    *,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    case_id: str | None = None,
    topic: str | None = None,
) -> dict[str, Any] | None:
    must: list[dict[str, Any]] = []
    if patent_id:
        must.append({"key": "patent_id", "match": {"value": patent_id}})
    if case_id:
        must.append({"key": "case_id", "match": {"value": case_id}})
    if topic:
        must.append({"key": "topic", "match": {"value": topic}})
    if source_types:
        values = sorted(str(item) for item in source_types if item)
        if len(values) == 1:
            must.append({"key": "source_type", "match": {"value": values[0]}})
        elif values:
            must.append({"key": "source_type", "match": {"any": values}})
    return {"must": must} if must else None


def _hit_from_point(point: dict[str, Any], query: str) -> dict[str, Any]:
    payload = point.get("payload") if isinstance(point.get("payload"), dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    text = str(payload.get("page_content") or "")
    return {
        "patent_id": str(payload.get("patent_id") or metadata.get("patent_id") or ""),
        "score": round(float(point.get("score") or 0.0), 6),
        "excerpt": _excerpt(text, query),
        "page_content": text,
        "metadata": metadata,
        "doc_id": payload.get("doc_id"),
    }


def _excerpt(text: str, query: str, size: int = 500) -> str:
    value = str(text or "")
    if len(value) <= size:
        return value
    lower = value.lower()
    positions = [lower.find(token.lower()) for token in TOKEN_RE.findall(query) if lower.find(token.lower()) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - size // 3)
    end = min(len(value), start + size)
    return f"{'...' if start else ''}{value[start:end]}{'...' if end < len(value) else ''}"


def search_documents(
    collection: str,
    query: str,
    *,
    top_k: int = 8,
    patent_id: str | None = None,
    source_types: set[str] | None = None,
    case_id: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    if not collection_exists(collection):
        return {
            "query": query,
            "mode": "qdrant_search",
            "collection": collection,
            "hit_count": 0,
            "hits": [],
        }
    vectors, provider, embedding_error = embed_texts([query])
    payload: dict[str, Any] = {
        "vector": vectors[0],
        "limit": top_k,
        "with_payload": True,
        "with_vector": False,
    }
    query_filter = _filter_conditions(patent_id=patent_id, source_types=source_types, case_id=case_id, topic=topic)
    if query_filter:
        payload["filter"] = query_filter
    encoded = quote(collection, safe="")
    response = _json_request("POST", f"/collections/{encoded}/points/search", payload)
    points = response.get("result") or []
    hits = [_hit_from_point(point, query) for point in points if isinstance(point, dict)]
    return {
        "query": query,
        "mode": "qdrant_search",
        "collection": collection,
        "top_k": top_k,
        "patent_id": patent_id,
        "source_types": sorted(source_types) if source_types else None,
        "hit_count": len(hits),
        "hits": hits,
        "embedding_provider": provider,
        "embedding_error": embedding_error,
    }


def scroll_documents(
    collection: str,
    *,
    limit: int = 1000,
    source_types: set[str] | None = None,
    case_id: str | None = None,
    topic: str | None = None,
) -> list[dict[str, Any]]:
    if not collection_exists(collection):
        return []
    encoded = quote(collection, safe="")
    docs: list[dict[str, Any]] = []
    offset: Any = None
    while len(docs) < limit:
        payload: dict[str, Any] = {"limit": min(256, limit - len(docs)), "with_payload": True, "with_vector": False}
        query_filter = _filter_conditions(source_types=source_types, case_id=case_id, topic=topic)
        if query_filter:
            payload["filter"] = query_filter
        if offset is not None:
            payload["offset"] = offset
        response = _json_request("POST", f"/collections/{encoded}/points/scroll", payload)
        result = response.get("result") if isinstance(response.get("result"), dict) else {}
        points = result.get("points") or []
        for point in points:
            payload = point.get("payload") if isinstance(point, dict) and isinstance(point.get("payload"), dict) else {}
            metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
            docs.append(
                {
                    "doc_id": payload.get("doc_id"),
                    "page_content": payload.get("page_content") or "",
                    "metadata": metadata,
                }
            )
        offset = result.get("next_page_offset")
        if not offset or not points:
            break
    return docs


# ---------------------------------------------------------------------------
# Blue-green alias management
#
# 검색은 alias 이름(skipa_patent_live / skipa_wiki_live)으로만 수행되고,
# 실제 데이터는 _green / _blue 컬렉션 중 현재 활성 슬롯에 저장됩니다.
#
# 재인덱싱 흐름:
#   현재 green → _blue 빌드 → alias를 blue로 교체 (green은 다음 사이클에 재활용)
#   현재 blue  → _green 빌드 → alias를 green으로 교체
#   alias 없음 → _green 빌드 → alias 생성 (최초 실행)
# ---------------------------------------------------------------------------

def bluegreen_patent_alias() -> str:
    """글로벌 특허 검색에 사용되는 live alias 이름."""
    return collection_name("patent_live")


def bluegreen_wiki_alias() -> str:
    """글로벌 wiki 검색에 사용되는 live alias 이름."""
    return collection_name("wiki_live")


def _aliases_list() -> list[dict[str, Any]]:
    """Qdrant에 등록된 모든 alias 목록을 반환. 오류 시 빈 리스트."""
    try:
        resp = _json_request("GET", "/aliases", None)  # POST는 /collections/aliases, GET은 /aliases
        return list((resp.get("result") or {}).get("aliases") or [])
    except Exception:
        return []


def get_alias_target(alias_name: str) -> str | None:
    """alias_name이 가리키는 컬렉션 이름을 반환. 없으면 None."""
    for item in _aliases_list():
        if item.get("alias_name") == alias_name:
            return str(item.get("collection_name") or "")
    return None


def _real_collection_names() -> set[str]:
    """Qdrant에 실제 컬렉션(alias 제외)으로 존재하는 이름 집합."""
    try:
        resp = _json_request("GET", "/collections", None)
        return {c.get("name", "") for c in (resp.get("result") or {}).get("collections") or []}
    except Exception:
        return set()


def set_alias(alias_name: str, target_collection: str) -> None:
    """alias를 target_collection으로 원자적(atomic) 교체/생성.

    alias_name과 동일한 이름의 일반 컬렉션이 존재하면 자동 삭제 후 alias 생성 (마이그레이션).
    """
    current = get_alias_target(alias_name)
    actions: list[dict[str, Any]] = []
    if current is not None:
        actions.append({"delete_alias": {"alias_name": alias_name}})
    elif alias_name in _real_collection_names():
        # 같은 이름의 일반 컬렉션이 있으면 삭제 후 alias로 교체
        encoded = quote(alias_name, safe="")
        try:
            _json_request("DELETE", f"/collections/{encoded}", None)
        except Exception:
            pass
    actions.append({"create_alias": {"alias_name": alias_name, "collection_name": target_collection}})
    _json_request("POST", "/collections/aliases", {"actions": actions})


def bluegreen_active_color(alias_name: str, green_collection: str, blue_collection: str) -> str:
    """현재 alias가 가리키는 슬롯을 'green' | 'blue' | 'none' 으로 반환."""
    target = get_alias_target(alias_name)
    if target == green_collection:
        return "green"
    if target == blue_collection:
        return "blue"
    return "none"


def bluegreen_upsert_documents(
    alias_name: str,
    green_collection: str,
    blue_collection: str,
    docs: list[dict[str, Any]],
    *,
    collection_scope: str,
    extra_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """비활성 슬롯에 문서를 빌드한 뒤 alias를 원자적으로 교체한다.

    슬롯 로테이션:
      none / blue → _green 빌드 후 alias → green
      green       → _blue  빌드 후 alias → blue
    """
    current_color = bluegreen_active_color(alias_name, green_collection, blue_collection)
    if current_color == "green":
        build_col, new_color = blue_collection, "blue"
    else:
        build_col, new_color = green_collection, "green"

    result = upsert_documents(
        build_col,
        docs,
        collection_scope=collection_scope,
        recreate=True,
        extra_payload=extra_payload,
    )
    set_alias(alias_name, build_col)

    result.update({
        "bluegreen": True,
        "alias": alias_name,
        "previous_color": current_color,
        "active_color": new_color,
        "active_collection": build_col,
    })
    return result


def bluegreen_collection_status(alias_name: str, green_collection: str, blue_collection: str) -> dict[str, Any]:
    """alias와 green/blue 슬롯의 현재 상태 스냅샷을 반환."""
    target = get_alias_target(alias_name)
    color = bluegreen_active_color(alias_name, green_collection, blue_collection)
    green_info = collection_info(green_collection)
    blue_info = collection_info(blue_collection)
    return {
        "alias": alias_name,
        "active_color": color,
        "active_collection": target,
        "green": {
            "collection": green_collection,
            "exists": bool(green_info.get("exists")),
            "document_count": green_info.get("points_count", 0),
            "qdrant_status": green_info.get("status"),
            "is_active": target == green_collection,
        },
        "blue": {
            "collection": blue_collection,
            "exists": bool(blue_info.get("exists")),
            "document_count": blue_info.get("points_count", 0),
            "qdrant_status": blue_info.get("status"),
            "is_active": target == blue_collection,
        },
        "dashboard_url": qdrant_dashboard_url(),
    }
