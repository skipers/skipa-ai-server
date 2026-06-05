import os
import re
import sys
import json
import textwrap
import warnings
from pathlib import Path
from collections import defaultdict
from dotenv import load_dotenv
import pdfplumber
import pypdf
from wcwidth import wcswidth
from core.paths import SAMPLE_PATENT_DOCUMENT_DIR

load_dotenv()

PATENT_DIR = SAMPLE_PATENT_DOCUMENT_DIR

# ── 정규식 상수 ────────────────────────────────────────────────────────────
KOREAN_NAME = re.compile(r"^[가-힣]{2,5}$")
CODE_RE     = re.compile(r"[A-Z]\d{2}[A-Z]\s+[\d./]+\s*\(\d{4}(?:\.\d+)?\)")
SECTION_RE  = re.compile(r"^\(\d{2,3}\)")

# 주소 행 판별 — 타워/빌딩은 회사명과 겹칠 수 있어 제외; 강한 행정구역 단위만 사용
ADDR_RE = re.compile(
    r"특별시|광역시|특별자치|경기도|충청|전라|경상|강원|제주"
    r"|\d+[동호]\b"          # 101동, 1205호
    r"|번길|\d+층"            # 도로명+층
    r"|성남시|종로구|서린동"  # 특수 케이스 (SK 본사 주소 조각)
)

# 요약 추출 시 제거할 잡음 행
JUNK_LINE = re.compile(
    r"^[-\s\d]+$"
    r"|^등록특허"
    r"|^대\s*표\s*도"
    r"|^-\s*도\d"
    r"|^\(뒷면에"
    r"|^\(\d{2,3}\)\s*$"
)


# ── 출력 유틸 (한글 폭 보정) ──────────────────────────────────────────────
def _pad(text: str, width: int) -> str:
    """wcswidth 기준으로 display width를 맞춰 공백 패딩을 추가한다."""
    dw = wcswidth(text)
    if dw < 0:          # 제어문자 등 계산 불가 시 len() fallback
        dw = len(text)
    return text + " " * max(0, width - dw)


# ── PDF 유틸 ──────────────────────────────────────────────────────────────
def _words_to_rows(
    words: list[dict], x_min: float = 0, x_max: float = 9999
) -> list[list[dict]]:
    filtered = [w for w in words if x_min <= w["x0"] < x_max]
    row_map: dict[int, list[dict]] = defaultdict(list)
    for w in filtered:
        row_map[round(w["top"])].append(w)
    return [sorted(v, key=lambda w: w["x0"]) for _, v in sorted(row_map.items())]


def _row_text(row: list[dict]) -> str:
    return " ".join(w["text"] for w in row)


def _find(text: str, pattern: str, default: str = "-") -> str:
    m = re.search(pattern, text, re.DOTALL)
    return m.group(1).strip() if m else default


def extract_pdf_sys_meta(pdf_path: Path) -> dict:
    with open(pdf_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        result = {"pages": len(reader.pages)}
        for k, v in (reader.metadata or {}).items():
            result[k.lstrip("/")] = str(v)
    return result


def extract_page_words(pdf_path: Path) -> list[list[dict]]:
    """페이지별 단어+좌표 반환. 빈 페이지·텍스트 없는 페이지는 빈 리스트로 처리."""
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_words() or [] for page in pdf.pages]


def extract_full_text(pages_words: list[list[dict]]) -> str:
    return "\n".join(
        "\n".join(_row_text(r) for r in _words_to_rows(words))
        for words in pages_words
    )


# ── 컬럼 분할 자동 감지 ───────────────────────────────────────────────────
def detect_column_split(page_words: list[dict]) -> tuple[float, bool]:
    """
    오른쪽 컬럼 마커 (73)/(72)/(74)의 x0 좌표로 컬럼 경계를 추정한다.
    반환: (col_x, detected) — detected=False 이면 기본값 300.0 사용.
    """
    RIGHT_MARKERS = re.compile(r"\(7[234]\)")
    xs = []
    row_map: dict[int, list[dict]] = defaultdict(list)
    for w in page_words:
        row_map[round(w["top"])].append(w)
    for row in row_map.values():
        text = _row_text(sorted(row, key=lambda w: w["x0"]))
        if RIGHT_MARKERS.search(text):
            xs.append(min(w["x0"] for w in row))
    if xs:
        return min(xs) - 5, True
    return 300.0, False


