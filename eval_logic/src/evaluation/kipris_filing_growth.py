"""KIPRIS IPC yearly filing activity adapter."""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from typing import Any

import requests

from core.env import load_runtime_env
from core.paths import KIPRIS_CRAWLING_DIR


load_runtime_env()

KIPRIS_PLUS_URL = "https://plus.kipris.or.kr/portal/main.do"
KIPRIS_ADVANCED_SEARCH_URL = (
    "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"
)
KIPRIS_API_KEY = os.environ.get("KIPRIS_API_KEY")


def _normalize_ipc(value: Any) -> str:
    text = re.sub(r"\s+", "", str(value or "").strip())
    text = re.sub(r"\(\d{4}(?:\.\d+)?\)$", "", text)
    return text


def extract_ipc_codes(patent: dict[str, Any], limit: int = 3) -> list[str]:
    meta = patent.get("meta") if isinstance(patent.get("meta"), dict) else {}
    raw = meta.get("ipc") or patent.get("ipc") or patent.get("ipc_codes") or []
    if not isinstance(raw, list):
        raw = [raw]
    codes: list[str] = []
    for value in raw:
        code = _normalize_ipc(value)
        if code and code not in codes:
            codes.append(code)
        if len(codes) >= limit:
            break
    return codes


def _year_window(years: int = 5) -> list[int]:
    # 출원 공개 지연으로 최근 18개월 안팎은 과소 집계될 수 있다.
    # 보고서 점수 왜곡을 피하기 위해 최근 5개 공개완료 연도를 기본 창으로 둔다.
    end_year = datetime.now().year - 3
    start_year = end_year - years + 1
    return list(range(start_year, end_year + 1))


def _query_count(*, year: int, ipc_query: str | None) -> int:
    if not KIPRIS_API_KEY:
        raise RuntimeError("KIPRIS_API_KEY 환경변수가 설정되어 있지 않습니다.")

    params = {
        "ServiceKey": KIPRIS_API_KEY,
        "applicationDate": f"{year}0101~{year}1231",
        "patent": "true",
        "utility": "false",
        "numOfRows": 1,
        "pageNo": 1,
        "sortSpec": "AD",
        "descSort": "false",
    }
    if ipc_query:
        params["ipcNumber"] = ipc_query

    response = requests.get(KIPRIS_ADVANCED_SEARCH_URL, params=params, timeout=15)
    response.raise_for_status()
    root = ET.fromstring(response.text)
    result_code = root.findtext(".//resultCode", "")
    if result_code not in ("", "00", "000"):
        result_msg = root.findtext(".//resultMsg", "")
        raise RuntimeError(f"KIPRIS API error {result_code}: {result_msg or '-'}")
    total = root.findtext(".//totalCount")
    return int(total or 0)


def _growth_rate(counts: list[dict[str, int]]) -> float | None:
    nonzero = [row for row in counts if row.get("count", 0) > 0]
    if len(nonzero) < 2:
        return None
    first = nonzero[0]["count"]
    last = nonzero[-1]["count"]
    if first <= 0:
        return None
    return round(((last - first) / first) * 100, 2)


def _score_from_growth(growth_rate: float | None, total_growth_rate: float | None) -> int:
    if growth_rate is None:
        return 3
    if total_growth_rate is not None and total_growth_rate > 0:
        ratio = growth_rate / total_growth_rate
        if ratio >= 4:
            return 5
        if ratio >= 2:
            return 4
        if ratio >= 0.8:
            return 3
        if growth_rate >= -20:
            return 2
        return 1
    if growth_rate >= 80:
        return 5
    if growth_rate >= 20:
        return 4
    if growth_rate >= 0:
        return 3
    if growth_rate >= -20:
        return 2
    return 1


def _fallback(reason: str, ipc_codes: list[str] | None = None) -> dict[str, Any]:
    return {
        "source": "KIPRIS IPC yearly application count",
        "ipc_codes": ipc_codes or [],
        "growth_rate": None,
        "total_growth_rate": None,
        "years": _year_window(),
        "yearly_counts": [],
        "total_yearly_counts": [],
        "score": 3,
        "fallback": True,
        "error": reason,
        "url": KIPRIS_PLUS_URL,
    }


def _cache_path(ipc_codes: list[str], years: list[int]) -> Path:
    slug = re.sub(r"[^0-9A-Za-z]+", "_", "_".join(ipc_codes)).strip("_") or "unknown"
    return KIPRIS_CRAWLING_DIR / f"ipc_yearly_growth_{slug}_{years[0]}_{years[-1]}.json"


def get_patent_filing_growth_score(patent: dict[str, Any], years: int = 5) -> dict[str, Any]:
    ipc_codes = extract_ipc_codes(patent)
    if not ipc_codes:
        return _fallback("IPC 코드가 없어 KIPRIS 출원 증가율을 조회하지 못했습니다.", ipc_codes)

    year_values = _year_window(years)
    cache = _cache_path(ipc_codes, year_values)
    if cache.exists():
        with cache.open(encoding="utf-8") as file:
            return json.load(file)

    ipc_query = "+".join(ipc_codes)
    try:
        yearly_counts = [{"year": year, "count": _query_count(year=year, ipc_query=ipc_query)} for year in year_values]
        total_counts = [{"year": year, "count": _query_count(year=year, ipc_query=None)} for year in year_values]
        growth_rate = _growth_rate(yearly_counts)
        total_growth_rate = _growth_rate(total_counts)
        result = {
            "source": "KIPRIS IPC yearly application count",
            "ipc_codes": ipc_codes,
            "ipc_query": ipc_query,
            "growth_rate": growth_rate,
            "total_growth_rate": total_growth_rate,
            "growth_ratio": (
                round(growth_rate / total_growth_rate, 2)
                if growth_rate is not None and total_growth_rate not in (None, 0)
                else None
            ),
            "years": year_values,
            "yearly_counts": yearly_counts,
            "total_yearly_counts": total_counts,
            "score": _score_from_growth(growth_rate, total_growth_rate),
            "fallback": growth_rate is None,
            "url": KIPRIS_PLUS_URL,
        }
    except Exception as exc:
        result = _fallback(str(exc), ipc_codes)

    cache.parent.mkdir(parents=True, exist_ok=True)
    with cache.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    return result
