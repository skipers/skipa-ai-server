"""
IPC → KSIC 매핑 모듈
특허 IPC 코드를 받아 KSIC 산업분류로 변환

매핑 3단계:
  1. 정확 매핑: IPC 세부코드 → 테이블 직접 룩업
  2. 대분류 매핑: 세부코드 매핑 실패 시 IPC 대분류(4자리)로 fallback
  3. LLM 매핑: 1, 2 모두 실패 또는 중복 시 명세서 기반 LLM 판단

사용법:
  from ipc_ksic_mapper import load_mapping_table, map_ipc_to_ksic
  df = load_mapping_table("산업_KSIC_-특허_IPC__연계표.xlsx")
  result = map_ipc_to_ksic("G06Q 50/10", df, title="발명명칭", abstract="요약")
"""

import re
import pandas as pd
from typing import Optional


def load_mapping_table(path: str) -> pd.DataFrame:
    """엑셀 매핑 테이블 로드 및 전처리"""
    df = pd.read_excel(path)
    df.columns = ['연번', '산업번호', 'KSIC_대분류', 'KSIC', '산업명', 'IPC패턴', '비고']
    df['IPC_prefix'] = df['IPC패턴'].str.replace('%', '', regex=False).str.strip()
    return df


def normalize_ipc(ipc: str) -> str:
    """'G06F 16/65' → 'G06F16/65' 공백 제거 정규화"""
    return re.sub(r'\s+', '', ipc.strip().upper())


def exact_match(ipc: str, df: pd.DataFrame) -> list[dict]:
    """STEP 1: IPC 세부코드 직접 룩업 (가장 긴 prefix 우선)"""
    ipc_norm = normalize_ipc(ipc)
    candidates = []

    for row in df.itertuples():
        prefix = row.IPC_prefix
        if ipc_norm.startswith(prefix):
            candidates.append({
                'ksic':       str(row.KSIC),
                'ksic_대분류': row.KSIC_대분류,
                '산업명':      row.산업명,
                'ipc_prefix': prefix,
                'match_len':  len(prefix),
                '비고':        row.비고 if pd.notna(row.비고) else ''
            })

    if candidates:
        max_len = max(c['match_len'] for c in candidates)
        return [c for c in candidates if c['match_len'] == max_len]
    return []


def class_fallback(ipc: str, df: pd.DataFrame) -> list[dict]:
    """STEP 2: IPC 대분류 4자리(예: G06F)로 fallback"""
    ipc_norm  = normalize_ipc(ipc)
    ipc_class = re.match(r'^[A-H]\d{2}[A-Z]', ipc_norm)
    if not ipc_class:
        return []

    class_prefix = ipc_class.group()
    seen, unique = set(), []
    for row in df.itertuples():
        if row.IPC_prefix.startswith(class_prefix):
            ksic = str(row.KSIC)
            if ksic not in seen:
                seen.add(ksic)
                unique.append({
                    'ksic':       ksic,
                    'ksic_대분류': row.KSIC_대분류,
                    '산업명':      row.산업명,
                    'ipc_prefix': row.IPC_prefix,
                    'match_len':  len(class_prefix),
                    '비고':        row.비고 if pd.notna(row.비고) else ''
                })
    return unique


def build_llm_prompt(ipc: str, candidates: list[dict],
                     title: str, abstract: str) -> str:
    """STEP 3: LLM에 넘길 프롬프트 생성"""
    candidate_text = "\n".join([
        f"  - KSIC {c['ksic']}: {c['산업명']} ({c['ksic_대분류']})"
        for c in candidates
    ]) if candidates else "  - 매핑 후보 없음"

    return f"""다음 특허의 IPC 코드와 기술 내용을 보고, 가장 적합한 KSIC 산업분류를 선택해주세요.

[특허 정보]
- IPC 코드: {ipc}
- 발명 명칭: {title}
- 요약: {abstract[:500]}

[매핑 후보 KSIC]
{candidate_text}

[요청]
위 후보 중 이 특허의 핵심 기술이 실제로 사용될 산업과 가장 가까운 KSIC를 선택하세요.
후보가 없거나 모두 부적합하면 적합한 KSIC 코드와 산업명을 직접 제안하세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "ksic": "산업분류코드",
  "산업명": "산업명",
  "근거": "선택 이유 한 줄"
}}"""


def map_ipc_to_ksic(
    ipc: str,
    df: pd.DataFrame,
    title: str = "",
    abstract: str = "",
    use_llm: bool = True
) -> dict:
    """
    IPC → KSIC 3단계 매핑 실행

        반환값:
            method가 'exact' 또는 'class_fallback' → ksic, 산업명 바로 사용
            method가 'llm_required' → llm_prompt를 OpenAI에 전달 후 ksic 주입
    """
    result = {
        'ipc': ipc, 'ksic': None, '산업명': None,
        'ksic_대분류': None, 'method': None,
        'candidates': [], 'llm_prompt': None
    }

    # STEP 1: 정확 매핑
    exact = exact_match(ipc, df)
    if len(exact) == 1:
        result.update({**exact[0], 'method': 'exact', 'candidates': exact})
        return result
    if len(exact) > 1:
        if use_llm:
            result.update({'method': 'llm_required', 'candidates': exact,
                           'llm_prompt': build_llm_prompt(ipc, exact, title, abstract)})
        else:
            result.update({**exact[0], 'method': 'exact_ambiguous'})
        return result

    # STEP 2: 대분류 fallback
    fallback = class_fallback(ipc, df)
    if len(fallback) == 1:
        result.update({**fallback[0], 'method': 'class_fallback', 'candidates': fallback})
        return result
    if len(fallback) > 1:
        if use_llm:
            result.update({'method': 'llm_required', 'candidates': fallback,
                           'llm_prompt': build_llm_prompt(ipc, fallback, title, abstract)})
        else:
            result.update({**fallback[0], 'method': 'fallback_ambiguous'})
        return result

    # STEP 3: 완전 실패 → LLM
    result.update({'method': 'llm_required', 'candidates': [],
                   'llm_prompt': build_llm_prompt(ipc, [], title, abstract)})
    return result