# ── 필드 파싱 ─────────────────────────────────────────────────────────────
def _is_address(text: str) -> bool:
    return bool(ADDR_RE.search(text))


# 건물명 단독 행 판별 — 이름과 혼동되는 케이스 방지
BUILDING_SUFFIX = re.compile(r"타워$|빌딩$|아파트$|빌라$|센터$|플라자$")


def _korean_names_from(text: str, seen: list[str]) -> list[str]:
    result = []
    for token in re.split(r"[,，、\s]+", text):
        token = token.strip()
        if KOREAN_NAME.match(token) and token not in seen and token not in result:
            result.append(token)
    return result


def _extract_name_from_row(text: str) -> str | None:
    """
    단독 이름 행과 '홍길동 서울특별시...' 처럼 이름+주소가 한 줄인 경우를 처리.
    건물명(이유타워 등) 은 BUILDING_SUFFIX 로 걸러낸다.
    """
    words_ = text.split()
    if not words_:
        return None
    first = words_[0]
    if not KOREAN_NAME.match(first):
        return None
    if len(words_) == 1:
        # 단독 단어: 주소 패턴이거나 건물명 접미사면 제외
        if _is_address(text) or BUILDING_SUFFIX.search(text):
            return None
        return first
    # 이름 + 주소가 같은 줄: 나머지가 주소일 때만 수집
    rest = " ".join(words_[1:])
    if _is_address(rest):
        return first
    return None


def parse_fields(pages_words: list[list[dict]], col_x: float) -> dict:
    # ── 왼쪽 컬럼 텍스트 ──
    left_all = "\n".join(
        _row_text(r)
        for words in pages_words
        for r in _words_to_rows(words, x_max=col_x)
    )
    left_p12 = "\n".join(
        _row_text(r)
        for words in pages_words[:2]
        for r in _words_to_rows(words, x_max=col_x)
    )

    def fv(pat, src=left_p12):
        return _find(src, pat)

    # 출원/공개 정보
    app_no    = fv(r"\(21\)\s*출원번호\s+([\d-]+)")
    app_date  = fv(r"\(22\)\s*출원일자\s+(\d{4}년\d{2}월\d{2}일)")
    exam_date = fv(r"심사청구일자\s+(\d{4}년\d{2}월\d{2}일)")
    pub_no    = fv(r"\(65\)\s*공개번호\s+([\d-]+)")
    pub_date  = fv(r"\(43\)\s*공개일자\s+(\d{4}년\d{2}월\d{2}일)")

    # 선행기술 (* 주석 자동 제거)
    prior_arts = list(dict.fromkeys(
        re.findall(r"(?:KR|US|JP|EP)\d+\s+[A-Z]\d+", left_p12)
    ))

    # 청구항 수
    m = re.search(r"전체 청구항 수\s*:\s*총\s*(\d+)\s*항", left_all)
    claim_count = m.group(1) if m else "-"

    # IPC: (51) 섹션
    ipc_block = _find(left_all, r"\(51\)[^\n]*\n(.*?)(?=\(52\)|\(21\))", "")
    ipc_codes = list(dict.fromkeys(CODE_RE.findall(ipc_block)))

    # CPC: (52) 섹션 전부 (여러 페이지에 걸쳐 있을 수 있음)
    cpc_blocks = re.findall(
        r"\(52\)[^\n]*\n(.*?)(?=\n\(\d{2,3}\)|\Z)", left_all, re.DOTALL
    )
    cpc_codes = list(dict.fromkeys(
        c for block in cpc_blocks for c in CODE_RE.findall(block)
        if c not in ipc_codes
    ))

    # ── 오른쪽 컬럼 ──
    reg_no = announce_date = reg_date = examiner = assignee = "-"
    inventors: list[str] = []
    agents: list[str] = []
    r_section = None
    inv_carry = False

    for page_idx, page_words in enumerate(pages_words[:3]):
        if inv_carry:
            r_section = "inventor"
            inv_carry = False

        for row in _words_to_rows(page_words, x_min=col_x):
            text = _row_text(row)
            if re.match(r"^[-\s\d]+$", text.strip()):
                continue

            # 고정값
            m = re.search(r"\(11\)\s*등록번호\s+([\d-]+)", text)
            if m:
                reg_no = m.group(1); continue
            m = re.search(r"\(24\)\s*등록일자\s+(\d{4}년\d{2}월\d{2}일)", text)
            if m:
                reg_date = m.group(1); continue
            m = re.search(r"\(45\)\s*공고일자\s+(\d{4}년\d{2}월\d{2}일)", text)
            if m:
                announce_date = m.group(1); continue
            m = re.search(r"심사관\s*:\s*(\S+)", text)
            if m:
                examiner = m.group(1); continue

            # 섹션 마커
            if re.search(r"\(73\).*특허권자", text):
                r_section = "assignee"; continue
            if re.search(r"\(72\).*발명자", text):
                r_section = "inventor"; continue
            if re.search(r"\(74\).*대리인", text):
                r_section = "agent"; continue
            if SECTION_RE.match(text):
                r_section = None; continue

            if r_section == "assignee":
                if assignee == "-" and not _is_address(text):
                    assignee = text
                    r_section = None

            elif r_section == "inventor":
                if re.search(r"뒷면에|계속", text):
                    inv_carry = True; continue
                if _is_address(text):
                    continue
                name = _extract_name_from_row(text)
                if name and name not in inventors:
                    inventors.append(name)

            elif r_section == "agent":
                if not _is_address(text):
                    for n in _korean_names_from(text, agents):
                        agents.append(n)
                    r_section = None

        # 왼쪽 컬럼 page 2+ 발명자 보완
        if page_idx >= 1:
            l_section = None
            for row in _words_to_rows(page_words, x_max=col_x):
                text = _row_text(row)
                if re.search(r"\(72\).*발명자", text):
                    l_section = "inventor"; continue
                if SECTION_RE.match(text):
                    l_section = None; continue
                if l_section == "inventor":
                    if _is_address(text):
                        continue
                    name = _extract_name_from_row(text)
                    if name and name not in inventors:
                        inventors.append(name)

    return {
        "등록번호":          reg_no,
        "출원번호":          app_no,
        "출원일자":          app_date,
        "심사청구일자":      exam_date,
        "공개번호":          pub_no,
        "공개일자":          pub_date,
        "등록일자":          reg_date,
        "공고일자":          announce_date,
        "특허권자":          assignee,
        "발명자":            inventors,
        "대리인":            agents,
        "심사관":            examiner,
        "국제특허분류(IPC)": ipc_codes,
        "CPC특허분류":       cpc_codes,
        "선행기술조사문헌":  prior_arts,
        "청구항_수":         claim_count,
    }


