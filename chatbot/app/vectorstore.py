"""Local vectorstore refresh used by chatbot audit APIs.

The production chatbot can replace this with an embedding/FAISS backend. This
module keeps the same data contract in a dependency-light way: every audit run
rescans the shared data folder, writes vectorized document JSONL files, and lets
Swagger query APIs search the refreshed store immediately.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

from .config import BUSINESS_ROOT, PATENTS_ROOT, PROJECT_ROOT, WIKI_AUDITOR_ROOT


VECTOR_DIMENSIONS = 256
MAX_TEXT_CHARS = 20000
TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path)


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


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
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


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
    text = " ".join(str(text or "").split())
    return text[:MAX_TEXT_CHARS]


def _document(
    *,
    patent_id: str,
    text: str,
    source_path: Path,
    source_type: str,
    metadata: dict[str, Any] | None = None,
    line_no: int | None = None,
) -> dict[str, Any] | None:
    content = _truncate(text)
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


def collect_patent_documents(patent_id: str) -> list[dict[str, Any]]:
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

    docs.extend(_wiki_documents(patent_id, patent_dir / "wiki") or [])
    return docs


def _write_vectorstore(output_dir: Path, docs: list[dict[str, Any]], *, scope: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    docs_path = output_dir / "documents.jsonl"
    manifest_path = output_dir / "manifest.json"
    source_paths: set[Path] = set()
    with docs_path.open("w", encoding="utf-8") as file:
        for doc in docs:
            file.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")
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
        "document_count": len(docs),
        "documents_path": str(docs_path),
        "source_fingerprints": source_fingerprints,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "scope": scope,
        "document_count": len(docs),
        "manifest_path": str(manifest_path),
        "documents_path": str(docs_path),
    }


def refresh_vectorstores() -> dict[str, Any]:
    patent_results = []
    global_docs: list[dict[str, Any]] = []
    wiki_docs: list[dict[str, Any]] = []

    for patent_id in _patent_ids():
        patent_dir = PATENTS_ROOT / patent_id
        docs = collect_patent_documents(patent_id)
        global_docs.extend(docs)
        patent_results.append(_write_vectorstore(patent_dir / "index" / "vectorstore", docs, scope=f"patent:{patent_id}"))
        patent_wiki_docs = [doc for doc in docs if doc.get("metadata", {}).get("source_type") == "WIKI"]
        wiki_docs.extend(patent_wiki_docs)
        _write_vectorstore(patent_dir / "wiki" / "vectorstore" / "local", patent_wiki_docs, scope=f"wiki:{patent_id}")

    business_docs = _business_documents()
    global_docs.extend(business_docs)
    business_result = _write_vectorstore(BUSINESS_ROOT / "index" / "vectorstore", business_docs, scope="business")
    global_result = _write_vectorstore(PATENTS_ROOT / "_global" / "index" / "vectorstore", global_docs, scope="global")
    wiki_result = _write_vectorstore(PATENTS_ROOT / "_global" / "wiki" / "vectorstore" / "local", wiki_docs, scope="wiki:global")

    return {
        "status": "refreshed",
        "refreshed_at": _now(),
        "patent_count": len(patent_results),
        "patent_vectorstores": patent_results,
        "business_vectorstore": business_result,
        "global_vectorstore": global_result,
        "wiki_vectorstore": wiki_result,
    }


def vectorstore_status() -> dict[str, Any]:
    patent_status = []
    for patent_id in _patent_ids():
        patent_dir = PATENTS_ROOT / patent_id
        manifest_path = patent_dir / "index" / "vectorstore" / "manifest.json"
        manifest = _read_json(manifest_path)
        patent_status.append(
            {
                "patent_id": patent_id,
                "exists": manifest_path.exists(),
                "document_count": manifest.get("document_count", 0),
                "refreshed_at": manifest.get("refreshed_at"),
                "manifest_path": str(manifest_path),
            }
        )
    global_manifest = _read_json(PATENTS_ROOT / "_global" / "index" / "vectorstore" / "manifest.json")
    return {
        "backend": "local_hashed_bow",
        "global": {
            "exists": bool(global_manifest),
            "document_count": global_manifest.get("document_count", 0),
            "refreshed_at": global_manifest.get("refreshed_at"),
            "manifest_path": str(PATENTS_ROOT / "_global" / "index" / "vectorstore" / "manifest.json"),
        },
        "patents": patent_status,
    }


def _iter_vector_documents(patent_id: str | None) -> Iterable[dict[str, Any]]:
    docs_path = (
        PATENTS_ROOT / patent_id / "index" / "vectorstore" / "documents.jsonl"
        if patent_id
        else PATENTS_ROOT / "_global" / "index" / "vectorstore" / "documents.jsonl"
    )
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
    if not query_vector:
        return {
            "query": query,
            "mode": "local_vectorstore_search",
            "patent_id": patent_id,
            "top_k": top_k,
            "hit_count": 0,
            "hits": [],
        }
    scored: list[tuple[float, dict[str, Any]]] = []
    for doc in _iter_vector_documents(patent_id) or []:
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        source_type = str(metadata.get("source_type", ""))
        if source_types and source_type not in source_types:
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
        "hit_count": len(hits),
        "hits": hits,
    }


def audit_and_refresh_vectorstores(*, refresh_vectorstore: bool = True) -> dict[str, Any]:
    findings = []
    for patent_id in _patent_ids():
        patent_dir = PATENTS_ROOT / patent_id
        if not (patent_dir / "manifest.json").exists():
            findings.append({"severity": "medium", "patent_id": patent_id, "message": "manifest.json 없음"})
        if not (patent_dir / "extracted" / "all_chunks.jsonl").exists() and not (
            patent_dir / "original" / "input" / "latest.json"
        ).exists():
            findings.append({"severity": "high", "patent_id": patent_id, "message": "검색 가능한 원문/input 데이터 없음"})
        if not (patent_dir / "reports" / "json" / "latest.json").exists():
            findings.append({"severity": "low", "patent_id": patent_id, "message": "latest report JSON 없음"})

    refresh_result = refresh_vectorstores() if refresh_vectorstore else None
    status = "ok" if not findings else "needs_review"
    report = {
        "status": status,
        "audited_at": _now(),
        "patent_count": len(_patent_ids()),
        "finding_count": len(findings),
        "findings": findings,
        "vectorstore_refresh": refresh_result,
    }
    _write_audit_report(report)
    return report


def _write_audit_report(report: dict[str, Any]) -> None:
    WIKI_AUDITOR_ROOT.mkdir(parents=True, exist_ok=True)
    markdown_path = WIKI_AUDITOR_ROOT / "audit_report.md"
    lines = [
        "# 위키/챗봇 데이터 감사 리포트",
        "",
        f"**감사 일시**: {report['audited_at']}",
        f"**상태**: {report['status']}",
        f"**특허 수**: {report['patent_count']}",
        f"**발견 이슈**: {report['finding_count']}개",
        "",
        "## Vectorstore 갱신",
    ]
    refresh = report.get("vectorstore_refresh") or {}
    if refresh:
        lines.extend(
            [
                "",
                f"- 상태: {refresh.get('status')}",
                f"- 갱신 시각: {refresh.get('refreshed_at')}",
                f"- 특허별 vectorstore 수: {refresh.get('patent_count')}",
                f"- global 문서 수: {refresh.get('global_vectorstore', {}).get('document_count')}",
            ]
        )
    else:
        lines.append("")
        lines.append("- 이번 감사에서는 vectorstore 갱신을 수행하지 않았습니다.")
    lines.extend(["", "## 발견 이슈"])
    findings = report.get("findings") or []
    if findings:
        for finding in findings:
            lines.append(f"- [{finding['severity']}] {finding['patent_id']}: {finding['message']}")
    else:
        lines.append("- 발견된 이슈 없음")
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_path = WIKI_AUDITOR_ROOT / "audit.log"
    with log_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n")
