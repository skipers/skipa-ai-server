"""Audit, human review, and Qdrant vectorstore refresh for chatbot data.

The important contract is the workflow:

1. Audit scans raw shared data and flags suspicious documents.
2. A human reviews the findings in Swagger or the generated Markdown.
3. Only human-approved content is saved as Markdown/JSONL.
4. Qdrant vectorstores are rebuilt from the approved content.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from fastapi import HTTPException

from .config import BUSINESS_ROOT, PATENTS_ROOT, PROJECT_ROOT, WIKI_AUDITOR_ROOT, WIKI_ROOT
from .config import QDRANT_COLLECTION_PREFIX
from .qdrant_store import (
    bluegreen_collection_status,
    bluegreen_patent_alias,
    bluegreen_upsert_documents,
    bluegreen_wiki_alias,
    collection_exists,
    collection_info,
    patent_collection,
    search_documents,
    shared_patents_collection,
    upsert_documents,
    wiki_collection,
)

# ---------------------------------------------------------------------------
# 컬렉션 이름 주석 (명시적 참조)
#
# shared_patents_collection()      → skipa_patent_docs        ← 메인 특허 검색 (parsed.json + report.json)
# patent_collection(patent_id)     → skipa_patent_doc_{id}   ← ingestion graph로 생성된 특허별 컬렉션
# patent_collection(None)          → skipa_patent_docs_global ← review 워크플로우 글로벌 컬렉션
# wiki_collection(topic_slug)      → skipa_wiki_topic_{slug}  ← 분야별 wiki
# wiki_collection(None)            → skipa_wiki_docs_global   ← 전체 wiki 통합
# bluegreen_patent_alias()         → skipa_patent_live        ← blue-green alias (patent)
# bluegreen_wiki_alias()           → skipa_wiki_live          ← blue-green alias (wiki)
# ---------------------------------------------------------------------------
from .rag.quality import is_usable_evidence, preprocess_evidence_text


VECTOR_DIMENSIONS = 256
MAX_TEXT_CHARS = 20000
CORE_SEARCH_SOURCE_TYPES = frozenset(
    {"ORIGINAL_PDF", "REPORT_PDF", "PATENT_INPUT_JSON", "REPORT_JSON"}
)
WIKI_SEARCH_SOURCE_TYPES = frozenset({"WIKI"})
TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY|AKIA[0-9A-Z]{16}|"
    r"(?i:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*[A-Za-z0-9_.-]{12,})"
)
ERROR_RE = re.compile(r"(?i)(traceback|exception|stack trace|nonetype|undefined|nan|jsondecodeerror|internal server error)")
REPEATED_CHAR_RE = re.compile(r"(.)\1{12,}")
AUDIT_SCHEMA_VERSION = "chatbot-audit/v1"


AUDIT_CRITERIA = [
    {
        "rule_id": "EMPTY_OR_TOO_SHORT",
        "severity": "high",
        "default_action": "exclude",
        "description": "공백 제거 후 본문이 30자 미만이면 RAG 근거로 가치가 낮아 제외 후보로 봅니다.",
    },
    {
        "rule_id": "OCR_NOISE",
        "severity": "high",
        "default_action": "exclude",
        "description": "한글/영문/숫자 비율이 낮고 기호가 과도하면 PDF OCR 또는 표 추출 잡음으로 봅니다.",
    },
    {
        "rule_id": "ERROR_TEXT",
        "severity": "high",
        "default_action": "exclude",
        "description": "traceback, exception, undefined, NaN 등 시스템 오류 문자열이 포함되면 제외 후보로 봅니다.",
    },
    {
        "rule_id": "SECRET_PATTERN",
        "severity": "high",
        "default_action": "exclude",
        "description": "API key, secret, private key 패턴이 보이면 민감정보 유출 위험으로 제외 후보로 봅니다.",
    },
    {
        "rule_id": "METADATA_MISMATCH",
        "severity": "high",
        "default_action": "exclude",
        "description": "문서 metadata의 patent_id가 현재 특허 폴더와 다르면 잘못 섞인 데이터로 봅니다.",
    },
    {
        "rule_id": "DUPLICATE_TEXT",
        "severity": "medium",
        "default_action": "exclude",
        "description": "동일 text hash가 이미 등장하면 중복 chunk로 보고 기본 제외 후보로 둡니다.",
    },
    {
        "rule_id": "REPEATED_PATTERN",
        "severity": "medium",
        "default_action": "review",
        "description": "동일 문자/토큰 반복이 과하면 OCR, table parsing, PDF footer 반복 가능성이 있어 검토 대상으로 둡니다.",
    },
    {
        "rule_id": "MISSING_METADATA",
        "severity": "low",
        "default_action": "review",
        "description": "source_type, source_path 등 출처 추적 metadata가 부족하면 사람이 확인할 수 있게 표시합니다.",
    },
    {
        "rule_id": "OVERSIZED_DOCUMENT",
        "severity": "low",
        "default_action": "review",
        "description": "본문이 매우 길어 vectorstore 저장 시 잘릴 수 있으면 검토 대상으로 표시합니다.",
    },
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _audit_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _safe_relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path)


def _utf8_safe(value: Any) -> str:
    return str(value or "").encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")


def _hash_text(text: str) -> str:
    return hashlib.sha1(_utf8_safe(text).encode("utf-8", errors="ignore")).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def _vectorize(text: str) -> dict[str, float]:
    counts: Counter[int] = Counter()
    for token in _tokens(text):
        bucket = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % VECTOR_DIMENSIONS
        counts[bucket] += 1
    norm = math.sqrt(sum(value * value for value in counts.values()))
    if not norm:
        return {}
    return {str(bucket): round(value / norm, 6) for bucket, value in sorted(counts.items())}


def _dot(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(key, 0.0) for key, value in left.items())


def _json_text(value: Any) -> str:
    try:
        return _utf8_safe(json.dumps(value, ensure_ascii=False, sort_keys=True))
    except TypeError:
        return _utf8_safe(value)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_jsonl(path: Path) -> Iterable[tuple[int, dict[str, Any]]]:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                yield line_no, item


def _truncate(text: str) -> str:
    text = " ".join(_utf8_safe(text).split())
    return text[:MAX_TEXT_CHARS]


def _source_type(doc: dict[str, Any]) -> str:
    metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    return str(metadata.get("source_type") or "")


def _is_core_search_doc(doc: dict[str, Any]) -> bool:
    return _source_type(doc) in CORE_SEARCH_SOURCE_TYPES


def _is_wiki_doc(doc: dict[str, Any]) -> bool:
    return _source_type(doc) in WIKI_SEARCH_SOURCE_TYPES


def _is_approved_wiki_doc(doc: dict[str, Any]) -> bool:
    metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    source_path = str(metadata.get("source_path") or "")
    file_name = str(metadata.get("file_name") or Path(source_path).name)
    return _is_wiki_doc(doc) and file_name == "approved_context.md" and "web_search_drafts" not in source_path


def _document(
    *,
    patent_id: str,
    text: str,
    source_path: Path,
    source_type: str,
    metadata: dict[str, Any] | None = None,
    line_no: int | None = None,
) -> dict[str, Any] | None:
    content = _truncate(preprocess_evidence_text(text))
    if not content:
        return None
    text_hash = _hash_text(content)
    doc_id_seed = f"{patent_id}:{source_type}:{_safe_relative(source_path)}:{line_no or 0}:{text_hash}"
    doc_metadata = dict(metadata or {})
    doc_metadata.update(
        {
            "patent_id": patent_id,
            "source_type": source_type,
            "source_path": str(source_path),
            "relative_source_path": _safe_relative(source_path),
            "line_no": line_no,
            "text_hash": text_hash,
        }
    )
    return {
        "doc_id": hashlib.sha1(doc_id_seed.encode("utf-8")).hexdigest(),
        "page_content": content,
        "metadata": doc_metadata,
        "vector": _vectorize(content),
    }


def _chunk_documents(patent_id: str, path: Path) -> Iterable[dict[str, Any]]:
    for line_no, item in _read_jsonl(path) or []:
        text = str(item.get("page_content") or "")
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        source_type = str(metadata.get("source_type") or "CHUNK")
        doc = _document(
            patent_id=patent_id,
            text=text,
            source_path=path,
            source_type=source_type,
            metadata=metadata,
            line_no=line_no,
        )
        if doc:
            yield doc


def _json_document(patent_id: str, path: Path, source_type: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = _read_json(path)
    if not data:
        return None
    title = None
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    if isinstance(meta, dict):
        title = meta.get("title")
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
    title = title or validation.get("title")
    return _document(
        patent_id=patent_id,
        text=_json_text(data),
        source_path=path,
        source_type=source_type,
        metadata={"title": title, "file_name": path.name},
    )


def _wiki_documents(patent_id: str, wiki_root: Path) -> Iterable[dict[str, Any]]:
    if not wiki_root.exists():
        return
    for path in sorted(wiki_root.rglob("*")):
        if not path.is_file() or "vectorstore" in path.parts:
            continue
        if path.name != "approved_context.md" or "web_search_drafts" in path.parts:
            continue
        if path.suffix.lower() not in {".md", ".txt", ".json", ".jsonl"}:
            continue
        if path.suffix.lower() == ".jsonl":
            for line_no, item in _read_jsonl(path) or []:
                text = item.get("page_content") or item.get("text") or _json_text(item)
                doc = _document(
                    patent_id=patent_id,
                    text=str(text),
                    source_path=path,
                    source_type="WIKI",
                    metadata={"file_name": path.name},
                    line_no=line_no,
                )
                if doc:
                    yield doc
        else:
            doc = _document(
                patent_id=patent_id,
                text=path.read_text(encoding="utf-8", errors="ignore"),
                source_path=path,
                source_type="WIKI",
                metadata={"file_name": path.name},
            )
            if doc:
                yield doc


def _topic_wiki_documents(topic_slug: str) -> Iterable[dict[str, Any]]:
    """Yield approved wiki documents for a topic from WIKI_ROOT/{topic}/approved_context.md."""
    from .wiki.topics import topic_approved_md
    approved_md = topic_approved_md(topic_slug)
    if not approved_md.exists():
        return
    doc = _document(
        patent_id=f"_wiki_{topic_slug}",
        text=approved_md.read_text(encoding="utf-8", errors="ignore"),
        source_path=approved_md,
        source_type="WIKI",
        metadata={"title": f"{topic_slug} wiki", "file_name": approved_md.name, "topic": topic_slug},
    )
    if doc:
        yield doc



def _business_documents() -> list[dict[str, Any]]:
    path = BUSINESS_ROOT / "index" / "all_chunks.jsonl"
    docs = []
    for line_no, item in _read_jsonl(path) or []:
        text = str(item.get("page_content") or "")
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        doc = _document(
            patent_id="_business",
            text=text,
            source_path=path,
            source_type=str(metadata.get("source_type") or "BUSINESS"),
            metadata=metadata,
            line_no=line_no,
        )
        if doc:
            docs.append(doc)
    return docs


def _patent_ids() -> list[str]:
    if not PATENTS_ROOT.exists():
        return []
    return [
        path.name
        for path in sorted(PATENTS_ROOT.iterdir(), key=lambda item: item.name)
        if path.is_dir() and not path.name.startswith(".") and path.name != "_global"
    ]


def _reviewed_docs_path(patent_id: str) -> Path:
    return PATENTS_ROOT / patent_id / "reviewed" / "approved_documents.jsonl"


def _reviewed_md_path(patent_id: str) -> Path:
    return PATENTS_ROOT / patent_id / "reviewed" / "approved_context.md"


def _load_reviewed_documents(patent_id: str) -> list[dict[str, Any]]:
    path = _reviewed_docs_path(patent_id)
    docs = []
    for _, doc in _read_jsonl(path) or []:
        if not isinstance(doc, dict):
            continue
        text = str(doc.get("page_content") or "")
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        if text and not doc.get("vector"):
            doc["vector"] = _vectorize(text)
        metadata.setdefault("patent_id", patent_id)
        metadata["human_review_status"] = "approved"
        doc["metadata"] = metadata
        docs.append(doc)
    return docs


def normalize_wiki_context_files() -> dict[str, Any]:
    """Rewrite approved wiki contexts from reviewed docs into topic-based approved_context.md."""
    from .wiki.topics import get_patent_topic, topic_approved_md

    updated = []
    for patent_id in _patent_ids():
        reviewed_path = _reviewed_docs_path(patent_id)
        if not reviewed_path.exists():
            continue
        reviewed_dir = PATENTS_ROOT / patent_id / "reviewed"
        manifest = _read_json(reviewed_dir / "manifest.json")
        audit_id = str(manifest.get("audit_id") or "unknown")
        approved_at = str(manifest.get("approved_at") or _now())
        reviewer = manifest.get("reviewer")

        docs: list[dict[str, Any]] = []
        for _, doc in _read_jsonl(reviewed_path) or []:
            if not isinstance(doc, dict):
                continue
            metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
            if metadata.get("source_type") == "WIKI":
                continue
            docs.append(doc)

        topic = get_patent_topic(patent_id)
        wiki_md_path = topic_approved_md(topic)
        wiki_md_path.parent.mkdir(parents=True, exist_ok=True)
        wiki_markdown = _wiki_markdown_from_approved_docs(patent_id, docs, audit_id=audit_id)
        # Append to topic-level file rather than overwriting
        with wiki_md_path.open("a", encoding="utf-8") as f:
            f.write(wiki_markdown)

        wiki_doc = _document(
            patent_id=f"_wiki_{topic}",
            text=wiki_markdown,
            source_path=wiki_md_path,
            source_type="WIKI",
            metadata={
                "title": f"{topic} 감사 승인 Wiki Context",
                "file_name": wiki_md_path.name,
                "topic": topic,
                "human_review_source": "approved_context",
                "human_review_status": "approved",
                "human_review_audit_id": audit_id,
                "human_reviewed_at": approved_at,
            },
        )
        if wiki_doc:
            wiki_doc_metadata = wiki_doc.get("metadata") if isinstance(wiki_doc.get("metadata"), dict) else {}
            if reviewer:
                wiki_doc_metadata["human_reviewer"] = reviewer
            wiki_doc["metadata"] = wiki_doc_metadata
            docs.append(wiki_doc)
        with reviewed_path.open("w", encoding="utf-8") as file:
            for doc in docs:
                file.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")
        updated.append(
            {
                "patent_id": patent_id,
                "topic": topic,
                "wiki_markdown_path": str(wiki_md_path),
                "approved_documents_path": str(reviewed_path),
                "document_count": len(docs),
            }
        )
    return {"status": "normalized", "updated_count": len(updated), "patents": updated}


def collect_patent_documents(patent_id: str, *, use_reviewed: bool = True) -> list[dict[str, Any]]:
    if use_reviewed and _reviewed_docs_path(patent_id).exists():
        return _load_reviewed_documents(patent_id)

    patent_dir = PATENTS_ROOT / patent_id
    docs: list[dict[str, Any]] = []
    chunk_path = patent_dir / "extracted" / "all_chunks.jsonl"
    if chunk_path.exists():
        docs.extend(_chunk_documents(patent_id, chunk_path))

    for path, source_type in [
        (patent_dir / "original" / "input" / "latest.json", "PATENT_INPUT_JSON"),
        (patent_dir / "reports" / "json" / "latest.json", "REPORT_JSON"),
    ]:
        doc = _json_document(patent_id, path, source_type)
        if doc:
            docs.append(doc)

    return docs


def _collection_for_scope(scope: str) -> str:
    """스코프 이름 → Qdrant alias(또는 컬렉션) 이름.

    모든 스코프가 blue-green으로 관리되므로 이 이름이 alias의 canonical 이름이 된다.
    """
    if scope == "global":
        return bluegreen_patent_alias()          # skipa_patent_live
    if scope == "wiki:global":
        return bluegreen_wiki_alias()            # skipa_wiki_live
    if scope == "shared_patents":
        return shared_patents_collection()       # skipa_patent_docs
    if scope.startswith("patent:"):
        return patent_collection(scope.split(":", 1)[1])   # skipa_patent_doc_{id}
    if scope.startswith("wiki:"):
        return wiki_collection(scope.split(":", 1)[1])     # skipa_wiki_topic_{slug}
    # application, business, preeval 등 → 컬렉션 이름 그대로 alias로 사용
    return f"{QDRANT_COLLECTION_PREFIX}_{scope.replace(':', '_').replace('-', '_')}"


def _write_vectorstore(output_dir: Path, docs: list[dict[str, Any]], *, scope: str, source: str = "unknown") -> dict[str, Any]:
    """모든 스코프에 blue-green alias 방식 적용. 기존 컬렉션이면 자동 마이그레이션."""
    for doc in docs:
        if doc.get("page_content") and not doc.get("vector"):
            doc["vector"] = _vectorize(str(doc.get("page_content") or ""))

    refreshed_at = _now()
    extra = {"source": source, "logical_index_root": str(output_dir)}
    alias = _collection_for_scope(scope)
    green = f"{alias}_green"
    blue = f"{alias}_blue"

    qdrant = bluegreen_upsert_documents(
        alias, green, blue, docs, collection_scope=scope, extra_payload=extra,
    )
    active_collection = str(qdrant.get("active_collection") or alias)

    return {
        "scope": scope,
        "backend": "qdrant",
        "document_count": len(docs),
        "collection": active_collection,
        "alias": alias,
        "active_color": qdrant.get("active_color"),
        "previous_color": qdrant.get("previous_color"),
        "qdrant": qdrant,
        "refreshed_at": refreshed_at,
        "source": source,
    }


def refresh_vectorstores(*, use_reviewed: bool = True) -> dict[str, Any]:
    from .wiki.topics import all_active_topic_slugs, topic_approved_md

    patent_results = []
    global_docs: list[dict[str, Any]] = []
    excluded_by_policy: dict[str, int] = defaultdict(int)
    source = "human_reviewed" if use_reviewed else "raw"

    for patent_id in _patent_ids():
        patent_dir = PATENTS_ROOT / patent_id
        docs = collect_patent_documents(patent_id, use_reviewed=use_reviewed)
        core_docs = [doc for doc in docs if _is_core_search_doc(doc)]
        for doc in docs:
            if not _is_core_search_doc(doc) and not _is_wiki_doc(doc):
                excluded_by_policy[_source_type(doc) or "UNKNOWN"] += 1
        global_docs.extend(core_docs)
        patent_results.append(
            _write_vectorstore(patent_dir / "index" / "qdrant", core_docs, scope=f"patent:{patent_id}", source=source)
        )

    business_docs = _business_documents()
    for doc in business_docs:
        excluded_by_policy[_source_type(doc) or "BUSINESS"] += 1
    _write_vectorstore(
        BUSINESS_ROOT / "index" / "qdrant",
        [],
        scope="business-disabled",
        source="disabled_non_core_web_routing",
    )
    global_result = _write_vectorstore(PATENTS_ROOT / "_global" / "index" / "qdrant", global_docs, scope="global", source=source)

    # Build per-topic wiki vectorstores in Qdrant.
    topic_wiki_results = []
    all_wiki_docs: list[dict[str, Any]] = []
    for topic_slug in all_active_topic_slugs():
        topic_docs = list(_topic_wiki_documents(topic_slug))
        all_wiki_docs.extend(topic_docs)
        topic_wiki_results.append(
            _write_vectorstore(topic_approved_md(topic_slug).parent / "qdrant", topic_docs, scope=f"wiki:{topic_slug}", source=source)
        )

    # Global wiki = merge of all topic wikis
    global_wiki_result = _write_vectorstore(
        WIKI_ROOT / "_global" / "qdrant",
        all_wiki_docs,
        scope="wiki:global",
        source=source,
    )

    return {
        "status": "refreshed",
        "refreshed_at": _now(),
        "source": source,
        "patent_count": len(patent_results),
        "patent_vectorstores": patent_results,
        "topic_wiki_vectorstores": topic_wiki_results,
        "global_vectorstore": global_result,
        "global_wiki_vectorstore": global_wiki_result,
        "core_source_types": sorted(CORE_SEARCH_SOURCE_TYPES),
        "excluded_from_core_search": dict(sorted(excluded_by_policy.items())),
        "wiki_policy": "wiki is topic-based: WIKI_ROOT/{topic_slug}/approved_context.md indexed into a dedicated Qdrant collection",
        "web_policy": "non-core data is excluded from core vectorstores; questions without original/report/wiki evidence route to web search",
    }


def vectorstore_status() -> dict[str, Any]:
    from .wiki.topics import all_active_topic_slugs, topic_approved_md

    patent_status = []
    for patent_id in _patent_ids():
        patent_dir = PATENTS_ROOT / patent_id
        reviewed_path = _reviewed_docs_path(patent_id)
        info = collection_info(patent_collection(patent_id))
        patent_status.append(
            {
                "patent_id": patent_id,
                "exists": bool(info.get("exists")),
                "backend": "qdrant",
                "collection": patent_collection(patent_id),
                "document_count": info.get("points_count", 0),
                "refreshed_at": None,
                "qdrant": info,
                "has_human_reviewed_source": reviewed_path.exists(),
                "approved_markdown_path": str(_reviewed_md_path(patent_id)) if _reviewed_md_path(patent_id).exists() else None,
            }
        )

    topic_status = []
    for topic_slug in all_active_topic_slugs():
        approved = topic_approved_md(topic_slug)
        info = collection_info(wiki_collection(topic_slug))
        topic_status.append(
            {
                "topic": topic_slug,
                "vectorstore_exists": bool(info.get("exists")),
                "backend": "qdrant",
                "collection": wiki_collection(topic_slug),
                "document_count": info.get("points_count", 0),
                "refreshed_at": None,
                "approved_md_exists": approved.exists(),
                "approved_md_path": str(approved),
                "qdrant": info,
            }
        )

    global_info = collection_info(patent_collection(None))
    global_wiki_info = collection_info(wiki_collection(None))
    return {
        "backend": "qdrant",
        "rotation_policy": "qdrant_collection_replace; MinIO/local cache remains source of truth",
        "core_source_types": sorted(CORE_SEARCH_SOURCE_TYPES),
        "core_policy": "patent/report only; wiki is topic-based in dedicated Qdrant collections",
        "global": {
            "exists": bool(global_info.get("exists")),
            "backend": "qdrant",
            "collection": patent_collection(None),
            "document_count": global_info.get("points_count", 0),
            "refreshed_at": None,
            "qdrant": global_info,
        },
        "global_wiki": {
            "exists": bool(global_wiki_info.get("exists")),
            "backend": "qdrant",
            "collection": wiki_collection(None),
            "document_count": global_wiki_info.get("points_count", 0),
            "policy": "merged wiki from all topic vectorstores",
            "qdrant": global_wiki_info,
        },
        "topic_wiki": topic_status,
        "patents": patent_status,
    }


def _vector_collection(*, patent_id: str | None, source_types: set[str] | None) -> str:
    """검색에 사용할 Qdrant 컬렉션 이름을 반환.

    우선순위:
    1. wiki 검색 → 분야별 wiki collection (topic_slug) 또는 wiki live alias
    2. 특허 id 지정 → per-patent collection (있으면) → 공유 특허 collection (fallback)
    3. 전체 검색 → blue-green live alias → global 컬렉션 → 공유 특허 collection
    """
    requested = set(source_types or [])
    if requested and requested <= WIKI_SEARCH_SOURCE_TYPES:
        if patent_id:
            from .wiki.topics import get_patent_topic
            topic = get_patent_topic(patent_id)
            return wiki_collection(topic)
        alias = bluegreen_wiki_alias()
        if collection_exists(alias):
            return alias
        return wiki_collection(None)

    if patent_id:
        per_col = patent_collection(patent_id)
        if collection_exists(per_col) and (collection_info(per_col).get("points_count") or 0) > 0:
            return per_col
        return shared_patents_collection()  # alias → 실제 데이터 있는 슬롯

    # 전체 검색: 문서가 있는 alias 우선, 없으면 shared collection
    for candidate in [bluegreen_patent_alias(), patent_collection(None), shared_patents_collection()]:
        info = collection_info(candidate)
        if info.get("exists") and (info.get("points_count") or 0) > 0:
            return candidate
    return shared_patents_collection()


def _excerpt(text: str, query: str, size: int = 360) -> str:
    if len(text) <= size:
        return text
    lower = text.lower()
    positions = [lower.find(term) for term in _tokens(query) if lower.find(term) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - size // 3)
    end = min(len(text), start + size)
    return f"{'...' if start else ''}{text[start:end]}{'...' if end < len(text) else ''}"


def search_vectorstore(query: str, *, patent_id: str | None, source_types: set[str] | None, top_k: int) -> dict[str, Any]:
    effective_source_types = set(source_types) if source_types is not None else set(CORE_SEARCH_SOURCE_TYPES)
    collection = _vector_collection(patent_id=patent_id, source_types=effective_source_types)
    filter_patent_id = None if patent_id and effective_source_types <= WIKI_SEARCH_SOURCE_TYPES else patent_id

    # shared_patents_collection 사용 시 소스 타입을 SHARED_* 로 정규화
    # (ORIGINAL_PDF→SHARED_PATENT, REPORT_PDF→SHARED_REPORT 등)
    filter_source_types: set[str] | None = effective_source_types
    if collection == shared_patents_collection():
        try:
            from .shared_data import _normalize_shared_source_types
            filter_source_types = _normalize_shared_source_types(effective_source_types) or None
        except Exception:
            filter_source_types = None  # 필터 없이 전체 검색

    result = search_documents(
        collection,
        query,
        top_k=top_k,
        patent_id=filter_patent_id,
        source_types=filter_source_types,
    )
    usable_hits = [hit for hit in result.get("hits", []) if is_usable_evidence(hit.get("page_content"))]
    return {
        "query": query,
        "mode": "qdrant_vectorstore_search",
        "patent_id": patent_id,
        "top_k": top_k,
        "source_types": sorted(effective_source_types),
        "collection": collection,
        "hit_count": len(usable_hits),
        "hits": usable_hits,
        "embedding_provider": result.get("embedding_provider"),
        "embedding_error": result.get("embedding_error"),
    }


def _text_quality(text: str) -> dict[str, Any]:
    compact = "".join(str(text or "").split())
    signal = sum(1 for char in compact if char.isalnum() or ("가" <= char <= "힣"))
    signal_ratio = signal / max(len(compact), 1)
    tokens = _tokens(text)
    token_counts = Counter(tokens)
    most_common_ratio = token_counts.most_common(1)[0][1] / max(len(tokens), 1) if tokens else 0.0
    return {
        "char_count": len(text or ""),
        "compact_char_count": len(compact),
        "signal_ratio": round(signal_ratio, 4),
        "token_count": len(tokens),
        "most_common_token_ratio": round(most_common_ratio, 4),
    }


def _finding(
    *,
    rule_id: str,
    doc: dict[str, Any],
    message: str,
    quality: dict[str, Any],
    related_doc_id: str | None = None,
) -> dict[str, Any]:
    criteria = next(item for item in AUDIT_CRITERIA if item["rule_id"] == rule_id)
    metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
    text = str(doc.get("page_content") or "")
    seed = f"{doc.get('doc_id')}:{rule_id}:{related_doc_id or ''}"
    return {
        "finding_id": hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16],
        "rule_id": rule_id,
        "severity": criteria["severity"],
        "default_action": criteria["default_action"],
        "doc_id": doc.get("doc_id"),
        "related_doc_id": related_doc_id,
        "patent_id": metadata.get("patent_id"),
        "source_type": metadata.get("source_type"),
        "source_path": metadata.get("source_path"),
        "relative_source_path": metadata.get("relative_source_path"),
        "line_no": metadata.get("line_no"),
        "title": metadata.get("title"),
        "section_title": metadata.get("section_title"),
        "message": message,
        "quality": quality,
        "excerpt": text[:500],
    }


def _audit_documents() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for patent_id in _patent_ids():
        docs.extend(collect_patent_documents(patent_id, use_reviewed=False))
    docs.extend(_business_documents())

    findings: list[dict[str, Any]] = []
    seen_hashes: dict[str, str] = {}
    by_severity: dict[str, int] = defaultdict(int)
    by_rule: dict[str, int] = defaultdict(int)

    for doc in docs:
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        patent_id = str(metadata.get("patent_id") or "")
        text = str(doc.get("page_content") or "")
        quality = _text_quality(text)

        def add(rule_id: str, message: str, related_doc_id: str | None = None) -> None:
            finding = _finding(rule_id=rule_id, doc=doc, message=message, quality=quality, related_doc_id=related_doc_id)
            findings.append(finding)
            by_severity[finding["severity"]] += 1
            by_rule[rule_id] += 1

        if quality["compact_char_count"] < 30:
            add("EMPTY_OR_TOO_SHORT", "본문이 너무 짧아 검색 근거로 사용하기 어렵습니다.")
        if quality["compact_char_count"] >= 80 and quality["signal_ratio"] < 0.45:
            add("OCR_NOISE", "문자 대비 기호/잡음 비율이 높아 OCR 또는 표 추출 잡음일 가능성이 큽니다.")
        if ERROR_RE.search(text):
            add("ERROR_TEXT", "오류/traceback 계열 문자열이 포함되어 있습니다.")
        if SECRET_RE.search(text):
            add("SECRET_PATTERN", "API key 또는 private key로 보이는 민감정보 패턴이 포함되어 있습니다.")
        if patent_id not in {"", "_business"}:
            source_path = str(metadata.get("source_path") or "")
            if "/mapped_patent_reports/" in source_path and f"/{patent_id}/" not in source_path:
                add("METADATA_MISMATCH", "metadata patent_id와 실제 source path의 특허 폴더가 다릅니다.")
        if quality["most_common_token_ratio"] > 0.35 or REPEATED_CHAR_RE.search(text):
            add("REPEATED_PATTERN", "동일 토큰 또는 문자가 과도하게 반복됩니다.")
        if not metadata.get("source_type") or not metadata.get("source_path"):
            add("MISSING_METADATA", "출처 추적에 필요한 metadata가 부족합니다.")
        if len(text) >= MAX_TEXT_CHARS:
            add("OVERSIZED_DOCUMENT", f"본문이 {MAX_TEXT_CHARS}자 이상이라 vectorstore 저장 시 잘릴 수 있습니다.")

        text_hash = str(metadata.get("text_hash") or _hash_text(text))
        if text_hash in seen_hashes:
            add("DUPLICATE_TEXT", "동일 text hash가 이미 존재합니다.", related_doc_id=seen_hashes[text_hash])
        else:
            seen_hashes[text_hash] = str(doc.get("doc_id"))

    summary = {
        "documents_scanned": len(docs),
        "finding_count": len(findings),
        "by_severity": dict(sorted(by_severity.items())),
        "by_rule": dict(sorted(by_rule.items())),
        "default_exclude_count": sum(1 for finding in findings if finding["default_action"] == "exclude"),
        "review_count": sum(1 for finding in findings if finding["default_action"] == "review"),
    }
    return docs, findings, summary


def _audit_dir(audit_id: str) -> Path:
    return WIKI_AUDITOR_ROOT / "audits" / audit_id


def _current_audit_path() -> Path:
    return WIKI_AUDITOR_ROOT / "current_audit.json"


def _load_audit(audit_id: str | None = None) -> dict[str, Any]:
    if not audit_id:
        current = _read_json(_current_audit_path())
        audit_id = current.get("audit_id")
    if not audit_id:
        raise HTTPException(status_code=404, detail="실행된 감사가 없습니다.")
    path = _audit_dir(str(audit_id)) / "audit.json"
    audit = _read_json(path)
    if not audit:
        raise HTTPException(status_code=404, detail=f"감사 결과를 찾을 수 없습니다: {audit_id}")
    return audit


def _write_review_markdown(audit: dict[str, Any]) -> str:
    audit_id = str(audit["audit_id"])
    path = _audit_dir(audit_id) / "review.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 챗봇 데이터 감사 검토서",
        "",
        f"- Audit ID: `{audit_id}`",
        f"- 감사 일시: {audit['audited_at']}",
        f"- 스캔 문서 수: {audit['summary']['documents_scanned']}",
        f"- 발견 후보 수: {audit['summary']['finding_count']}",
        f"- 기본 제외 후보 수: {audit['summary']['default_exclude_count']}",
        "",
        "## 평가 기준",
    ]
    for criteria in AUDIT_CRITERIA:
        lines.append(
            f"- `{criteria['rule_id']}` / {criteria['severity']} / 기본 `{criteria['default_action']}`: "
            f"{criteria['description']}"
        )
    lines.extend(["", "## 사람 검토가 필요한 후보"])
    if not audit["findings"]:
        lines.append("- 발견된 후보 없음")
    for finding in audit["findings"]:
        lines.extend(
            [
                "",
                f"### {finding['finding_id']} - {finding['rule_id']}",
                "",
                f"- severity: `{finding['severity']}`",
                f"- default_action: `{finding['default_action']}`",
                f"- patent_id: `{finding.get('patent_id')}`",
                f"- source_type: `{finding.get('source_type')}`",
                f"- source: `{finding.get('relative_source_path')}`",
                f"- line: `{finding.get('line_no')}`",
                f"- message: {finding['message']}",
                "",
                "```text",
                str(finding.get("excerpt") or "")[:1200],
                "```",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def run_audit() -> dict[str, Any]:
    _, findings, summary = _audit_documents()
    audit_id = _audit_id()
    audit = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "audit_id": audit_id,
        "audited_at": _now(),
        "status": "human_review_required" if findings else "clean",
        "criteria": AUDIT_CRITERIA,
        "summary": summary,
        "findings": findings,
    }
    audit_path = _audit_dir(audit_id) / "audit.json"
    _write_json(audit_path, audit)
    review_path = _write_review_markdown(audit)
    audit["audit_path"] = str(audit_path)
    audit["review_markdown_path"] = review_path
    _write_json(audit_path, audit)
    _write_json(_current_audit_path(), {"audit_id": audit_id, "audit_path": str(audit_path), "review_markdown_path": review_path})
    _write_audit_report(audit)
    return audit


def audit_review_report(audit_id: str | None = None) -> dict[str, Any]:
    audit = _load_audit(audit_id)
    review_path = Path(str(audit.get("review_markdown_path") or _audit_dir(str(audit["audit_id"])) / "review.md"))
    if not review_path.exists():
        review_path = Path(_write_review_markdown(audit))
    return {"audit": audit, "path": str(review_path), "markdown": review_path.read_text(encoding="utf-8")}


def _finding_doc_ids(audit: dict[str, Any], exclude_finding_ids: set[str]) -> set[str]:
    excluded = set()
    for finding in audit.get("findings") or []:
        if finding.get("finding_id") in exclude_finding_ids and finding.get("doc_id"):
            excluded.add(str(finding["doc_id"]))
    return excluded


def _default_exclude_ids(audit: dict[str, Any]) -> set[str]:
    return {
        str(finding["finding_id"])
        for finding in audit.get("findings") or []
        if finding.get("default_action") == "exclude" and finding.get("finding_id")
    }


def _auto_caution_exclude_ids(audit: dict[str, Any]) -> set[str]:
    """Exclude bad/high-risk findings and medium caution findings automatically.

    Low-severity review findings still stay in the approved corpus unless a
    human excludes them explicitly, because they are usually metadata or length
    notices rather than evidence corruption.
    """
    selected = _default_exclude_ids(audit)
    for finding in audit.get("findings") or []:
        if not finding.get("finding_id"):
            continue
        if finding.get("default_action") == "review" and finding.get("severity") in {"high", "medium"}:
            selected.add(str(finding["finding_id"]))
    return selected


def _wiki_markdown_from_approved_docs(patent_id: str, approved_docs: list[dict[str, Any]], *, audit_id: str) -> str:
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for doc in approved_docs:
        source_type = _source_type(doc) or "UNKNOWN"
        if source_type == "WIKI":
            continue
        by_type[source_type].append(doc)

    lines = [
        f"# {patent_id} 감사 승인 Wiki Context",
        "",
        "## 질문",
        "",
        f"`{patent_id}` 특허에 대해 사람이 승인한 데이터만 기준으로 답변할 때 사용할 핵심 근거는 무엇인가?",
        "",
        "## 답변",
    ]
    for source_type in sorted(by_type):
        docs = by_type[source_type][:6]
        lines.extend(["", f"### {source_type}"])
        for index, doc in enumerate(docs, 1):
            metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
            title = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title") or doc.get("doc_id")
            text = preprocess_evidence_text(doc.get("page_content"), max_chars=650)
            lines.append(f"- {index}. {title}: {text[:650]}")
    lines.extend(
        [
            "",
            "## 메타정보",
            "",
            f"- Patent ID: `{patent_id}`",
            f"- Audit ID: `{audit_id}`",
            "- Source: human-approved patent/report/wiki corpus",
            "- Vectorstore policy: 이 wiki 문서는 해당 특허의 단독 wiki vectorstore에만 반영되고 global vectorstore에는 포함되지 않습니다.",
            "- Excluded data: 감사에서 제외된 finding과 저품질 placeholder 문장은 반영하지 않습니다.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _write_approved_files(
    *,
    audit: dict[str, Any],
    excluded_finding_ids: set[str],
    reviewer: str | None,
    notes: str | None,
) -> dict[str, Any]:
    excluded_doc_ids = _finding_doc_ids(audit, excluded_finding_ids)
    written = []
    total_approved = 0
    total_excluded = 0
    approved_at = _now()

    for patent_id in _patent_ids():
        raw_docs = collect_patent_documents(patent_id, use_reviewed=False)
        approved_docs = []
        excluded_docs = []
        for doc in raw_docs:
            metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
            metadata.update(
                {
                    "human_review_status": "approved",
                    "human_review_audit_id": audit["audit_id"],
                    "human_reviewed_at": approved_at,
                }
            )
            if reviewer:
                metadata["human_reviewer"] = reviewer
            doc["metadata"] = metadata
            if str(doc.get("doc_id")) in excluded_doc_ids:
                excluded_docs.append(doc)
            else:
                approved_docs.append(doc)

        from .wiki.topics import get_patent_topic, topic_approved_md

        reviewed_dir = PATENTS_ROOT / patent_id / "reviewed"
        reviewed_dir.mkdir(parents=True, exist_ok=True)
        docs_path = reviewed_dir / "approved_documents.jsonl"
        md_path = reviewed_dir / "approved_context.md"
        manifest_path = reviewed_dir / "manifest.json"

        topic = get_patent_topic(patent_id)
        wiki_md_path = topic_approved_md(topic)
        wiki_md_path.parent.mkdir(parents=True, exist_ok=True)
        wiki_markdown = _wiki_markdown_from_approved_docs(patent_id, approved_docs, audit_id=str(audit["audit_id"]))
        with wiki_md_path.open("a", encoding="utf-8") as f:
            f.write(wiki_markdown)
        wiki_doc = _document(
            patent_id=f"_wiki_{topic}",
            text=wiki_markdown,
            source_path=wiki_md_path,
            source_type="WIKI",
            metadata={
                "title": f"{topic} 감사 승인 Wiki Context",
                "file_name": wiki_md_path.name,
                "topic": topic,
                "human_review_source": "approved_context",
            },
        )
        if wiki_doc:
            wiki_doc_metadata = wiki_doc.get("metadata") if isinstance(wiki_doc.get("metadata"), dict) else {}
            wiki_doc_metadata.update(
                {
                    "human_review_status": "approved",
                    "human_review_audit_id": audit["audit_id"],
                    "human_reviewed_at": approved_at,
                }
            )
            if reviewer:
                wiki_doc_metadata["human_reviewer"] = reviewer
            wiki_doc["metadata"] = wiki_doc_metadata
            approved_docs.append(wiki_doc)

        with docs_path.open("w", encoding="utf-8") as file:
            for doc in approved_docs:
                file.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")

        lines = [
            "# Human Approved Chatbot Context",
            "",
            f"- Patent ID: `{patent_id}`",
            f"- Audit ID: `{audit['audit_id']}`",
            f"- Approved at: {approved_at}",
            f"- Reviewer: {reviewer or 'unspecified'}",
            f"- Approved documents: {len(approved_docs)}",
            f"- Excluded documents: {len(excluded_docs)}",
        ]
        if notes:
            lines.extend(["", "## Review Notes", "", notes])
        lines.extend(["", "## Approved Content"])
        for index, doc in enumerate(approved_docs, 1):
            metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
            lines.extend(
                [
                    "",
                    f"### {index}. {metadata.get('source_type')} / {metadata.get('section_title') or metadata.get('file_name') or doc.get('doc_id')}",
                    "",
                    f"- doc_id: `{doc.get('doc_id')}`",
                    f"- source: `{metadata.get('relative_source_path')}`",
                    f"- line: `{metadata.get('line_no')}`",
                    "",
                    str(doc.get("page_content") or ""),
                ]
            )
        manifest = {
            "audit_id": audit["audit_id"],
            "approved_at": approved_at,
            "reviewer": reviewer,
            "notes": notes,
            "excluded_finding_ids": sorted(excluded_finding_ids),
            "excluded_doc_ids": sorted(excluded_doc_ids),
            "approved_document_count": len(approved_docs),
            "excluded_document_count": len(excluded_docs),
            "approved_markdown_path": str(md_path),
            "topic_wiki_markdown_path": str(wiki_md_path),
            "approved_documents_path": str(docs_path),
        }
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        _write_json(manifest_path, manifest)

        total_approved += len(approved_docs)
        total_excluded += len(excluded_docs)
        written.append(
            {
                "patent_id": patent_id,
                "approved_document_count": len(approved_docs),
                "excluded_document_count": len(excluded_docs),
                "approved_markdown_path": str(md_path),
                "wiki_markdown_path": str(wiki_md_path),
                "approved_documents_path": str(docs_path),
                "manifest_path": str(manifest_path),
            }
        )

    return {
        "approved_at": approved_at,
        "reviewer": reviewer,
        "approved_document_count": total_approved,
        "excluded_document_count": total_excluded,
        "patents": written,
    }


def apply_human_review(
    *,
    audit_id: str | None = None,
    exclude_finding_ids: list[str] | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
    refresh_vectorstore: bool = True,
) -> dict[str, Any]:
    audit = _load_audit(audit_id)
    selected_ids = set(exclude_finding_ids) if exclude_finding_ids is not None else _default_exclude_ids(audit)
    known_ids = {str(finding.get("finding_id")) for finding in audit.get("findings") or []}
    unknown = sorted(item for item in selected_ids if item not in known_ids)
    if unknown:
        raise HTTPException(status_code=400, detail={"message": "알 수 없는 finding_id가 있습니다.", "unknown": unknown})

    approved = _write_approved_files(audit=audit, excluded_finding_ids=selected_ids, reviewer=reviewer, notes=notes)
    vectorstore_refresh = refresh_vectorstores(use_reviewed=True) if refresh_vectorstore else None
    result = {
        "status": "applied",
        "audit_id": audit["audit_id"],
        "excluded_finding_ids": sorted(selected_ids),
        "approved": approved,
        "vectorstore_refresh": vectorstore_refresh,
    }
    result_path = _audit_dir(str(audit["audit_id"])) / "apply_result.json"
    _write_json(result_path, result)
    _write_audit_report({**audit, "status": "applied", "apply_result": result, "vectorstore_refresh": vectorstore_refresh})
    return result


def auto_audit_apply_and_refresh(*, refresh_vectorstore: bool = True) -> dict[str, Any]:
    audit = run_audit()
    selected_ids = _auto_caution_exclude_ids(audit)
    approved = _write_approved_files(
        audit=audit,
        excluded_finding_ids=selected_ids,
        reviewer="auto-auditor",
        notes=(
            "자동 감사 정책: default_action=exclude 후보와 severity=medium 이상 review 후보를 "
            "주의/나쁜 데이터로 보고 승인 corpus에서 제외했습니다. low review 후보는 보존합니다."
        ),
    )
    vectorstore_refresh = refresh_vectorstores(use_reviewed=True) if refresh_vectorstore else None
    result = {
        "status": "auto_applied",
        "audit_id": audit["audit_id"],
        "auto_policy": {
            "excluded": "default_action=exclude OR (default_action=review AND severity in high,medium)",
            "kept_for_human_only": "low severity review findings",
            "atomic_refresh": True,
        },
        "excluded_finding_ids": sorted(selected_ids),
        "approved": approved,
        "vectorstore_refresh": vectorstore_refresh,
    }
    result_path = _audit_dir(str(audit["audit_id"])) / "auto_apply_result.json"
    _write_json(result_path, result)
    _write_audit_report(
        {
            **audit,
            "status": "auto_applied",
            "apply_result": result,
            "vectorstore_refresh": vectorstore_refresh,
        }
    )
    return {"audit": audit, "apply_result": result}


def nightly_reindex_all() -> dict[str, Any]:
    """Run the Kubernetes CronJob reindex workflow once.

    This is intentionally one-shot. Kubernetes should schedule it at midnight
    with a CronJob. MinIO/local cache is the source of truth and Qdrant
    collections are rebuilt from that approved data.
    """

    started_at = _now()
    wiki_result = auto_audit_apply_and_refresh(refresh_vectorstore=True)

    # Rebuild shared patent vectorstore (PROJECT_ROOT/data/patent)
    shared_index_result: dict[str, Any] | None = None
    try:
        from .shared_data import build_shared_vectorstore
        shared_index_result = build_shared_vectorstore()
    except Exception as exc:
        shared_index_result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    # Incrementally build visual-only vectorstore for newly added patent originals.
    visual_index_result: dict[str, Any] | None = None
    try:
        from .visual_data import build_missing_patent_visual_indexes

        visual_index_result = build_missing_patent_visual_indexes(force=False)
    except Exception as exc:
        visual_index_result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    result = {
        "status": "completed",
        "workflow": "nightly_qdrant_reindex",
        "started_at": started_at,
        "finished_at": _now(),
        "schedule_hint": "Kubernetes CronJob: 0 0 * * *",
        "wiki_auto_audit": wiki_result,
        "shared_patent_index": shared_index_result,
        "shared_patent_visual_index": visual_index_result,
        "vectorstore_status": vectorstore_status(),
    }
    log_path = WIKI_AUDITOR_ROOT / "nightly_reindex.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    return result


def audit_and_refresh_vectorstores(*, refresh_vectorstore: bool = False) -> dict[str, Any]:
    audit = run_audit()
    if refresh_vectorstore:
        audit["vectorstore_refresh"] = refresh_vectorstores(use_reviewed=False)
        audit["status"] = "raw_vectorstore_refreshed"
        _write_json(_audit_dir(str(audit["audit_id"])) / "audit.json", audit)
        _write_audit_report(audit)
    return audit


def _write_audit_report(report: dict[str, Any]) -> None:
    WIKI_AUDITOR_ROOT.mkdir(parents=True, exist_ok=True)
    markdown_path = WIKI_AUDITOR_ROOT / "audit_report.md"
    summary = report.get("summary") or {}
    lines = [
        "# 위키/챗봇 데이터 감사 리포트",
        "",
        f"**감사 일시**: {report.get('audited_at')}",
        f"**상태**: {report.get('status')}",
        f"**Audit ID**: `{report.get('audit_id')}`",
        f"**스캔 문서 수**: {summary.get('documents_scanned')}",
        f"**발견 후보**: {summary.get('finding_count')}개",
        f"**기본 제외 후보**: {summary.get('default_exclude_count')}개",
        "",
        "## 평가 기준",
    ]
    for criteria in AUDIT_CRITERIA:
        lines.append(f"- `{criteria['rule_id']}`: {criteria['description']}")

    apply_result = report.get("apply_result") or {}
    if apply_result:
        approved = apply_result.get("approved") or {}
        lines.extend(
            [
                "",
                "## 사람 검토 적용 결과",
                "",
                f"- 승인 문서 수: {approved.get('approved_document_count')}",
                f"- 제외 문서 수: {approved.get('excluded_document_count')}",
                f"- 제외 finding 수: {len(apply_result.get('excluded_finding_ids') or [])}",
            ]
        )

    refresh = report.get("vectorstore_refresh") or {}
    lines.extend(["", "## Vectorstore 갱신"])
    if refresh:
        lines.extend(
            [
                "",
                f"- 상태: {refresh.get('status')}",
                f"- 갱신 시각: {refresh.get('refreshed_at')}",
                f"- source: {refresh.get('source')}",
                f"- 특허별 vectorstore 수: {refresh.get('patent_count')}",
                f"- global 문서 수: {refresh.get('global_vectorstore', {}).get('document_count')}",
            ]
        )
    else:
        lines.extend(["", "- 아직 vectorstore 갱신 전입니다. 사람 검토 적용 후 갱신하세요."])

    lines.extend(["", "## 발견 후보"])
    findings = report.get("findings") or []
    if findings:
        for finding in findings[:100]:
            lines.append(
                f"- [{finding['severity']}] `{finding['finding_id']}` {finding['patent_id']} "
                f"{finding['rule_id']}: {finding['message']}"
            )
        if len(findings) > 100:
            lines.append(f"- ... {len(findings) - 100}개 추가 후보 생략")
    else:
        lines.append("- 발견된 후보 없음")

    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_path = WIKI_AUDITOR_ROOT / "audit.log"
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")


# ---------------------------------------------------------------------------
# Web draft index + auto-approve
# ---------------------------------------------------------------------------

WIKI_AUTO_APPROVE_MIN_RELEVANCE = 0.50
WIKI_AUTO_APPROVE_MIN_RESULTS = 1
WIKI_DRAFT_DEDUP_HOURS = 20


def _read_draft_index(topic_slug: str) -> dict[str, Any]:
    from .wiki.topics import topic_draft_index_path
    path = topic_draft_index_path(topic_slug)
    if not path.exists():
        return {"topic": topic_slug, "drafts": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"topic": topic_slug, "drafts": []}
    return data if isinstance(data, dict) else {"topic": topic_slug, "drafts": []}


def _write_draft_index(topic_slug: str, index: dict[str, Any]) -> None:
    from .wiki.topics import topic_draft_index_path
    path = topic_draft_index_path(topic_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    index["updated_at"] = _now()
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")


def is_duplicate_web_query(patent_id: str, query_hash: str) -> bool:
    """True if the same query hash was searched for this patent's topic within WIKI_DRAFT_DEDUP_HOURS."""
    from datetime import datetime, timedelta
    from .wiki.topics import get_patent_topic

    topic = get_patent_topic(patent_id)
    index = _read_draft_index(topic)
    cutoff = (datetime.now() - timedelta(hours=WIKI_DRAFT_DEDUP_HOURS)).isoformat()
    for draft in index.get("drafts", []):
        if draft.get("query_hash") == query_hash and draft.get("created_at", "") >= cutoff:
            return True
    return False