def parse_title_abstract(full_text: str) -> dict:
    title = _find(full_text, r"\(54\)\s*발명의\s*명칭\s+(.+?)(?=\n.*\(57\)|\n\s*\(57\))")
    if "\n" in title:
        title = title.split("\n")[0].strip()

    raw = _find(
        full_text,
        r"\(57\)\s*요\s*약\s*\n(.+?)(?=\n\(52\)|\n명\s*세\s*서|\n청구범위)",
    )
    if raw == "-":
        return {"발명의_명칭": title, "요약": "-"}

    clean = [
        line.strip() for line in raw.splitlines()
        if line.strip()
        and not JUNK_LINE.search(line.strip())
        and not KOREAN_NAME.match(line.strip())
    ]
    abstract = re.sub(r"\s+", " ", " ".join(clean)).strip()
    return {"발명의_명칭": title, "요약": abstract}


def _clean_section_text(text: str, limit: int | None = None) -> str:
    """PDF 행 기반 추출 텍스트에서 평가에 방해되는 머리말/쪽번호 잡음을 줄입니다."""
    lines = []
    for line in text.splitlines():
        stripped = re.sub(r"\s+", " ", line).strip()
        if not stripped:
            continue
        if JUNK_LINE.search(stripped):
            continue
        if re.match(r"^등록특허\s+\d{2}-\d+", stripped):
            continue
        if re.match(r"^-?\s*\d+\s*-?$", stripped):
            continue
        lines.append(stripped)
    cleaned = re.sub(r"\s+", " ", "\n".join(lines)).strip()
    if limit and len(cleaned) > limit:
        return cleaned[:limit].rstrip() + "..."
    return cleaned


