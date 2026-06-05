"""
KIPRIS API - IPC 코드별 특허 건수 조회
- IPC 코드 1개 또는 여러 개를 입력하면 해당 코드 중 하나라도 일치하는 특허 총 건수를 반환
- 건수만 필요하므로 numOfRows=1로 설정해 totalCount만 추출 (API 호출 최소화)

사전 준비:
  pip install requests

API 키 발급:
  https://plus.kipris.or.kr 회원가입 → OpenAPI 신청 → 마이페이지 → 구독에서 키 확인
"""

import os
import requests
import xml.etree.ElementTree as ET
from typing import Union

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
API_KEY  = os.environ.get("KIPRIS_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getWordSearch"


# ─────────────────────────────────────────
# 핵심 함수
# ─────────────────────────────────────────
def get_patent_count_by_ipc(ipc_codes: Union[str, list[str]]) -> dict:
    """
    IPC 코드로 특허 건수 조회

    Args:
        ipc_codes: 단일 문자열 또는 리스트
                   예) "G06Q50/10"
                   예) ["G06Q50/10", "G10L13/08", "G06F16/65"]

    Returns:
        {
            "ipc_query": "G06Q50/10+G10L13/08",  # 실제 API에 보낸 쿼리
            "total_count": 1234,                   # 총 특허 건수
            "status": "success" or "error",
            "message": "..." (에러 시)
        }
    """
    # 리스트면 + 로 연결 (OR 조건)
    if isinstance(ipc_codes, list):
        ipc_query = "+".join(ipc_codes)
    else:
        ipc_query = ipc_codes

    params = {
        "ServiceKey": API_KEY,
        "ipcNumber":  ipc_query,
        "numOfRows":  1,          # 건수만 필요하므로 1건만 요청
        "pageNo":     1,
        "type":       "json",     # json 또는 xml
    }

    try:
        res = requests.get(BASE_URL, params=params, timeout=10)
        res.raise_for_status()

        # JSON 응답 파싱
        if params["type"] == "json":
            data = res.json()
            body = data.get("response", {}).get("body", {})
            total_count = int(body.get("totalCount", 0))
        else:
            # XML 파싱 (fallback)
            root = ET.fromstring(res.text)
            total_elem = root.find(".//totalCount")
            total_count = int(total_elem.text) if total_elem is not None else 0

        return {
            "ipc_query":   ipc_query,
            "total_count": total_count,
            "status":      "success",
        }

    except requests.exceptions.RequestException as e:
        return {"ipc_query": ipc_query, "total_count": 0, "status": "error", "message": str(e)}
    except (KeyError, ValueError, ET.ParseError) as e:
        return {"ipc_query": ipc_query, "total_count": 0, "status": "error", "message": f"파싱 오류: {e}"}


def get_counts_for_multiple_queries(ipc_groups: list) -> list[dict]:
    """
    여러 IPC 그룹에 대해 각각 건수 조회

    Args:
        ipc_groups: 각 원소가 단일 코드(str) 또는 코드 리스트(list)
                    예) ["G06Q50/10", ["G10L13/08", "G06F16/65"]]

    Returns: 각 그룹별 결과 리스트
    """
    results = []
    for group in ipc_groups:
        result = get_patent_count_by_ipc(group)
        results.append(result)
        label = result["ipc_query"]
        count = result["total_count"]
        status = result["status"]
        if status == "success":
            print(f"  [{label}] → {count:,}건")
        else:
            print(f"  [{label}] → 오류: {result.get('message')}")
    return results


# ─────────────────────────────────────────
# 실행
# ─────────────────────────────────────────
if __name__ == "__main__":

    print("=" * 50)
    print("예시 1: 단일 IPC 코드")
    print("=" * 50)
    result = get_patent_count_by_ipc("G06Q50/10")
    print(f"  IPC: {result['ipc_query']}")
    print(f"  총 건수: {result['total_count']:,}건")

    print()
    print("=" * 50)
    print("예시 2: 여러 IPC 코드 (OR 조건 — 하나라도 일치)")
    print("=" * 50)
    ipc_list = ["G06Q50/10", "G10L13/08", "G06F16/65", "G06F16/68"]
    result = get_patent_count_by_ipc(ipc_list)
    print(f"  IPC: {result['ipc_query']}")
    print(f"  총 건수: {result['total_count']:,}건")

    print()
    print("=" * 50)
    print("예시 3: 여러 그룹 각각 조회")
    print("=" * 50)
    groups = [
        "G06Q50/10",                              # 단일
        ["G10L13/08", "G06F16/65"],               # OR 묶음
        ["G06Q50/10", "G10L13/08", "G06F16/68"], # OR 묶음 (3개)
    ]
    get_counts_for_multiple_queries(groups)