def get_patent_draft_stats(patent_id: str) -> dict[str, Any]:
    """Return counts of pending / auto-approved web search drafts for a patent's topic."""
    from .wiki.topics import get_patent_topic

    topic = get_patent_topic(patent_id)
    index = _read_draft_index(topic)
    drafts = index.get("drafts", [])
    pending = sum(1 for d in drafts if d.get("status") == "pending")
    auto_approved = sum(1 for d in drafts if d.get("status") == "auto_approved")
    return {
        "patent_id": patent_id,
        "topic": topic,
        "total_drafts": len(drafts),
        "pending_review": pending,
        "auto_approved": auto_approved,
        "has_pending": pending > 0,
    }


def auto_approve_web_draft(
    patent_id: str,
    *,
    draft_path: str | None,
    query: str,
    results: list[dict[str, Any]],
    topic_override: str | None = None,
) -> dict[str, Any]:
    """Promote high-quality web results to the topic wiki vectorstore without human review.

    If avg relevance >= WIKI_AUTO_APPROVE_MIN_RELEVANCE, content is appended to
    WIKI_ROOT/{topic}/approved_context.md and the topic vectorstore is refreshed.
    Low-quality drafts are recorded as pending for the normal audit cycle.
    _global patent and empty result lists are always skipped.
    topic_override forces a specific topic slug regardless of patent_id mapping.
    """
    from .wiki.topics import (
        get_patent_topic,
        topic_approved_md,
        topic_wiki_root,
    )

    if patent_id in {"_global", ""} or not results:
        return {"auto_approved": False, "reason": "skipped_global_or_empty"}

    topic = topic_override or get_patent_topic(patent_id)
    query_hash = hashlib.sha1(query.encode("utf-8")).hexdigest()[:12]

    relevance_scores = [
        float((r.get("relevance") or {}).get("score") or 0.0)
        for r in results
    ]
    avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    result_count = len(results)

    index = _read_draft_index(topic)
    drafts: list[dict[str, Any]] = index.get("drafts", [])

    draft_entry: dict[str, Any] = {
        "query_hash": query_hash,
        "query": query,
        "patent_id": patent_id,
        "topic": topic,
        "created_at": _now(),
        "draft_file": Path(draft_path).name if draft_path else "",
        "result_count": result_count,
        "avg_relevance": round(avg_relevance, 4),
        "status": "pending",
    }

    can_auto_approve = (
        result_count >= WIKI_AUTO_APPROVE_MIN_RESULTS
        and avg_relevance >= WIKI_AUTO_APPROVE_MIN_RELEVANCE
    )

    if can_auto_approve:
        lines = [
            "",
            f"## 자동 승인 웹 근거 — {_now()[:10]}",
            "",
            f"- 특허: {patent_id}  분야: {topic}",
            f"- 질문: {query}",
            f"- 평균 관련도: {avg_relevance:.2f} (기준 ≥ {WIKI_AUTO_APPROVE_MIN_RELEVANCE})",
            f"- 결과 수: {result_count}",
            "",
        ]
        for idx, r in enumerate(results, 1):
            title = str(r.get("title") or "web result")
            url = str(r.get("url") or "")
            snippet = preprocess_evidence_text(r.get("snippet") or "", max_chars=600)
            rel = r.get("relevance") if isinstance(r.get("relevance"), dict) else {}
            matched = rel.get("matched_terms") or []
            lines.append(f"### {idx}. {title}")
            if url:
                lines.append(f"- URL: {url}")
            if matched:
                lines.append(f"- 매칭 키워드: {', '.join(str(t) for t in matched)}")
            lines.extend(["", snippet or "", ""])

        approved_md = topic_approved_md(topic)
        approved_md.parent.mkdir(parents=True, exist_ok=True)
        with approved_md.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        topic_docs = list(_topic_wiki_documents(topic))
        _write_vectorstore(
            approved_md.parent / "qdrant",
            topic_docs,
            scope=f"wiki:{topic}",
            source="auto_approved_web",
        )

        draft_entry["status"] = "auto_approved"
        draft_entry["auto_approved_at"] = _now()

    drafts.append(draft_entry)
    index["drafts"] = drafts
    _write_draft_index(topic, index)

    return {
        "auto_approved": can_auto_approve,
        "topic": topic,
        "avg_relevance": round(avg_relevance, 4),
        "result_count": result_count,
        "reason": "high_relevance" if can_auto_approve else f"low_relevance ({avg_relevance:.2f} < {WIKI_AUTO_APPROVE_MIN_RELEVANCE})",
    }


