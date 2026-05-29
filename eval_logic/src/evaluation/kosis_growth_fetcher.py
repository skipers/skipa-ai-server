"""KOSIS 시장 성장률 데이터 어댑터입니다.

특허 유지/포기 판단에서 시장성은 "이 기술이 속한 산업이 성장 중인가"를
보는 중요한 보조 신호입니다. 이 모듈은 특허의 IPC/KSIC/산업코드를 KOSIS
산업 분류(C2)로 연결하고, 최근 매출 성장률을 1~5점으로 바꿉니다.

서비스 레이어에서 이 모듈을 먼저 호출하는 이유는 ``Auto_score``의
``매출 성장성`` 항목이 ``patent["market_growth"]`` 결과를 그대로 사용하기
때문입니다.

KOSIS API 연동 모듈 — 산업별 시장 성장률 조회
전국사업체조사 DT_1K52F08 테이블 하나로 전 산업 커버

기본 설정: 최신 연도(전년도) 기준으로 최근 5년 성장률 계산
→ 실행할 때마다 자동으로 최신 데이터 반영

[사용법 1] example_input.json 직접 입력
  from kosis_growth_fetcher import get_growth_score_from_json
  import json
  with open("example_input.json") as f:
      data = json.load(f)
  result = get_growth_score_from_json(data)  # 자동으로 최신 5년 반영

[사용법 2] IPC 코드로 입력
  from kosis_growth_fetcher import get_growth_score_from_ipc
  result = get_growth_score_from_ipc(ipc="G06Q 50/10", mapping_df=df)

[사용법 3] C2 코드 직접 입력
  from kosis_growth_fetcher import get_market_growth_score
  result = get_market_growth_score(c2_code="J63")  # 자동으로 최신 5년 반영
"""

import os
import re
import json
import requests
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
from core.paths import RESOURCES_DIR, ROOT_DIR

load_dotenv(ROOT_DIR / ".env")
KOSIS_API_KEY = os.environ.get("KOSIS_API_KEY")
KSIC_RESOURCE_PATH = RESOURCES_DIR / "산업_KSIC_-특허_IPC__연계표.xlsx"

# ──────────────────────────────────────────
# KSIC → C2 코드 매핑 (실제 DT_1K52F08 기준)
# ──────────────────────────────────────────

KSIC_TO_C2 = {
    "01~03": "A",  "01": "A01", "02": "A02", "03": "A03",
    "05~08": "B",  "05": "B05", "06": "B06", "07": "B07", "08": "B08",
    "10": "C10", "11": "C11", "12": "C12", "13": "C13", "14": "C14",
    "15": "C15", "16": "C16", "17": "C17", "18": "C18", "19": "C19",
    "201": "C20", "202": "C20", "203": "C20", "2041": "C20",
    "2042": "C20", "2049": "C20", "205": "C20",
    "211": "C21", "212": "C21", "213": "C21",
    "221": "C22", "222": "C22",
    "231": "C23", "232": "C23", "233": "C23", "239": "C23",
    "241": "C24", "242": "C24", "243": "C24",
    "251": "C25", "252": "C25", "259": "C25",
    "261": "C26", "2621": "C26", "2622": "C26", "2629": "C26",
    "2631": "C26", "2632": "C26", "2641": "C26", "26421": "C26",
    "26422": "C26", "26429": "C26", "2651": "C26", "2652": "C26", "266": "C26",
    "271": "C27", "272": "C27", "273": "C27",
    "281": "C28", "282": "C28", "283": "C28", "284": "C28", "285": "C28", "289": "C28",
    "2911": "C29", "2912": "C29", "2913": "C29", "2914": "C29", "2915": "C29",
    "2916": "C29", "2917": "C29", "2918": "C29", "2919": "C29", "2921": "C29",
    "2922": "C29", "2923": "C29", "2924": "C29", "2925": "C29", "2926": "C29",
    "2927": "C29", "2928": "C29", "2929": "C29",
    "301": "C30", "302": "C30", "303": "C30",
    "311": "C31", "312": "C31", "313": "C31",
    "3191": "C31", "3192": "C31", "3199": "C31",
    "32": "C32", "33": "C33", "34": "C34",
    "35": "D35", "36": "E36", "37": "E37", "38": "E38", "39": "E39",
    "41": "F41", "42": "F42",
    "45": "G45", "46": "G46", "47": "G47",
    "49": "H49", "50": "H50", "51": "H51", "52": "H52",
    "55": "I55", "56": "I56",
    "58": "J58", "59": "J59", "60": "J60", "61": "J61",
    "62": "J62", "63": "J63",
    "64": "K64", "65": "K65", "66": "K66",
    "68": "L68",
    "70": "M70", "71": "M71", "72": "M72", "73": "M73",
    "74": "N74", "75": "N75", "76": "N76",
    "84": "O84", "85": "P85",
    "86": "Q86", "87": "Q87",
    "90": "R90", "91": "R91",
    "94": "S94", "95": "S95", "96": "S96",
}

