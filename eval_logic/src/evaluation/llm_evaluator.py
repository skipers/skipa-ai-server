"""LLM 기반 특허 가치 평가기입니다.

이 모듈은 정형 데이터만으로 판단하기 어려운 평가 항목을 담당합니다.
서비스 레이어 기준으로는 "고비용·고지연·외부 의존" 단계이므로 다음 원칙을
따릅니다.

1. ``checklist_fixed.md``를 파싱해 평가 항목과 점수 기준을 데이터화합니다.
2. 항목별로 청구항 전용 / 웹 검색 / 혼합 전략을 나눕니다.
3. 웹 검색 결과가 있는 항목은 LLM 응답에 출처 번호를 포함하게 합니다.
4. 응답은 보고서/서비스가 소비하기 쉬운 점수 dict로 정규화합니다.

LLM 기반 특허 평가 모듈
명세서 텍스트를 읽고 체크리스트 항목별 점수 + 근거를 반환
웹 검색(Tavily)으로 뉴스·논문 근거를 가져와 LLM이 인용하도록 함

체크리스트 원본: checklist_fixed.md

[변경사항]
- search_patent_evidence() 호출 시그니처 변경:
    (title, dim) → (title, item, ipc, ipc_desc)
- 항목별로 웹서치를 개별 수행 (차원 단위 → 항목 단위)
- claims_only 항목: 웹서치 스킵 + 전용 프롬프트 사용
- web_search / hybrid 항목: 항목별 웹서치 결과를 프롬프트에 포함
- IPC → ipc_desc 매핑 추가
"""

import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path
import re

from evaluation.web_searcher import search_patent_evidence, get_search_strategy
from evaluation.ipc_ksic_mapper import load_mapping_table, map_ipc_to_ksic
from core.paths import RESOURCES_DIR, ROOT_DIR

load_dotenv(ROOT_DIR / ".env")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL   = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
CHECKLIST_PATH = RESOURCES_DIR / "checklist_fixed.md"

# 엑셀 매핑 테이블 경로 (.env 또는 기본값)
_ksic_env = os.environ.get("KSIC_TABLE_PATH")
KSIC_TABLE_PATH = Path(_ksic_env) if _ksic_env else RESOURCES_DIR / "산업_KSIC_-특허_IPC__연계표.xlsx"
if not KSIC_TABLE_PATH.is_absolute():
    KSIC_TABLE_PATH = ROOT_DIR / KSIC_TABLE_PATH

# 매핑 테이블 로드 (파일 없으면 None → 대체 경로 사용)
try:
    _KSIC_DF = load_mapping_table(KSIC_TABLE_PATH)
    print(f"✅ KSIC 매핑 테이블 로드: {KSIC_TABLE_PATH} ({len(_KSIC_DF)}행)")
except Exception as e:
    print(f"⚠️  KSIC 매핑 테이블 로드 실패 ({e}) → IPC 코드 원문 사용")
    _KSIC_DF = None


def _ipc_to_desc(ipc_list: list[str], title: str = "", summary: str = "") -> str:
    """
    IPC 코드 리스트 → 산업명(한국어) 반환.

    매핑 우선순위:
      1. ipc_ksic_mapper 엑셀 룩업 (exact / class_fallback)
      2. llm_required인 경우 candidates 중 첫 번째 산업명 사용
         (LLM 호출 비용 절감 목적 — 평가용 쿼리 힌트이므로 정밀도보다 속도 우선)
      3. 테이블 없거나 완전 실패 → IPC 코드 원문 반환
    """
    if not ipc_list:
        return ""

    if _KSIC_DF is None:
        return ipc_list[0]

    ipc = ipc_list[0]
    result = map_ipc_to_ksic(
        ipc=ipc,
        df=_KSIC_DF,
        title=title,
        abstract=summary,
        use_llm=False,      # LLM 호출 없이 테이블 룩업만 사용
    )

    method = result.get("method", "")

    # 정확 매핑 / 대분류 대체 매핑 → 산업명 바로 사용
    if method in ("exact", "class_fallback") and result.get("산업명"):
        return result["산업명"]

    # LLM 판단 필요(후보 여러 개) → 첫 번째 후보 산업명 사용
    if method in ("llm_required", "exact_ambiguous", "fallback_ambiguous"):
        candidates = result.get("candidates", [])
        if candidates and candidates[0].get("산업명"):
            return candidates[0]["산업명"]

    # 완전 실패 → IPC 코드 원문
    return ipc


