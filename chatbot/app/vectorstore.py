"""Audit, human review, and local vectorstore refresh for chatbot data.

The production chatbot can replace the local hashed vectors with an embedding
and FAISS backend. The important contract is the workflow:

1. Audit scans raw shared data and flags suspicious documents.
2. A human reviews the findings in Swagger or the generated Markdown.
3. Only human-approved content is saved as Markdown/JSONL.
4. Vectorstores are rebuilt from the approved content.
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
from .index_rotation import active_documents_path, active_manifest_path, rotation_status, write_rotating_index
from .rag.quality import is_usable_evidence, preprocess_evidence_text


VECTOR_DIMENSIONS = 256
MAX_TEXT_CHARS = 20000
CORE_SEARCH_SOURCE_TYPES = frozenset(
    {"ORIGINAL_PDF", "REPORT_PDF", "PATENT_INPUT_JSON", "REPORT_JSON", "APPLICATION_FEEDBACK_REPORT"}
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


def _application_feedback_documents(patent_id: str, patent_dir: Path) -> Iterable[dict[str, Any]]:
    feedback_root = patent_dir / "reports" / "application_feedback"
    latest_md = feedback_root / "latest.md"
    if not latest_md.exists():
        return
    doc = _document(
        patent_id=patent_id,
        text=latest_md.read_text(encoding="utf-8", errors="ignore"),
        source_path=latest_md,
        source_type="APPLICATION_FEEDBACK_REPORT",
        metadata={"file_name": latest_md.name, "section_title": "출원/실패 피드백 리포트"},
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
    from .wiki.topics import get_patent_topic, topic_approved_md, topic_vectorstore_root

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

    docs.extend(_application_feedback_documents(patent_id, patent_dir) or [])
    return docs


def _write_vectorstore(output_dir: Path, docs: list[dict[str, Any]], *, scope: str, source: str = "unknown") -> dict[str, Any]:
    source_paths: set[Path] = set()
    for doc in docs:
        if doc.get("page_content") and not doc.get("vector"):
            doc["vector"] = _vectorize(str(doc.get("page_content") or ""))
        source_path = Path(str(doc.get("metadata", {}).get("source_path", "")))
        if source_path.exists():
            source_paths.add(source_path)
    source_fingerprints = [
        {
            "path": str(source_path),
            "size_bytes": source_path.stat().st_size,
            "sha1": _hash_file(source_path),
        }
        for source_path in sorted(source_paths)
    ]
    manifest = {
        "scope": scope,
        "refreshed_at": _now(),
        "vector_dimensions": VECTOR_DIMENSIONS,
        "backend": "local_hashed_bow",
        "source": source,
        "document_count": len(docs),
        "source_fingerprints": source_fingerprints,
    }
    rotation = write_rotating_index(output_dir, docs, manifest)
    return {
        "scope": scope,
        "document_count": len(docs),
        "manifest_path": rotation["manifest_path"],
        "documents_path": rotation["documents_path"],
        "active_slot": rotation["active_slot"],
        "previous_active_slot": rotation["previous_active_slot"],
        "legacy_manifest_path": rotation["legacy_manifest_path"],
        "legacy_documents_path": rotation["legacy_documents_path"],
    }


def refresh_vectorstores(*, use_reviewed: bool = True) -> dict[str, Any]:
    from .wiki.topics import all_active_topic_slugs, topic_vectorstore_root

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
            _write_vectorstore(patent_dir / "index" / "vectorstore", core_docs, scope=f"patent:{patent_id}", source=source)
        )

    business_docs = _business_documents()
    for doc in business_docs:
        excluded_by_policy[_source_type(doc) or "BUSINESS"] += 1
    _write_vectorstore(
        BUSINESS_ROOT / "index" / "vectorstore",
        [],
        scope="business-disabled",
        source="disabled_non_core_web_routing",
    )
    global_result = _write_vectorstore(PATENTS_ROOT / "_global" / "index" / "vectorstore", global_docs, scope="global", source=source)

    # Build per-topic wiki vectorstores (blue/green)
    topic_wiki_results = []
    all_wiki_docs: list[dict[str, Any]] = []
    for topic_slug in all_active_topic_slugs():
        topic_docs = list(_topic_wiki_documents(topic_slug))
        all_wiki_docs.extend(topic_docs)
        topic_wiki_results.append(
            _write_vectorstore(topic_vectorstore_root(topic_slug), topic_docs, scope=f"wiki:{topic_slug}", source=source)
        )

    # Global wiki = merge of all topic wikis
    global_wiki_result = _write_vectorstore(
        WIKI_ROOT / "_global" / "vectorstore",
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
        "wiki_policy": "wiki is topic-based: WIKI_ROOT/{topic_slug}/vectorstore with blue/green rotation",
        "web_policy": "non-core data is excluded from core vectorstores; questions without original/report/wiki evidence route to web search",
    }


def vectorstore_status() -> dict[str, Any]:
    from .wiki.topics import all_active_topic_slugs, topic_vectorstore_root, topic_approved_md

    patent_status = []
    for patent_id in _patent_ids():
        patent_dir = PATENTS_ROOT / patent_id
        core_root = patent_dir / "index" / "vectorstore"
        manifest_path = active_manifest_path(core_root)
        manifest = _read_json(manifest_path)
        reviewed_path = _reviewed_docs_path(patent_id)
        patent_status.append(
            {
                "patent_id": patent_id,
                "exists": manifest_path.exists(),
                "document_count": manifest.get("document_count", 0),
                "refreshed_at": manifest.get("refreshed_at"),
                "manifest_path": str(manifest_path),
                "rotation": rotation_status(core_root),
                "has_human_reviewed_source": reviewed_path.exists(),
                "approved_markdown_path": str(_reviewed_md_path(patent_id)) if _reviewed_md_path(patent_id).exists() else None,
            }
        )

    topic_status = []
    for topic_slug in all_active_topic_slugs():
        vs_root = topic_vectorstore_root(topic_slug)
        vs_manifest = _read_json(active_manifest_path(vs_root))
        approved = topic_approved_md(topic_slug)
        topic_status.append(
            {
                "topic": topic_slug,
                "vectorstore_exists": active_manifest_path(vs_root).exists(),
                "document_count": vs_manifest.get("document_count", 0),
                "refreshed_at": vs_manifest.get("refreshed_at"),
                "approved_md_exists": approved.exists(),
                "approved_md_path": str(approved),
                "rotation": rotation_status(vs_root),
            }
        )

    global_root = PATENTS_ROOT / "_global" / "index" / "vectorstore"
    global_wiki_root = WIKI_ROOT / "_global" / "vectorstore"
    global_manifest = _read_json(active_manifest_path(global_root))
    global_wiki_manifest = _read_json(active_manifest_path(global_wiki_root))
    return {
        "backend": "local_hashed_bow",
        "rotation_policy": "blue_green; readers use active_slot.json and writers build the standby slot before switching",
        "core_source_types": sorted(CORE_SEARCH_SOURCE_TYPES),
        "core_policy": "patent/report only; wiki is topic-based in WIKI_ROOT/{topic}/vectorstore",
        "global": {
            "exists": bool(global_manifest),
            "document_count": global_manifest.get("document_count", 0),
            "refreshed_at": global_manifest.get("refreshed_at"),
            "source": global_manifest.get("source"),
            "manifest_path": str(active_manifest_path(global_root)),
            "rotation": rotation_status(global_root),
        },
        "global_wiki": {
            "exists": bool(global_wiki_manifest),
            "document_count": global_wiki_manifest.get("document_count", 0),
            "source": global_wiki_manifest.get("source"),
            "policy": "merged wiki from all topic vectorstores",
            "manifest_path": str(active_manifest_path(global_wiki_root)),
            "rotation": rotation_status(global_wiki_root),
        },
        "topic_wiki": topic_status,
        "patents": patent_status,
    }


def _vector_documents_path(*, patent_id: str | None, source_types: set[str] | None) -> Path:
    requested = set(source_types or [])
    if requested and requested <= WIKI_SEARCH_SOURCE_TYPES:
        if patent_id:
            from .wiki.topics import get_patent_topic, topic_vectorstore_root
            topic = get_patent_topic(patent_id)
            return active_documents_path(topic_vectorstore_root(topic))
        return active_documents_path(WIKI_ROOT / "_global" / "vectorstore")
    root = PATENTS_ROOT / patent_id / "index" / "vectorstore" if patent_id else PATENTS_ROOT / "_global" / "index" / "vectorstore"
    return active_documents_path(root)


def _iter_vector_documents(patent_id: str | None, source_types: set[str] | None = None) -> Iterable[dict[str, Any]]:
    docs_path = _vector_documents_path(patent_id=patent_id, source_types=source_types)
    if not docs_path.exists():
        return
    for _, item in _read_jsonl(docs_path) or []:
        yield item


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
    query_vector = _vectorize(query)
    effective_source_types = set(source_types) if source_types is not None else set(CORE_SEARCH_SOURCE_TYPES)
    docs_path = _vector_documents_path(patent_id=patent_id, source_types=effective_source_types)
    if not query_vector:
        return {
            "query": query,
            "mode": "local_vectorstore_search",
            "patent_id": patent_id,
            "top_k": top_k,
            "source_types": sorted(effective_source_types),
            "documents_path": str(docs_path),
            "hit_count": 0,
            "hits": [],
        }
    if not docs_path.exists():
        return {
            "query": query,
            "mode": "local_vectorstore_search",
            "patent_id": patent_id,
            "top_k": top_k,
            "source_types": sorted(effective_source_types),
            "documents_path": str(docs_path),
            "hit_count": 0,
            "hits": [],
        }
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in _iter_vector_documents(patent_id, effective_source_types) or []:
        text = str(doc.get("page_content") or "")
        if not is_usable_evidence(text):
            continue
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        source_type = str(metadata.get("source_type", ""))
        if effective_source_types and source_type not in effective_source_types:
            continue
        vector = doc.get("vector") if isinstance(doc.get("vector"), dict) else {}
        score = _dot(query_vector, {str(key): float(value) for key, value in vector.items()})
        if score <= 0:
            continue
        scored.append((score, doc))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    hits = []
    for score, doc in scored[:top_k]:
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        text = str(doc.get("page_content") or "")
        hits.append(
            {
                "patent_id": str(metadata.get("patent_id") or patent_id or ""),
                "score": round(score, 6),
                "excerpt": _excerpt(text, query),
                "page_content": text,
                "metadata": metadata,
            }
        )
    return {
        "query": query,
        "mode": "local_vectorstore_search",
        "patent_id": patent_id,
        "top_k": top_k,
        "source_types": sorted(effective_source_types),
        "documents_path": str(docs_path),
        "hit_count": len(hits),
        "hits": hits,
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

        from .wiki.topics import get_patent_topic, topic_approved_md, topic_vectorstore_root

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
    with a CronJob, while the chatbot/eval pods keep serving from the current
    active blue/green slot until this job finishes and switches the pointer.
    """

    started_at = _now()
    wiki_result = auto_audit_apply_and_refresh(refresh_vectorstore=True)

    application_result: dict[str, Any] | None = None
    failed_case_results: list[dict[str, Any]] = []
    try:
        from .application_data import (
            list_failed_patent_cases,
            preprocess_application_pack,
            refresh_failed_patent_case_index,
        )

        application_result = preprocess_application_pack(refresh_index=True)
        cases = list_failed_patent_cases()
        for item in cases.get("items") or []:
            case_id = item.get("case_id") if isinstance(item, dict) else None
            if not case_id:
                continue
            if item.get("has_original_pdf") is False:
                failed_case_results.append(
                    {"case_id": case_id, "status": "skipped", "reason": "missing_original_pdf"}
                )
                continue
            try:
                failed_case_results.append(refresh_failed_patent_case_index(str(case_id)))
            except Exception as exc:
                failed_case_results.append(
                    {"case_id": case_id, "status": "error", "error": f"{type(exc).__name__}: {exc}"}
                )
    except Exception as exc:
        application_result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    result = {
        "status": "completed",
        "workflow": "nightly_blue_green_reindex",
        "started_at": started_at,
        "finished_at": _now(),
        "schedule_hint": "Kubernetes CronJob: 0 0 * * *",
        "wiki_auto_audit": wiki_result,
        "application_pack": application_result,
        "failed_patent_cases": failed_case_results,
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
) -> dict[str, Any]:
    """Promote high-quality web results to the topic wiki vectorstore without human review.

    If avg relevance >= WIKI_AUTO_APPROVE_MIN_RELEVANCE, content is appended to
    WIKI_ROOT/{topic}/approved_context.md and the topic vectorstore is refreshed.
    Low-quality drafts are recorded as pending for the normal audit cycle.
    _global patent and empty result lists are always skipped.
    """
    from .wiki.topics import (
        get_patent_topic,
        topic_approved_md,
        topic_vectorstore_root,
        topic_wiki_root,
    )

    if patent_id in {"_global", ""} or not results:
        return {"auto_approved": False, "reason": "skipped_global_or_empty"}

    topic = get_patent_topic(patent_id)
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
            topic_vectorstore_root(topic),
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