# C2 코드 → 산업명 (DT_1K52F08 실제 값 기준)
C2_TO_SECTOR = {
    "A": "농업·임업·어업", "A01": "농업", "A02": "임업", "A03": "어업",
    "B": "광업", "C": "제조업",
    "C10": "식료품제조업", "C19": "석유정제품제조업", "C20": "화학제품제조업",
    "C21": "의약품제조업", "C26": "전자부품·컴퓨터·통신장비제조업",
    "C27": "의료정밀기기제조업", "C28": "전기장비제조업", "C29": "기타기계제조업",
    "C30": "자동차제조업", "C31": "기타운송장비제조업",
    "D35": "전기·가스·증기공급업", "E36": "수도업",
    "F": "건설업", "F41": "종합건설업", "F42": "전문건설업",
    "G": "도매및소매업", "G46": "도매업", "G47": "소매업",
    "H": "운수및창고업",
    "I": "숙박및음식점업",
    "J": "정보통신업",
    "J58": "출판업",
    "J61": "우편및통신업",
    "J62": "컴퓨터프로그래밍·시스템통합",
    "J63": "정보서비스업",
    "K": "금융및보험업",
    "M": "전문·과학·기술서비스업",
    "M70": "연구개발업",
    "M71": "전문서비스업",
    "M72": "건축·엔지니어링서비스업",
}

BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"


# ──────────────────────────────────────────
# KOSIS API 호출
# ──────────────────────────────────────────

def fetch_kosis_revenue(
    c2_code: str,
    start_year: str,
    end_year: str,
    api_key: str = None,
) -> list[dict]:
    """DT_1K52F08 에서 전국 기준 특정 산업 연도별 매출액 조회.

    반환값은 KOSIS 원본 필드를 그대로 노출하지 않고, 이후 성장률 계산에
    필요한 ``연도``와 ``값``만 남긴 작은 리스트입니다. API 장애나 미조회는
    빈 리스트로 반환하고, 점수화 단계에서 대체값 3점으로 처리합니다.
    """
    key = api_key or KOSIS_API_KEY
    if not key:
        raise ValueError(
            "KOSIS API 키 없음.\n"
            ".env 파일에 KOSIS_API_KEY=발급받은_키 추가 후 재실행하세요.\n"
            "키 발급: https://kosis.kr/openapi"
        )

    params = {
        "method":     "getList",
        "apiKey":     key,
        "format":     "json",
        "jsonVD":     "Y",
        "orgId":      "101",
        "tblId":      "DT_1K52F08",
        "itmId":      "T3",       # 매출액
        "objL1":      "00",       # 전국
        "objL2":      c2_code,
        "prdSe":      "Y",
        "startPrdDe": start_year,
        "endPrdDe":   end_year,
    }

    try:
        resp = requests.get(BASE_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict) and "err" in data:
            print(f"  ⚠ KOSIS 에러: {data}")
            return []

        results = []
        for item in data:
            year  = item.get("PRD_DE", "")
            value = str(item.get("DT", "0")).replace(",", "")
            if re.match(r'^[\d.]+$', value):
                results.append({"연도": year, "값": float(value)})

        return sorted(results, key=lambda x: x["연도"])

    except requests.RequestException as e:
        print(f"  ⚠ KOSIS 요청 실패: {e}")
        return []


# ──────────────────────────────────────────
# 성장률 계산 및 점수 변환
# ──────────────────────────────────────────

def calc_growth_rate(data: list[dict], years: int = 3) -> Optional[float]:
    """최근 N년 평균 성장률(%) 계산"""
    if len(data) < 2:
        return None
    recent = data[-min(years + 1, len(data)):]
    rates  = []
    for i in range(1, len(recent)):
        prev = recent[i-1]["값"]
        curr = recent[i]["값"]
        if prev > 0:
            rates.append((curr - prev) / prev * 100)
    return round(sum(rates) / len(rates), 2) if rates else None


def growth_rate_to_score(rate: Optional[float]) -> int:
    """
    성장률(%) → 1~5점
      5점: 10% 이상  (고성장)
      4점:  5~10%
      3점:  0~5%
      2점: -5~0%
      1점: -5% 미만
    """
    if rate is None: return 3
    if rate >= 10:   return 5
    elif rate >= 5:  return 4
    elif rate >= 0:  return 3
    elif rate >= -5: return 2
    else:            return 1