def _find_section_bounds(text: str, start_patterns: list[str], end_patterns: list[str]) -> tuple[int, int] | None:
    start_match = None
    for pattern in start_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match and (start_match is None or match.start() < start_match.start()):
            start_match = match
    if not start_match:
        return None

    start = start_match.end()
    end = len(text)
    tail = text[start:]
    for pattern in end_patterns:
        match = re.search(pattern, tail, re.MULTILINE)
        if match:
            end = min(end, start + match.start())
    return start, end


def _infer_claim_category(text: str) -> str:
    if re.search(r"방법|단계|공정", text):
        return "방법"
    if re.search(r"시스템|장치|서버|단말|모듈|부", text):
        return "시스템"
    if re.search(r"기록매체|저장매체|프로그램|컴퓨터 판독", text):
        return "매체"
    return "기타"


def _claim_dependency(text: str) -> int | None:
    patterns = [
        r"청구항\s*(\d+)\s*에\s*있어서",
        r"제\s*(\d+)\s*항\s*에\s*있어서",
        r"청구항\s*(\d+)\s*항",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))
    return None


def parse_claims(full_text: str) -> dict:
    """청구범위 섹션에서 청구항별 텍스트, 독립/종속, 삭제항을 추출합니다."""
    bounds = _find_section_bounds(
        full_text,
        [r"^\s*청\s*구\s*범\s*위\s*$", r"청\s*구\s*범\s*위"],
        [
            r"^\s*발\s*명\s*의\s*설\s*명\s*$",
            r"^\s*발명의\s*설명\s*$",
            r"^\s*기\s*술\s*분\s*야\s*$",
            r"^\s*도\s*면\s*$",
            r"^\s*요\s*약\s*서\s*$",
        ],
    )
    if not bounds:
        return {"claims_text": {}, "deleted_claims": [], "claims_raw_text": ""}

    section = full_text[bounds[0]:bounds[1]]
    matches = list(
        re.finditer(r"^\s*청구항\s*(\d+)(?!\s*에\s*있어서)(?:\s*$|\s+)", section, re.MULTILINE)
    )
    claims: dict[str, dict] = {}
    deleted_claims: list[int] = []

    for idx, match in enumerate(matches):
        claim_no = int(match.group(1))
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section)
        claim_text = _clean_section_text(section[start:end])
        claim_text = re.sub(r"^[.\s:：]+", "", claim_text).strip()
        if not claim_text:
            continue
        if re.search(r"^삭제|삭제$", claim_text):
            deleted_claims.append(claim_no)
            continue

        depends_on = _claim_dependency(claim_text)
        item = {
            "type": "종속항" if depends_on else "독립항",
            "category": _infer_claim_category(claim_text),
            "text": claim_text,
        }
        if depends_on:
            item["depends_on"] = depends_on
        claims[f"claim_{claim_no}"] = item

    return {
        "claims_text": claims,
        "deleted_claims": deleted_claims,
        "claims_raw_text": _clean_section_text(section, limit=12000),
    }


def _extract_labeled_subsection(text: str, label_patterns: list[str], end_labels: list[str], limit: int) -> str:
    bounds = _find_section_bounds(text, label_patterns, end_labels)
    if not bounds:
        return ""
    return _clean_section_text(text[bounds[0]:bounds[1]], limit=limit)


