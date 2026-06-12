"""Parse global patent PDFs into Korean JSON files.

Global PDFs are mixed across US/EP/CN/JP formats and many are scanned image
PDFs.  This script therefore separates extraction, translation/structuring, and
final storage:

  parsing_data/global/*.pdf
  -> parsing_data/parsed/global/_cache/*.txt
  -> parsing_data/parsed/global/{identifier}/parsed.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any


SERVER_ROOT = Path(__file__).resolve().parents[1]
EVAL_SRC = SERVER_ROOT / "eval_logic" / "src"
if str(EVAL_SRC) not in sys.path:
    sys.path.insert(0, str(EVAL_SRC))

from core.env import load_runtime_env

load_runtime_env()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="parsing_data/global PDF를 OCR/번역하여 sample 구조 JSON으로 저장합니다."
    )
    parser.add_argument(
        "--input-dir",
        default=str(SERVER_ROOT / "parsing_data" / "global"),
        help="global PDF가 있는 디렉토리. 기본값: parsing_data/global",
    )
    parser.add_argument(
        "--output-dir",
        default=str(SERVER_ROOT / "parsing_data" / "parsed" / "global"),
        help="파싱 JSON을 저장할 디렉토리. 기본값: parsing_data/parsed/global",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_GLOBAL_PARSE_MODEL") or os.getenv("OPENAI_INTENT_MODEL") or "gpt-4.1-mini",
        help="번역/구조화에 사용할 OpenAI 모델.",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="파일명 stem 또는 PDF 파일명을 지정해 일부만 처리합니다. 여러 번 지정 가능.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="같은 identifier의 parsed.json이 이미 있으면 건너뜁니다.",
    )
    parser.add_argument(
        "--max-text-chars",
        type=int,
        default=55000,
        help="LLM에 보낼 원문 최대 글자 수. 기본값: 55000",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="LLM 번역 없이 원문 기반 휴리스틱 JSON만 생성합니다.",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(text: str, limit: int | None = None) -> str:
    text = text.replace("\x0c", "\n")
    lines: list[str] = []
    for line in text.splitlines():
        stripped = re.sub(r"\s+", " ", line).strip()
        if not stripped:
            continue
        if re.fullmatch(r"[-–—\s\d/]+", stripped):
            continue
        lines.append(stripped)
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if limit and len(cleaned) > limit:
        return cleaned[:limit].rstrip() + "\n[TRUNCATED]"
    return cleaned


def clean_inline(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip(" :：,;")


def extract_pdf_text(pdf_path: Path) -> tuple[str, dict[str, Any]]:
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        pages = len(pdf.pages)
        metadata = dict(pdf.metadata or {})
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    metadata["pages"] = pages
    return clean_text(text), metadata


def ocr_pdf(pdf_path: Path, cache_text: Path) -> str:
    if shutil.which("pdftoppm") is None:
        raise RuntimeError("pdftoppm을 찾을 수 없습니다.")
    if shutil.which("tesseract") is None:
        raise RuntimeError("tesseract를 찾을 수 없습니다.")

    with tempfile.TemporaryDirectory(prefix="global_patent_ocr_") as tmp:
        prefix = Path(tmp) / "page"
        subprocess.run(
            ["pdftoppm", "-r", "300", "-png", str(pdf_path), str(prefix)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        page_files = sorted(Path(tmp).glob("page-*.png"))
        if not page_files:
            raise RuntimeError("OCR용 페이지 이미지를 생성하지 못했습니다.")

        texts: list[str] = []
        lang = "eng+chi_sim+chi_tra+jpn+kor"
        for page_file in page_files:
            result = subprocess.run(
                ["tesseract", str(page_file), "stdout", "-l", lang, "--psm", "6"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if result.returncode != 0:
                result = subprocess.run(
                    ["tesseract", str(page_file), "stdout", "-l", lang],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            texts.append(result.stdout)

    text = clean_text("\n\n".join(texts))
    cache_text.write_text(text, encoding="utf-8")
    return text


def get_extracted_text(pdf_path: Path, cache_dir: Path) -> tuple[str, dict[str, Any]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_text = cache_dir / f"{pdf_path.stem}.txt"
    cache_meta = cache_dir / f"{pdf_path.stem}.extraction.json"
    if cache_text.exists() and cache_meta.exists():
        return cache_text.read_text(encoding="utf-8"), read_json(cache_meta)

    pdf_text, pdf_meta = extract_pdf_text(pdf_path)
    extraction_method = "pdf_text"
    text = pdf_text
    if len(pdf_text.strip()) < 500:
        extraction_method = "ocr"
        text = ocr_pdf(pdf_path, cache_text)
    else:
        cache_text.write_text(text, encoding="utf-8")

    info = {
        "source_pdf": str(pdf_path.resolve()),
        "extraction_method": extraction_method,
        "text_length": len(text),
        "pdf_metadata": pdf_meta,
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
    }
    write_json(cache_meta, info)
    return text, info


def detect_language(text: str, filename: str, identifier: str = "") -> str:
    upper_id = identifier.upper()
    if upper_id.startswith(("US", "EP")):
        return "en"
    if upper_id.startswith("CN"):
        return "zh"
    if upper_id.startswith("JP"):
        return "ja"
    latin_in_name = len(re.findall(r"[A-Za-z]", filename))
    if latin_in_name > 20:
        return "en"
    sample = f"{filename}\n{text[:4000]}"
    cjk = len(re.findall(r"[\u4e00-\u9fff]", sample))
    kana = len(re.findall(r"[\u3040-\u30ff]", sample))
    latin = len(re.findall(r"[A-Za-z]", sample))
    if kana > 20:
        return "ja"
    if cjk > max(30, latin // 4):
        return "zh"
    return "en"


def normalize_identifier(value: str) -> str:
    text = clean_inline(value).upper()
    text = text.replace(" ", "").replace("-", "")
    return text


def language_from_identifier(identifier: str, current: str) -> str:
    upper_id = identifier.upper()
    if upper_id.startswith(("US", "EP")):
        return "en"
    if upper_id.startswith(("CN", "TW")):
        return "zh"
    if upper_id.startswith("JP"):
        return "ja"
    return current


def identifier_from_sources(text: str, filename: str, metadata: dict[str, Any]) -> str:
    joined = "\n".join(
        [
            str(metadata.get("Title") or ""),
            filename,
            text[:8000],
        ]
    )
    patterns = [
        r"\bUS0*(\d{11})(A\d)\b",
        r"\bUS0*(\d{7,8})(B\d)\b",
        r"\bUS\s*(\d{4})[/-]?(\d{7})\s*(A\d)\b",
        r"\bUS\s*(\d{7,8})\s*(B\d)\b",
        r"\bEP\s*0*([\d\s]{7,})\s*(A\d|B\d)\b",
        r"\bCN\s*([\d\s]{8,12})\s*([ABU])\b",
        r"\bJP\s*([\d\s]{6,8})\s*(A|B\d)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, joined, re.IGNORECASE)
        if not match:
            continue
        groups = match.groups()
        if pattern.startswith(r"\bUS\s*(\d{4})"):
            return f"US{groups[0]}{groups[1]}{groups[2].upper()}"
        number = re.sub(r"\D", "", groups[0])
        suffix = groups[1].upper()
        prefix = pattern[2:4]
        return normalize_identifier(f"{prefix}{number}{suffix}")
    return normalize_identifier(Path(filename).stem)[:80]


def parse_date(value: str) -> str:
    text = clean_inline(value)
    if not text:
        return ""
    match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
    if match:
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    match = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text)
    if match:
        d, m, y = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    match = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", text)
    if match:
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    return text


def regex_fallback(text: str, filename: str, metadata: dict[str, Any]) -> dict[str, Any]:
    identifier = identifier_from_sources(text, filename, metadata)
    title = clean_inline(Path(filename).stem)
    title = re.sub(r"^\((공개전문|공고전문)\)", "", title).strip()
    abstract = ""
    title_patterns = [
        r"\(54\)\s*(?:Title|发明名称|発明の名称)?\s*(.+?)(?=\n\s*\(57\)|\n\s*Abstract|\n\s*摘要|\n\s*【?要約|$)",
        r"\(54\)\s*(.+)",
    ]
    for pattern in title_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            title = clean_text(match.group(1), limit=500)
            break
    abstract_patterns = [
        r"\(57\)\s*(?:Abstract|摘要|要約)?\s*(.+?)(?=\n\s*(?:Claims|权\s*利\s*要\s*求\s*书|【特許請求の範囲】|\(51\)|\Z))",
        r"\bAbstract\s*(.+?)(?=\n\s*(?:Claims|Description|BACKGROUND|\Z))",
        r"摘要\s*(.+?)(?=\n\s*权\s*利\s*要\s*求\s*书|\Z)",
    ]
    for pattern in abstract_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            abstract = clean_text(match.group(1), limit=3000)
            break
    return {
        "identifier": identifier,
        "registration_number": identifier if re.search(r"(B\d?|授权|登録)", text, re.IGNORECASE) else "",
        "publication_number": identifier if re.search(r"A\d?$", identifier) else "",
        "application_number": clean_inline((re.search(r"\(21\)\s*(?:Application number|申请号)?\s*([\w./-]+)", text) or ["", ""])[1]),
        "application_date": parse_date(clean_inline((re.search(r"\(22\)\s*(?:Date of filing|申请日)?\s*([\d./年月日 -]+)", text) or ["", ""])[1])),
        "publication_date": parse_date(clean_inline((re.search(r"\(43\)\s*(?:Date of publication|申请公布日|公開日)?\s*([\d./年月日 -]+)", text) or ["", ""])[1])),
        "registration_date": parse_date(clean_inline((re.search(r"\(45\)\s*(?:授权公告日|Date of publication|発行日)?\s*([\d./年月日 -]+)", text) or ["", ""])[1])),
        "assignee": [],
        "inventors": [],
        "agent": [],
        "examiner": "",
        "ipc": list(dict.fromkeys(re.findall(r"\b[A-H]\d{2}[A-Z]\s*\d+/\d+", text))),
        "cpc": [],
        "prior_art_cited": [],
        "title_original": title,
        "abstract_original": abstract,
    }


def build_prompt(text: str, fallback: dict[str, Any], language: str) -> str:
    return f"""
