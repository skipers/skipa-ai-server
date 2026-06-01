"""Patent-application assistant data download, indexing, and retrieval."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from html import escape as html_escape, unescape
from html.parser import HTMLParser
import csv
import hashlib
import json
import math
import mimetypes
import re
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen
import zipfile
import xml.etree.ElementTree as ET

from fastapi import HTTPException

from .config import DATA_ROOT, PATENT_APPLICATION_ROOT


TOKEN_RE = re.compile(r"[A-Za-z0-9가-힣]{2,}")
URL_RE = re.compile(r"https?://[^\s\"'<>),]+")
VECTOR_DIMENSIONS = 256
MAX_DOWNLOADS_PER_RUN = 80
MAX_EMBEDDED_DOWNLOADS_PER_RUN = 120
USER_AGENT = "Mozilla/5.0 SKIPA-Patent-Application-Assistant/1.0"
DOCUMENT_EXTENSIONS = {".pdf", ".hwp", ".hwpx", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}
DOCUMENT_ENDPOINT_TERMS = (
    "filedown",
    "filedownload",
    "bultnfiledown",
    "contfiledown",
    "fldownload",
    "download",
    "filetoss",
    "atchfile",
)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _safe_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(DATA_ROOT.resolve()))
    except Exception:
        return str(path)


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text or "")]


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


def _hash_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _hash_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _index_dir() -> Path:
    return PATENT_APPLICATION_ROOT / "index" / "vectorstore"


def _documents_path() -> Path:
    return _index_dir() / "documents.jsonl"


def _manifest_path() -> Path:
    return _index_dir() / "manifest.json"


def _download_dir() -> Path:
    return PATENT_APPLICATION_ROOT / "downloads" / "raw"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = unescape(text)
    return _clean_boilerplate(text)


def _clean_boilerplate(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    cut_markers = [
        "현재 페이지의 구성과 내용에 만족하시나요?",
        "만족도 점수 선택",
        "만족도 조사 참여가 정상 처리되었습니다.",
        "소중한 의견 감사합니다.",
    ]
    for marker in cut_markers:
        index = text.find(marker)
        if index > 0:
            text = text[:index].strip()
    return text


def _extract_pdf_text(path: Path) -> tuple[str, str | None]:
    try:
        import fitz
    except Exception as exc:
        return "", f"PyMuPDF unavailable: {exc}"
    try:
        parts = []
        with fitz.open(str(path)) as pdf:
            for page_index, page in enumerate(pdf, 1):
                text = page.get_text("text").strip()
                if text:
                    parts.append(f"[page {page_index}]\n{text}")
        return "\n\n".join(parts), None
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        raw = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ET.fromstring(raw)
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = []
    for item in root.findall(".//a:si", ns):
        texts = [node.text or "" for node in item.findall(".//a:t", ns)]
        values.append("".join(texts))
    return values


def _extract_xlsx_text(path: Path) -> tuple[str, str | None]:
    try:
        with zipfile.ZipFile(path) as zf:
            shared = _xlsx_shared_strings(zf)
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            lines = []
            for name in sorted(item for item in zf.namelist() if item.startswith("xl/worksheets/sheet") and item.endswith(".xml")):
                root = ET.fromstring(zf.read(name))
                lines.append(f"# {name}")
                for row in root.findall(".//a:row", ns):
                    cells = []
                    for cell in row.findall("a:c", ns):
                        raw_value = cell.findtext("a:v", default="", namespaces=ns)
                        if cell.attrib.get("t") == "s" and raw_value.isdigit():
                            index = int(raw_value)
                            cells.append(shared[index] if index < len(shared) else raw_value)
                        else:
                            cells.append(raw_value)
                    if any(cells):
                        lines.append(" | ".join(cells))
            return "\n".join(lines), None
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"


def _read_source_text(path: Path) -> tuple[str, str | None]:
    suffix = path.suffix.lower()
    try:
        head = path.read_bytes()[:2048]
    except Exception:
        head = b""
    if suffix == ".pdf" or head.startswith(b"%PDF"):
        return _extract_pdf_text(path)
    if suffix == ".xlsx":
        return _extract_xlsx_text(path)
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"
    if suffix == ".json":
        parsed = _read_json(path)
        if parsed is not None:
            return _clean_boilerplate(json.dumps(parsed, ensure_ascii=False, indent=2)), None
    if suffix in {".html", ".htm"} or b"<html" in head.lower() or b"<!doctype html" in head.lower():
        return _strip_html(text), None
    return _clean_boilerplate(text), None


def _source_type(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".") or "text"
    if "downloads" in path.parts:
        return f"APPLICATION_DOWNLOADED_{suffix.upper()}"
    return f"APPLICATION_OFFICIAL_{suffix.upper()}"


def _iter_source_files() -> Iterable[Path]:
    if not PATENT_APPLICATION_ROOT.exists():
        return
    allowed = {".md", ".txt", ".csv", ".json", ".html", ".htm", ".pdf", ".xlsx", ".do", ".jsp", ".bin"}
    skip_parts = {"index", "__pycache__", "readable", "named"}
    generated_names = {
        "download_manifest.json",
        "download_report.md",
        "file_index.csv",
        "file_index.json",
        "file_names.md",
        "open_index.html",
        "README.md",
    }
    for path in sorted(PATENT_APPLICATION_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        if any(part in skip_parts for part in path.relative_to(PATENT_APPLICATION_ROOT).parts):
            continue
        if path.parent.name == "downloads" and path.name in generated_names:
            continue
        if path.parent == PATENT_APPLICATION_ROOT and path.name in {"download_manifest.json", "download_report.md"}:
            continue
        yield path


def _chunk_text(text: str, *, size: int = 1800, overlap: int = 220) -> list[str]:
    compact = re.sub(r"\s+", " ", text or "").strip()
    if not compact:
        return []
    chunks = []
    start = 0
    while start < len(compact):
        end = min(len(compact), start + size)
        chunks.append(compact[start:end])
        if end >= len(compact):
            break
        start = max(0, end - overlap)
    return chunks


def _source_url(metadata: dict[str, Any]) -> str | None:
    source_path = metadata.get("source_path")
    if not source_path:
        return None
    path = Path(str(source_path))
    try:
        rel = path.resolve().relative_to(DATA_ROOT.resolve())
    except Exception:
        return None
    return "/files/data/" + quote(str(rel).replace("\\", "/"))


def refresh_application_index(*, force: bool = True) -> dict[str, Any]:
    if not PATENT_APPLICATION_ROOT.exists():
        raise HTTPException(status_code=404, detail=f"출원 공식팩을 찾을 수 없습니다: {PATENT_APPLICATION_ROOT}")
    docs = []
    errors = []
    source_files = list(_iter_source_files() or [])
    for path in source_files:
        text, error = _read_source_text(path)
        if error:
            errors.append({"path": str(path), "error": error})
        for chunk_index, chunk in enumerate(_chunk_text(text), 1):
            metadata = {
                "source_type": _source_type(path),
                "source_path": str(path),
                "relative_source_path": _safe_relative(path),
                "file_name": path.name,
                "chunk_index": chunk_index,
                "text_hash": _hash_text(chunk),
                "assistant_scope": "patent_application",
            }
            doc_id_seed = f"application:{path}:{chunk_index}:{metadata['text_hash']}"
            docs.append(
                {
                    "doc_id": hashlib.sha1(doc_id_seed.encode("utf-8")).hexdigest(),
                    "page_content": chunk,
                    "metadata": metadata,
                    "vector": _vectorize(chunk),
                }
            )

    output_dir = _index_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    docs_path = _documents_path()
    manifest_path = _manifest_path()
    tmp_docs = output_dir / "documents.jsonl.tmp"
    tmp_manifest = output_dir / "manifest.json.tmp"
    with tmp_docs.open("w", encoding="utf-8") as file:
        for doc in docs:
            file.write(json.dumps(doc, ensure_ascii=False, sort_keys=True) + "\n")
    fingerprints = [
        {"path": str(path), "size_bytes": path.stat().st_size, "sha1": _hash_file(path)}
        for path in source_files
        if path.exists()
    ]
    manifest = {
        "scope": "patent_application",
        "backend": "local_hashed_bow",
        "vector_dimensions": VECTOR_DIMENSIONS,
        "refreshed_at": _now(),
        "document_count": len(docs),
        "source_file_count": len(source_files),
        "documents_path": str(docs_path),
        "source_fingerprints": fingerprints,
        "errors": errors,
    }
    tmp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_docs.replace(docs_path)
    tmp_manifest.replace(manifest_path)
    return {
        "status": "refreshed",
        "scope": "patent_application",
        "document_count": len(docs),
        "source_file_count": len(source_files),
        "manifest_path": str(manifest_path),
        "documents_path": str(docs_path),
        "errors": errors,
    }


def application_index_status() -> dict[str, Any]:
    manifest = _read_json(_manifest_path()) or {}
    report = application_download_report()
    return {
        "root": str(PATENT_APPLICATION_ROOT),
        "root_exists": PATENT_APPLICATION_ROOT.exists(),
        "index_exists": _documents_path().exists(),
        "manifest": manifest,
        "download_report": {
            "exists": report.get("exists"),
            "success_count": report.get("success_count"),
            "failure_count": report.get("failure_count"),
            "report_path": report.get("report_path"),
            "manifest_path": report.get("manifest_path"),
        },
    }


def _iter_index_docs() -> Iterable[dict[str, Any]]:
    path = _documents_path()
    if not path.exists():
        return
    with path.open(encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(doc, dict):
                yield doc


def search_application_index(query: str, *, top_k: int = 6) -> dict[str, Any]:
    if not _documents_path().exists():
        refresh_application_index(force=True)
    query_vector = _vectorize(query)
    scored = []
    for doc in _iter_index_docs() or []:
        vector = doc.get("vector") if isinstance(doc.get("vector"), dict) else {}
        score = _dot(query_vector, {str(key): float(value) for key, value in vector.items()})
        if score <= 0:
            continue
        scored.append((score, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    hits = []
    for score, doc in scored[:top_k]:
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        text = str(doc.get("page_content") or "")
        hits.append(
            {
                "patent_id": "patent_application",
                "score": round(score, 6),
                "excerpt": text[:500],
                "page_content": text,
                "metadata": metadata,
            }
        )
    return {
        "query": query,
        "mode": "patent_application_local_vectorstore",
        "patent_id": "patent_application",
        "top_k": top_k,
        "hit_count": len(hits),
        "hits": hits,
    }


def preferred_application_hits(preferred_terms: list[str], *, top_k: int = 6) -> list[dict[str, Any]]:
    terms = [term.lower() for term in preferred_terms if term]
    hits = []
    for doc in _iter_index_docs() or []:
        metadata = doc.get("metadata") if isinstance(doc.get("metadata"), dict) else {}
        haystack = " ".join(
            [
                str(metadata.get("file_name") or ""),
                str(metadata.get("relative_source_path") or ""),
            ]
        ).lower()
        matched = [term for term in terms if term in haystack]
        if not matched:
            continue
        source_path = str(metadata.get("relative_source_path") or "")
        local_pack_boost = 0.12 if "/downloads/" not in source_path else 0.0
        text = str(doc.get("page_content") or "")
        hits.append(
            {
                "patent_id": "patent_application",
                "score": round(0.42 + min(len(matched), 4) * 0.05 + local_pack_boost, 6),
                "excerpt": text[:500],
                "page_content": text,
                "metadata": metadata,
            }
        )
    hits.sort(key=lambda item: item["score"], reverse=True)
    return hits[:top_k]


def cards_from_application_hits(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cards = []
    for index, hit in enumerate(hits, 1):
        metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
        cards.append(
            {
                "label": f"출원 근거 {index}",
                "title": metadata.get("file_name"),
                "source_type": str(metadata.get("source_type") or "APPLICATION_OFFICIAL"),
                "page_no": None,
                "url": _source_url(metadata),
                "snippet": str(hit.get("excerpt") or ""),
                "metadata": metadata,
            }
        )
    return cards


def _declared_sources() -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for name in ("official_sources.json", "patent_rejection_notice_sources.json"):
        data = _read_json(PATENT_APPLICATION_ROOT / name)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    sources.append(item)
    csv_path = PATENT_APPLICATION_ROOT / "official_sources.csv"
    if csv_path.exists():
        try:
            with csv_path.open(encoding="utf-8-sig", newline="") as file:
                sources.extend(dict(row) for row in csv.DictReader(file))
        except Exception:
            pass
    return sources


def extract_application_urls() -> list[dict[str, str]]:
    seen: set[str] = set()
    urls: list[dict[str, str]] = []

    def add(url: str, *, title: str, source_id: str, url_type: str) -> None:
        clean = url.strip().rstrip(".,")
        if not clean or clean in seen:
            return
        seen.add(clean)
        urls.append({"url": clean, "title": title, "source_id": source_id, "url_type": url_type})

    for index, item in enumerate(_declared_sources(), 1):
        title = str(item.get("title") or f"source-{index}")
        source_id = str(item.get("id") or item.get("source_id") or f"SRC-{index:03d}")
        for key, url_type in (("direct_download_url", "direct_download"), ("page_url", "page"), ("official_url", "page")):
            value = str(item.get(key) or "").strip()
            if value:
                add(value, title=title, source_id=source_id, url_type=url_type)

    for path in sorted(PATENT_APPLICATION_ROOT.glob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".html", ".csv", ".json"}:
            continue
        if path.name in {"download_manifest.json", "download_report.md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in URL_RE.findall(text):
            add(match, title=path.name, source_id=path.stem, url_type="discovered")
    return urls


class _LinkExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self._current_href: str | None = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs if value}
        if tag.lower() == "a" and attrs_dict.get("href"):
            self._current_href = attrs_dict["href"]
            self._current_text = []
        elif tag.lower() in {"iframe", "embed", "source"} and attrs_dict.get("src"):
            self.links.append({"url": attrs_dict["src"], "label": tag})

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            label = " ".join(" ".join(self._current_text).split())
            self.links.append({"url": self._current_href, "label": label})
            self._current_href = None
            self._current_text = []


def _extract_page_links(html: str, base_url: str) -> list[dict[str, str]]:
    parser = _LinkExtractor()
    try:
        parser.feed(html)
    except Exception:
        return []
    links = []
    for item in parser.links:
        url = urljoin(base_url, item["url"])
        if url.startswith("http://") or url.startswith("https://"):
            links.append({"url": url, "label": item.get("label", "")})
    return links


def _looks_like_document_link(url: str, label: str = "") -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    query = parsed.query.lower()
    suffix = Path(path).suffix.lower()
    if suffix in DOCUMENT_EXTENSIONS:
        return True
    haystack = f"{path} {query} {label.lower()}"
    if any(term in haystack for term in DOCUMENT_ENDPOINT_TERMS):
        return True
    return any(term in label.lower() for term in ("pdf", "hwp", "hwpx", "doc", "xls", "ppt", "zip", "다운로드", "첨부", "원문"))


def _embedded_document_items(results: list[dict[str, Any]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    items: list[dict[str, str]] = []
    for result in results:
        if not result.get("ok") or not result.get("path"):
            continue
        content_type = str(result.get("content_type") or "").lower()
        path = Path(str(result["path"]))
        if not path.exists():
            continue
        if "html" not in content_type and path.suffix.lower() not in {".html", ".htm", ".do", ".jsp"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for link in _extract_page_links(text, str(result.get("url") or "")):
            url = link["url"].strip()
            label = link.get("label", "")
            if url in seen or not _looks_like_document_link(url, label):
                continue
            seen.add(url)
            parent_id = str(result.get("source_id") or "embedded")
            source_id = f"{parent_id}-DOC-{len(items) + 1:03d}"
            items.append(
                {
                    "url": url,
                    "title": f"{result.get('title') or parent_id} / {label or 'embedded document'}",
                    "source_id": source_id,
                    "url_type": "embedded_document",
                    "parent_url": str(result.get("url") or ""),
                    "parent_path": str(path),
                }
            )
            if len(items) >= MAX_EMBEDDED_DOWNLOADS_PER_RUN:
                return items
    return items


def _extension_for_download(url: str, content_type: str) -> str:
    parsed = urlparse(url)
    suffix = Path(parsed.path).suffix.lower()
    if suffix and len(suffix) <= 8:
        return suffix
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip()) if content_type else None
    if guessed:
        return guessed
    if "html" in content_type:
        return ".html"
    if "pdf" in content_type:
        return ".pdf"
    return ".bin"


def _iri_to_uri(url: str) -> str:
    parts = urlsplit(url)
    path = quote(parts.path, safe="/%")
    query = quote(parts.query, safe="=&%?/:;+,-._~")
    fragment = quote(parts.fragment, safe="=&%?/:;+,-._~")
    return urlunsplit((parts.scheme, parts.netloc, path, query, fragment))


def _safe_download_name(item: dict[str, str], extension: str) -> str:
    seed = hashlib.sha1(item["url"].encode("utf-8")).hexdigest()[:10]
    source_id = re.sub(r"[^A-Za-z0-9_-]+", "_", item.get("source_id") or "source")[:32]
    return f"{source_id}_{seed}{extension}"


def download_application_sources(
    *,
    force: bool = False,
    timeout: int = 20,
    limit: int | None = None,
    include_embedded: bool = True,
) -> dict[str, Any]:
    if not PATENT_APPLICATION_ROOT.exists():
        raise HTTPException(status_code=404, detail=f"출원 공식팩을 찾을 수 없습니다: {PATENT_APPLICATION_ROOT}")
    items = extract_application_urls()
    if limit is not None:
        items = items[: max(0, limit)]
    else:
        items = items[:MAX_DOWNLOADS_PER_RUN]

    raw_dir = _download_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    seen_urls = {item["url"] for item in items}

    def download_item(item: dict[str, str]) -> dict[str, Any]:
        url = item["url"]
        request_url = _iri_to_uri(url)
        request = Request(request_url, headers={"User-Agent": USER_AGENT})
        started_at = _now()
        try:
            with urlopen(request, timeout=timeout) as response:
                content_type = response.headers.get("Content-Type", "")
                extension = _extension_for_download(url, content_type)
                target = raw_dir / _safe_download_name(item, extension)
                if target.exists() and not force:
                    status = "cached"
                    size = target.stat().st_size
                else:
                    body = response.read()
                    target.write_bytes(body)
                    status = "downloaded"
                    size = len(body)
                if size <= 0:
                    target.unlink(missing_ok=True)
                    raise ValueError("empty response body")
                return {
                    **item,
                    "ok": True,
                    "status": status,
                    "http_status": getattr(response, "status", None),
                    "content_type": content_type,
                    "size_bytes": size,
                    "path": str(target),
                    "started_at": started_at,
                    "finished_at": _now(),
                }
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, ValueError) as exc:
            return {
                **item,
                "ok": False,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "started_at": started_at,
                "finished_at": _now(),
            }

    for item in items:
        results.append(download_item(item))

    embedded_items: list[dict[str, str]] = []
    if include_embedded:
        for item in _embedded_document_items(results):
            if item["url"] in seen_urls:
                continue
            seen_urls.add(item["url"])
            embedded_items.append(item)
        for item in embedded_items:
            results.append(download_item(item))

    success = [item for item in results if item.get("ok")]
    failures = [item for item in results if not item.get("ok")]
    manifest = {
        "generated_at": _now(),
        "root": str(PATENT_APPLICATION_ROOT),
        "attempted_count": len(results),
        "success_count": len(success),
        "failure_count": len(failures),
        "base_url_count": len(items),
        "embedded_url_count": len(embedded_items),
        "results": results,
    }
    manifest_path = PATENT_APPLICATION_ROOT / "download_manifest.json"
    report_path = PATENT_APPLICATION_ROOT / "download_report.md"
    _write_json(manifest_path, manifest)
    _write_download_report(report_path, manifest)
    _write_download_open_helpers(manifest)
    return {
        "status": "completed",
        "attempted_count": len(results),
        "success_count": len(success),
        "failure_count": len(failures),
        "base_url_count": len(items),
        "embedded_url_count": len(embedded_items),
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
        "failures": failures,
    }


def _write_download_report(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# 특허 출원 공식 자료 다운로드/크롤링 리포트",
        "",
        f"- 생성 시각: {manifest.get('generated_at')}",
        f"- 시도: {manifest.get('attempted_count')}건",
        f"- 성공: {manifest.get('success_count')}건",
        f"- 실패: {manifest.get('failure_count')}건",
        f"- 원본 URL: {manifest.get('base_url_count')}건",
        f"- 페이지 내부 문서 URL: {manifest.get('embedded_url_count')}건",
        "",
        "## 성공",
    ]
    for item in manifest.get("results") or []:
        if item.get("ok"):
            lines.append(f"- `{item.get('source_id')}` {item.get('title')} / {item.get('status')} / {item.get('path')}")
    lines.extend(["", "## 다운로드/크롤링 불가"])
    failures = [item for item in manifest.get("results") or [] if not item.get("ok")]
    if not failures:
        lines.append("- 없음")
    for item in failures:
        lines.append(f"- `{item.get('source_id')}` {item.get('title')}: {item.get('error')} ({item.get('url')})")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _download_file_kind(path: Path, item: dict[str, Any]) -> tuple[str, str, str]:
    suffix = path.suffix.lower()
    try:
        head = path.read_bytes()[:2048]
    except Exception:
        head = b""
    text_hint = " ".join(str(item.get(key, "")) for key in ("title", "url", "content_type")).lower()
    if head.startswith(b"%PDF") or suffix == ".pdf":
        return "pdf", ".pdf", "PDF 문서: 브라우저, Preview, Acrobat으로 열기"
    if head.startswith(b"\xd0\xcf\x11\xe0") or suffix == ".hwp":
        return "hwp", ".hwp", "HWP 문서: 한글/한컴오피스, 또는 HWP 변환 도구로 열기"
    if head.startswith(b"PK"):
        if "hwpx" in text_hint or suffix == ".hwpx":
            return "zip/hwpx", ".hwpx", "HWPX 문서: 한글/한컴오피스로 열기"
        return "zip", ".zip", "ZIP 압축파일: 압축 해제로 확인"
    if head.startswith(b"MZ") or suffix == ".exe":
        return "exe", ".exe", "Windows 실행 설치파일: macOS에서는 내용 확인용으로만 보관"
    lower_head = head.lower()
    if suffix in {".html", ".htm"} or b"<html" in lower_head or b"<!doctype html" in lower_head:
        return "html", ".html", "HTML 웹페이지: 브라우저로 열기"
    if suffix in {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}:
        kind = suffix.lstrip(".")
        return kind, suffix, "Office 문서: Microsoft Office 또는 호환 앱으로 열기"
    return suffix.lstrip(".") or "file", suffix if suffix else ".bin", "파일 형식 자동 판별 필요"


def _safe_local_title(value: str) -> str:
    compact = re.sub(r"\s+", " ", (value or "").strip())
    compact = re.sub(r"[\\/:*?\"<>|]", "_", compact)
    compact = compact.replace("[", "").replace("]", "")
    return (compact.strip(" ._") or "untitled")[:90].strip(" ._") or "untitled"


def _without_duplicate_extension(title: str, extension: str) -> str:
    cleaned = title
    for suffix in (extension.lower(), ".pdf", ".hwp", ".hwpx", ".html", ".htm", ".zip"):
        while suffix and cleaned.lower().endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip(" ._")
    return cleaned


def _size_label(size: int) -> str:
    size = int(size or 0)
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


def _write_download_open_helpers(manifest: dict[str, Any]) -> None:
    downloads_dir = PATENT_APPLICATION_ROOT / "downloads"
    raw_dir = downloads_dir / "raw"
    readable_dir = downloads_dir / "readable"
    named_dir = downloads_dir / "named"
    readable_dir.mkdir(parents=True, exist_ok=True)
    named_dir.mkdir(parents=True, exist_ok=True)
    for folder in (readable_dir, named_dir):
        for child in folder.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()

    rows: list[dict[str, Any]] = []
    successes = [item for item in manifest.get("results") or [] if item.get("ok") and item.get("path")]
    for index, item in enumerate(successes, start=1):
        raw_path = Path(str(item.get("path")))
        if not raw_path.exists():
            continue
        kind, extension, open_method = _download_file_kind(raw_path, item)
        source_id = _safe_local_title(str(item.get("source_id") or raw_path.stem))
        title = _without_duplicate_extension(_safe_local_title(str(item.get("title") or raw_path.stem)), extension)
        readable_name = f"{raw_path.stem}{extension}"
        named_name = f"{index:03d}_{source_id}_{title}{extension}"
        readable_link = readable_dir / readable_name
        named_link = named_dir / named_name
        if readable_link.exists() or readable_link.is_symlink():
            readable_link.unlink()
        if named_link.exists() or named_link.is_symlink():
            named_link.unlink()
        readable_link.symlink_to(Path("..") / "raw" / raw_path.name)
        named_link.symlink_to(Path("..") / "readable" / readable_name)
        rows.append(
            {
                "no": index,
                "title": title,
                "source_id": source_id,
                "kind": kind,
                "size_bytes": raw_path.stat().st_size,
                "size": _size_label(raw_path.stat().st_size),
                "raw_file": raw_path.name,
                "readable_file": readable_name,
                "named_file": named_name,
                "open_method": open_method,
                "url": item.get("url", ""),
            }
        )

    csv_path = downloads_dir / "file_index.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "no",
                "title",
                "source_id",
                "kind",
                "size_bytes",
                "size",
                "raw_file",
                "readable_file",
                "named_file",
                "open_method",
                "url",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    _write_json(downloads_dir / "file_index.json", rows)

    counts = Counter(row["kind"] for row in rows)
    readme_lines = [
        "# 다운로드 자료 보는 방법",
        "",
        "이 폴더의 `raw/*.do` 파일은 정부/공공기관 URL endpoint 이름이 그대로 저장된 것입니다. 실제 파일 형식은 확장자가 아니라 파일 내부 MIME/signature로 판단해야 합니다.",
        "",
        "## 빠르게 보는 방법",
        "",
        "- `open_index.html`: 브라우저에서 문서명으로 검색하고 `열기` 버튼으로 바로 확인하는 로컬 목록입니다.",
        "- `named/` 폴더: 한국어 제목과 실제 확장자를 붙인 보기용 바로가기입니다.",
        "- `readable/` 폴더: 원본 파일명을 유지하되 실제 형식에 맞춰 `.pdf`, `.html`, `.hwp`, `.hwpx`, `.exe` 이름으로 만든 바로가기입니다.",
        "- `file_names.md`: 전체 파일명을 표로 정리한 문서입니다.",
        "- `raw/` 폴더: 원본 그대로 저장한 파일입니다. 챗봇 인덱싱은 이 원본을 사용합니다.",
        "",
        "## 파일 종류 요약",
        "",
    ]
    for kind, count in sorted(counts.items()):
        readme_lines.append(f"- {kind}: {count}개")
    readme_lines.extend(
        [
            "",
            "## 추천",
            "",
            "발표나 직접 확인에는 `open_index.html` 또는 `named/` 폴더를 사용하세요. `.do` 파일을 직접 더블클릭하면 macOS가 파일 종류를 몰라 깨져 보일 수 있습니다.",
        ]
    )
    (downloads_dir / "README.md").write_text("\n".join(readme_lines) + "\n", encoding="utf-8")

    names_lines = [
        "# 출원 공식 자료 로컬 파일 목록",
        "",
        "이 문서는 `downloads/raw`에 `.do`로 저장된 원본 파일을 사람이 열기 쉬운 이름과 확장자로 다시 연결한 목록입니다.",
        "",
        "- 바로 열기용 폴더: `downloads/named`",
        "- 원본 보관 폴더: `downloads/raw`",
        "- 확장자 보정 폴더: `downloads/readable`",
        "- 로컬 HTML 목록: `downloads/open_index.html`",
        "",
        "| 번호 | 문서명 | 형식 | 파일명 | 열기 방법 |",
        "|---:|---|---|---|---|",
    ]
    for row in rows:
        names_lines.append(
            f"| {row['no']} | {row['title']} | {row['kind'].upper()} | `named/{row['named_file']}` | {row['open_method']} |"
        )
    failures = [item for item in manifest.get("results") or [] if not item.get("ok")]
    if failures:
        names_lines.extend(["", "## 다운로드 실패", ""])
        for item in failures:
            names_lines.append(f"- `{item.get('source_id')}` {item.get('title')}: {item.get('error')} ({item.get('url')})")
    (downloads_dir / "file_names.md").write_text("\n".join(names_lines) + "\n", encoding="utf-8")

    html_rows = []
    for row in rows:
        local_href = quote(f"named/{row['named_file']}")
        source_href = html_escape(str(row.get("url") or ""), quote=True)
        searchable = html_escape(f"{row['title']} {row['source_id']} {row['named_file']}".lower(), quote=True)
        html_rows.append(
            "<tr data-kind=\"{kind}\" data-text=\"{searchable}\">"
            "<td class=\"num\">{no:03d}</td>"
            "<td><strong>{title}</strong><span>{source_id}</span></td>"
            "<td><code>{kind}</code></td>"
            "<td>{size}</td>"
            "<td><a class=\"button\" href=\"{local_href}\">열기</a></td>"
            "<td class=\"file\"><code>{named_file}</code></td>"
            "<td><a href=\"{source_href}\" target=\"_blank\" rel=\"noopener\">원문 URL</a></td>"
            "</tr>".format(
                kind=html_escape(row["kind"].upper()),
                searchable=searchable,
                no=row["no"],
                title=html_escape(row["title"]),
                source_id=html_escape(row["source_id"]),
                size=html_escape(row["size"]),
                local_href=local_href,
                named_file=html_escape(row["named_file"]),
                source_href=source_href,
            )
        )
    failure_html = ""
    if failures:
        items = [
            "<li><code>{source_id}</code> {title} <span>{status}</span></li>".format(
                source_id=html_escape(str(item.get("source_id", ""))),
                title=html_escape(str(item.get("title", ""))),
                status=html_escape(str(item.get("status", ""))),
            )
            for item in failures
        ]
        failure_html = f"<section><h2>다운로드 실패</h2><ul>{''.join(items)}</ul></section>"
    html_body = "\n        ".join(html_rows)
    (downloads_dir / "open_index.html").write_text(
        f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>출원 공식 자료 로컬 파일 목록</title>
  <style>
    :root {{ color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f7f7f4; color: #202124; }}
    header {{ position: sticky; top: 0; z-index: 2; background: #fff; border-bottom: 1px solid #dedbd2; padding: 18px 24px 16px; }}
    h1 {{ margin: 0 0 10px; font-size: 22px; font-weight: 750; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 8px 16px; font-size: 13px; color: #5f6368; }}
    .toolbar {{ display: flex; gap: 8px; align-items: center; margin-top: 14px; flex-wrap: wrap; }}
    input, select {{ height: 36px; border: 1px solid #c9c5ba; background: #fff; border-radius: 6px; padding: 0 10px; font-size: 14px; }}
    input {{ min-width: 280px; flex: 1; }}
    main {{ padding: 18px 24px 32px; }}
    .hint {{ margin: 0 0 14px; color: #4b4f55; font-size: 14px; line-height: 1.5; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #dedbd2; }}
    th, td {{ border-bottom: 1px solid #ebe8df; padding: 10px 12px; text-align: left; vertical-align: middle; font-size: 14px; }}
    th {{ position: sticky; top: 112px; background: #efede7; font-size: 12px; color: #4b4f55; text-transform: uppercase; letter-spacing: .02em; z-index: 1; }}
    tr:hover td {{ background: #fbfaf7; }}
    td.num {{ width: 54px; color: #6f746f; font-variant-numeric: tabular-nums; }}
    td span {{ display: block; margin-top: 3px; color: #6f746f; font-size: 12px; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; }}
    .file code {{ word-break: break-all; }}
    .button {{ display: inline-flex; align-items: center; justify-content: center; min-width: 52px; height: 30px; padding: 0 10px; border: 1px solid #9b8d67; border-radius: 6px; color: #312b1b; text-decoration: none; background: #fff7df; font-weight: 650; }}
    a {{ color: #2457a6; }}
    section {{ margin-top: 22px; }}
    h2 {{ font-size: 16px; margin: 0 0 8px; }}
    @media (max-width: 820px) {{ header {{ padding: 14px; }} main {{ padding: 14px; overflow-x: auto; }} table {{ min-width: 920px; }} th {{ top: 134px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>출원 공식 자료 로컬 파일 목록</h1>
    <div class="meta"><div>성공 파일 {len(rows)}개</div><div>보기용 폴더: <code>downloads/named</code></div><div>원본 폴더: <code>downloads/raw</code></div></div>
    <div class="toolbar"><input id="q" type="search" placeholder="파일명, 문서명, SRC 번호 검색"><select id="kind"><option value="">전체 형식</option><option value="PDF">PDF</option><option value="HTML">HTML</option><option value="HWP">HWP</option><option value="ZIP/HWPX">HWPX</option><option value="EXE">EXE</option></select></div>
  </header>
  <main>
    <p class="hint">아래의 <strong>열기</strong>를 누르면 <code>named/</code> 폴더의 보기용 파일이 열립니다. HWP/HWPX는 한컴오피스가 설치되어 있어야 정상적으로 열립니다.</p>
    <table><thead><tr><th>번호</th><th>문서명</th><th>형식</th><th>크기</th><th>열기</th><th>로컬 파일명</th><th>원문</th></tr></thead><tbody id="rows">
        {html_body}
    </tbody></table>
    {failure_html}
  </main>
  <script>
    const q = document.getElementById('q');
    const kind = document.getElementById('kind');
    const rows = Array.from(document.querySelectorAll('#rows tr'));
    function applyFilter() {{
      const needle = q.value.trim().toLowerCase();
      const selected = kind.value;
      for (const row of rows) {{
        const textOk = !needle || row.dataset.text.includes(needle);
        const kindOk = !selected || row.dataset.kind === selected;
        row.style.display = textOk && kindOk ? '' : 'none';
      }}
    }}
    q.addEventListener('input', applyFilter);
    kind.addEventListener('change', applyFilter);
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )
    command_path = downloads_dir / "open_downloads.command"
    command_path.write_text(f'#!/bin/zsh\ncd "{downloads_dir}"\nopen "open_index.html"\nopen "named"\n', encoding="utf-8")
    command_path.chmod(0o755)


def application_download_report() -> dict[str, Any]:
    manifest_path = PATENT_APPLICATION_ROOT / "download_manifest.json"
    report_path = PATENT_APPLICATION_ROOT / "download_report.md"
    manifest = _read_json(manifest_path) if manifest_path.exists() else {}
    return {
        "exists": bool(manifest),
        "manifest_path": str(manifest_path),
        "report_path": str(report_path),
        "markdown": report_path.read_text(encoding="utf-8") if report_path.exists() else "",
        "success_count": manifest.get("success_count", 0) if isinstance(manifest, dict) else 0,
        "failure_count": manifest.get("failure_count", 0) if isinstance(manifest, dict) else 0,
        "failures": [item for item in (manifest.get("results", []) if isinstance(manifest, dict) else []) if not item.get("ok")],
    }