# ---------------------------------------------------------------------------
# Blue-green hourly refresh (무중단 글로벌 색인 교체)
# ---------------------------------------------------------------------------

def full_rebuild_vectorstores() -> dict[str, Any]:
    """모든 특허·wiki Qdrant 컬렉션을 삭제하고 처음부터 재구축.

    삭제 대상 (pre-eval/visual 은 건드리지 않음):
      - skipa_patent_docs, skipa_patent_docs_global
      - skipa_wiki_docs_global, skipa_wiki_topic_* 컬렉션
      - skipa_patent_live*, skipa_wiki_live* (blue-green 슬롯)
      - per-patent 컬렉션 (skipa_patent_doc_*)

    재구축 순서:
      1. shared 특허 컬렉션 (data/patent/ → skipa_patent_docs)
      2. wiki 컬렉션 (approved_context.md → skipa_wiki_topic_*)
      3. global wiki 컬렉션 (skipa_wiki_docs_global)
    """
    from urllib.parse import quote as _url_quote
    from .qdrant_store import _json_request, _aliases_list, QDRANT_COLLECTION_PREFIX

    started_at = _now()
    deleted: list[str] = []
    errors: list[str] = []

    # 삭제할 컬렉션 패턴
    _DELETE_PATTERNS = (
        f"{QDRANT_COLLECTION_PREFIX}_patent_docs",        # shared main
        f"{QDRANT_COLLECTION_PREFIX}_patent_docs_global", # review global
        f"{QDRANT_COLLECTION_PREFIX}_wiki_docs_global",   # wiki global
        f"{QDRANT_COLLECTION_PREFIX}_patent_live",        # blue-green alias slots
        f"{QDRANT_COLLECTION_PREFIX}_wiki_live",          # blue-green alias slots
        f"{QDRANT_COLLECTION_PREFIX}_patent_doc_",        # per-patent prefix
        f"{QDRANT_COLLECTION_PREFIX}_wiki_topic_",        # per-topic wiki prefix
    )

    # 기존 컬렉션 목록 조회
    try:
        resp = _json_request("GET", "/collections", None)
        existing = [c.get("name", "") for c in (resp.get("result") or {}).get("collections") or []]
    except Exception as exc:
        return {"status": "error", "error": f"컬렉션 목록 조회 실패: {exc}"}

    # alias 삭제 (blue-green alias)
    for alias_item in _aliases_list():
        alias_name = str(alias_item.get("alias_name") or "")
        if any(alias_name.startswith(p) for p in _DELETE_PATTERNS):
            try:
                _json_request("POST", "/collections/aliases", {
                    "actions": [{"delete_alias": {"alias_name": alias_name}}]
                })
                deleted.append(f"alias:{alias_name}")
            except Exception as exc:
                errors.append(f"alias:{alias_name} 삭제 실패: {exc}")

    # 컬렉션 삭제
    for col in existing:
        if any(col.startswith(p) or col == p.rstrip("_") for p in _DELETE_PATTERNS):
            try:
                _json_request("DELETE", f"/collections/{_url_quote(col, safe='')}", None)
                deleted.append(f"collection:{col}")
            except Exception as exc:
                errors.append(f"collection:{col} 삭제 실패: {exc}")

    # 재구축 1: shared 특허 컬렉션
    shared_result: dict[str, Any] = {}
    try:
        from .shared_data import build_shared_vectorstore
        shared_result = build_shared_vectorstore()
    except Exception as exc:
        shared_result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        errors.append(f"shared 특허 컬렉션 재구축 실패: {exc}")

    # 재구축 2: wiki 컬렉션 (분야별)
    from .wiki.topics import all_active_topic_slugs, topic_approved_md
    topic_results: list[dict[str, Any]] = []
    all_wiki_docs: list[dict[str, Any]] = []
    for topic_slug in all_active_topic_slugs():
        topic_docs = list(_topic_wiki_documents(topic_slug))
        all_wiki_docs.extend(topic_docs)
        try:
            r = _write_vectorstore(
                topic_approved_md(topic_slug).parent / "qdrant",
                topic_docs,
                scope=f"wiki:{topic_slug}",
                source="full_rebuild",
            )
            topic_results.append({"topic": topic_slug, **r})
        except Exception as exc:
            topic_results.append({"topic": topic_slug, "status": "error", "error": str(exc)})
            errors.append(f"wiki:{topic_slug} 재구축 실패: {exc}")

    # 재구축 3: global wiki (blue-green)
    global_wiki_result: dict[str, Any] = {}
    try:
        global_wiki_result = _write_vectorstore(
            WIKI_ROOT / "_global" / "qdrant",
            all_wiki_docs,
            scope="wiki:global",
            source="full_rebuild",
        )
    except Exception as exc:
        global_wiki_result = {"status": "error", "error": str(exc)}
        errors.append(f"wiki:global 재구축 실패: {exc}")

    result = {
        "status": "completed" if not errors else "completed_with_errors",
        "workflow": "full_rebuild_vectorstores",
        "started_at": started_at,
        "finished_at": _now(),
        "deleted": deleted,
        "errors": errors,
        "shared_patents": {
            "collection": shared_patents_collection(),
            "patent_count": shared_result.get("patent_count"),
            "document_count": shared_result.get("document_count"),
            "status": shared_result.get("status", "built"),
        },
        "wiki_topics": topic_results,
        "wiki_global": {
            "collection": global_wiki_result.get("collection"),
            "document_count": global_wiki_result.get("document_count"),
            "qdrant": global_wiki_result.get("qdrant"),
        },
    }
    _save_bluegreen_status({"type": "full_rebuild", **result})
    return result