# ──────────────────────────────────────────
# 체크리스트 파싱
# ──────────────────────────────────────────
def parse_checklist_markdown(path: Path) -> dict[str, list[dict]]:
    """마크다운 체크리스트를 차원별 평가 항목 구조로 파싱합니다.

    법률/가치 평가 기준은 사람이 검토하기 쉬운 마크다운 파일로 관리합니다.
    런타임 코드는 프롬프트를 만들기 전에 이 파일을 구조화된 평가 항목 정의로
    변환합니다.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    dimensions: dict[str, list[dict]] = {}
    current_dim: str | None = None
    current_item: dict | None = None
    awaiting_desc = False

    dim_pattern      = re.compile(r"^##\s+(.+?)\s*\(")
    item_pattern     = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")
    criteria_pattern = re.compile(r"^-\s+\*\*(.+?)\*\*:\s*(.+)$")

    def flush_item() -> None:
        nonlocal current_item, awaiting_desc
        if current_dim and current_item:
            if "desc_lines" in current_item:
                current_item["desc"] = " ".join(current_item.pop("desc_lines")).strip()
            dimensions.setdefault(current_dim, []).append(current_item)
        current_item = None
        awaiting_desc = False

    for raw_line in lines:
        line    = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped == "---" or stripped.startswith(">"):
            continue

        dim_match = dim_pattern.match(stripped)
        if dim_match:
            flush_item()
            current_dim = dim_match.group(1).strip()
            dimensions.setdefault(current_dim, [])
            continue

        item_match = item_pattern.match(stripped)
        if item_match:
            flush_item()
            current_item = {
                "number":    int(item_match.group(1)),
                "item":      item_match.group(2).strip(),
                "desc_lines": [],
                "criteria":  [],
            }
            awaiting_desc = True
            continue

        if current_item is None or current_dim is None:
            continue

        criteria_match = criteria_pattern.match(stripped)
        if criteria_match:
            awaiting_desc = False
            current_item["criteria"].append({
                "level": criteria_match.group(1).strip(),
                "text":  criteria_match.group(2).strip(),
            })
            continue

        if awaiting_desc:
            current_item.setdefault("desc_lines", []).append(stripped)

    flush_item()
    return dimensions


LLM_ITEMS = parse_checklist_markdown(CHECKLIST_PATH)


# ──────────────────────────────────────────
# 자동 평가 항목 (LLM 평가 제외)
# ──────────────────────────────────────────
AUTO_ITEMS: set[str] = {
    "IP 원천성",
    "권리의 충실성",
    "권리행사 제한 가능성",
    "특허출원 활성도",
    "매출 성장성",
}


# ──────────────────────────────────────────
# 프롬프트 생성
# ──────────────────────────────────────────
def _format_web_sources(sources: list[dict]) -> str:
    if not sources:
        return "검색된 참고 자료 없음"
    lines = []
    for i, s in enumerate(sources, 1):
        date_str = f" ({s['published_date']})" if s.get("published_date") else ""
        lines.append(
            f"[출처 {i}] {s['title']}{date_str}\n"
            f"URL: {s['url']}\n"
            f"내용: {s['snippet']}"
        )
    return "\n\n".join(lines)


def _format_claims(claims: dict, dim: str) -> str:
    if not claims:
        return "청구항 정보 없음"

    if dim == "권리성":
        indep_limit = None
        dep_limit   = 400
        max_deps    = 10
    else:
        indep_limit = 1500
        dep_limit   = 200
        max_deps    = 5

    indep_lines, dep_lines = [], []

    for k, v in claims.items():
        if isinstance(v, dict):
            text     = v.get("text", "")
            ctype    = v.get("type", "")
            category = v.get("category", "")
            depends  = v.get("depends_on")
        else:
            text     = str(v)
            ctype    = "독립항" if k in ("claim_1", "claim_11") else "종속항"
            category = ""
            depends  = None

        if ctype == "독립항":
            head = f"[{k} · 독립항" + (f" · {category}" if category else "") + "]"
            body = text if indep_limit is None or len(text) <= indep_limit else text[:indep_limit] + " ...(이하 생략)"
            indep_lines.append(f"{head}\n{body}")
        else:
            head = f"[{k} · 종속항" + (f" → 청구항 {depends} 인용" if depends else "") + "]"
            body = text if len(text) <= dep_limit else text[:dep_limit] + " ...(이하 생략)"
            dep_lines.append(f"{head} {body}")

    parts = []
    if indep_lines:
        parts.append("\n\n".join(indep_lines))
    if dep_lines:
        parts.append("\n".join(dep_lines[:max_deps]))
        if len(dep_lines) > max_deps:
            parts.append(f"...(나머지 종속항 {len(dep_lines) - max_deps}개 생략)")
    return "\n\n".join(parts)


# ── 공통 평가 원칙 (두 프롬프트 모두 사용) ──
_EVAL_PRINCIPLES = """[평가 원칙 - 반드시 준수]
1. **5점은 예외적인 우수성에만 부여**: 명확히 두드러지는 혁신·강점이 입증된 경우에만 5점. 단순히 "괜찮다" 정도면 4점이 상한.
2. **정보 부족 시 3점 이하**: 명시적 근거가 부족하면 추측으로 후하게 주지 말고 3점 이하로 보수적으로 평가.
3. **근거 없는 가산점 금지**: 키워드 기반 후한 평가 금지. 청구항의 구체적 구성요소가 기준을 충족할 때만 가산.
4. **점수 분포의 변별력 유지**: 모든 항목을 4점으로 매기지 말고 1~5점 전 구간을 활용.
5. **경쟁 관련 항목 (기술 경쟁성·시장 경쟁성·경쟁자의 영향·경쟁적 반응) 주의사항**:
   - 구체적인 경쟁사명·경쟁기술명·시장점유율 수치가 없으면 3점 이하로 평가.
   - "경쟁이 있을 것이다" 같은 추측으로 점수를 높이지 말 것. 참고 자료에서 실제 경쟁 현황이 확인된 경우에만 4점 이상 부여.