You parse patent gazettes. The source text may be OCR-noisy and written in English, Chinese, Japanese, or mixed languages.

Return ONLY a valid JSON object. Translate human-readable patent content into Korean.
Do not invent missing bibliographic values. If a value is not present, use an empty string or empty array.

Required JSON schema:
{{
  "identifier": "publication or grant identifier, e.g. US11483303B2, EP3907618A1, CN110770661B, JP6757846B2",
  "registration_number": "grant/registration number if present",
  "publication_number": "publication number if present",
  "application_number": "",
  "application_date": "YYYY-MM-DD or source date if uncertain",
  "publication_date": "YYYY-MM-DD or source date if uncertain",
  "registration_date": "YYYY-MM-DD or source date if uncertain",
  "notice_date": "YYYY-MM-DD or source date if uncertain",
  "assignee": ["Korean translated assignee names if translatable; otherwise original names"],
  "inventors": ["inventor names"],
  "agent": ["agent or representative names"],
  "examiner": "",
  "ipc": ["IPC codes"],
  "cpc": ["CPC codes"],
  "prior_art_cited": ["prior art publication numbers"],
  "title_ko": "Korean translated title",
  "abstract_ko": "Korean translated abstract",
  "claims": [
    {{
      "number": 1,
      "type": "독립항 or 종속항",
      "category": "방법 or 시스템 or 장치 or 매체 or 기타",
      "text_ko": "Korean translated full claim text",
      "depends_on": 1
    }}
  ],
  "deleted_claims": [2],
  "description": {{
    "description_text": "Korean translated description/specification text. Preserve paragraph meaning, but concise if source is very long.",
    "technical_field": "",
    "background_art": "",
    "problem_to_solve": "",
    "solution": "",
    "advantageous_effects": "",
    "implementation": ""
  }},
  "keywords": ["Korean technical keywords, max 10"],
  "brief_summary": {{
    "개요": "one Korean sentence",
    "핵심_내용": "one or two Korean sentences"
  }}
}}

