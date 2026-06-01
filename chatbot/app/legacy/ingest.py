# -*- coding: utf-8 -*-

import base64
import hashlib
import json
import os
import re
import shutil
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import fitz  # PyMuPDF

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None

try:
    from langchain_core.documents import Document
except Exception:  # pragma: no cover
    from langchain.docstore.document import Document

from .compat import load_compatible_patent_meta


JSON_PATENT_DOCS = (
    ("decisions/decisions.json", "BUSINESS_DOC", "사업부 결정 이력"),
    ("annuity/annuity.json", "BUSINESS_DOC", "연차료 이력"),
    ("internal_projects.json", "BUSINESS_DOC", "사내 활용 현황"),
    ("similar_patents.json", "BUSINESS_DOC", "유사 특허 목록"),
)

ENABLE_VISUAL_ASSET_EXTRACTION = os.getenv("ENABLE_VISUAL_ASSET_EXTRACTION", "true").lower() in (
    "1",
    "true",
    "yes",
)
ENABLE_VISUAL_BASE64 = os.getenv("ENABLE_VISUAL_BASE64", "true").lower() in ("1", "true", "yes")
VISUAL_BASE64_MAX_BYTES = int(os.getenv("VISUAL_BASE64_MAX_BYTES", "180000"))
MAX_VISUAL_ASSETS_PER_DOCUMENT = int(os.getenv("MAX_VISUAL_ASSETS_PER_DOCUMENT", "80"))


