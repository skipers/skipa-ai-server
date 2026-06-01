"""Patent-application assistant data download, indexing, and retrieval."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from html import unescape
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
    skip_parts = {"index", "__pycache__", "readable"}
    generated_names = {"download_manifest.json", "download_report.md", "file_index.csv", "file_index.json", "README.md"}
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
