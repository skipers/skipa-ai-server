"""Access to the shared chatbot/eval data folder."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from fastapi import HTTPException

from .config import BUSINESS_ROOT, DATA_ROOT, PATENTS_ROOT, PROJECT_ROOT, WIKI_AUDITOR_ROOT
from .qdrant_store import collection_info, patent_collection, qdrant_status
from .rag.quality import is_usable_evidence
from .rag.source_card_utils import enrich_source_card
from .vectorstore import CORE_SEARCH_SOURCE_TYPES, WIKI_SEARCH_SOURCE_TYPES, search_vectorstore, vectorstore_status


CHUNK_FILES = {
    "all": "all_chunks.jsonl",
    "original": "original_pdf_chunks.jsonl",
    "report": "report_pdf_chunks.jsonl",
    "original_visual": "original_visual_chunks.jsonl",
    "report_visual": "report_visual_chunks.jsonl",
}


def _safe_relative(path: Path, base: Path = PROJECT_ROOT) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except Exception:
        return str(path)


def _iso_mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    except OSError:
        return None


def _file_summary(path: Path) -> dict[str, Any]:
    exists = path.exists()
    return {
        "path": str(path),
        "relative_path": _safe_relative(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists and path.is_file() else None,
        "modified_at": _iso_mtime(path) if exists else None,
    }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"JSON 파일을 읽을 수 없습니다: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail=f"JSON root가 object가 아닙니다: {path}")
    return data


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(encoding="utf-8") as file:
        return sum(1 for _ in file)


def _count_files(path: Path, pattern: str = "*") -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob(pattern) if item.is_file())


def _guard_child(base: Path, child: Path) -> Path:
    base_resolved = base.resolve()
    child_resolved = child.resolve()
    try:
        child_resolved.relative_to(base_resolved)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="허용되지 않은 경로입니다.") from exc
    return child_resolved


def resolve_patent_dir(patent_id: str) -> Path:
    if not patent_id or "/" in patent_id or "\\" in patent_id:
        raise HTTPException(status_code=400, detail="잘못된 patent_id입니다.")
    patent_dir = _guard_child(PATENTS_ROOT, PATENTS_ROOT / patent_id)
    if not patent_dir.exists() or not patent_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"특허 폴더를 찾을 수 없습니다: {patent_id}")
    return patent_dir


def _is_shared_patent(patent_id: str | None) -> bool:
    if not patent_id:
        return False
    try:
        from .shared_data import is_shared_patent_id

        return is_shared_patent_id(patent_id)
    except Exception:
        return False


def data_overview() -> dict[str, Any]:
    from .shared_data import list_shared_patent_ids, shared_vectorstore_status
    from .config import SHARED_DATA_ROOT, SHARED_PATENT_ROOT
    from .visual_data import patent_visual_index_status

    return {
        "data_root": _file_summary(DATA_ROOT),
        "patents_root": _file_summary(PATENTS_ROOT),
        "business_root": _file_summary(BUSINESS_ROOT),
        "shared_data_root": _file_summary(SHARED_DATA_ROOT),
        "shared_patent_root": _file_summary(SHARED_PATENT_ROOT),
        "patent_count": len(list_patents()),
        "shared_patent_count": len(list_shared_patent_ids()),
        "business_index": {
            "chunks": _file_summary(BUSINESS_ROOT / "index" / "all_chunks.jsonl"),
            "qdrant": collection_info(patent_collection("_business")),
        },
        "shared_vectorstore": shared_vectorstore_status(),
        "shared_visual_vectorstore": patent_visual_index_status(),
        "vectorstore": vectorstore_status(),
        "qdrant": qdrant_status(),
    }


def link_status() -> dict[str, Any]:
    chatbot_data = PROJECT_ROOT / "chatbot" / "data"
    links = {}
    for name in ("mapped_patent_reports", "business"):
        path = chatbot_data / name
        links[name] = {
            **_file_summary(path),
            "is_symlink": path.is_symlink(),
            "target": str(path.readlink()) if path.is_symlink() else None,
        }
    return links


def patent_summary(patent_dir: Path) -> dict[str, Any]:
    manifest = _read_json(patent_dir / "manifest.json")
    patent_id = manifest.get("patent_id") or patent_dir.name
    title = manifest.get("title")
    all_chunks = patent_dir / "extracted" / "all_chunks.jsonl"
    latest_input = patent_dir / "original" / "input" / "latest.json"
    latest_pdf = patent_dir / "original" / "pdf" / "latest.pdf"
    latest_report = patent_dir / "reports" / "json" / "latest.json"
    qdrant = collection_info(patent_collection(str(patent_id)))
    return {
        "patent_id": patent_id,
        "title": title,
        "patent_dir": str(patent_dir),
        "relative_path": _safe_relative(patent_dir),
        "updated_at": manifest.get("updated_at"),
        "has_manifest": (patent_dir / "manifest.json").exists(),
        "has_latest_input": latest_input.exists(),
        "has_latest_pdf": latest_pdf.exists(),
        "has_latest_report": latest_report.exists(),
        "has_patent_index": bool(qdrant.get("exists")),
        "has_local_vectorstore": bool(qdrant.get("exists")),
        "has_qdrant_vectorstore": bool(qdrant.get("exists")),
        "qdrant_collection": patent_collection(str(patent_id)),
        "chunk_count": _count_lines(all_chunks),
        "report_json_count": _count_files(patent_dir / "reports" / "json", "*.json"),
        "asset_count": _count_files(patent_dir / "extracted" / "assets"),
        "manifest_path": str(patent_dir / "manifest.json"),
    }


def list_patents() -> list[dict[str, Any]]:
    patents: list[dict[str, Any]] = []
    seen: set[str] = set()
    if PATENTS_ROOT.exists():
        for patent_dir in sorted(PATENTS_ROOT.iterdir(), key=lambda item: item.name):
            if patent_dir.name.startswith(".") or patent_dir.name == "_global" or not patent_dir.is_dir():
                continue
            item = patent_summary(patent_dir)
            patents.append(item)
            seen.add(str(item.get("patent_id") or patent_dir.name))
    try:
        from .shared_data import list_shared_patent_ids, shared_patent_summary

        for patent_id in list_shared_patent_ids():
            if patent_id in seen:
                continue
            patents.append(shared_patent_summary(patent_id))
            seen.add(patent_id)
    except Exception:
        pass
    return patents


def patent_detail(patent_id: str, include_files: bool = True) -> dict[str, Any]:
    if _is_shared_patent(patent_id):
        try:
            from .shared_data import shared_patent_detail

            return shared_patent_detail(patent_id, include_files=include_files)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"공유 특허 상세 조회 실패: {patent_id} ({exc})") from exc
    patent_dir = resolve_patent_dir(patent_id)
    detail = patent_summary(patent_dir)
    detail["manifest"] = _read_json(patent_dir / "manifest.json")
    detail["paths"] = {
        "latest_input": _file_summary(patent_dir / "original" / "input" / "latest.json"),
        "latest_pdf": _file_summary(patent_dir / "original" / "pdf" / "latest.pdf"),
        "latest_report": _file_summary(patent_dir / "reports" / "json" / "latest.json"),
        "all_chunks": _file_summary(patent_dir / "extracted" / "all_chunks.jsonl"),
        "patent_index": collection_info(patent_collection(patent_id)),
        "local_vectorstore": collection_info(patent_collection(patent_id)),
        "qdrant_vectorstore": collection_info(patent_collection(patent_id)),
    }
    if include_files:
        detail["files"] = list_files(patent_id, limit=300)
    return detail


def list_files(patent_id: str, limit: int = 300) -> list[dict[str, Any]]:
    if _is_shared_patent(patent_id):
        try:
            from .shared_data import shared_list_files

            return shared_list_files(patent_id, limit=limit)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"공유 특허 파일 조회 실패: {patent_id} ({exc})") from exc
    patent_dir = resolve_patent_dir(patent_id)
    files = []
    for path in sorted(patent_dir.rglob("*")):
        if path.is_file():
            files.append(_file_summary(path))
        if len(files) >= limit:
            break
    return files


def latest_json(patent_id: str, kind: str) -> dict[str, Any]:
    if _is_shared_patent(patent_id):
        try:
            from .shared_data import shared_latest_json

            return shared_latest_json(patent_id, kind)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=f"latest {kind} JSON이 없습니다: {patent_id}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 kind입니다: {kind}") from exc
    patent_dir = resolve_patent_dir(patent_id)
    if kind == "input":
        path = patent_dir / "original" / "input" / "latest.json"
    elif kind == "report":
        path = patent_dir / "reports" / "json" / "latest.json"
    else:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 kind입니다: {kind}")
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"latest {kind} JSON이 없습니다: {patent_id}")
    return {"path": _file_summary(path), "data": _read_json(path)}


def read_jsonl(path: Path, *, offset: int = 0, limit: int = 20, source_types: set[str] | None = None) -> dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"chunk 파일을 찾을 수 없습니다: {path}")
    items: list[dict[str, Any]] = []
    matched = 0
    with path.open(encoding="utf-8") as file:
        for line_no, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            source_type = str(metadata.get("source_type", ""))
            if source_types and source_type not in source_types:
                continue
            if matched >= offset and len(items) < limit:
                item["_line_no"] = line_no
                items.append(item)
            matched += 1
    return {"path": _file_summary(path), "offset": offset, "limit": limit, "matched_count": matched, "items": items}


def patent_chunks(
    patent_id: str,
    *,
    chunk_file: str = "all",
    offset: int = 0,
    limit: int = 20,
    source_types: set[str] | None = None,
) -> dict[str, Any]:
    if _is_shared_patent(patent_id):
        try:
            from .shared_data import shared_patent_chunks

            return shared_patent_chunks(
                patent_id,
                offset=offset,
                limit=limit,
                source_types=source_types,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"공유 특허 chunk 조회 실패: {patent_id} ({exc})") from exc
    patent_dir = resolve_patent_dir(patent_id)
    file_name = CHUNK_FILES.get(chunk_file, chunk_file)
    if "/" in file_name or "\\" in file_name:
        raise HTTPException(status_code=400, detail="잘못된 chunk_file입니다.")
    result = read_jsonl(patent_dir / "extracted" / file_name, offset=offset, limit=limit, source_types=source_types)
    result["patent_id"] = patent_id
    result["chunk_file"] = file_name
    return result


def business_chunks(*, offset: int = 0, limit: int = 20) -> dict[str, Any]:
    return read_jsonl(BUSINESS_ROOT / "index" / "all_chunks.jsonl", offset=offset, limit=limit)


def _iter_chunk_items(patent_id: str | None, source_types: set[str] | None) -> Iterable[dict[str, Any]]:
    if patent_id and _is_shared_patent(patent_id):
        return
    patent_dirs = [resolve_patent_dir(patent_id)] if patent_id else [
        PATENTS_ROOT / summary["patent_id"] for summary in list_patents()
        if (PATENTS_ROOT / str(summary["patent_id"])).exists()
    ]
    for patent_dir in patent_dirs:
        path = patent_dir / "extracted" / "all_chunks.jsonl"
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as file:
            for line_no, line in enumerate(file, 1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
                source_type = str(metadata.get("source_type", ""))
                if source_types and source_type not in source_types:
                    continue
                item["_line_no"] = line_no
                item["_chunk_file"] = str(path)
                yield item


def _terms(query: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[\w가-힣]+", query) if len(term.strip()) >= 2]


def _score(query: str, item: dict[str, Any]) -> float:
    text = str(item.get("page_content") or "")
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    haystack = " ".join(
        [
            text,
            str(metadata.get("title") or ""),
            str(metadata.get("section_title") or ""),
            str(metadata.get("section_key") or ""),
        ]
    ).lower()
    query_lower = query.lower().strip()
    score = 0.0
    if query_lower and query_lower in haystack:
        score += 10.0
    for term in _terms(query):
        score += haystack.count(term) * max(1.0, min(len(term), 8) / 2)
    return score


def _excerpt(text: str, query: str, size: int = 360) -> str:
    if len(text) <= size:
        return text
    lower = text.lower()
    positions = [lower.find(term) for term in _terms(query) if lower.find(term) >= 0]
    center = min(positions) if positions else 0
    start = max(0, center - size // 3)
    end = min(len(text), start + size)
    prefix = "..." if start else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def search_chunks(query: str, *, patent_id: str | None, source_types: set[str] | None, top_k: int, rerank: bool = False) -> dict[str, Any]:
    effective_source_types = set(source_types) if source_types is not None else set(CORE_SEARCH_SOURCE_TYPES)
    vector_result = search_vectorstore(query, patent_id=patent_id, source_types=effective_source_types, top_k=top_k, rerank=rerank)
    if vector_result["hit_count"] > 0 or effective_source_types <= WIKI_SEARCH_SOURCE_TYPES:
        return vector_result

    scored: list[tuple[float, dict[str, Any]]] = []
    for item in _iter_chunk_items(patent_id, effective_source_types):
        if not is_usable_evidence(item.get("page_content")):
            continue
        score = _score(query, item)
        if score <= 0:
            continue
        scored.append((score, item))

    # Also search shared patent data (PROJECT_ROOT/data/patent/{id}/), including
    # patent-scoped queries where the current repository has no legacy chunks.
    if not scored:
        try:
            from .shared_data import search_shared_vectorstore, SHARED_PATENT_SOURCE_TYPE, SHARED_REPORT_SOURCE_TYPE

            if patent_id:
                # source_types에 SHARED_PATENT·SHARED_REPORT 중 어느 쪽만 요청됐는지 확인
                from .shared_data import _normalize_shared_source_types
                resolved_st = _normalize_shared_source_types(effective_source_types)
                wants_patent = SHARED_PATENT_SOURCE_TYPE in resolved_st
                wants_report = SHARED_REPORT_SOURCE_TYPE in resolved_st

                if wants_patent and wants_report:
                    # 두 타입 모두 필요 → dual search
                    # 의미 유사도 기준으로는 SHARED_REPORT가 항상 상위를 차지하므로
                    # SHARED_PATENT 내용을 강제로 포함시킨다.
                    n_report = max(top_k - 2, top_k // 2)
                    n_patent = max(2, top_k - n_report)

                    report_result = search_shared_vectorstore(
                        query, top_k=n_report, patent_id=patent_id,
                        source_types={SHARED_REPORT_SOURCE_TYPE},
                    )
                    patent_query = f"청구항 발명 기술 특징 {query}"
                    patent_result = search_shared_vectorstore(
                        patent_query, top_k=n_patent, patent_id=patent_id,
                        source_types={SHARED_PATENT_SOURCE_TYPE},
                    )
                    combined_hits: list[dict[str, Any]] = []
                    seen_ids: set[str] = set()
                    for hit in (patent_result.get("hits") or []) + (report_result.get("hits") or []):
                        doc_id = str(hit.get("metadata", {}).get("patent_id", "")) + str(hit.get("page_content", ""))[:60]
                        if doc_id not in seen_ids:
                            seen_ids.add(doc_id)
                            combined_hits.append(hit)
                    if combined_hits:
                        return {
                            **report_result,
                            "hits": combined_hits[:top_k],
                            "hit_count": min(len(combined_hits), top_k),
                            "mode": "shared_qdrant_dual_search",
                        }
                else:
                    # 단일 타입 요청 (patent_report → REPORT만, patent_original → PATENT만)
                    single_result = search_shared_vectorstore(
                        query, top_k=top_k, patent_id=patent_id, source_types=resolved_st,
                    )
                    if single_result.get("hits"):
                        return {**single_result, "mode": "shared_qdrant_search"}
            else:
                shared_result = search_shared_vectorstore(
                    query,
                    top_k=top_k,
                    patent_id=None,
                    source_types=effective_source_types,
                )
                shared_hits = shared_result.get("hits") or []
                if shared_hits:
                    return {**shared_result, "mode": "shared_qdrant_search"}
        except Exception:
            pass

    scored.sort(key=lambda pair: pair[0], reverse=True)
    hits = []
    for score, item in scored[:top_k]:
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        text = str(item.get("page_content") or "")
        hits.append(
            {
                "patent_id": str(metadata.get("patent_id") or patent_id or ""),
                "score": round(score, 3),
                "excerpt": _excerpt(text, query),
                "page_content": text,
                "metadata": metadata,
            }
        )
    return {
        "query": query,
        "mode": "keyword_chunk_search",
        "patent_id": patent_id,
        "top_k": top_k,
        "source_types": sorted(effective_source_types),
        "hit_count": len(hits),
        "hits": hits,
    }


def _source_url(metadata: dict[str, Any]) -> str | None:
    source_path = metadata.get("source_path")
    if not source_path:
        return None
    path = Path(str(source_path))
    try:
        from .config import SHARED_DATA_ROOT
    except Exception:
        SHARED_DATA_ROOT = PROJECT_ROOT / "data"
    for base, prefix in (
        (DATA_ROOT, "/files/data/"),
        (SHARED_DATA_ROOT, "/files/shared/"),
    ):
        try:
            rel = path.resolve().relative_to(base.resolve())
        except Exception:
            continue
        return prefix + quote(str(rel).replace("\\", "/"))
    return None


def _clean_sentence(text: str, limit: int = 220) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _answer_line(hit: dict[str, Any], index: int) -> str:
    metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    source_type = str(metadata.get("source_type") or "unknown")
    section = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title") or "근거"
    excerpt = _clean_sentence(str(hit.get("excerpt") or hit.get("page_content") or ""))
    return f"{index}. {source_type} / {section}: {excerpt}"


def answer_query(query: str, *, patent_id: str | None, source_types: set[str] | None, top_k: int) -> dict[str, Any]:
    search = search_chunks(query, patent_id=patent_id, source_types=source_types, top_k=top_k)
    hits = search.get("hits") or []
    if not hits:
        answer = (
            "관련 근거를 찾지 못했습니다.\n\n"
            "- 다른 특허를 선택하거나 전체 특허 범위로 다시 질문해 주세요.\n"
            "- 감사 적용 후 vectorstore가 비어 있으면 먼저 Audit Apply 또는 vectorstore refresh를 실행해 주세요."
        )
    else:
        scoped = f"`{patent_id}` 특허" if patent_id else "전체 특허"
        lines = [
            f"{scoped}에서 질문과 관련된 근거 {len(hits)}개를 찾았습니다.",
            "",
            "## 답변 요약",
            "검색된 근거 기준으로 보면 다음 항목들이 질문에 직접 연결됩니다.",
            "",
        ]
        lines.extend(_answer_line(hit, index) for index, hit in enumerate(hits[:4], 1))
        lines.extend(
            [
                "",
                "## 확인 방법",
                "아래 근거 카드를 클릭하면 원문 excerpt, source_type, source_path metadata를 확인할 수 있습니다.",
            ]
        )
        answer = "\n".join(lines)

    source_cards = []
    for index, hit in enumerate(hits, 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        source_type = str(metadata.get("source_type") or "unknown")
        title = metadata.get("section_title") or metadata.get("file_name") or metadata.get("title")
        page_no = metadata.get("page_no") or metadata.get("page")
        try:
            page_no = int(page_no) if page_no is not None else None
        except (TypeError, ValueError):
            page_no = None
        source_cards.append(
            enrich_source_card(
                {
                    "label": f"근거 {index}",
                    "title": str(title) if title else None,
                    "source_type": source_type,
                    "page_no": page_no,
                    "url": _source_url(metadata),
                    "snippet": str(hit.get("excerpt") or hit.get("page_content") or ""),
                    "metadata": metadata,
                },
                query=query,
                index=index,
            )
        )

    return {
        "query": query,
        "patent_id": patent_id,
        "answer": answer,
        "source_cards": source_cards,
        "metrics": {
            "mode": search.get("mode"),
            "hit_count": search.get("hit_count", 0),
            "top_k": top_k,
            "source_types": sorted(source_types) if source_types else None,
        },
    }


def wiki_audit_report() -> dict[str, Any]:
    candidates = [
        WIKI_AUDITOR_ROOT / "audit_report.md",
        PROJECT_ROOT / "chatbot" / "audit_report.md",
    ]
    for path in candidates:
        if path.exists():
            return {"path": _file_summary(path), "markdown": path.read_text(encoding="utf-8")}
    raise HTTPException(status_code=404, detail="wiki audit report를 찾을 수 없습니다.")
