"""Parse legacy Korean patent PDFs under parsing_data/old into JSON.

The legacy PDFs use older Korean gazette labels such as ``특허청구의 범위``
and ``발명의 상세한 설명``.  Those labels are close to, but not quite the same
as, the current parser's expected layout, so this script keeps the parsing path
separate and writes JSON matching parsing_data/parsing_sample.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


SERVER_ROOT = Path(__file__).resolve().parents[1]
EVAL_SRC = SERVER_ROOT / "eval_logic" / "src"
if str(EVAL_SRC) not in sys.path:
    sys.path.insert(0, str(EVAL_SRC))

from document_processing import patent_pdf_extractor as base_parser
from services.evidence_collection_service import PatentMetadataExtractionService


DATE_RE = r"\d{4}년\s*\d{1,2}월\s*\d{1,2}일"
CODE_RE = re.compile(r"[A-Z]\d{2}[A-Z]\s*[\d./]+[A-Z0-9,/\s.-]*\(\d{4}(?:\.\d+)?\)")
KOREAN_NAME_RE = re.compile(r"^[가-힣]{2,5}$")
NAME_STOPWORDS = {
    "출원번호",
    "출원일자",
    "공개번호",
    "공개일자",
    "등록번호",
    "등록일자",
    "공고일자",
    "심사관",
    "심사관에",
    "의하여",
    "인용된",
    "문헌",
    "대리인",
    "발명자",
    "특허권자",
    "등록특허",
    "청구범위",
}
ADDRESS_RE = re.compile(
    r"특별시|광역시|특별자치|경기도|충청|전라|경상|강원|제주|"
    r"시\s|구\s|동\s|읍\s|면\s|로\s|길\s|번길|아파트|타워|빌딩|"
    r"\d+[동호]\b|\d+층"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="parsing_data/old PDF를 old 포맷 전용 로직으로 JSON 파싱합니다."
    )
    parser.add_argument(
        "--input-dir",
        default=str(SERVER_ROOT / "parsing_data" / "old"),
        help="old PDF가 있는 디렉토리. 기본값: parsing_data/old",
    )
    parser.add_argument(
        "--output-dir",
        default=str(SERVER_ROOT / "parsing_data" / "parsed" / "old"),
        help="파싱 JSON을 저장할 디렉토리. 기본값: parsing_data/parsed/old",
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
        help="같은 이름의 JSON이 이미 있으면 건너뜁니다.",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clean_text(text: str, limit: int | None = None) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = re.sub(r"\s+", " ", line).strip()
        if not stripped:
            continue
        if re.match(r"^-?\s*\d+\s*-?$", stripped):
            continue
        if re.match(r"^등록특허\s+\d{2}-\d+", stripped):
            continue
        lines.append(stripped)
    cleaned = re.sub(r"\s+", " ", "\n".join(lines)).strip()
    if limit and len(cleaned) > limit:
        return cleaned[:limit].rstrip() + "..."
    return cleaned


def find_first(text: str, pattern: str, default: str = "-") -> str:
    match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    if not match:
        return default
    return clean_inline(match.group(1))


def clean_inline(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" :：")


def extract_text_by_pages(pdf_path: Path) -> tuple[list[str], str]:
    import pdfplumber

    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    return pages, "\n".join(pages)


def section_after(text: str, starts: list[str], ends: list[str]) -> str:
    start_match = None
    for pattern in starts:
        match = re.search(pattern, text, re.MULTILINE)
        if match and (start_match is None or match.start() < start_match.start()):
            start_match = match
    if not start_match:
        return ""

    start = start_match.end()
    tail = text[start:]
    end = len(tail)
    for pattern in ends:
        match = re.search(pattern, tail, re.MULTILINE)
        if match:
            end = min(end, match.start())
    return tail[:end]


def extract_title(full_text: str, fallback: str) -> str:
    title = find_first(
        full_text,
        r"\(54\)\s*(?:발명의\s*명칭\s*)?(.+?)(?=\n\s*\(57\)|\n\s*요\s*약|\n\s*대\s*표\s*도|\Z)",
        default=fallback,
    )
    return title if title and title != "-" else fallback


def extract_abstract(full_text: str, fallback: str) -> str:
    raw = find_first(
        full_text,
        r"\(57\)\s*요\s*약\s*(.+?)(?=\n\s*대\s*표\s*도|\n\s*대표도|\n\s*-\s*1\s*-|\n등록특허\s+\d{2}-|\n특허청구의\s*범위|\Z)",
        default=fallback,
    )
    if not raw or raw == "-":
        return fallback
    raw = re.sub(r"\(72\)\s*발명자.*", "", raw, flags=re.DOTALL)
    return clean_text(raw, limit=4000) or fallback


def extract_assignee(first_pages_text: str, fallback: str) -> str:
    block = section_after(
        first_pages_text,
        [r"\(73\)\s*특허권자"],
        [r"\(72\)\s*발명자", r"\(74\)\s*대리인", r"\(21\)\s*출원번호"],
    )
    candidates = re.findall(r"([가-힣A-Za-z0-9·.\s&()-]+?(?:주식회사|회사|법인|Corporation|Inc\.?|Ltd\.?))", block)
    for candidate in candidates:
        cleaned = clean_inline(candidate)
        cleaned = re.sub(r"^.*?([가-힣A-Za-z0-9·.&()-]+(?:주식회사|회사|법인|Corporation|Inc\.?|Ltd\.?))$", r"\1", cleaned)
        if cleaned and cleaned not in {"주식회사", "회사", "법인"} and not CODE_RE.search(cleaned):
            return cleaned
    return fallback


def extract_names_from_block(block: str) -> list[str]:
    names: list[str] = []
    for line in block.splitlines():
        cleaned = clean_inline(line)
        if not cleaned or ADDRESS_RE.search(cleaned):
            continue
        for token in re.split(r"[,，、\s]+", cleaned):
            if KOREAN_NAME_RE.match(token) and token not in NAME_STOPWORDS and token not in names:
                names.append(token)
    return names


def merge_people(primary: list[str], fallback: list[str]) -> list[str]:
    result: list[str] = []
    for name in [*primary, *fallback]:
        if name and name != "-" and name not in result:
            result.append(name)
    return result


def extract_people(first_pages_text: str, fallback_meta: dict[str, Any]) -> tuple[list[str], list[str]]:
    inventor_block = section_after(
        first_pages_text,
        [r"\(72\)\s*발명자"],
        [r"\(74\)\s*대리인", r"\(54\)", r"특허청구의\s*범위", r"청구항\s*1"],
    )
    agent_block = section_after(
        first_pages_text,
        [r"\(74\)\s*대리인"],
        [r"\(54\)", r"전체\s*청구항", r"특허청구의\s*범위", r"청구항\s*1"],
    )
    inventors = merge_people(fallback_meta.get("발명자") or [], extract_names_from_block(inventor_block))
    agents = merge_people(fallback_meta.get("대리인") or [], extract_names_from_block(agent_block))
    return inventors, agents


def extract_classifications(first_pages_text: str, fallback: list[str]) -> list[str]:
    block = section_after(
        first_pages_text,
        [r"\(51\).*?(?:Int\.\s*Cl\.|국제특허분류)?"],
        [r"\(21\)\s*출원번호", r"\(73\)\s*특허권자", r"\(72\)\s*발명자"],
    )
    codes = list(dict.fromkeys(code.strip() for code in CODE_RE.findall(block or first_pages_text[:2500])))
    return codes or fallback


def extract_prior_arts(first_pages_text: str, fallback: list[str]) -> list[str]:
    block = section_after(
        first_pages_text,
        [r"\(56\)\s*선행기술조사문헌"],
        [r"\(74\)\s*대리인", r"전체\s*청구항", r"\(54\)", r"\(57\)"],
    )
    found = re.findall(r"\b(?:KR|JP|US|EP)?\d{7,}[A-Z0-9 -]*\b", block)
    cleaned = [clean_inline(item).rstrip("*") for item in found]
    return list(dict.fromkeys(cleaned)) or fallback


def build_meta(full_text: str, first_pages_text: str, fallback_meta: dict[str, Any]) -> dict[str, Any]:
    inventors, agents = extract_people(first_pages_text, fallback_meta)
    title = extract_title(full_text, fallback_meta.get("발명의_명칭", "-"))
    abstract = extract_abstract(full_text, fallback_meta.get("요약", "-"))
    return {
        "등록번호": find_first(
            full_text,
            r"\(11\)\s*등록번호\s+([\d-]+)",
            find_first(full_text, r"등록특허\s+([\d-]+)", fallback_meta.get("등록번호", "-")),
        ),
        "출원번호": find_first(full_text, r"\(21\)\s*출원번호\s+([\d-]+)", fallback_meta.get("출원번호", "-")),
        "출원일자": find_first(full_text, rf"\(22\)\s*출원일자\s+({DATE_RE})", fallback_meta.get("출원일자", "-")),
        "심사청구일자": find_first(full_text, rf"심사청구일자\s+({DATE_RE})", fallback_meta.get("심사청구일자", "-")),
        "공개번호": find_first(full_text, r"\(65\)\s*공개번호\s+([\d-]+)", fallback_meta.get("공개번호", "-")),
        "공개일자": find_first(full_text, rf"\(43\)\s*공개일자\s+({DATE_RE})", fallback_meta.get("공개일자", "-")),
        "등록일자": find_first(full_text, rf"\(24\)\s*등록일자\s+({DATE_RE})", fallback_meta.get("등록일자", "-")),
        "공고일자": find_first(full_text, rf"\(45\)\s*공고일자\s+({DATE_RE})", fallback_meta.get("공고일자", "-")),
        "특허권자": extract_assignee(first_pages_text, fallback_meta.get("특허권자", "-")),
        "발명자": inventors,
        "대리인": agents,
        "심사관": find_first(full_text, r"심사관\s*[:：]\s*([가-힣A-Za-z]+)", fallback_meta.get("심사관", "-")),
        "국제특허분류(IPC)": extract_classifications(first_pages_text, fallback_meta.get("국제특허분류(IPC)") or []),
        "CPC특허분류": fallback_meta.get("CPC특허분류") or [],
        "선행기술조사문헌": extract_prior_arts(first_pages_text, fallback_meta.get("선행기술조사문헌") or []),
        "청구항_수": find_first(full_text, r"전체\s*청구항\s*수\s*:\s*총\s*(\d+)\s*항", fallback_meta.get("청구항_수", "-")),
        "발명의_명칭": title,
        "요약": abstract,
        "_legacy_old_parser": True,
    }


def infer_claim_category(text: str) -> str:
    if re.search(r"방법|단계|과정|공정", text):
        return "방법"
    if re.search(r"시스템|장치|서버|단말|모듈|부|수단", text):
        return "시스템"
    if re.search(r"기록\s*매체|저장\s*매체|프로그램|컴퓨터", text):
        return "매체"
    return "기타"


def claim_dependency(text: str) -> int | None:
    for pattern in [r"제\s*(\d+)\s*항에\s*있어서", r"청구항\s*(\d+)\s*에\s*있어서"]:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def parse_claims(full_text: str) -> dict[str, Any]:
    section = section_after(
        full_text,
        [r"^\s*특허청구의\s*범위\s*$", r"^\s*청\s*구\s*범\s*위\s*$", r"^\s*청구범위\s*$"],
        [r"^\s*명\s*세\s*서\s*$", r"^\s*발명의\s*상세한\s*설명\s*$", r"^\s*발명의\s*설명\s*$"],
    )
    if not section:
        return {"claims_text": {}, "deleted_claims": [], "claims_raw_text": ""}

    matches = list(re.finditer(r"^\s*청구항\s*(\d+)\s*$", section, re.MULTILINE))
    claims: dict[str, dict[str, Any]] = {}
    deleted_claims: list[int] = []

    for index, match in enumerate(matches):
        claim_no = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        claim_text = clean_text(section[start:end], limit=9000).strip(" .:：")
        if not claim_text or re.fullmatch(r"삭제", claim_text):
            deleted_claims.append(claim_no)
            continue
        depends_on = claim_dependency(claim_text)
        item: dict[str, Any] = {
            "type": "종속항" if depends_on else "독립항",
            "category": infer_claim_category(claim_text),
            "text": claim_text,
        }
        if depends_on:
            item["depends_on"] = depends_on
        claims[f"claim_{claim_no}"] = item

    return {
        "claims_text": claims,
        "deleted_claims": deleted_claims,
        "claims_raw_text": clean_text(section, limit=12000),
    }


def parse_description(full_text: str) -> dict[str, str]:
    description = section_after(
        full_text,
        [r"^\s*명\s*세\s*서\s*$", r"^\s*발명의\s*상세한\s*설명\s*$", r"^\s*발명의\s*설명\s*$"],
        [r"^\s*도면의\s*간단한\s*설명\s*$", r"^\s*도\s*면\s*$"],
    )
    if not description:
        description = full_text
    end_labels = [
        r"^\s*발명의\s*목적\s*$",
        r"^\s*발명이\s*속하는\s*기술.*$",
        r"^\s*발명이\s*이루고자\s*하는\s*기술적\s*과제\s*$",
        r"^\s*발명의\s*구성\s*및\s*작용\s*$",
        r"^\s*발명의\s*효과\s*$",
        r"^\s*발명을\s*실시하기\s*위한\s*구체적인\s*내용\s*$",
        r"^\s*부호의\s*설명\s*$",
    ]
    technical_field = section_after(
        description,
        [r"^\s*발명이\s*속하는\s*기술.*$", r"^\s*기\s*술\s*분\s*야\s*$"],
        end_labels,
    )
    problem = section_after(
        description,
        [r"^\s*발명이\s*이루고자\s*하는\s*기술적\s*과제\s*$", r"^\s*해결하려는\s*과제\s*$"],
        end_labels,
    )
    implementation = section_after(
        description,
        [r"^\s*발명의\s*구성\s*및\s*작용\s*$", r"^\s*발명을\s*실시하기\s*위한\s*구체적인\s*내용\s*$"],
        end_labels,
    )
    effects = section_after(
        description,
        [r"^\s*발명의\s*효과\s*$"],
        end_labels,
    )
    return {
        "description_text": clean_text(description, limit=20000),
        "technical_field": clean_text(technical_field, limit=2500),
        "background_art": "",
        "problem_to_solve": clean_text(problem, limit=2500),
        "solution": clean_text(implementation, limit=3500),
        "advantageous_effects": clean_text(effects, limit=2500),
        "implementation": clean_text(implementation, limit=6000),
    }


def heuristic_keywords(title: str, abstract: str, limit: int = 10) -> list[str]:
    source = f"{title} {abstract}"
    tokens = re.findall(r"[가-힣A-Za-z0-9]{2,}", source)
    stopwords = {
        "본", "발명", "상기", "대한", "하는", "있다", "있어서", "그리고", "또는",
        "방법", "시스템", "장치", "제공", "단계", "특징", "포함", "따른",
    }
    result: list[str] = []
    for token in tokens:
        if token in stopwords or token.isdigit():
            continue
        if token not in result:
            result.append(token)
        if len(result) >= limit:
            break
    return result


def parse_old_pdf(pdf_path: Path, normalizer: PatentMetadataExtractionService) -> dict[str, Any]:
    pages_text, full_text = extract_text_by_pages(pdf_path)
    pages_words = base_parser.extract_page_words(pdf_path)
    col_x, detected = base_parser.detect_column_split(pages_words[0] if pages_words else [])
    fallback_meta = base_parser.parse_fields(pages_words, col_x) if pages_words else {}
    if fallback_meta.get("발명의_명칭") in (None, "", "-"):
        fallback_meta["발명의_명칭"] = pdf_path.stem

    first_pages_text = "\n".join(pages_text[:3])
    meta = build_meta(full_text, first_pages_text, fallback_meta)
    meta["_col_x_detected"] = detected

    raw_result = {
        "filename": pdf_path.name,
        "sys_meta": base_parser.extract_pdf_sys_meta(pdf_path),
        "meta": meta,
        "claims": parse_claims(full_text),
        "description": parse_description(full_text),
    }
    title = str(meta.get("발명의_명칭") or "")
    abstract = str(meta.get("요약") or "")
    keywords = heuristic_keywords(title, abstract)
    brief_summary = base_parser.make_brief_summary(title, abstract)
    normalized = normalizer._normalize(meta, raw_result, keywords, brief_summary)
    return {
        "source_pdf": str(pdf_path.resolve()),
        "raw": raw_result,
        "keywords": keywords,
        "brief_summary": brief_summary,
        "normalized_patent": normalized,
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


def output_path_for(output_dir: Path, pdf_path: Path) -> Path:
    return output_dir / f"{pdf_path.stem}.json"


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    targets = find_targets(input_dir, args.only)
    normalizer = PatentMetadataExtractionService()
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    print(f"input: {input_dir}")
    print(f"output: {output_dir}")
    print(f"targets: {len(targets)}")

    for index, pdf_path in enumerate(targets, 1):
        started = time.time()
        json_path = output_path_for(output_dir, pdf_path)
        if args.skip_existing and json_path.exists():
            print(f"[{index}/{len(targets)}] {pdf_path.name} skip-existing")
            continue
        print(f"[{index}/{len(targets)}] {pdf_path.name}")
        try:
            parsed = parse_old_pdf(pdf_path, normalizer)
            parsed["batch_metadata"] = {
                "source_dir": "parsing_data/old",
                "parsed_at": datetime.now().isoformat(timespec="seconds"),
                "parser": "scripts/parse_old_patents.py",
            }
            write_json(json_path, parsed)
            claim_count = len(parsed["raw"].get("claims", {}).get("claims_text", {}))
            title = parsed["raw"].get("meta", {}).get("발명의_명칭")
            elapsed = round(time.time() - started, 2)
            successes.append(
                {
                    "pdf": str(pdf_path),
                    "json": str(json_path),
                    "title": title,
                    "claim_count": claim_count,
                    "elapsed_seconds": elapsed,
                }
            )
            print(f"  ok claims={claim_count} elapsed={elapsed}s")
        except Exception as exc:
            elapsed = round(time.time() - started, 2)
            failures.append({"pdf": str(pdf_path), "error": str(exc), "elapsed_seconds": elapsed})
            print(f"  failed: {exc}")

    summary = {
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "target_count": len(targets),
        "success_count": len(successes),
        "failed_count": len(failures),
        "results": successes,
        "failures": failures,
    }
    summary_path = output_dir / "batch_summary.json"
    write_json(summary_path, summary)
    print(f"summary: {summary_path}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