# ──────────────────────────────────────────
# [핵심] C2 코드 직접 입력 → 성장률 점수
# ──────────────────────────────────────────

def get_market_growth_score(
    c2_code: str,
    base_year: int | None = None,
    lookback_years: int = 5,
    api_key: str = None,
) -> dict:
    """
    C2 코드 → 시장 성장률 점수(1~5) 반환
    
    기본값: 최신 연도(전년도)를 기준으로 최근 5년 성장률 계산

    반환: {
        "c2_code": str,
        "sector": str,
        "growth_rate": float | None,
        "score": int,           ← 매출성장성 항목 점수로 사용
        "data": list,
        "start_year": str,
        "end_year": str,
        "fallback": bool
    }
    """
    # 기준 연도 미지정 시 현재 연도 - 1 사용 (KOSIS 최신 데이터)
    if base_year is None:
        base_year = datetime.now().year - 1
    
    start_year = str(base_year - lookback_years)
    end_year   = str(base_year)
    sector     = C2_TO_SECTOR.get(c2_code, c2_code)

    print(f"  KOSIS 조회: C2 {c2_code} ({sector}) | {start_year}~{end_year} ({lookback_years}년 성장률)")

    data = fetch_kosis_revenue(c2_code, start_year, end_year, api_key)

    if not data:
        print(f"  데이터 없음 → 기본값 3점")
        return {
            "c2_code": c2_code, "sector": sector,
            "growth_rate": None, "score": 3,
            "data": [], "start_year": start_year,
            "end_year": end_year, "fallback": True
        }

    growth_rate = calc_growth_rate(data, years=lookback_years)
    score       = growth_rate_to_score(growth_rate)

    return {
        "c2_code":    c2_code,
        "sector":     sector,
        "growth_rate": growth_rate,
        "score":      score,
        "data":       data,
        "start_year": start_year,
        "end_year":   end_year,
        "fallback":   False,
    }


# ──────────────────────────────────────────
# [핵심] 예시 입력 JSON → 성장률 점수
# ──────────────────────────────────────────

def get_growth_score_from_json(
    patent_json: dict,
    base_year: int | None = None,
    lookback_years: int = 5,
    api_key: str = None,
) -> dict:
    """
    example_input.json 구조의 dict를 받아 시장 성장률 점수 반환.
    market_data.related_industry_code (C2 코드) 를 우선 사용.
    없으면 ipc 리스트로 KSIC 매핑 시도.
    
    기본값: 최신 연도(전년도)를 기준으로 최근 5년 성장률 계산

    반환: get_market_growth_score() 결과 +
        "patent_id": str,
        "source_field": str   ← 어느 필드에서 C2를 가져왔는지
    """
    patent_id  = patent_json.get("patent_id", "unknown")
    market     = patent_json.get("market_data", {})
    meta       = patent_json.get("meta", {})

    # 1순위: 시장 데이터의 관련 산업 코드 (C2 코드 직접 기재)
    # 사용자가 이미 산업 코드를 확정해 준 경우가 가장 신뢰도 높습니다.
    c2_code = market.get("related_industry_code")
    source_field = "market_data.related_industry_code"

    # 2순위: KSIC 코드가 있는 경우 (확장 대비)
    # KSIC가 있으면 내부 매핑표를 거치지 않고 KOSIS C2 코드로 변환합니다.
    if not c2_code:
        ksic = market.get("ksic_code")
        if ksic:
            c2_code = KSIC_TO_C2.get(str(ksic))
            source_field = "market_data.ksic_code → KSIC_TO_C2"

    # 3순위: IPC 리스트로 매핑 (IPC-KSIC 매핑 유틸 필요)
    # 특허 데이터만 있는 상황을 위한 대체 경로입니다. IPC→KSIC 매핑은 다대다
    # 성격이 있어 완벽하지 않으므로 source_field에 매핑 방식을 남깁니다.
    if not c2_code:
        ipc_list = meta.get("ipc", [])
        if isinstance(ipc_list, str):
            ipc_list = [ipc_list]
        if ipc_list:
            try:
                from evaluation.ipc_ksic_mapper import load_mapping_table, map_ipc_to_ksic
                df = load_mapping_table(KSIC_RESOURCE_PATH)
                for ipc in ipc_list:
                    mapping = map_ipc_to_ksic(
                        ipc.replace("/", " ").replace("  ", " "),
                        df, use_llm=False
                    )
                    if mapping["method"] in ("exact", "class_fallback", "fallback_ambiguous", "exact_ambiguous") and mapping.get("ksic"):
                        c2_code = KSIC_TO_C2.get(mapping["ksic"])
                        source_field = f"meta.ipc[{ipc}] → KSIC {mapping['ksic']} (method: {mapping['method']})"
                        if c2_code:
                            break
            except Exception as e:
                print(f"  IPC 매핑 실패: {e}")

    if not c2_code:
        print(f"  [{patent_id}] C2 코드 결정 불가 → 기본값 3점")
        return {
            "patent_id": patent_id, "c2_code": None,
            "sector": "미분류", "growth_rate": None,
            "score": 3, "data": [], "fallback": True,
            "source_field": "없음",
        }

    print(f"  [{patent_id}] C2 결정: {c2_code} (출처: {source_field})")

    result = get_market_growth_score(
        c2_code=c2_code,
        base_year=base_year,
        lookback_years=lookback_years,
        api_key=api_key,
    )
    result["patent_id"]    = patent_id
    result["source_field"] = source_field
    return result