def _bluegreen_log_path() -> Path:
    return WIKI_AUDITOR_ROOT / "bluegreen_status.json"


def _save_bluegreen_status(data: dict[str, Any]) -> None:
    """마지막 blue-green 실행 결과를 JSON 파일로 영속화."""
    path = _bluegreen_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    except Exception:
        pass


def _load_bluegreen_status() -> dict[str, Any]:
    path = _bluegreen_log_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def bluegreen_refresh_patent_only() -> dict[str, Any]:
    """특허 원본 PDF·보고서 글로벌 컬렉션만 blue-green 재색인.

    API 호출 시 트리거됩니다 (POST /api/v1/chatbot/bluegreen/refresh).
    wiki는 1시간 스케줄러(bluegreen_refresh_wiki_only)가 담당합니다.
    """
    started_at = _now()
    source = "bluegreen_api_trigger"

    global_docs: list[dict[str, Any]] = []
    patent_results = []
    for patent_id in _patent_ids():
        docs = collect_patent_documents(patent_id, use_reviewed=True)
        core_docs = [doc for doc in docs if _is_core_search_doc(doc)]
        global_docs.extend(core_docs)
        patent_results.append({"patent_id": patent_id, "doc_count": len(core_docs)})

    global_patent_result = _write_vectorstore(
        PATENTS_ROOT / "_global" / "index" / "qdrant",
        global_docs,
        scope="global",
        source=source,
    )

    result: dict[str, Any] = {
        "status": "completed",
        "workflow": "bluegreen_patent_refresh",
        "started_at": started_at,
        "finished_at": _now(),
        "patent_doc_count": len(global_docs),
        "patents": patent_results,
        "global_patent": {
            "collection": global_patent_result.get("collection"),
            "document_count": global_patent_result.get("document_count"),
            "active_color": (global_patent_result.get("qdrant") or {}).get("active_color"),
            "alias": (global_patent_result.get("qdrant") or {}).get("alias"),
        },
    }
    last = _load_bluegreen_status()
    _save_bluegreen_status({**last, **result, "patent_refreshed_at": started_at})
    return result