6. **영업 이익성 주의사항**:
   - 업종 평균 영업이익률 수치(DART·KOSIS 등 재무DB 기반)가 참고 자료에 없으면 반드시 3점으로 평가.
   - 수치 없이 "높을 것으로 예상된다" 같은 추측으로 점수를 높이지 말 것."""


def build_prompt_with_search(
    patent: dict,
    dim: str,
    item_info: dict,
    web_sources: list[dict],
) -> str:
    """웹 검색 / 혼합 전략 항목용 프롬프트입니다. 웹서치 결과를 포함해 항목 1개씩 평가합니다."""
    title       = patent.get("meta", {}).get("title", "")
    summary     = patent.get("description_summary", "")
    claims_text = _format_claims(patent.get("claims_text", {}), dim)
    sources_section = _format_web_sources(web_sources)
    num_sources = len(web_sources)

    criteria_text = "\n".join(
        f"    {c['level']}: {c['text']}"
        for c in item_info.get("criteria", [])
    )

    citation_instruction = (
        f"위의 [참고 자료] 중 관련 있는 것을 cited_sources에 번호(1~{num_sources})로 기재하세요. "
        "웹 검색 결과가 제공되었으므로 반드시 관련 출처를 인용하세요. 없으면 빈 배열로 두세요."
        if num_sources > 0
        else "cited_sources는 빈 배열로 두세요."
    )

    return f"""당신은 특허 가치 평가 전문가입니다.