def parse_description_sections(full_text: str) -> dict:
    """명세서 본문에서 LLM 평가에 유용한 발명의 설명 섹션들을 추출합니다."""
    description_bounds = _find_section_bounds(
        full_text,
        [r"^\s*발\s*명\s*의\s*설\s*명\s*$", r"^\s*발명의\s*설명\s*$"],
        [r"^\s*부\s*호\s*의\s*설\s*명\s*$", r"^\s*도\s*면\s*$", r"^\s*도면의\s*간단한\s*설명\s*$"],
    )
    description_text = full_text[description_bounds[0]:description_bounds[1]] if description_bounds else full_text
    section_end_labels = [
        r"^\s*배\s*경\s*기\s*술\s*$",
        r"^\s*발\s*명\s*의\s*내\s*용\s*$",
        r"^\s*해결하려는\s*과제\s*$",
        r"^\s*과제의\s*해결\s*수단\s*$",
        r"^\s*발명의\s*효과\s*$",
        r"^\s*도면의\s*간단한\s*설명\s*$",
        r"^\s*발명을\s*실시하기\s*위한\s*구체적인\s*내용\s*$",
        r"^\s*부\s*호\s*의\s*설\s*명\s*$",
    ]
    return {
        "description_text": _clean_section_text(description_text, limit=20000),
        "technical_field": _extract_labeled_subsection(
            description_text,
            [r"^\s*기\s*술\s*분\s*야\s*$", r"^\s*기술분야\s*$"],
            section_end_labels,
            2500,
        ),
        "background_art": _extract_labeled_subsection(
            description_text,
            [r"^\s*배\s*경\s*기\s*술\s*$", r"^\s*배경기술\s*$"],
            section_end_labels,
            3500,
        ),
        "problem_to_solve": _extract_labeled_subsection(
            description_text,
            [r"^\s*해결하려는\s*과제\s*$"],
            section_end_labels,
            2500,
        ),
        "solution": _extract_labeled_subsection(
            description_text,
            [r"^\s*과제의\s*해결\s*수단\s*$"],
            section_end_labels,
            3500,
        ),
        "advantageous_effects": _extract_labeled_subsection(
            description_text,
            [r"^\s*발명의\s*효과\s*$"],
            section_end_labels,
            2500,
        ),
        "implementation": _extract_labeled_subsection(
            description_text,
            [r"^\s*발명을\s*실시하기\s*위한\s*구체적인\s*내용\s*$"],
            [r"^\s*부\s*호\s*의\s*설\s*명\s*$", r"^\s*도\s*면\s*$"],
            6000,
        ),
    }


def parse_patent(pdf_path: Path) -> dict:
    sys_meta    = extract_pdf_sys_meta(pdf_path)
    pages_words = extract_page_words(pdf_path)

    # 빈 PDF / 텍스트 레이어 없는 PDF 방어
    non_empty = [p for p in pages_words if p]
    if not non_empty:
        warnings.warn(f"{pdf_path.name}: 텍스트를 추출할 수 없습니다 (스캔 PDF 등).")
        return {
            "filename": pdf_path.name,
            "sys_meta": sys_meta,
            "meta": {"발명의_명칭": "-", "요약": "-"},
            "error": "텍스트 추출 불가",
        }

    full_text        = extract_full_text(pages_words)
    col_x, detected  = detect_column_split(pages_words[0])
    if not detected:
        warnings.warn(
            f"{pdf_path.name}: 컬럼 경계 자동 감지 실패, 기본값 {col_x} 사용."
        )

    meta = parse_fields(pages_words, col_x)
    meta.update(parse_title_abstract(full_text))
    meta["_col_x_detected"] = detected  # 감지 성공 여부를 메타에 기록
    claims = parse_claims(full_text)
    description = parse_description_sections(full_text)

    return {
        "filename": pdf_path.name,
        "sys_meta": sys_meta,
        "meta": meta,
        "claims": claims,
        "description": description,
    }