# ──────────────────────────────────────────
# IPC → KSIC → C2 → 성장률 점수 (기존 파이프라인 유지)
# ──────────────────────────────────────────

def get_growth_score_from_ipc(
    ipc: str,
    mapping_df: pd.DataFrame,
    title: str = "",
    abstract: str = "",
    base_year: int | None = None,
    lookback_years: int = 5,
    api_key: str = None,
) -> dict:
    """IPC 코드 입력 → KSIC 매핑 → C2 변환 → 성장률 점수
    
    기본값: 최신 연도(전년도)를 기준으로 최근 5년 성장률 계산"""
    from evaluation.ipc_ksic_mapper import map_ipc_to_ksic

    mapping = map_ipc_to_ksic(ipc, mapping_df, title=title,
                               abstract=abstract, use_llm=True)

    if mapping["method"] == "llm_required":
        return {
            "ipc": ipc, "c2_code": None, "sector": None,
            "growth_rate": None, "score": 3,
            "mapping_method": "llm_required",
            "llm_required": True,
            "llm_prompt": mapping["llm_prompt"],
        }

    ksic   = mapping["ksic"]
    c2     = KSIC_TO_C2.get(str(ksic))

    if not c2:
        return {
            "ipc": ipc, "ksic": ksic, "c2_code": None,
            "sector": None, "growth_rate": None, "score": 3,
            "mapping_method": mapping["method"],
            "llm_required": False, "fallback": True,
        }

    result = get_market_growth_score(c2, base_year=base_year, lookback_years=lookback_years, api_key=api_key)
    result.update({
        "ipc":            ipc,
        "ksic":           ksic,
        "mapping_method": mapping["method"],
        "llm_required":   False,
    })
    return result


# ──────────────────────────────────────────
# 실행 예시
# ──────────────────────────────────────────

if __name__ == "__main__":
    if not KOSIS_API_KEY:
        print("❌ KOSIS_API_KEY 없음. .env 확인하세요.")
        exit(1)
    print(f"✅ KOSIS_API_KEY 로드: {KOSIS_API_KEY[:6]}...\n")

    # ── 테스트 1: 예시 입력 JSON 직접 입력 ──
    try:
        with open("example_input.json", encoding="utf-8") as f:
            patent_data = json.load(f)

        print("=" * 60)
        print("[테스트 1] example_input.json → 시장 성장률")
        print("=" * 60)
        result = get_growth_score_from_json(patent_data)

        print(f"\n  특허번호:   {result.get('patent_id')}")
        print(f"  C2 코드:    {result.get('c2_code')} ({result.get('sector')})")
        print(f"  C2 출처:    {result.get('source_field')}")
        print(f"  성장률:     {result.get('growth_rate')}%")
        print(f"  점수:       {result.get('score')}점 / 5점")
        if result.get("data"):
            print("  연도별 매출액(백만원):")
            for row in result["data"]:
                print(f"    {row['연도']}: {row['값']:>15,.0f}")

    except FileNotFoundError:
        print("  example_input.json 없음 → 테스트 2로 진행")

    # ── 테스트 2: C2 코드 직접 입력 ──
    print("\n" + "=" * 60)
    print("[테스트 2] C2 코드 직접 입력 (J63 정보서비스업)")
    print("=" * 60)
    r = get_market_growth_score("J63")
    print(f"\n  C2:     {r['c2_code']} ({r['sector']})")
    print(f"  성장률: {r['growth_rate']}%")
    print(f"  점수:   {r['score']}점 / 5점")
    if r.get("data"):
        print("  연도별 매출액(백만원):")
        for row in r["data"]:
            print(f"    {row['연도']}: {row['값']:>15,.0f}")