아래 특허 정보와 웹 검색 근거 자료를 바탕으로, 지정된 평가 항목에 1~5점을 부여하고 근거를 제시하세요.

{_EVAL_PRINCIPLES}

5. **참고 자료 필수 인용**: [참고 자료]에서 관련 내용이 있으면 reason에 명시적으로 인용하고 cited_sources 번호로 표기하세요. 웹 검색 결과가 제공되었으므로 반드시 관련 내용을 인용해야 합니다. 참고 자료를 무시하고 일반론으로 답하지 마세요.

[특허 정보]
- 발명 명칭: {title}
- 기술 요약: {summary}

[청구항]
{claims_text}

[참고 자료 - 웹 검색 결과]
{sources_section}

[평가 항목 - {dim} / {item_info['item']}]
평가 포인트: {item_info['desc']}
점수 기준:
{criteria_text}

[응답 형식]
반드시 아래 JSON 형식으로만 응답하세요.
{citation_instruction}
{{
    "item": "{item_info['item']}",
    "score": 점수(1~5 정수),
    "reason": "점수를 부여한 구체적인 근거. 특허 데이터(meta, description_summary, claims_text 등)와 참고 자료를 인용하며 2~3문장으로 서술.",
    "cited_sources": [인용한 출처 번호 목록, 예: [1, 3]]
}}"""


def build_prompt_claims_only(
    patent: dict,
    dim: str,
    item_info: dict,
) -> str:
    """청구항 전용 항목용 프롬프트입니다.

    웹서치 없이 청구항·명세서 텍스트만으로 판단.
    해당 항목: 권리성 대부분 (회피설계 용이성, 권리범위 적절성 등)
    """
    title       = patent.get("meta", {}).get("title", "")
    summary     = patent.get("description_summary", "")
    claims_text = _format_claims(patent.get("claims_text", {}), dim)

    criteria_text = "\n".join(
        f"    {c['level']}: {c['text']}"
        for c in item_info.get("criteria", [])
    )

    return f"""당신은 특허 가치 평가 전문가입니다.
아래 특허의 청구항과 명세서 텍스트만을 근거로, 지정된 평가 항목에 1~5점을 부여하고 근거를 제시하세요.

{_EVAL_PRINCIPLES}

5. **청구항 텍스트 직접 분석**: 이 항목은 외부 시장 데이터가 아닌 청구항의 구성요소·기재 방식·권리범위를 직접 분석하여 판단합니다. 웹 검색 결과는 제공되지 않으며, 아래 청구항 텍스트가 유일한 근거입니다.
6. **추측 금지**: 청구항에 명시되지 않은 내용을 추측하여 점수를 높이지 마세요.

[특허 정보]
- 발명 명칭: {title}
- 기술 요약: {summary}

[청구항]
{claims_text}

[평가 항목 - {dim} / {item_info['item']}]
평가 포인트: {item_info['desc']}
점수 기준:
{criteria_text}

[응답 형식]
반드시 아래 JSON 형식으로만 응답하세요.
{{
    "item": "{item_info['item']}",
    "score": 점수(1~5 정수),
    "reason": "청구항·명세서에서 직접 확인한 내용을 인용하며 2~3문장으로 서술. 청구항에 없는 내용을 추측하지 말 것.",
    "cited_sources": []
}}"""


def build_prompt_hybrid(
    patent: dict,
    dim: str,
    item_info: dict,
    web_sources: list[dict],
) -> str:
    """혼합 전략 항목용 프롬프트입니다.

    웹서치 결과(시장·기술 동향) + 청구항 텍스트를 동등하게 활용.
    해당 항목: 차별성, 혁신성, 기술의 개척성, 파급 및 활용성,
               고객의 지불의지, 고객에 미치는 영향, 기술 사업화 환경 등
    """
    title       = patent.get("meta", {}).get("title", "")
    summary     = patent.get("description_summary", "")
    claims_text = _format_claims(patent.get("claims_text", {}), dim)
    sources_section = _format_web_sources(web_sources)
    num_sources = len(web_sources)

    criteria_text = "\n".join(
        f"    {c['level']}: {c['text']}"
        for c in item_info.get("criteria", [])
    )

    citation_instruction = (
        f"위의 [참고 자료] 중 관련 있는 것을 cited_sources에 번호(1~{num_sources})로 기재하세요. "
        "최소 1개 이상 인용하세요. 없으면 빈 배열로 두세요."
        if num_sources > 0
        else "cited_sources는 빈 배열로 두세요."
    )

    return f"""당신은 특허 가치 평가 전문가입니다.