# ── OpenAI 키워드 추출 ────────────────────────────────────────────────────
def extract_keywords(title: str, abstract: str) -> list[str]:
    """OpenAI로 키워드 추출. API 키 미설정·호출 실패·파싱 오류 시 빈 리스트 반환."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content":
                f"다음 특허의 제목과 요약을 읽고, 기술적 핵심 키워드를 10개 이내로 추출해주세요.\n"
                f"반드시 {{\"keywords\": [\"키워드1\", ...]}} 형태의 JSON만 반환하세요.\n\n"
                f"제목: {title}\n요약: {abstract}"
            }],
            temperature=0.2,
            max_tokens=200,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        return data.get("keywords", [])
    except Exception:
        return []


def make_brief_summary(title: str, abstract: str) -> dict:
    """개요와 핵심 내용을 1~2줄로 생성. OpenAI 실패 시 원문 요약에서 짧게 대체한다."""
    fallback = {
        "개요": title if title and title != "-" else "-",
        "핵심_내용": _shorten_abstract(abstract),
    }

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not abstract or abstract == "-":
        return fallback

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content":
                f"다음 특허의 제목과 요약을 바탕으로 독자가 빠르게 이해할 수 있게 정리해주세요.\n"
                f"반드시 {{\"overview\": \"개요 1문장\", \"key_points\": \"핵심 내용 1~2문장\"}} "
                f"형태의 JSON만 반환하세요.\n"
                f"각 값은 한국어로 간결하게 작성하고, 원문에 없는 내용을 추측하지 마세요.\n\n"
                f"제목: {title}\n요약: {abstract}"
            }],
            temperature=0.2,
            max_tokens=350,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        overview = str(data.get("overview", "")).strip()
        key_points = str(data.get("key_points", "")).strip()
        return {
            "개요": overview or fallback["개요"],
            "핵심_내용": key_points or fallback["핵심_내용"],
        }
    except Exception:
        return fallback


def _shorten_abstract(abstract: str, limit: int = 180) -> str:
    if not abstract or abstract == "-":
        return "-"
    text = re.sub(r"\s+", " ", abstract).strip()
    sentences = []
    start = 0
    for m in re.finditer(r"(?:다\.|[.!?。])\s+", text):
        sentences.append(text[start:m.end()].strip())
        start = m.end()
    if start < len(text):
        sentences.append(text[start:].strip())
    brief = " ".join(s for s in sentences[:2] if s).strip() or text
    if len(brief) <= limit:
        return brief
    return brief[:limit].rstrip() + "..."


# ── 터미널 출력 ───────────────────────────────────────────────────────────
def _fmt(vals) -> str:
    if not vals or vals == "-":
        return "-"
    return ", ".join(vals) if isinstance(vals, list) else str(vals)


def print_report(patents: list[dict]) -> None:
    W = 72  # 터미널 display width 기준

    def row(label: str, val: str, lw: int = 10, vw: int = None) -> None:
        vw = vw or (W - 6 - lw)
        lines = textwrap.wrap(val, vw) or ["-"]
        for i, line in enumerate(lines):
            l = label if i == 0 else ""
            print(f"│   {_pad(l, lw)}  {_pad(line, vw)} │")

    for idx, p in enumerate(patents, 1):
        meta  = p["meta"]
        sys_m = p["sys_meta"]
        kw    = p.get("keywords", [])
        brief = p.get("brief_summary", {})
        err   = p.get("error")

        def v(key):
            val = meta.get(key, "-")
            return val if val else "-"

        if idx > 1:
            print()

        # 헤더
        print("┌" + "─" * (W - 2) + "┐")
        title_lines = textwrap.wrap(v("발명의_명칭"), W - 14) or ["-"]
        for i, line in enumerate(title_lines):
            prefix = "  특허  " if i == 0 else "        "
            print(f"│ {prefix}{_pad(line, W - 12)} │")

        if err:
            print("├" + "─" * (W - 2) + "┤")
            print(f"│   ⚠  {_pad(err, W - 8)} │")
            print("└" + "─" * (W - 2) + "┘")
            continue

        print("├" + "─" * (W - 2) + "┤")

        # 출원·등록 정보
        print(f"│ {_pad('[ 출원·등록 정보 ]', W - 4)} │")
        for label, val in [
            ("등록번호",    v("등록번호")),
            ("출원번호",    v("출원번호")),
            ("출원일자",    v("출원일자")),
            ("심사청구일자", v("심사청구일자")),
            ("공개번호",    v("공개번호")),
            ("공개일자",    v("공개일자")),
            ("등록일자",    v("등록일자")),
            ("공고일자",    v("공고일자")),
            ("청구항 수",   f"{v('청구항_수')} 항"),
            ("심사관",      v("심사관")),
            ("PDF 페이지",  f"{sys_m.get('pages', '-')} 페이지"),
        ]:
            row(label, val)
        print("├" + "─" * (W - 2) + "┤")

        # 권리자 정보
        print(f"│ {_pad('[ 권리자 정보 ]', W - 4)} │")
        row("특허권자", v("특허권자"))
        row("발명자",   _fmt(v("발명자")))
        row("대리인",   _fmt(v("대리인")))
        print("├" + "─" * (W - 2) + "┤")

        # 특허 분류
        print(f"│ {_pad('[ 특허 분류 ]', W - 4)} │")
        row("IPC", _fmt(v("국제특허분류(IPC)")))
        row("CPC", _fmt(v("CPC특허분류")))
        print("├" + "─" * (W - 2) + "┤")

        # 선행기술
        print(f"│ {_pad('[ 선행기술조사문헌 ]', W - 4)} │")
        row("", _fmt(v("선행기술조사문헌")), lw=0, vw=W - 6)
        print("├" + "─" * (W - 2) + "┤")

        # AI 키워드
        print(f"│ {_pad('[ AI 추출 키워드 ]', W - 4)} │")
        kw_str = _fmt(kw) if kw else "(추출 실패)"
        row("", kw_str, lw=0, vw=W - 6)
        print("├" + "─" * (W - 2) + "┤")

        # 개요와 핵심 내용
        print(f"│ {_pad('[ 개요 및 핵심 내용 ]', W - 4)} │")
        row("개요", brief.get("개요", "-"))
        row("핵심 내용", brief.get("핵심_내용", "-"))
        print("└" + "─" * (W - 2) + "┘")


# ── 파일 선택 ─────────────────────────────────────────────────────────────
def select_files(pdf_files: list[Path]) -> list[Path]:
    print("처리할 특허 PDF를 선택하세요.\n")
    print(f"  [0] 전체 ({len(pdf_files)}건 모두)")
    for i, f in enumerate(pdf_files, 1):
        print(f"  [{i}] {f.name}")

    while True:
        raw = input("\n번호 입력 (쉼표로 복수 선택 가능, 예: 1,3): ").strip()
        if not raw:
            continue
        selected: list[Path] = []
        try:
            for token in re.split(r"[,\s]+", raw):
                n = int(token)
                if n == 0:
                    return pdf_files
                if 1 <= n <= len(pdf_files):
                    f = pdf_files[n - 1]
                    if f not in selected:
                        selected.append(f)
                else:
                    print(f"  유효하지 않은 번호: {n}")
                    selected = []
                    break
        except ValueError:
            print("  숫자만 입력해주세요.")
            continue
        if selected:
            return selected


# ── 진입점 ────────────────────────────────────────────────────────────────
def _process(pdf_files: list[Path], save_json: bool = False) -> None:
    patents = []
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {pdf_path.name}", flush=True)
        p = parse_patent(pdf_path)
        if not p.get("error"):
            print("        키워드 추출 중 (OpenAI)...", end=" ", flush=True)
            p["keywords"] = extract_keywords(
                p["meta"].get("발명의_명칭", ""),
                p["meta"].get("요약", ""),
            )
            print("완료")
            print("        개요/핵심 내용 생성 중 (OpenAI)...", end=" ", flush=True)
            p["brief_summary"] = make_brief_summary(
                p["meta"].get("발명의_명칭", ""),
                p["meta"].get("요약", ""),
            )
            print("완료")
        patents.append(p)

    print()
    print_report(patents)

    if save_json:
        out = Path("patents.json")
        # _col_x_detected 같은 내부 필드 제거 후 저장
        export = []
        for p in patents:
            ep = {k: v for k, v in p.items()}
            ep["meta"] = {k: v for k, v in p["meta"].items() if not k.startswith("_")}
            export.append(ep)
        out.write_text(json.dumps(export, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 저장: {out.resolve()}")


def main():
    pdf_files = sorted(PATENT_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"'{PATENT_DIR}' 폴더에 PDF 파일이 없습니다.")
        return

    save_json = "--json" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--json"]

    if args:
        targets: list[Path] = []
        for arg in args:
            if arg.isdigit():
                n = int(arg)
                if 1 <= n <= len(pdf_files):
                    targets.append(pdf_files[n - 1])
                else:
                    print(f"유효하지 않은 번호: {n}  (1~{len(pdf_files)})")
                    return
            else:
                path = PATENT_DIR / arg
                if not path.exists():
                    path = PATENT_DIR / (arg + ".pdf")
                if path.exists():
                    targets.append(path)
                else:
                    print(f"파일을 찾을 수 없습니다: {arg}")
                    return
        _process(targets, save_json)
    else:
        targets = select_files(pdf_files)
        print(f"\n총 {len(targets)}건 처리 중...\n", flush=True)
        _process(targets, save_json)


if __name__ == "__main__":
    main()