def bluegreen_refresh_wiki_only() -> dict[str, Any]:
    """글로벌 wiki 컬렉션만 blue-green 재색인.

    1시간 스케줄러에서 호출됩니다.
    """
    from .wiki.topics import all_active_topic_slugs

    started_at = _now()
    source = "bluegreen_hourly"

    all_wiki_docs: list[dict[str, Any]] = []
    for topic_slug in all_active_topic_slugs():
        all_wiki_docs.extend(list(_topic_wiki_documents(topic_slug)))

    global_wiki_result = _write_vectorstore(
        WIKI_ROOT / "_global" / "qdrant",
        all_wiki_docs,
        scope="wiki:global",
        source=source,
    )

    result: dict[str, Any] = {
        "status": "completed",
        "workflow": "bluegreen_wiki_hourly",
        "started_at": started_at,
        "finished_at": _now(),
        "wiki_doc_count": len(all_wiki_docs),
        "global_wiki": {
            "collection": global_wiki_result.get("collection"),
            "document_count": global_wiki_result.get("document_count"),
            "active_color": (global_wiki_result.get("qdrant") or {}).get("active_color"),
            "alias": (global_wiki_result.get("qdrant") or {}).get("alias"),
        },
    }
    last = _load_bluegreen_status()
    _save_bluegreen_status({**last, **result, "wiki_refreshed_at": started_at})
    return result