아래 특허의 청구항·명세서와 웹 검색 자료를 **모두** 활용하여, 지정된 평가 항목에 1~5점을 부여하고 근거를 제시하세요.

{_EVAL_PRINCIPLES}

5. **청구항과 웹 자료를 병행 분석**: 이 항목은 청구항에 기재된 기술 내용과 외부 시장·기술 동향을 함께 고려해야 합니다.
   - 청구항에서: 기술의 구체적 구성요소·특징·차별점을 확인합니다.
   - 웹 자료에서: 해당 기술분야의 동향·경쟁구도·시장 반응을 확인합니다.
   - 둘 중 하나만 보고 판단하지 마세요. 청구항 근거 없이 웹 자료만으로 후하게 주거나, 웹 자료를 무시하고 청구항만으로 판단하지 마세요.
6. **참고 자료 필수 인용**: 웹 자료에서 관련 내용이 있으면 reason에 명시적으로 인용하고 cited_sources 번호로 표기하세요. 웹 자료가 제공되었다면 반드시 reason에서 관련 내용을 인용하고 cited_sources에 번호를 기재하세요.
7. **[특별한 인정] 항목 전용 지시**: 이 항목은 "이 기술을 도입한 출원인이 앞으로 산업 내 선도자로 인정받을 가능성"을 묻습니다.
   - 현재 수상·인증 이력이 아니라 미래 가능성을 판단하는 항목입니다.
   - 출원인의 업계 입지(웹 자료), 기술의 차별성(청구항), 해당 분야의 기술 선도 경쟁 구도를 종합하여 판단하세요.
   - 웹 자료에서 출원인 관련 내용이 없으면 3점으로 평가하세요.

[특허 정보]
- 발명 명칭: {title}
- 기술 요약: {summary}

[청구항]
{claims_text}

[참고 자료 - 웹 검색 결과]
{sources_section}

[평가 항목 - {dim} / {item_info['item']}]
평가 포인트: {item_info['desc']}
점수 기준:
{criteria_text}

[응답 형식]
반드시 아래 JSON 형식으로만 응답하세요.
{citation_instruction}
{{
    "item": "{item_info['item']}",
    "score": 점수(1~5 정수),
    "reason": "청구항에서 확인한 기술 특징과 웹 자료에서 확인한 시장·기술 동향을 모두 언급하며 2~3문장으로 서술. [참고 자료 X]의 내용을 인용하여 서술할 것.",
    "cited_sources": [인용한 출처 번호 목록, 예: [1, 3]]
}}"""


# ──────────────────────────────────────────
# OpenAI API 호출
# ──────────────────────────────────────────
def call_openai(prompt: str) -> dict:
    """OpenAI 채팅 완성 API를 호출하고 JSON 객체 응답 1개를 파싱합니다.

    아직은 프로토타입 HTTP 호출을 직접 사용합니다. 서버 통합 단계에서는 테스트
    시 mock 처리할 수 있고 운영 환경에서 재시도/사용량 제한 정책을 중앙화할 수
    있도록 주입 가능한 LLM 클라이언트로 바꾸는 것이 좋습니다.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    body = {
        "model": OPENAI_MODEL,
        "max_tokens": 800,   # 항목 1개씩이므로 토큰 절감
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Return only one valid JSON object."},
            {"role": "user",   "content": prompt},
        ],
    }
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers, json=body, timeout=60,
    )
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"].strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    return json.loads(text)