Parsing hints:
- Prefer this fallback identifier if the text is unclear: {fallback.get("identifier", "")}
- Prefer this fallback title if no title is present: {fallback.get("title_original", "")}
- Source language estimate: {language}
- Claims must be individual claims where possible. Keep all claim numbers you can find.
- Translate claim text to Korean, but keep formulas, reference numerals, and patent numbers unchanged.

SOURCE TEXT:
```text
{text}
```
""".strip()


def select_prompt_text(text: str, max_chars: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= max_chars:
        return cleaned

    section_patterns = [
        r"\bClaims\b",
        r"权\s*利\s*要\s*求\s*书",
        r"【特許請求の範囲】",
        r"特許請求の範囲",
        r"請求項１",
    ]
    claim_start = -1
    for pattern in section_patterns:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if match:
            claim_start = match.start()
            break

    head_budget = min(14000, max_chars // 3)
    head = cleaned[:head_budget]
    if claim_start >= 0:
        claim_budget = max_chars - len(head) - 200
        claims = cleaned[claim_start:claim_start + claim_budget]
        return clean_text(f"{head}\n\n[CLAIMS SECTION PRIORITIZED]\n{claims}", limit=max_chars)
    return clean_text(cleaned, limit=max_chars)


def call_openai_structurer(text: str, fallback: dict[str, Any], language: str, model: str) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are a careful multilingual patent parser and Korean technical translator.",
            },
            {"role": "user", "content": build_prompt(text, fallback, language)},
        ],
        temperature=0.0,
        max_tokens=16000,
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)


def listify(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean_inline(item) for item in value if clean_inline(item)]
    text = clean_inline(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,;，、]\s*", text) if part.strip()]


def safe_int(value: Any) -> int | None:
    try:
        return int(str(value).strip())
    except Exception:
        return None


def infer_claim_category(text: str) -> str:
    if re.search(r"방법|단계|공정|프로세스", text):
        return "방법"
    if re.search(r"시스템|장치|서버|단말|모듈|부|유닛|프로세서", text):
        return "시스템"
    if re.search(r"매체|프로그램|컴퓨터", text):
        return "매체"
    return "기타"


def build_claims(parsed: dict[str, Any]) -> tuple[dict[str, Any], list[int], str]:
    claims: dict[str, Any] = {}
    raw_parts: list[str] = []
    deleted: list[int] = []
    for item in parsed.get("claims") or []:
        if not isinstance(item, dict):
            continue
        number = safe_int(item.get("number"))
        text = clean_text(str(item.get("text_ko") or item.get("text") or ""), limit=9000)
        if number is None:
            number = len(claims) + 1
        if not text or text == "삭제":
            deleted.append(number)
            continue
        claim: dict[str, Any] = {
            "type": clean_inline(item.get("type")) or ("종속항" if item.get("depends_on") else "독립항"),
            "category": clean_inline(item.get("category")) or infer_claim_category(text),
            "text": text,
        }
        depends_on = safe_int(item.get("depends_on"))
        if depends_on:
            claim["depends_on"] = depends_on
        claims[f"claim_{number}"] = claim
        raw_parts.append(f"청구항 {number} {text}")
    for item in parsed.get("deleted_claims") or []:
        number = safe_int(item)
        if number is not None and number not in deleted:
            deleted.append(number)
    return claims, sorted(deleted), clean_text("\n".join(raw_parts), limit=12000)


def build_description(parsed: dict[str, Any], abstract: str) -> dict[str, str]:
    desc = parsed.get("description") if isinstance(parsed.get("description"), dict) else {}
    description_text = clean_text(desc.get("description_text") or "", limit=20000)
    if not description_text:
        description_text = abstract
    return {
        "description_text": description_text,
        "technical_field": clean_text(desc.get("technical_field") or "", limit=2500),
        "background_art": clean_text(desc.get("background_art") or "", limit=3500),
        "problem_to_solve": clean_text(desc.get("problem_to_solve") or "", limit=2500),
        "solution": clean_text(desc.get("solution") or "", limit=3500),
        "advantageous_effects": clean_text(desc.get("advantageous_effects") or "", limit=2500),
        "implementation": clean_text(desc.get("implementation") or "", limit=6000),
    }


def description_summary(abstract: str, description: dict[str, str]) -> str:
    parts: list[str] = []
    if abstract:
        parts.append(f"[요약] {abstract}")
    for key, label in [
        ("technical_field", "기술분야"),
        ("problem_to_solve", "해결과제"),
        ("solution", "해결수단"),
        ("advantageous_effects", "발명의 효과"),
    ]:
        if description.get(key):
            parts.append(f"[{label}] {description[key]}")
    return clean_text("\n".join(parts), limit=6000)


def build_output(
    pdf_path: Path,
    text: str,
    extraction_info: dict[str, Any],
    fallback: dict[str, Any],
    parsed: dict[str, Any],
    language: str,
    translation_status: str,
) -> tuple[str, dict[str, Any]]:
    identifier = normalize_identifier(parsed.get("identifier") or fallback.get("identifier") or pdf_path.stem)
    language = language_from_identifier(identifier, language)
    registration_number = clean_inline(parsed.get("registration_number") or fallback.get("registration_number"))
    publication_number = clean_inline(parsed.get("publication_number") or fallback.get("publication_number"))
    if not registration_number and re.search(r"B\d?$", identifier):
        registration_number = identifier
    if not publication_number and re.search(r"A\d?$", identifier):
        publication_number = identifier

    title = clean_text(parsed.get("title_ko") or fallback.get("title_original") or pdf_path.stem, limit=500)
    abstract = clean_text(parsed.get("abstract_ko") or fallback.get("abstract_original") or "", limit=4000)
    claims_text, deleted_claims, claims_raw_text = build_claims(parsed)
    description = build_description(parsed, abstract)
    keywords = listify(parsed.get("keywords"))[:10]
    brief = parsed.get("brief_summary") if isinstance(parsed.get("brief_summary"), dict) else {}
    brief_summary = {
        "개요": clean_inline(brief.get("개요")) or title,
        "핵심_내용": clean_text(brief.get("핵심_내용") or abstract, limit=300),
    }

    raw_meta = {
        "등록번호": registration_number or "-",
        "출원번호": clean_inline(parsed.get("application_number") or fallback.get("application_number")) or "-",
        "출원일자": parse_date(clean_inline(parsed.get("application_date") or fallback.get("application_date"))) or "-",
        "심사청구일자": "-",
        "공개번호": publication_number or "-",
        "공개일자": parse_date(clean_inline(parsed.get("publication_date") or fallback.get("publication_date"))) or "-",
        "등록일자": parse_date(clean_inline(parsed.get("registration_date") or fallback.get("registration_date"))) or "-",
        "공고일자": parse_date(clean_inline(parsed.get("notice_date") or parsed.get("registration_date") or fallback.get("registration_date"))) or "-",
        "특허권자": listify(parsed.get("assignee")),
        "발명자": listify(parsed.get("inventors")),
        "대리인": listify(parsed.get("agent")),
        "심사관": clean_inline(parsed.get("examiner")) or "-",
        "국제특허분류(IPC)": listify(parsed.get("ipc") or fallback.get("ipc")),
        "CPC특허분류": listify(parsed.get("cpc") or fallback.get("cpc")),
        "선행기술조사문헌": listify(parsed.get("prior_art_cited")),
        "청구항_수": str(len(claims_text)) if claims_text else "-",
        "발명의_명칭": title,
        "요약": abstract or "-",
        "_global_parser": True,
    }

    normalized = {
        "patent_id": registration_number or publication_number or identifier,
        "meta": {
            "title": title,
            "registration_number": registration_number,
            "registration_date": parse_date(raw_meta["등록일자"]) if raw_meta["등록일자"] != "-" else "",
            "application_number": raw_meta["출원번호"] if raw_meta["출원번호"] != "-" else "",
            "application_date": parse_date(raw_meta["출원일자"]) if raw_meta["출원일자"] != "-" else "",
            "publication_number": publication_number,
            "publication_date": parse_date(raw_meta["공개일자"]) if raw_meta["공개일자"] != "-" else "",
            "legal_status": "등록" if registration_number else "공개",
            "assignee": raw_meta["특허권자"],
            "inventors": raw_meta["발명자"],
            "agent": raw_meta["대리인"],
            "examiner": "" if raw_meta["심사관"] == "-" else raw_meta["심사관"],
            "ipc": raw_meta["국제특허분류(IPC)"],
            "cpc": raw_meta["CPC특허분류"],
            "prior_art_cited": raw_meta["선행기술조사문헌"],
            "total_claims": len(claims_text) if claims_text else None,
            "deleted_claims": deleted_claims,
            "keywords": keywords,
        },
        "description_summary": description_summary(abstract, description),
        "claims_text": claims_text,
        "specification": {
            "claims_raw_text": claims_raw_text,
            "description_text": description["description_text"],
            "technical_field": description["technical_field"],
            "background_art": description["background_art"],
            "problem_to_solve": description["problem_to_solve"],
            "solution": description["solution"],
            "advantageous_effects": description["advantageous_effects"],
            "implementation": description["implementation"],
        },
        "legal": {
            "registration_date": parse_date(raw_meta["등록일자"]) if raw_meta["등록일자"] != "-" else "",
            "notice_date": parse_date(raw_meta["공고일자"]) if raw_meta["공고일자"] != "-" else "",
            "examination_request_date": "",
        },
        "source_pdf": pdf_path.name,
        "brief_summary": brief_summary,
    }
    normalized["specification"] = {
        key: value for key, value in normalized["specification"].items() if value not in ("", [], {}, None)
    }

    output = {
        "source_pdf": str(pdf_path.resolve()),
        "raw": {
            "filename": pdf_path.name,
            "sys_meta": extraction_info.get("pdf_metadata") or {},
            "meta": raw_meta,
            "claims": {
                "claims_text": claims_text,
                "deleted_claims": deleted_claims,
                "claims_raw_text": claims_raw_text,
            },
            "description": description,
            "original_language": language,
            "extraction_method": extraction_info.get("extraction_method"),
            "translation_status": translation_status,
            "original_text": clean_text(text, limit=12000),
        },
        "keywords": keywords,
        "brief_summary": brief_summary,
        "normalized_patent": normalized,
    }
    return identifier, output


def parse_one(pdf_path: Path, output_dir: Path, cache_dir: Path, model: str, max_text_chars: int, no_llm: bool) -> dict[str, Any]:
    started = time.time()
    text, extraction_info = get_extracted_text(pdf_path, cache_dir)
    fallback = regex_fallback(text, pdf_path.name, extraction_info.get("pdf_metadata") or {})
    language = detect_language(text, pdf_path.name, fallback.get("identifier", ""))
    llm_cache = cache_dir / f"{pdf_path.stem}.structured.json"
    translation_status = "heuristic"

    if llm_cache.exists():
        structured = read_json(llm_cache)
        translation_status = structured.get("_translation_status", "translated")
    elif no_llm:
        structured = {
            "identifier": fallback.get("identifier"),
            "title_ko": fallback.get("title_original"),
            "abstract_ko": fallback.get("abstract_original"),
            "claims": [],
            "description": {"description_text": fallback.get("abstract_original", "")},
            "keywords": [],
            "brief_summary": {"개요": fallback.get("title_original", ""), "핵심_내용": fallback.get("abstract_original", "")},
            "_translation_status": "not_requested",
        }
        write_json(llm_cache, structured)
        translation_status = "not_requested"
    else:
        prompt_text = select_prompt_text(text, max_text_chars)
        structured = call_openai_structurer(prompt_text, fallback, language, model)
        structured["_translation_status"] = "translated"
        write_json(llm_cache, structured)
        translation_status = "translated"

    identifier, output = build_output(pdf_path, text, extraction_info, fallback, structured, language, translation_status)
    dest = output_dir / identifier / "parsed.json"
    output["batch_metadata"] = {
        "source_dir": "parsing_data/global",
        "parsed_at": datetime.now().isoformat(timespec="seconds"),
        "parser": "scripts/parse_global_patents.py",
        "model": model if not no_llm else "",
    }
    write_json(dest, output)

    return {
        "identifier": identifier,
        "pdf": str(pdf_path),
        "json": str(dest),
        "language": output["raw"]["original_language"],
        "extraction_method": extraction_info.get("extraction_method"),
        "translation_status": translation_status,
        "claim_count": len(output["raw"]["claims"]["claims_text"]),
        "title": output["raw"]["meta"]["발명의_명칭"],
        "elapsed_seconds": round(time.time() - started, 2),
    }


def find_targets(input_dir: Path, only: list[str]) -> list[Path]:
    if not input_dir.exists():
        raise FileNotFoundError(f"input-dir를 찾을 수 없습니다: {input_dir}")
    allow = set(only)
    pdfs = sorted(input_dir.glob("*.pdf"))
    if allow:
        pdfs = [pdf for pdf in pdfs if pdf.name in allow or pdf.stem in allow]
    if not pdfs:
        raise FileNotFoundError(f"처리할 PDF가 없습니다: {input_dir}")
    return pdfs


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    cache_dir = output_dir / "_cache"
    targets = find_targets(input_dir, args.only)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    print(f"input: {input_dir}", flush=True)
    print(f"output: {output_dir}", flush=True)
    print(f"targets: {len(targets)}", flush=True)
    print(f"model: {args.model}", flush=True)

    for index, pdf_path in enumerate(targets, 1):
        print(f"[{index}/{len(targets)}] {pdf_path.name}", flush=True)
        try:
            text, extraction_info = get_extracted_text(pdf_path, cache_dir)
            fallback = regex_fallback(text, pdf_path.name, extraction_info.get("pdf_metadata") or {})
            existing_id = fallback.get("identifier") or normalize_identifier(pdf_path.stem)[:80]
            if args.skip_existing and (output_dir / existing_id / "parsed.json").exists():
                print(f"  skip-existing {existing_id}", flush=True)
                continue
            summary = parse_one(pdf_path, output_dir, cache_dir, args.model, args.max_text_chars, args.no_llm)
            results.append(summary)
            print(
                f"  ok id={summary['identifier']} lang={summary['language']} "
                f"extract={summary['extraction_method']} claims={summary['claim_count']} "
                f"elapsed={summary['elapsed_seconds']}s",
                flush=True,
            )
        except Exception as exc:
            failure = {"pdf": str(pdf_path), "error": str(exc)}
            failures.append(failure)
            print(f"  failed: {exc}", flush=True)

    summary_payload = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "target_count": len(targets),
        "success_count": len(results),
        "failed_count": len(failures),
        "results": results,
        "failures": failures,
    }
    write_json(output_dir / "batch_summary.json", summary_payload)
    print(f"summary: {output_dir / 'batch_summary.json'}", flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