def bluegreen_refresh_global() -> dict[str, Any]:
    """특허·wiki 글로벌 컬렉션 모두 blue-green 재색인 (수동/레거시 호환).

    일반 운영에서는 특허는 API 트리거(bluegreen_refresh_patent_only),
    wiki는 1시간 스케줄러(bluegreen_refresh_wiki_only)로 각각 실행합니다.
    """
    patent_result = bluegreen_refresh_patent_only()
    wiki_result = bluegreen_refresh_wiki_only()
    result: dict[str, Any] = {
        "status": "completed",
        "workflow": "bluegreen_full_refresh",
        "started_at": patent_result["started_at"],
        "finished_at": wiki_result["finished_at"],
        "patent_doc_count": patent_result["patent_doc_count"],
        "wiki_doc_count": wiki_result["wiki_doc_count"],
        "global_patent": patent_result["global_patent"],
        "global_wiki": wiki_result["global_wiki"],
    }
    _save_bluegreen_status(result)
    return result


def bluegreen_reindex_status() -> dict[str, Any]:
    """모든 blue-green alias의 현재 상태와 마지막 실행 기록을 반환."""
    from .qdrant_store import _aliases_list

    last_run = _load_bluegreen_status()
    last_run_at = last_run.get("started_at")
    next_run_at: str | None = None
    if last_run_at:
        try:
            from datetime import datetime, timedelta
            next_dt = datetime.fromisoformat(last_run_at) + timedelta(hours=1)
            next_run_at = next_dt.isoformat(timespec="seconds")
        except Exception:
            pass

    # 등록된 모든 alias → _green/_blue 슬롯 상태 조회
    aliases_raw = _aliases_list()
    collections: dict[str, Any] = {}
    for item in aliases_raw:
        alias_name = str(item.get("alias_name") or "")
        target = str(item.get("collection_name") or "")
        # _green/_blue 슬롯은 제외 (alias만 표시)
        if alias_name.endswith(("_green", "_blue")):
            continue
        green = f"{alias_name}_green"
        blue = f"{alias_name}_blue"
        collections[alias_name] = bluegreen_collection_status(alias_name, green, blue)

    return {
        "strategy": "blue_green_alias_split",
        "patent_schedule": "on_api_call",
        "wiki_schedule": "every_1_hour",
        "last_run_at": last_run_at,
        "next_wiki_run_at": next_run_at,
        "patent_refreshed_at": last_run.get("patent_refreshed_at"),
        "wiki_refreshed_at": last_run.get("wiki_refreshed_at"),
        "last_run_status": last_run.get("status"),
        "managed_collections": len(collections),
        "collections": collections,
    }