# ──────────────────────────────────────────
# 항목 1개 평가
# ──────────────────────────────────────────
def _evaluate_single_item(
    patent: dict,
    dim: str,
    item_info: dict,
    ipc: str,
    ipc_desc: str,
    assignee: str,
    patent_id_out: str,
    input_file_out: str,
) -> dict:
    """항목 1개를 평가하여 점수 딕셔너리를 반환합니다."""
    item_name = item_info["item"]
    strategy  = get_search_strategy(item_name)
    requires_external_sources = strategy in {"web_search", "hybrid"}

    if strategy == "claims_only":
        # B유형: 청구항 텍스트만으로 판단, 웹서치 없음
        print(f"      → [claims_only] 웹서치 스킵")
        web_sources = []
        prompt = build_prompt_claims_only(patent, dim, item_info)

    elif strategy == "hybrid":
        # C유형: 웹서치 + 청구항 병행
        print(f"      → [hybrid] 웹서치 + 청구항 병행")
        web_sources = search_patent_evidence(
            patent_title=patent.get("meta", {}).get("title", ""),
            item=item_name,
            ipc=ipc,
            ipc_desc=ipc_desc,
            assignee=assignee,
            max_results=5,
        )
        prompt = build_prompt_hybrid(patent, dim, item_info, web_sources)

    else:
        # A유형(웹 검색): 웹서치 결과 위주
        print(f"      → [web_search] 웹서치 위주")
        web_sources = search_patent_evidence(
            patent_title=patent.get("meta", {}).get("title", ""),
            item=item_name,
            ipc=ipc,
            ipc_desc=ipc_desc,
            assignee=assignee,
            max_results=5,
        )
        prompt = build_prompt_with_search(patent, dim, item_info, web_sources)

    result = call_openai(prompt)

    # 인용 출처 번호 → 실제 출처 객체 매핑
    cited_indices = result.get("cited_sources", [])
    cited = [
        web_sources[i - 1]
        for i in cited_indices
        if isinstance(i, int) and 1 <= i <= len(web_sources)
    ]

    reason = result.get("reason", "").strip() or (
        "LLM이 명시적 근거를 제공하지 않았습니다. "
        "입력 파일의 description_summary와 claims_text를 참조하여 판단했습니다."
    )

    score_val = result.get("score", 3)
    try:
        score_val = int(score_val)
    except Exception:
        score_val = 3
    score_val = max(1, min(5, score_val))

    confidence = ""
    evidence_policy = "not_required"
    citation_repaired = False

    if requires_external_sources:
        evidence_policy = "external_source_required"
        if not cited and web_sources:
            # 운영 보고서에서는 웹/혼합 전략 항목이 sources 없이 남으면 신뢰도 검증에서
            # 고위험으로 처리됩니다. LLM이 cited_sources 번호를 빼먹은 경우에는
            # 프롬프트에 실제 제공된 상위 검색 근거를 보수적으로 연결하고 표시합니다.
            cited = [web_sources[0]]
            citation_repaired = True
            reason = (
                f"{reason} "
                "다만 LLM 응답에 cited_sources 번호가 누락되어, "
                "검색 결과 상위 근거를 보수적으로 연결했습니다."
            )
        if not cited:
            confidence = "낮음"
            if score_val > 3:
                score_val = 3
                reason = (
                    f"{reason} "
                    "외부 검증 출처가 없어 해당 항목은 3점 이하로 보수 조정했습니다."
                )
        elif citation_repaired and score_val > 3:
            score_val = 3
            confidence = "보통"
            reason = (
                f"{reason} "
                "명시 인용이 누락된 보정 근거이므로 3점 이하로 보수 조정했습니다."
            )

    output = {
        "item":       item_name,
        "dim":        dim,
        "score":      score_val,
        "reason":     reason,
        "sources":    cited,
        "method":     "llm",
        "strategy":   strategy,
        "patent_id":  patent_id_out,
        "input_file": input_file_out,
        "evidence_policy": evidence_policy,
    }
    if confidence:
        output["confidence"] = confidence
    if citation_repaired:
        output["citation_repaired"] = True
    return output