class _VisibleTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[tuple[str, Optional[str]]]) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript"}:
            self._skip_depth += 1
        if tag.lower() in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"script", "style", "svg", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        if tag.lower() in {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        clean = normalize_text(unescape(data))
        if clean:
            self.parts.append(clean)

    def text(self) -> str:
        return normalize_text(" ".join(self.parts))


def sha1_text(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def normalize_text(text: str) -> str:
    return " ".join((text or "").split())


def make_file_url(
    public_file_base_url: str,
    patent_id: str,
    file_name: str,
    page_no: Optional[int] = None,
) -> str:
    url = f"{public_file_base_url.rstrip('/')}/patents/{patent_id}/{file_name.lstrip('/')}"
    if page_no:
        url += f"#page={page_no}"
    return url


def _safe_name(value: str, max_len: int = 80) -> str:
    safe = re.sub(r"[^0-9A-Za-z가-힣_.-]+", "_", value or "").strip("_")
    return (safe[:max_len] or "asset")


def _asset_url(public_file_base_url: str, patent_id: str, rel_asset_path: str) -> str:
    return f"{public_file_base_url.rstrip('/')}/patents/{patent_id}/{rel_asset_path.lstrip('/')}"


def _rect_key(rect: fitz.Rect) -> Tuple[int, int, int, int]:
    return (int(rect.x0), int(rect.y0), int(rect.x1), int(rect.y1))


def _rect_intersection_ratio(a: fitz.Rect, b: fitz.Rect) -> float:
    inter = a & b
    if inter.is_empty or a.get_area() <= 0:
        return 0.0
    return inter.get_area() / max(1.0, a.get_area())


def _clip_rect(page: fitz.Page, rect: fitz.Rect, margin: float = 6.0) -> fitz.Rect:
    clipped = fitz.Rect(rect)
    clipped.x0 = max(page.rect.x0, clipped.x0 - margin)
    clipped.y0 = max(page.rect.y0, clipped.y0 - margin)
    clipped.x1 = min(page.rect.x1, clipped.x1 + margin)
    clipped.y1 = min(page.rect.y1, clipped.y1 + margin)
    return clipped


def _render_page_clip(page: fitz.Page, rect: fitz.Rect, output_path: Path, zoom: float = 1.7) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=_clip_rect(page, rect), alpha=False)
    pix.save(str(output_path))


def _image_base64(path: Path) -> Tuple[Optional[str], Optional[str]]:
    if not ENABLE_VISUAL_BASE64 or not path.exists():
        return None, None
    try:
        data_path = path
        if path.stat().st_size > VISUAL_BASE64_MAX_BYTES and Image is not None:
            thumb_path = path.with_suffix(".thumb.png")
            if not thumb_path.exists():
                with Image.open(path) as img:
                    img.thumbnail((900, 900))
                    img.save(thumb_path, format="PNG", optimize=True)
            data_path = thumb_path
        if data_path.stat().st_size > VISUAL_BASE64_MAX_BYTES:
            return None, None
        encoded = base64.b64encode(data_path.read_bytes()).decode("ascii")
        suffix = data_path.suffix.lower()
        mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/gif" if suffix == ".gif" else "image/png"
        return encoded, mime
    except Exception:
        return None, None


def _rows_to_markdown(rows: List[List[Any]]) -> str:
    clean_rows: List[List[str]] = []
    for row in rows:
        clean = [normalize_text(str(cell or "")) for cell in row]
        if any(clean):
            clean_rows.append(clean)
    if not clean_rows:
        return ""
    width = max(len(row) for row in clean_rows)
    clean_rows = [row + [""] * (width - len(row)) for row in clean_rows]
    header = clean_rows[0]
    lines = [
        "| " + " | ".join(cell.replace("|", "/") or "-" for cell in header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in clean_rows[1:]:
        lines.append("| " + " | ".join(cell.replace("|", "/") or "-" for cell in row) + " |")
    return "\n".join(lines)


def _render_table_image(rows: List[List[Any]], output_path: Path) -> bool:
    if Image is None or ImageDraw is None:
        return False
    clean_rows: List[List[str]] = []
    for row in rows:
        clean = [normalize_text(str(cell or ""))[:90] for cell in row]
        if any(clean):
            clean_rows.append(clean)
    if not clean_rows:
        return False
    width = min(6, max(len(row) for row in clean_rows))
    clean_rows = [(row + [""] * width)[:width] for row in clean_rows[:32]]
    font = ImageFont.load_default() if ImageFont else None
    col_w = 190
    row_h = 34
    pad = 10
    image_w = width * col_w + pad * 2
    image_h = len(clean_rows) * row_h + pad * 2
    img = Image.new("RGB", (image_w, image_h), "white")
    draw = ImageDraw.Draw(img)
    for r, row in enumerate(clean_rows):
        y0 = pad + r * row_h
        fill = "#f3f6fa" if r == 0 else "white"
        for c, cell in enumerate(row):
            x0 = pad + c * col_w
            draw.rectangle([x0, y0, x0 + col_w, y0 + row_h], outline="#b8c2cc", fill=fill)
            draw.text((x0 + 6, y0 + 9), cell[:32], fill="#111827", font=font)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG", optimize=True)
    return True


def _make_visual_document(
    *,
    patent_id: str,
    source_type: str,
    source_document_type: str,
    asset_kind: str,
    asset_path: Path,
    rel_asset_path: str,
    public_file_base_url: str,
    meta: Dict[str, Any],
    page_no: Optional[int],
    section_key: str,
    section_title: str,
    text: str,
    file_name_for_url: str,
    asset_bbox: Optional[Tuple[float, float, float, float]] = None,
) -> Document:
    asset_b64, asset_mime = _image_base64(asset_path)
    asset_url = _asset_url(public_file_base_url, patent_id, rel_asset_path)
    clean_text = normalize_text(text)
    content = "\n".join(
        line
        for line in [
            f"시각자료 유형: {asset_kind}",
            f"원본 문서유형: {source_document_type}",
            f"페이지: {page_no or '-'}",
            f"섹션: {section_title}",
            f"이미지 파일: {rel_asset_path}",
            f"이미지 URL: {asset_url}",
            f"텍스트 변환/캡션: {clean_text}",
        ]
        if line
    )
    text_hash = sha1_text(content)
    chunk_id = f"{patent_id}:{source_type}:{asset_kind}:p{page_no or 0}:{asset_path.stem}:{text_hash[:10]}"
    metadata = {
        **_base_metadata(meta, patent_id),
        "chunk_id": chunk_id,
        "source_type": source_type,
        "document_type": source_document_type,
        "content_type": "VISUAL_ASSET",
        "asset_kind": asset_kind,
        "asset_url": asset_url,
        "asset_file_name": rel_asset_path,
        "asset_base64": asset_b64,
        "asset_mime": asset_mime,
        "page_no": page_no,
        "section_key": section_key,
        "section_title": section_title,
        "source_url": make_file_url(
            public_file_base_url=public_file_base_url,
            patent_id=patent_id,
            file_name=file_name_for_url,
            page_no=page_no,
        ),
        "file_name": file_name_for_url,
        "text_hash": text_hash,
    }
    if asset_bbox is not None:
        metadata["asset_bbox"] = [round(v, 2) for v in asset_bbox]
    return Document(page_content=content, metadata=metadata)


def split_text(text: str, max_chars: int = 1200, overlap: int = 150) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _section_title(page_text: str) -> Optional[str]:
    for raw_line in (page_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if len(line) <= 80:
            return line
    return None


PATENT_SECTION_PATTERNS = (
    ("KR_BIBLIO", r"\(19\)\s*대한민국|대한민국\s*특허|등록특허공보|공개특허공보"),
    ("KR_ABSTRACT", r"\(57\)\s*요\s*약|요\s*약"),
    ("KR_CLAIMS", r"청구범위|청구항\s*\d+"),
    ("KR_TECH_FIELD", r"기\s*술\s*분\s*야|기술분야"),
    ("KR_BACKGROUND", r"배\s*경\s*기\s*술|배경기술"),
    ("KR_PROBLEM", r"해결하려는\s*과제"),
    ("KR_SOLUTION", r"과제의\s*해결\s*수단|해결\s*수단"),
    ("KR_EFFECT", r"발명의\s*효과"),
    ("KR_DRAWINGS", r"도면의\s*간단한\s*설명"),
    ("KR_DETAIL", r"발명을\s*실시하기\s*위한\s*구체적인\s*내용|구체적인\s*내용"),
    ("US_ABSTRACT", r"\bABSTRACT\b"),
    ("US_CLAIMS", r"\bCLAIMS?\b|What is claimed is"),
    ("US_BACKGROUND", r"\bBACKGROUND\b|BACKGROUND OF THE INVENTION"),
    ("US_SUMMARY", r"\bSUMMARY\b|SUMMARY OF THE INVENTION"),
    ("US_DESCRIPTION", r"\bDETAILED DESCRIPTION\b|DESCRIPTION OF EMBODIMENTS"),
    ("EP_CLAIMS", r"\bClaims?\b"),
    ("EP_DESCRIPTION", r"\bDescription\b"),
    ("JP_CLAIMS", r"【請求項\d+】|特許請求の範囲"),
    ("JP_BACKGROUND", r"【背景技術】"),
    ("JP_PROBLEM", r"【発明が解決しようとする課題】"),
    ("JP_SOLUTION", r"【課題を解決するための手段】"),
    ("JP_EFFECT", r"【発明の効果】"),
    ("CN_CLAIMS", r"权利要求书|权利要求\s*\d+"),
    ("CN_DESCRIPTION", r"说明书"),
)

REPORT_SECTION_PATTERNS = (
    ("REPORT_SUMMARY", r"\b01\s*평가\s*요약|1\.\s*평가\s*요약|\bI\.\s*평가\s*개요|평가\s*개요|평가\s*요약"),
    ("REPORT_SCORE_DETAIL", r"\b02\s*평가\s*기준별|2\.\s*평가\s*기준별|\bII\.\s*평가\s*기준별|평가\s*기준별\s*(상세\s*)?점수"),
    ("REPORT_INTERNAL_PROJECTS", r"\b03\s*사내\s*프로젝트|3\.\s*사내\s*프로젝트|사내\s*프로젝트|사업\s*적용\s*이력"),
    ("REPORT_SIMILAR_PATENTS", r"\b04\s*유사\s*특허|4\.\s*유사\s*특허|유사\s*특허\s*분석|KIPRIS\s*유사"),
    ("REPORT_CHECK_ITEMS", r"\b05\s*추가\s*확인|5\.\s*추가\s*확인|추가\s*확인\s*필요\s*사항|확인\s*필요\s*사항"),
    ("REPORT_REFERENCES", r"\b06\s*참고문헌|6\.\s*참고문헌|\bIII\.\s*참고문헌|참고문헌"),
    ("REPORT_DECISION", r"\bIV\.\s*의사결정|의사결정\s*가이드|유지|매각|제각"),
    ("REPORT_RISK", r"리스크|회피설계|무효|대체기술|경쟁성"),
)


SECTION_LABELS = {
    "KR_BIBLIO": "서지사항",
    "KR_ABSTRACT": "요약",
    "KR_CLAIMS": "청구범위",
    "KR_TECH_FIELD": "기술분야",
    "KR_BACKGROUND": "배경기술",
    "KR_PROBLEM": "해결하려는 과제",
    "KR_SOLUTION": "과제의 해결 수단",
    "KR_EFFECT": "발명의 효과",
    "KR_DRAWINGS": "도면의 간단한 설명",
    "KR_DETAIL": "구체적인 내용",
    "US_ABSTRACT": "Abstract",
    "US_CLAIMS": "Claims",
    "US_BACKGROUND": "Background",
    "US_SUMMARY": "Summary",
    "US_DESCRIPTION": "Detailed Description",
    "EP_CLAIMS": "Claims",
    "EP_DESCRIPTION": "Description",
    "JP_CLAIMS": "特許請求の範囲",
    "JP_BACKGROUND": "背景技術",
    "JP_PROBLEM": "発明が解決しようとする課題",
    "JP_SOLUTION": "課題を解決するための手段",
    "JP_EFFECT": "発明の効果",
    "CN_CLAIMS": "权利要求书",
    "CN_DESCRIPTION": "说明书",
    "REPORT_SUMMARY": "평가 요약",
    "REPORT_OVERVIEW": "평가 개요",
    "REPORT_SCORE_DETAIL": "평가 기준별 점수",
    "REPORT_INTERNAL_PROJECTS": "사내 프로젝트",
    "REPORT_SIMILAR_PATENTS": "유사 특허 분석",
    "REPORT_CHECK_ITEMS": "추가 확인 필요 사항",
    "REPORT_REFERENCES": "참고문헌",
    "REPORT_DECISION": "의사결정 가이드",
    "REPORT_RISK": "리스크 및 추가 확인",
}


def _detect_section_candidates(text: str, source_type: str) -> List[tuple[int, str]]:
    patterns = REPORT_SECTION_PATTERNS if source_type == "REPORT_PDF" else PATENT_SECTION_PATTERNS
    candidates: List[tuple[int, str]] = []
    for section_key, pattern in patterns:
        for match in re.finditer(pattern, text or "", flags=re.IGNORECASE):
            candidates.append((match.start(), section_key))
    candidates.sort(key=lambda item: item[0])
    return candidates


def _dominant_section(text: str, source_type: str, fallback: Optional[str]) -> tuple[str, str]:
    candidates = _detect_section_candidates(text, source_type)
    if candidates:
        section_key = candidates[0][1]
        return section_key, SECTION_LABELS.get(section_key, section_key)
    return "PAGE_TEXT", fallback or "페이지 본문"


def split_text_by_sections(
    text: str,
    source_type: str,
    max_chars: int = 1200,
    overlap: int = 150,
    fallback_section: Optional[str] = None,
) -> List[tuple[str, str, str]]:
    clean = normalize_text(text)
    if not clean:
        return []

    candidates = _detect_section_candidates(clean, source_type)
    if not candidates:
        section_key, section_label = _dominant_section(clean, source_type, fallback_section)
        return [(chunk, section_key, section_label) for chunk in split_text(clean, max_chars=max_chars, overlap=overlap)]

    spans: List[tuple[int, int, str]] = []
    for idx, (start, section_key) in enumerate(candidates):
        end = candidates[idx + 1][0] if idx + 1 < len(candidates) else len(clean)
        if end - start >= 40:
            spans.append((start, end, section_key))

    if spans and spans[0][0] > 80:
        prefix_key, _ = _dominant_section(clean[: spans[0][0]], source_type, fallback_section)
        spans.insert(0, (0, spans[0][0], prefix_key))

    chunks: List[tuple[str, str, str]] = []
    for start, end, section_key in spans:
        section_text = clean[start:end].strip()
        if not section_text:
            continue
        section_label = SECTION_LABELS.get(section_key, section_key)
        for chunk in split_text(section_text, max_chars=max_chars, overlap=overlap):
            chunks.append((chunk, section_key, section_label))
    return chunks


def _json_to_text(value: Any, prefix: str = "") -> str:
    if isinstance(value, dict) and ("auto_scores" in value or "llm_scores" in value):
        return _report_json_to_text(value)

    if isinstance(value, dict):
        lines: List[str] = []
        for key, item in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(item, (dict, list)):
                lines.append(_json_to_text(item, next_prefix))
            else:
                lines.append(f"{next_prefix}: {item}")
        return "\n".join(line for line in lines if line)

    if isinstance(value, list):
        lines = []
        for idx, item in enumerate(value, start=1):
            next_prefix = f"{prefix}[{idx}]" if prefix else f"[{idx}]"
            lines.append(_json_to_text(item, next_prefix))
        return "\n".join(line for line in lines if line)

    return f"{prefix}: {value}" if prefix else str(value)


def _report_json_to_text(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    if data.get("patent_id"):
        lines.append(f"특허번호: {data.get('patent_id')}")
    if data.get("title"):
        lines.append(f"특허명: {data.get('title')}")

    def append_score_rows(title: str, rows: Any) -> None:
        if not isinstance(rows, list) or not rows:
            return
        lines.append("")
        lines.append(title)
        for row in rows:
            if not isinstance(row, dict):
                continue
            dim = row.get("dim") or "평가"
            item = row.get("item") or "평가항목"
            score = row.get("score")
            basis = row.get("basis") or row.get("reason") or row.get("judgement") or "근거 확인 필요"
            method = row.get("method") or "-"
            lines.append(f"- [{dim}] {item}: {score}점. 근거: {normalize_text(str(basis))} 방법: {method}")
            sources = row.get("sources")
            if isinstance(sources, list):
                for source in sources[:3]:
                    if not isinstance(source, dict):
                        continue
                    source_title = source.get("title") or "참고자료"
                    url = source.get("url") or ""
                    snippet = normalize_text(str(source.get("snippet") or ""))
                    if snippet:
                        lines.append(f"  참고자료: {source_title}. {snippet[:300]} URL: {url}")
                    elif url:
                        lines.append(f"  참고자료: {source_title}. URL: {url}")

    append_score_rows("자동 평가 항목", data.get("auto_scores"))
    append_score_rows("LLM 평가 항목", data.get("llm_scores"))

    for key in ("market_growth", "similar_patents", "references", "decision_guide"):
        value = data.get(key)
        if value:
            lines.append("")
            lines.append(f"{key}:")
            lines.append(_json_to_text(value))

    return "\n".join(line for line in lines if line is not None)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_html_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    parser = _VisibleTextHTMLParser()
    parser.feed(raw)
    return parser.text()


def _html_fragment_text(fragment: str) -> str:
    parser = _VisibleTextHTMLParser()
    parser.feed(fragment or "")
    return parser.text()


def _html_attr(tag_text: str, attr_name: str) -> Optional[str]:
    match = re.search(
        rf"""{attr_name}\s*=\s*["']([^"']+)["']|{attr_name}\s*=\s*([^\s>]+)""",
        tag_text or "",
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return unescape(match.group(1) or match.group(2) or "").strip()


def _html_table_rows(table_html: str) -> List[List[str]]:
    rows: List[List[str]] = []
    for tr_match in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", table_html or "", flags=re.IGNORECASE | re.DOTALL):
        row_html = tr_match.group(1)
        cells: List[str] = []
        for cell_match in re.finditer(r"<(?:th|td)\b[^>]*>(.*?)</(?:th|td)>", row_html, flags=re.IGNORECASE | re.DOTALL):
            cell_text = _html_fragment_text(cell_match.group(1))
            cells.append(cell_text)
        if any(cells):
            rows.append(cells)
    if not rows:
        text = _html_fragment_text(table_html)
        if text:
            rows.append([text])
    return rows


def _nearest_report_section(raw_html: str, offset: int, fallback: str) -> Tuple[str, str]:
    prefix_text = _html_fragment_text(raw_html[max(0, offset - 8000) : offset])
    candidates = _detect_section_candidates(prefix_text, "REPORT_PDF")
    if not candidates:
        return "REPORT_VISUAL", fallback
    section_key = candidates[-1][1]
    return section_key, SECTION_LABELS.get(section_key, fallback)


def extract_html_visual_documents(
    html_path: Path,
    patent_dir: Path,
    patent_id: str,
    source_document_type: str,
    public_file_base_url: str,
    file_name_for_url: str,
    meta: Dict[str, Any],
    max_assets: int = MAX_VISUAL_ASSETS_PER_DOCUMENT,
) -> List[Document]:
    if not ENABLE_VISUAL_ASSET_EXTRACTION or not html_path.exists():
        return []

    raw = html_path.read_text(encoding="utf-8", errors="ignore")
    visual_source_type = "REPORT_VISUAL" if source_document_type == "REPORT_PDF" else "HTML_VISUAL"
    asset_group = _safe_name(f"{source_document_type.lower()}_{html_path.stem}")
    asset_dir = patent_dir / "extracted" / "assets" / asset_group
    rel_asset_prefix = f"extracted/assets/{asset_group}"
    docs: List[Document] = []
    asset_count = 0

    for table_idx, match in enumerate(re.finditer(r"<table\b[^>]*>.*?</table>", raw, flags=re.IGNORECASE | re.DOTALL), start=1):
        if asset_count >= max_assets:
            break
        table_html = match.group(0)
        rows = _html_table_rows(table_html)
        table_text = _rows_to_markdown(rows)
        if not table_text:
            continue
        section_key, section_title = _nearest_report_section(raw, match.start(), "보고서 표")
        html_file = asset_dir / f"{_safe_name(html_path.stem)}_table_{table_idx:02d}.html"
        png_file = asset_dir / f"{_safe_name(html_path.stem)}_table_{table_idx:02d}.png"
        html_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text(
            "<!doctype html><html><head><meta charset='utf-8'></head><body>"
            + table_html
            + "</body></html>",
            encoding="utf-8",
        )
        rendered = _render_table_image(rows, png_file)
        asset_path = png_file if rendered else html_file
        rel_asset_path = f"{rel_asset_prefix}/{asset_path.name}"
        asset_count += 1
        docs.append(
            _make_visual_document(
                patent_id=patent_id,
                source_type=visual_source_type,
                source_document_type=source_document_type,
                asset_kind="TABLE",
                asset_path=asset_path,
                rel_asset_path=rel_asset_path,
                public_file_base_url=public_file_base_url,
                meta=meta,
                page_no=None,
                section_key=f"{section_key}_TABLE",
                section_title=f"{section_title} 표",
                text=f"HTML 보고서 표 추출 텍스트:\n{table_text}",
                file_name_for_url=file_name_for_url,
            )
        )

    for img_idx, match in enumerate(re.finditer(r"<img\b[^>]*>", raw, flags=re.IGNORECASE | re.DOTALL), start=1):
        if asset_count >= max_assets:
            break
        tag = match.group(0)
        src = _html_attr(tag, "src")
        alt = _html_attr(tag, "alt") or "보고서 이미지"
        if not src:
            continue
        section_key, section_title = _nearest_report_section(raw, match.start(), "보고서 이미지")
        suffix = ".png"
        asset_path: Optional[Path] = None
        if src.startswith("data:image/"):
            header, _, payload = src.partition(",")
            image_type = header.split(";")[0].split("/")[-1] or "png"
            suffix = ".jpg" if image_type.lower() in {"jpeg", "jpg"} else f".{_safe_name(image_type.lower(), 8)}"
            asset_path = asset_dir / f"{_safe_name(html_path.stem)}_image_{img_idx:02d}{suffix}"
            try:
                asset_path.parent.mkdir(parents=True, exist_ok=True)
                asset_path.write_bytes(base64.b64decode(payload))
            except Exception:
                asset_path = None
        else:
            src_path = Path(unescape(src))
            if not src_path.is_absolute():
                src_path = html_path.parent / src_path
            if src_path.exists() and src_path.is_file():
                suffix = src_path.suffix or ".png"
                asset_path = asset_dir / f"{_safe_name(html_path.stem)}_image_{img_idx:02d}{suffix}"
                asset_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copyfile(src_path, asset_path)
                except Exception:
                    asset_path = None
        if asset_path is None or not asset_path.exists():
            continue
        rel_asset_path = f"{rel_asset_prefix}/{asset_path.name}"
        asset_count += 1
        docs.append(
            _make_visual_document(
                patent_id=patent_id,
                source_type=visual_source_type,
                source_document_type=source_document_type,
                asset_kind="IMAGE",
                asset_path=asset_path,
                rel_asset_path=rel_asset_path,
                public_file_base_url=public_file_base_url,
                meta=meta,
                page_no=None,
                section_key=f"{section_key}_IMAGE",
                section_title=f"{section_title} 이미지",
                text=f"HTML 보고서 이미지입니다. alt/caption: {alt}",
                file_name_for_url=file_name_for_url,
            )
        )

    return docs


def _base_metadata(meta: Dict[str, Any], patent_id: str) -> Dict[str, Any]:
    return {
        "patent_id": patent_id,
        "title": meta.get("title"),
        "application_number": meta.get("application_number"),
        "registration_number": meta.get("registration_number"),
        "applicant": meta.get("applicant"),
        "inventor": meta.get("inventor"),
        "ipc_code": meta.get("ipc_code"),
        "cpc_code": meta.get("cpc_code"),
        "tech_field": meta.get("tech_field"),
        "business_field": meta.get("business_field"),
        "department": meta.get("department"),
    }


def extract_pdf_to_documents(
    pdf_path: Path,
    patent_id: str,
    source_type: str,
    public_file_base_url: str,
    file_name_for_url: str,
    meta: Dict[str, Any],
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[Document]:
    docs: List[Document] = []
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with fitz.open(str(pdf_path)) as pdf:
        for page_idx in range(len(pdf)):
            page_no = page_idx + 1
            page = pdf.load_page(page_idx)
            page_text = page.get_text("text") or ""
            section = _section_title(page_text)

            section_chunks = split_text_by_sections(
                page_text,
                source_type=source_type,
                max_chars=max_chars,
                overlap=overlap,
                fallback_section=section,
            )
            for chunk_idx, (chunk_text, section_key, section_label) in enumerate(section_chunks):
                text_hash = sha1_text(chunk_text)
                chunk_id = f"{patent_id}:{source_type}:{section_key}:p{page_no}:c{chunk_idx}:{text_hash[:10]}"
                source_url = make_file_url(
                    public_file_base_url=public_file_base_url,
                    patent_id=patent_id,
                    file_name=file_name_for_url,
                    page_no=page_no,
                )
                metadata = {
                    **_base_metadata(meta, patent_id),
                    "chunk_id": chunk_id,
                    "source_type": source_type,
                    "page_no": page_no,
                    "section_title": section_label,
                    "section_key": section_key,
                    "source_url": source_url,
                    "file_name": file_name_for_url,
                    "text_hash": text_hash,
                }
                docs.append(Document(page_content=chunk_text, metadata=metadata))

    return docs


def extract_pdf_visual_documents(
    pdf_path: Path,
    patent_dir: Path,
    patent_id: str,
    source_document_type: str,
    public_file_base_url: str,
    file_name_for_url: str,
    meta: Dict[str, Any],
    max_assets: int = MAX_VISUAL_ASSETS_PER_DOCUMENT,
) -> List[Document]:
    if not ENABLE_VISUAL_ASSET_EXTRACTION or not pdf_path.exists():
        return []

    visual_source_type = "ORIGINAL_VISUAL" if source_document_type == "ORIGINAL_PDF" else "REPORT_VISUAL"
    asset_group = _safe_name(source_document_type.lower())
    asset_dir = patent_dir / "extracted" / "assets" / asset_group
    rel_asset_prefix = f"extracted/assets/{asset_group}"
    docs: List[Document] = []
    asset_count = 0

    def add_visual(
        *,
        page: fitz.Page,
        page_no: int,
        rect: fitz.Rect,
        kind: str,
        idx: int,
        text: str,
        section_key: str,
        section_title: str,
        suffix: str = "png",
        render_zoom: float = 1.7,
    ) -> Optional[Document]:
        nonlocal asset_count
        if asset_count >= max_assets:
            return None
        if rect.width < 40 or rect.height < 25:
            return None
        file_name = f"{_safe_name(pdf_path.stem)}_p{page_no:03d}_{kind.lower()}_{idx:02d}.{suffix}"
        asset_path = asset_dir / file_name
        try:
            _render_page_clip(page, rect, asset_path, zoom=render_zoom)
        except Exception:
            return None
        asset_count += 1
        rel_asset_path = f"{rel_asset_prefix}/{file_name}"
        return _make_visual_document(
            patent_id=patent_id,
            source_type=visual_source_type,
            source_document_type=source_document_type,
            asset_kind=kind,
            asset_path=asset_path,
            rel_asset_path=rel_asset_path,
            public_file_base_url=public_file_base_url,
            meta=meta,
            page_no=page_no,
            section_key=section_key,
            section_title=section_title,
            text=text,
            file_name_for_url=file_name_for_url,
            asset_bbox=(rect.x0, rect.y0, rect.x1, rect.y1),
        )

    with fitz.open(str(pdf_path)) as pdf:
        for page_idx in range(len(pdf)):
            if asset_count >= max_assets:
                break
            page_no = page_idx + 1
            page = pdf.load_page(page_idx)
            page_text = page.get_text("text") or ""
            section_key, section_title = _dominant_section(page_text, source_document_type, _section_title(page_text))
            page_context = normalize_text(page_text)[:900]
            table_rects: List[fitz.Rect] = []

            try:
                tables = page.find_tables()
                table_list = list(getattr(tables, "tables", []) or [])
            except Exception:
                table_list = []

            for table_idx, table in enumerate(table_list, start=1):
                if asset_count >= max_assets:
                    break
                try:
                    rect = fitz.Rect(table.bbox)
                    rows = table.extract() or []
                except Exception:
                    continue
                table_rects.append(rect)
                table_text = _rows_to_markdown(rows)
                if not table_text and page_context:
                    table_text = f"페이지 문맥: {page_context[:500]}"
                doc = add_visual(
                    page=page,
                    page_no=page_no,
                    rect=rect,
                    kind="TABLE",
                    idx=table_idx,
                    text=f"PDF 표 추출 텍스트:\n{table_text}\n페이지 문맥: {page_context[:500]}",
                    section_key=f"{section_key}_TABLE",
                    section_title=f"{section_title} 표",
                    render_zoom=1.9,
                )
                if doc:
                    docs.append(doc)

            try:
                blocks = page.get_text("dict").get("blocks", [])
            except Exception:
                blocks = []
            image_idx = 0
            seen_image_rects: set[Tuple[int, int, int, int]] = set()
            for block in blocks:
                if asset_count >= max_assets:
                    break
                if block.get("type") != 1 or "bbox" not in block:
                    continue
                rect = fitz.Rect(block["bbox"])
                if rect.width < 48 or rect.height < 48:
                    continue
                if any(_rect_intersection_ratio(rect, table_rect) > 0.45 for table_rect in table_rects):
                    continue
                key = _rect_key(rect)
                if key in seen_image_rects:
                    continue
                seen_image_rects.add(key)
                image_idx += 1
                doc = add_visual(
                    page=page,
                    page_no=page_no,
                    rect=rect,
                    kind="IMAGE",
                    idx=image_idx,
                    text=f"PDF 삽입 이미지 또는 도면입니다. 페이지 문맥: {page_context[:700]}",
                    section_key=f"{section_key}_IMAGE",
                    section_title=f"{section_title} 이미지",
                    render_zoom=1.9,
                )
                if doc:
                    docs.append(doc)

            try:
                drawing_count = len(page.get_drawings())
            except Exception:
                drawing_count = 0
            has_visual_keyword = bool(
                re.search(r"도\s*\d+|도면|블록도|흐름도|구성도|다이어그램|FIG\.?\s*\d+", page_text, flags=re.IGNORECASE)
            )
            should_save_page_visual = bool(has_visual_keyword or drawing_count >= 12)
            if should_save_page_visual and asset_count < max_assets:
                doc = add_visual(
                    page=page,
                    page_no=page_no,
                    rect=page.rect,
                    kind="DIAGRAM_PAGE" if drawing_count >= 12 or has_visual_keyword else "PAGE_VISUAL",
                    idx=1,
                    text=(
                        f"페이지 단위 도면/다이어그램 후보입니다. "
                        f"벡터 드로잉 수: {drawing_count}. 페이지 문맥: {page_context[:900]}"
                    ),
                    section_key=f"{section_key}_VISUAL_PAGE",
                    section_title=f"{section_title} 도면/페이지 이미지",
                    render_zoom=1.25,
                )
                if doc:
                    docs.append(doc)

    return docs


def _make_json_documents(
    json_path: Path,
    patent_id: str,
    source_type: str,
    document_title: str,
    public_file_base_url: str,
    meta: Dict[str, Any],
    file_name_for_url: str,
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[Document]:
    if not json_path.exists():
        return []

    data = _read_json(json_path)
    text = _json_to_text(data)
    source_url = make_file_url(
        public_file_base_url=public_file_base_url,
        patent_id=patent_id,
        file_name=file_name_for_url,
        page_no=None,
    )

    docs: List[Document] = []
    for idx, chunk_text in enumerate(split_text(text, max_chars=max_chars, overlap=overlap)):
        text_hash = sha1_text(chunk_text)
        chunk_id = f"{patent_id}:{source_type}:{json_path.stem}:c{idx}:{text_hash[:10]}"
        metadata = {
            **_base_metadata(meta, patent_id),
            "chunk_id": chunk_id,
            "source_type": source_type,
            "page_no": None,
            "section_title": document_title,
            "source_url": source_url,
            "file_name": file_name_for_url,
            "text_hash": text_hash,
        }
        docs.append(Document(page_content=chunk_text, metadata=metadata))
    return docs


def _make_html_documents(
    html_path: Path,
    patent_id: str,
    source_type: str,
    document_title: str,
    public_file_base_url: str,
    meta: Dict[str, Any],
    file_name_for_url: str,
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[Document]:
    if not html_path.exists():
        return []

    text = _read_html_text(html_path)
    source_url = make_file_url(
        public_file_base_url=public_file_base_url,
        patent_id=patent_id,
        file_name=file_name_for_url,
        page_no=None,
    )

    docs: List[Document] = []
    html_chunks = split_text_by_sections(
        text,
        source_type=source_type,
        max_chars=max_chars,
        overlap=overlap,
        fallback_section=document_title,
    )
    for idx, (chunk_text, section_key, section_title) in enumerate(html_chunks):
        text_hash = sha1_text(chunk_text)
        chunk_id = f"{patent_id}:{source_type}:{html_path.stem}:html:c{idx}:{text_hash[:10]}"
        metadata = {
            **_base_metadata(meta, patent_id),
            "chunk_id": chunk_id,
            "source_type": source_type,
            "page_no": None,
            "section_key": section_key,
            "section_title": section_title or document_title,
            "source_url": source_url,
            "file_name": file_name_for_url,
            "text_hash": text_hash,
        }
        docs.append(Document(page_content=chunk_text, metadata=metadata))
    return docs


def _make_metadata_fallback_document(
    patent_id: str,
    source_type: str,
    public_file_base_url: str,
    file_name_for_url: str,
    meta: Dict[str, Any],
    reason: str,
) -> Document:
    title = meta.get("title") or file_name_for_url
    content = "\n".join(
        [
            f"특허명: {title}",
            f"특허 ID: {patent_id}",
            f"등록번호: {meta.get('registration_number') or '확인되지 않음'}",
            f"출원번호: {meta.get('application_number') or '확인되지 않음'}",
            f"문서유형: {source_type}",
            f"파일: {file_name_for_url}",
            f"텍스트 추출 상태: {reason}",
            "주의: 이 PDF에서는 본문 텍스트가 추출되지 않아 제목 및 메타데이터만 색인되었습니다. "
            "청구항, 상세한 설명, 도면 설명 등 본문 답변에는 OCR 처리가 추가로 필요합니다.",
        ]
    )
    text_hash = sha1_text(content)
    return Document(
        page_content=content,
        metadata={
            **_base_metadata(meta, patent_id),
            "chunk_id": f"{patent_id}:{source_type}:metadata:{text_hash[:10]}",
            "source_type": source_type,
            "page_no": None,
            "section_title": "PDF metadata fallback",
            "source_url": make_file_url(
                public_file_base_url=public_file_base_url,
                patent_id=patent_id,
                file_name=file_name_for_url,
            ),
            "file_name": file_name_for_url,
            "text_hash": text_hash,
            "extraction_status": "NO_TEXT_FALLBACK",
        },
    )


def build_patent_documents(
    patent_dir: Path,
    public_file_base_url: str,
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[Document]:
    meta = load_compatible_patent_meta(patent_dir)
    patent_id = str(meta.get("patent_id") or patent_dir.name)

    docs: List[Document] = []
    original_rel = meta.get("original_pdf") or "original.pdf"
    report_rel = meta.get("report_pdf")
    original_path = patent_dir / original_rel if original_rel else None
    if original_path and original_path.exists():
        original_docs = extract_pdf_to_documents(
            pdf_path=original_path,
            patent_id=patent_id,
            source_type="ORIGINAL_PDF",
            public_file_base_url=public_file_base_url,
            file_name_for_url=meta.get("public_original_pdf") or original_rel,
            meta=meta,
            max_chars=max_chars,
            overlap=overlap,
        )
        if not original_docs:
            original_docs = [
                _make_metadata_fallback_document(
                    patent_id=patent_id,
                    source_type="ORIGINAL_PDF",
                    public_file_base_url=public_file_base_url,
                    file_name_for_url=meta.get("public_original_pdf") or original_rel,
                    meta=meta,
                    reason="PDF 본문 텍스트 없음 또는 스캔 이미지 PDF",
                )
            ]
        docs += original_docs
        docs += extract_pdf_visual_documents(
            pdf_path=original_path,
            patent_dir=patent_dir,
            patent_id=patent_id,
            source_document_type="ORIGINAL_PDF",
            public_file_base_url=public_file_base_url,
            file_name_for_url=meta.get("public_original_pdf") or original_rel,
            meta=meta,
        )

    if report_rel:
        report_path = patent_dir / report_rel
        if report_path.exists():
            docs += extract_pdf_to_documents(
                pdf_path=report_path,
                patent_id=patent_id,
                source_type="REPORT_PDF",
                public_file_base_url=public_file_base_url,
                file_name_for_url=meta.get("public_report_pdf") or report_rel,
                meta=meta,
                max_chars=max_chars,
                overlap=overlap,
            )
            docs += extract_pdf_visual_documents(
                pdf_path=report_path,
                patent_dir=patent_dir,
                patent_id=patent_id,
                source_document_type="REPORT_PDF",
                public_file_base_url=public_file_base_url,
                file_name_for_url=meta.get("public_report_pdf") or report_rel,
                meta=meta,
            )

    report_json_paths: List[Path] = []
    reports_dir = patent_dir / "reports"
    if reports_dir.exists():
        report_json_paths.extend(sorted(reports_dir.glob("*.json")))

    source_report_json = meta.get("source_report_json")
    if source_report_json:
        json_path = Path(str(source_report_json))
        if not json_path.is_absolute():
            json_path = Path.cwd() / json_path
        if json_path.exists() and json_path not in report_json_paths:
            report_json_paths.append(json_path)

    for json_path in report_json_paths:
        try:
            file_name_for_url = str(json_path.relative_to(patent_dir))
        except ValueError:
            file_name_for_url = str(json_path)
        docs += _make_json_documents(
            json_path=json_path,
            patent_id=patent_id,
            source_type="REPORT_PDF",
            document_title=f"AI 평가 보고서 JSON: {json_path.name}",
            public_file_base_url=public_file_base_url,
            meta=meta,
            file_name_for_url=file_name_for_url,
            max_chars=max_chars,
            overlap=overlap,
        )

    report_html_paths: List[Path] = []
    if reports_dir.exists():
        report_html_paths.extend(sorted(reports_dir.glob("*.html")))

    source_report_html = meta.get("report_html") or meta.get("source_report_html")
    if source_report_html:
        html_path = Path(str(source_report_html))
        if not html_path.is_absolute():
            html_path = patent_dir / html_path
        if html_path.exists() and html_path not in report_html_paths:
            report_html_paths.append(html_path)

    for html_path in report_html_paths:
        try:
            file_name_for_url = str(html_path.relative_to(patent_dir))
        except ValueError:
            file_name_for_url = str(html_path)
        docs += _make_html_documents(
            html_path=html_path,
            patent_id=patent_id,
            source_type="REPORT_PDF",
            document_title=f"최종 IP 가치 평가 보고서 HTML: {html_path.name}",
            public_file_base_url=public_file_base_url,
            meta=meta,
            file_name_for_url=file_name_for_url,
            max_chars=max_chars,
            overlap=overlap,
        )
        docs += extract_html_visual_documents(
            html_path=html_path,
            patent_dir=patent_dir,
            patent_id=patent_id,
            source_document_type="REPORT_PDF",
            public_file_base_url=public_file_base_url,
            file_name_for_url=file_name_for_url,
            meta=meta,
        )

    for rel_path, source_type, title in JSON_PATENT_DOCS:
        docs += _make_json_documents(
            json_path=patent_dir / rel_path,
            patent_id=patent_id,
            source_type=source_type,
            document_title=title,
            public_file_base_url=public_file_base_url,
            meta=meta,
            file_name_for_url=rel_path,
            max_chars=max_chars,
            overlap=overlap,
        )

    return docs


def _business_file_title(path: Path) -> str:
    title = path.stem.replace("-", " ").replace("_", " ").strip()
    return title or path.name


def _iter_business_files(business_dir: Path) -> Iterable[Path]:
    if not business_dir.exists():
        return []
    allowed = {".md", ".txt", ".json"}
    return (
        path
        for path in sorted(business_dir.rglob("*"))
        if path.is_file()
        and path.suffix.lower() in allowed
        and "index" not in path.relative_to(business_dir).parts
    )


def build_business_documents(
    business_dir: Path,
    public_file_base_url: str,
    max_chars: int = 1200,
    overlap: int = 150,
) -> List[Document]:
    docs: List[Document] = []
    for path in _iter_business_files(business_dir):
        if path.suffix.lower() == ".json":
            raw = _json_to_text(_read_json(path))
        else:
            raw = path.read_text(encoding="utf-8")

        rel_file = path.relative_to(business_dir).as_posix()
        title = _business_file_title(path)
        clean_title = re.sub(r"\s+", " ", title)

        for idx, chunk_text in enumerate(split_text(raw, max_chars=max_chars, overlap=overlap)):
            text_hash = sha1_text(chunk_text)
            chunk_id = f"BUSINESS:{rel_file}:c{idx}:{text_hash[:10]}"
            docs.append(
                Document(
                    page_content=chunk_text,
                    metadata={
                        "chunk_id": chunk_id,
                        "patent_id": None,
                        "source_type": "BUSINESS_DOC",
                        "page_no": None,
                        "section_title": clean_title,
                        "source_url": f"{public_file_base_url.rstrip('/')}/business/{rel_file}",
                        "file_name": rel_file,
                        "title": clean_title,
                        "text_hash": text_hash,
                    },
                )
            )
    return docs


def write_documents_jsonl(docs: List[Document], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(
                json.dumps(
                    {"page_content": doc.page_content, "metadata": doc.metadata},
                    ensure_ascii=False,
                )
                + "\n"
            )


def read_documents_jsonl(path: Path) -> List[Document]:
    docs: List[Document] = []
    if not path.exists():
        return docs
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        docs.append(Document(page_content=row["page_content"], metadata=row["metadata"]))
    return docs
