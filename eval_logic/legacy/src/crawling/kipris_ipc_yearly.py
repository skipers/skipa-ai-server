"""
KIPRIS Plus API - IPC 코드 연도별 특허 출원 건수 조회 (최근 10년)
- API: getAdvancedSearch
- IPC OR 조건: ipcNumber 파라미터에 + 연산자로 연결 (예: G06Q50/10+G10L13/08)
- 날짜 형식: 20160101~20161231

사전 준비: pip install requests
"""

import os
import requests
import xml.etree.ElementTree as ET
import csv
import sys
from datetime import datetime
from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.paths import ARTIFACT_CRAWLING_DIR  # noqa: E402

# ─────────────────────────────────────────
# 설정  <- 여기만 수정하면 됩니다
# ─────────────────────────────────────────
API_KEY = os.environ.get("KIPRIS_API_KEY", "YOUR_API_KEY_HERE")

IPC_CODES = [
    "G06Q50/10",
    "G10L13/08",
    "G06F16/65",
    "G06F16/68",
]

THIS_YEAR  = datetime.now().year
START_YEAR = THIS_YEAR - 10   # 2015
END_YEAR   = THIS_YEAR - 1    # 2024

OUTPUT_CSV = ARTIFACT_CRAWLING_DIR / "ipc_yearly_count.csv"
BASE_URL   = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"


# ─────────────────────────────────────────
# 건수 조회
# ─────────────────────────────────────────
def query_count(ipc_query: str, year: int) -> int:
    """IPC OR 조건 + 출원연도의 특허 건수 반환 (numOfRows=1로 totalCount만 추출)"""
    params = {
        "ServiceKey":      API_KEY,
        "ipcNumber":       ipc_query,           # + 연산자로 OR 조건
        "applicationDate": f"{year}0101~{year}1231",
        "patent":          "true",
        "utility":         "false",
        "numOfRows":       1,
        "pageNo":          1,
        "sortSpec":        "AD",
        "descSort":        "false",
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=15)
        res.raise_for_status()
        root = ET.fromstring(res.text)

        result_code = root.findtext(".//resultCode", "")
        if result_code not in ("00", "000", ""):
            msg = root.findtext(".//resultMsg", "오류")
            print(f"    API 오류 [{result_code}]: {msg}")
            return -1

        total_elem = root.find(".//totalCount")
        return int(total_elem.text) if total_elem is not None else 0

    except requests.exceptions.RequestException as e:
        print(f"    요청 오류: {e}")
        return -1
    except ET.ParseError as e:
        print(f"    XML 파싱 오류: {e}")
        return -1


# ─────────────────────────────────────────
# 연도별 집계
# ─────────────────────────────────────────
def fetch_yearly_counts() -> list:
    ipc_query = "+".join(IPC_CODES)  # OR 조건

    print(f"IPC 쿼리: {ipc_query}")
    print(f"조회 기간: {START_YEAR} ~ {END_YEAR}년 (출원일 기준)")
    print("-" * 40)

    results = []
    for year in range(START_YEAR, END_YEAR + 1):
        count = query_count(ipc_query, year)
        note = " (※미공개로 과소집계 가능)" if year >= THIS_YEAR - 2 else ""

        if count >= 0:
            print(f"  {year}년: {count:,}건{note}")
        else:
            print(f"  {year}년: 조회 실패")
            count = None

        results.append({"year": year, "count": count})

    return results


# ─────────────────────────────────────────
# 저장 및 요약
# ─────────────────────────────────────────
def save_csv(results: list):
    ipc_str = " | ".join(IPC_CODES)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["연도", "출원 건수", "IPC 조건(OR)"])
        for i, row in enumerate(results):
            count = row["count"] if row["count"] is not None else "오류"
            writer.writerow([row["year"], count, ipc_str if i == 0 else ""])
    print(f"\n저장 완료: {OUTPUT_CSV}")


def print_summary(results: list):
    valid = [r for r in results if r["count"] is not None]
    if not valid:
        print("집계된 데이터가 없습니다.")
        return
    total = sum(r["count"] for r in valid)
    peak  = max(valid, key=lambda r: r["count"])
    print(f"\n{'='*40}")
    print(f"기간 합계 : {total:,}건")
    print(f"최다 출원 : {peak['year']}년 ({peak['count']:,}건)")
    print(f"※ {THIS_YEAR-2}~{END_YEAR}년은 미공개 특허로 실제보다 적을 수 있음")


# ─────────────────────────────────────────
# 실행
# ─────────────────────────────────────────
if __name__ == "__main__":
    results = fetch_yearly_counts()
    print_summary(results)
    save_csv(results)