# ──────────────────────────────────────────
# 차원별 평가 실행
# ──────────────────────────────────────────
def evaluate_dim(patent: dict, dim: str) -> list[dict]:
    """특정 차원의 모든 LLM 항목을 항목별로 평가.

    Auto_score가 이미 계산하는 항목은 제외합니다. 이렇게 해야 최종 output에서
    동일 평가 항목이 auto와 llm에 중복으로 들어가지 않습니다.
    """
    all_items = LLM_ITEMS.get(dim, [])
    items     = [it for it in all_items if it["item"] not in AUTO_ITEMS]
    skipped   = [it["item"] for it in all_items if it["item"] in AUTO_ITEMS]

    if skipped:
        print(f"    auto 평가 항목 제외 ({len(skipped)}개): {', '.join(skipped)}")
    if not items:
        print(f"    [{dim}] 평가할 LLM 항목 없음 (전부 auto 처리)")
        return []

    # 특허 메타에서 IPC·출원인 추출
    ipc_list  = patent.get("meta", {}).get("ipc", [])
    ipc       = ipc_list[0] if ipc_list else ""
    ipc_desc  = _ipc_to_desc(
        ipc_list,
        title=patent.get("meta", {}).get("title", ""),
        summary=patent.get("description_summary", ""),
    )
    assignee_list = patent.get("meta", {}).get("assignee", [])
    assignee      = assignee_list[0] if assignee_list else ""

    patent_id_out   = patent.get("patent_id", "")
    input_file_out  = patent.get("_input_file") or patent.get("meta", {}).get("source_file", "")

    scores = []
    for item_info in items:
        item_name = item_info["item"]
        print(f"    [{item_name}] 평가 중...")
        try:
            score = _evaluate_single_item(
                patent, dim, item_info,
                ipc, ipc_desc, assignee,
                patent_id_out, input_file_out,
            )
            scores.append(score)
            bar = "█" * score["score"] + "░" * (5 - score["score"])
            print(f"      {score['score']}/5 [{bar}]  strategy={score['strategy']}")
            print(f"      {score['reason']}\n")
        except Exception as e:
            print(f"      [오류] {item_name}: {e}")

    return scores


def evaluate_all(patent: dict) -> list[dict]:
    """전체 4개 차원 LLM 평가 실행.

    현재는 항목을 순차 처리합니다. 실제 서비스 최적화 단계에서는 이 함수가
    병렬 실행, 캐시, 예산 제한, 재시도 정책을 갖는 agent/workflow node로
    대체될 가능성이 큽니다.
    """
    all_scores = []
    for dim in ["기술성", "권리성", "시장성", "사업성"]:
        print(f"\n  ═══ [{dim}] ═══")
        try:
            scores = evaluate_dim(patent, dim)
            all_scores.extend(scores)
        except Exception as e:
            print(f"  [{dim}] 오류: {e}")
    return all_scores


# ──────────────────────────────────────────
# 실행
# ──────────────────────────────────────────
if __name__ == "__main__":
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY 없음. .env 파일에 추가하세요.")
        exit(1)

    for fname in ["patent_10_2212093.json", "example_input.json"]:
        if os.path.exists(fname):
            with open(fname, encoding="utf-8") as f:
                patent = json.load(f)
            patent["_input_file"] = fname
            print(f"✅ 로드: {fname}")
            print(f"   특허: {patent.get('patent_id')} | {patent.get('meta',{}).get('title','')[:40]}\n")
            break
    else:
        print("❌ JSON 파일 없음")
        exit(1)

    print("=== 기술성 LLM 평가 ===\n")
    scores = evaluate_dim(patent, "기술성")
    print(f"\n총 {len(scores)}개 항목 평가 완료")
