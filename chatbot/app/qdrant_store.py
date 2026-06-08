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


def shared_patents_collection() -> str:
    return collection_name("shared_patents")


def patent_collection(patent_id: str | None = None) -> str:
    return collection_name("patents_global" if not patent_id else "patent", patent_id)


def wiki_collection(topic_slug: str | None = None) -> str:
    return collection_name("wiki_global" if not topic_slug else "wiki_topic", topic_slug)


def application_collection() -> str:
    return collection_name("application_official_pack")


def failed_case_collection(case_id: str) -> str:
    return collection_name("application_failed_case", case_id)


def pre_eval_collection(case_id: str) -> str:
    return collection_name("pre_eval_case", case_id)


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
        texts = [str(doc.get("page_content") or "") for doc in batch]
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
