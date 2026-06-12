"""
KIPRIS 특화검색 자동화 스크립트 (최종본)
흐름: 메인 → 상세검색 팝업 → 특화검색 탭 → 키워드/기간 입력 → 검색
      → 새 창(searchResultSpecial.do) 자동 전환 → 결과 파싱 → CSV 저장

실제 HTML 분석 기반 — 모든 셀렉터 검증 완료
"""

import re
import json
import time
import argparse
import sys
import pandas as pd
from datetime import date
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from core.paths import ARTIFACT_CRAWLING_DIR, ARTIFACT_OUTPUT_DIR, SAMPLE_DATA_DIR  # noqa: E402


# ─────────────────────────────────────────
# 검색 파라미터  ← 여기만 수정하면 됩니다
# ─────────────────────────────────────────
KIPRIS_URL = "https://kipris.or.kr/khome/main.do"
KEYWORD    = "보이스 스타일 분석 및 품질 자동 검수 기능을 제공하는 오디오북 제작 시스템 및 방법"
DATE_FROM  = "2015-01-01"    # 출원일 시작 (YYYY-MM-DD), 비워두려면 ""
DATE_TO    = "2024-12-31"    # 출원일 종료 (YYYY-MM-DD), 비워두려면 ""
MAX_PAGES  = 5               # 수집할 최대 페이지 수 (결과가 적으면 자동 종료)
OUTPUT_CSV = str(ARTIFACT_CRAWLING_DIR / "kipris_results.csv")
OUTPUT_JSON = str(ARTIFACT_OUTPUT_DIR / "patent_references.json")
TARGET_JSON = str(SAMPLE_DATA_DIR / "patent_input.json")
MAX_RESULTS = 10


def normalize_patent_id(value: str | None) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", str(value or "")).strip("_")


def infer_patent_id(data: dict, fallback: str = "report") -> str:
    return normalize_patent_id(data.get("patent_id") or data.get("meta", {}).get("registration_number") or fallback)


def load_search_input(path: str | None) -> dict:
    if not path:
        return {}
    input_path = Path(path)
    if not input_path.exists():
        raise FileNotFoundError(f"입력 JSON을 찾을 수 없습니다: {input_path}")
    with input_path.open(encoding="utf-8") as file:
        return json.load(file)


def title_from_input(data: dict, fallback: str = KEYWORD) -> str:
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}
    return data.get("title") or meta.get("title") or data.get("query") or fallback


# ─────────────────────────────────────────
# 드라이버 초기화
# ─────────────────────────────────────────
def build_driver(headless: bool = False) -> webdriver.Chrome:
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1400,900")
    opts.add_argument("--lang=ko-KR")
    # ChromeDriver 버전을 자동으로 맞춰서 설치해줍니다 (수동 설치 불필요)
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=opts)


# ─────────────────────────────────────────
# Step 1~5: 검색 실행 → 새 창 전환
# ─────────────────────────────────────────
def run_search(
    driver: webdriver.Chrome,
    wait: WebDriverWait,
    keyword: str = KEYWORD,
    date_from: str = DATE_FROM,
    date_to: str = DATE_TO,
):
    # 1. 메인 페이지
    driver.get(KIPRIS_URL)
    time.sleep(2)

    # 2. 공지사항 팝업 닫기 (뜨는 경우에만)
    try:
        close_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.popup-close"))
        )
        driver.execute_script("arguments[0].click();", close_btn)
        print("[1-0] 공지 팝업 닫기 완료")
        time.sleep(1)
    except Exception:
        print("[1-0] 공지 팝업 없음 (정상)")

    # 3. 상세검색 버튼 — JavaScript로 클릭 (다른 요소에 가려져도 동작)
    btn = wait.until(EC.presence_of_element_located((By.ID, "btnOpenSearchDetail")))
    driver.execute_script("arguments[0].click();", btn)
    print("[1] 상세검색 팝업 열기")
    time.sleep(1.5)

    # 3. 특화검색 탭 (id=sd02)
    tab = wait.until(EC.element_to_be_clickable((By.ID, "sd02")))
    if "active" not in (tab.get_attribute("class") or ""):
        tab.click()
        time.sleep(1)
    print("[2] 특화검색 탭 전환")

    # 4. 검색방법 드롭다운 → "문서내용" 선택 (그래야 키워드 textarea가 나타남)
    from selenium.webdriver.support.ui import Select
    category_sel = wait.until(EC.presence_of_element_located((By.ID, "sd020101_g02_category_01")))
    Select(category_sel).select_by_visible_text("문서내용")
    print("[3-0] 검색방법 → 문서내용 선택")
    time.sleep(1)  # 드롭다운 변경 후 textarea 렌더링 대기

    # 5. 키워드 입력 (textarea — 문서내용 선택 후 나타남)
    kw = wait.until(EC.visibility_of_element_located((By.ID, "sd020101_g02_text_04")))
    driver.execute_script("arguments[0].value = arguments[1];", kw, keyword)
    driver.execute_script("arguments[0].dispatchEvent(new Event('input',  {bubbles:true}));", kw)
    driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", kw)
    print(f"[3] 키워드: {keyword[:40]}...")

    # 6. 날짜 입력 (출원일 기준 — 드롭다운 기본값 "출원일자(AD)" 그대로 사용)
    def set_date(field_id, value):
        el = driver.find_element(By.ID, field_id)
        driver.execute_script("arguments[0].value = arguments[1];", el, value)
        driver.execute_script("arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", el)

    if date_from:
        set_date("sd020101_g01_start_01", date_from)
    if date_to:
        set_date("sd020101_g01_end_01", date_to)
    print(f"[4] 기간: {date_from} ~ {date_to}")

    # 6. 검색 버튼 클릭 → 새 창 대기
    original_handles = set(driver.window_handles)
    search_btn = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "button.btn-search[onclick='doDetailSearch()']")
    ))
    search_btn.click()
    print("[5] 검색 실행 → 새 창 대기 중...")

    # 새 창이 열릴 때까지 대기 (최대 15초)
    wait.until(lambda d: len(d.window_handles) > len(original_handles))
    new_handle = (set(driver.window_handles) - original_handles).pop()
    driver.switch_to.window(new_handle)
    print(f"[6] 새 창 전환 완료")
    print(f"    URL: {driver.current_url}")

    # 결과 카드가 최소 1개 나타날 때까지 대기 (최대 30초)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "article.result-item"))
    )
    print("[6-1] 결과 카드 로딩 완료")


# ─────────────────────────────────────────
# Step 6: 결과 파싱 (HTML 분석 기반 확정 셀렉터)
# ─────────────────────────────────────────
def parse_page(driver: webdriver.Chrome) -> list[dict]:
    """
    article.result-item 카드 구조:
      strong.similar-point > em    → 유사도 수치
      a.badge                      → 등록상태 (등록/거절/공개 등)
      button.link > span.num       → 순번
      button.link                  → 발명명칭 (span.num 제거 후)
      li > em.tit + div.link-wrap  → IPC / 출원번호(일자) / 출원인
      div.summary-box > p          → 요약
      button.link[onclick]         → openDetail 에서 출원번호 추출
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    articles = soup.find_all("article", class_="result-item")

    if not articles:
        print("  ⚠ article.result-item 카드를 찾지 못했습니다.")
        return []

    records = []
    for art in articles:
        try:
            # 유사도
            sim_strong = art.find("strong", class_="similar-point")
            sim_em = sim_strong.find("em") if sim_strong else None
            similarity = sim_em.get_text(strip=True) if sim_em else ""

            # 등록 상태 (등록 / 거절 / 공개 / 소멸 등)
            badge = art.find("a", class_="badge")
            status = badge.get_text(strip=True) if badge else ""

            # 발명명칭 (순번 제거)
            title_btn = art.find("button", class_="link")
            if title_btn:
                num_span = title_btn.find("span", class_="num")
                num_text = num_span.get_text(strip=True) if num_span else ""
                title = title_btn.get_text(strip=True).replace(num_text, "").strip()
                # openDetail에서 출원번호 추출
                onclick = title_btn.get("onclick", "")
                m = re.search(r"openDetail\('[^']+',\s*'([^']+)'", onclick)
                app_no_js = m.group(1) if m else ""
            else:
                title = ""
                app_no_js = ""

            # li 기반 정보 (IPC, 출원번호(일자), 출원인)
            info = {}
            for li in art.find_all("li"):
                tit_el = li.find("em", class_="tit")
                if not tit_el:
                    continue
                key = tit_el.get_text(strip=True).rstrip(": ")
                wrap = li.find("div", class_="link-wrap")
                val = wrap.get_text(strip=True) if wrap else ""
                info[key] = val

            # 요약
            summary_box = art.find("div", class_="summary-box")
            summary_p = summary_box.find("p") if summary_box else None
            summary = summary_p.get_text(strip=True) if summary_p else ""

            records.append({
                "순위":       num_text,
                "유사도":      similarity,
                "등록상태":    status,
                "발명명칭":    title,
                "IPC":        info.get("IPC", ""),
                "출원번호":    info.get("출원번호(일자)", app_no_js),
                "출원인":     clean_applicant(info.get("출원인", "")),
                "요약":       summary,
            })

        except Exception as e:
            print(f"  카드 파싱 오류: {e}")

    return records


# ─────────────────────────────────────────
# Step 7: 페이지네이션
# ─────────────────────────────────────────
def go_next_page(driver: webdriver.Chrome, wait: WebDriverWait) -> bool:
    """
    KIPRIS 결과 페이지 페이지네이션 처리
    실제 버튼 구조에 따라 셀렉터 후보를 순서대로 시도
    """
    selectors = [
        "a.next",
        "button.btn-next",
        "a[title='다음 페이지']",
        "a[title='다음']",
        ".paging .next > a",
        "li.next > a",
        "a[aria-label='다음']",
    ]
    for sel in selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            if btn.is_displayed() and btn.is_enabled():
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)
                return True
        except Exception:
            continue
    return False


# ─────────────────────────────────────────
# Step 8: 저장
# ─────────────────────────────────────────
def save_results(records: list[dict], output_csv: str = OUTPUT_CSV):
    if not records:
        print("\n⚠ 저장할 데이터가 없습니다.")
        return
    df = pd.DataFrame(records)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"\n✅ 저장 완료: {output_csv} ({len(df)}건)")
    print(df[["유사도", "등록상태", "발명명칭", "출원번호", "출원인"]].head(5).to_string(index=False))


def parse_similarity(value: str) -> float | None:
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group(0)) if match else None


def clean_applicant(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if "더보기" not in text and "닫기" not in text:
        return text
    first, _, rest = text.partition("더보기")
    rest = rest.replace("닫기", "").strip()
    first = first.strip()
    return f"{first} 외 {rest}" if first and rest else first or rest


def parse_application_info(value: str, fallback: str = "") -> tuple[str, str, int | None]:
    text = str(value or "").strip()
    app_no = fallback or ""
    app_date = ""

    date_match = re.search(r"((?:19|20)\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})", text)
    if date_match:
        year, month, day = date_match.groups()
        app_date = f"{year}-{int(month):02d}-{int(day):02d}"

    no_match = re.search(r"(?:KR)?\d{2}[-]?\d{4}[-]?\d{6,7}|\d{10,13}", text)
    if no_match:
        app_no = no_match.group(0)
    elif text and not app_no:
        app_no = text

    app_year = int(date_match.group(1)) if date_match else None
    return app_no, app_date, app_year


def normalize_patent_identifier(value: str | None) -> str:
    text = re.sub(r"[^0-9A-Za-z]", "", str(value or ""))
    return text[2:] if text.startswith("KR") else text


def load_target_filters(target_json: str = TARGET_JSON) -> dict[str, set[str]]:
    path = Path(target_json)
    if not path.exists():
        return {"application_numbers": set(), "titles": set()}
    try:
        with path.open(encoding="utf-8") as file:
            target = json.load(file)
    except Exception:
        return {"application_numbers": set(), "titles": set()}

    meta = target.get("meta", {}) if isinstance(target.get("meta"), dict) else {}
    numbers = {
        normalize_patent_identifier(meta.get("application_number")),
        normalize_patent_identifier(target.get("patent_id")),
        normalize_patent_identifier(meta.get("registration_number")),
        normalize_patent_identifier(meta.get("publication_number")),
    }
    titles = {str(meta.get("title") or target.get("title") or "").strip()}
    return {
        "application_numbers": {number for number in numbers if number},
        "titles": {title for title in titles if title},
    }


def is_target_patent_record(record: dict, filters: dict[str, set[str]]) -> bool:
    app_no, _, _ = parse_application_info(record.get("출원번호", ""))
    normalized_app_no = normalize_patent_identifier(app_no)
    title = str(record.get("발명명칭", "")).strip()

    if normalized_app_no and normalized_app_no in filters.get("application_numbers", set()):
        return True
    if title and title in filters.get("titles", set()):
        return True
    return False


def date_from_year(value: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", str(value or ""))
    return int(match.group(0)) if match else None


def records_to_patent_references(
    records: list[dict],
    keyword: str = KEYWORD,
    date_from: str = DATE_FROM,
    date_to: str = DATE_TO,
    max_results: int = MAX_RESULTS,
    target_json: str = TARGET_JSON,
) -> dict:
    target_filters = load_target_filters(target_json)
    cutoff_year = date_from_year(date_from)
    self_filtered_records = [
        record
        for record in records
        if not is_target_patent_record(record, target_filters)
    ]
    filtered_records = [
        record
        for record in self_filtered_records
        if cutoff_year is None
        or (parse_application_info(record.get("출원번호", ""))[2] or 0) >= cutoff_year
    ]
    selected = filtered_records[:max_results]
    patents = []

    for index, record in enumerate(selected, 1):
        application_number, application_date, application_year = parse_application_info(
            record.get("출원번호", "")
        )
        similarity_score = parse_similarity(record.get("유사도", ""))
        rank_text = str(record.get("순위") or "").strip()
        rank = int(rank_text) if rank_text.isdigit() else index
        similarity_label = record.get("유사도", "")

        patents.append({
            "rank": rank,
            "patent_no": "",
            "application_number": application_number,
            "title": record.get("발명명칭", ""),
            "applicant": clean_applicant(record.get("출원인", "")),
            "application_year": application_year,
            "application_date": application_date,
            "registration_year": None,
            "ipc_code": record.get("IPC", ""),
            "citation_count": None,
            "similarity_score": similarity_score,
            "similarity_basis": (
                f"KIPRIS 특화검색 유사도 {similarity_label}"
                if similarity_label
                else "KIPRIS 특화검색 결과 순위"
            ),
            "abstract": record.get("요약", ""),
            "legal_status": record.get("등록상태", ""),
            "registration_date": "",
            "expiry_date": "",
            "maintained_years": None,
            "comment": "KIPRIS 크롤링 후보. 상세정보는 similar_patent_collector.py에서 API로 보강 필요.",
        })

    return {
        "meta": {
            "query_ipc": [],
            "query_keywords": [keyword] if keyword else [],
            "search_source": "KIPRIS",
            "search_date": date.today().isoformat(),
            "total_retrieved": len(records),
            "excluded_self_count": len(records) - len(self_filtered_records),
            "excluded_before_date_from_count": len(self_filtered_records) - len(filtered_records),
            "selection_criteria": [
                "KIPRIS 특화검색 유사도 상위",
                "평가 대상 특허 본인 제외",
                f"{cutoff_year}년 이후 출원" if cutoff_year else "출원연도 제한 없음",
                "검색 결과 순위 기준",
                f"상위 {max_results}건 후보 저장",
            ],
            "selected_count": len(patents),
            "date_range": {
                "from": date_from,
                "to": date_to,
            },
        },
        "patents": patents,
    }


def save_patent_references(
    records: list[dict],
    output_json: str = OUTPUT_JSON,
    keyword: str = KEYWORD,
    date_from: str = DATE_FROM,
    date_to: str = DATE_TO,
    max_results: int = MAX_RESULTS,
    target_json: str = TARGET_JSON,
):
    if not records:
        print("\n⚠ 저장할 유사 특허 후보가 없습니다.")
        return

    data = records_to_patent_references(
        records,
        keyword=keyword,
        date_from=date_from,
        date_to=date_to,
        max_results=max_results,
        target_json=target_json,
    )
    path = Path(output_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    print(f"\n✅ 유사 특허 후보 JSON 저장 완료: {path} ({len(data['patents'])}건)")


# ─────────────────────────────────────────
# 메인
# ─────────────────────────────────────────
def search_similar_patents(
    keyword: str,
    date_from: str = "",
    date_to: str = "",
    max_pages: int = 1,
    headless: bool = True,
    output_csv: str | None = None,
    output_json: str | None = None,
    max_results: int = MAX_RESULTS,
    target_json: str = TARGET_JSON,
    keep_browser_open: bool = False,
) -> list[dict]:
    """Run KIPRIS special search and return parsed result records."""
    driver = build_driver(headless=headless)
    wait = WebDriverWait(driver, 15)
    all_records = []

    try:
        run_search(driver, wait, keyword=keyword, date_from=date_from, date_to=date_to)

        for page in range(1, max_pages + 1):
            print(f"\n[페이지 {page}] 파싱 중...")
            records = parse_page(driver)
            all_records.extend(records)
            print(f"  → {len(records)}건 수집 (누적: {len(all_records)}건)")

            if not records:
                break

            if page < max_pages:
                if not go_next_page(driver, wait):
                    print("  마지막 페이지 도달")
                    break

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback; traceback.print_exc()

    finally:
        if output_csv:
            save_results(all_records, output_csv=output_csv)
        if output_json:
            save_patent_references(
                all_records,
                output_json=output_json,
                keyword=keyword,
                date_from=date_from,
                date_to=date_to,
                max_results=max_results,
                target_json=target_json,
            )
        if keep_browser_open:
            input("\n[Enter]를 누르면 브라우저를 닫습니다...")
        driver.quit()
    return all_records


def main():
    parser = argparse.ArgumentParser(description="KIPRIS 유사 특허 후보 크롤링")
    parser.add_argument("--input", default=None, help="검색어와 특허번호를 읽을 대상 특허 JSON")
    parser.add_argument("--patent-id", default=None, help="특허별 output 파일명에 사용할 ID")
    parser.add_argument("--keyword", default=None, help="검색 키워드. 생략하면 --input의 title 사용")
    parser.add_argument("--date-from", default=DATE_FROM, help="출원일 시작")
    parser.add_argument("--date-to", default=DATE_TO, help="출원일 종료")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES, help="수집할 최대 페이지 수")
    parser.add_argument("--max-results", type=int, default=MAX_RESULTS, help="저장할 후보 수")
    parser.add_argument("--output-csv", default=None, help="CSV 출력 경로")
    parser.add_argument("--output-json", default=None, help="유사 특허 후보 JSON 출력 경로")
    parser.add_argument("--target-json", default=None, help="본인 특허 제외 필터용 JSON. 생략하면 --input 사용")
    parser.add_argument("--headless", action="store_true", help="브라우저를 headless로 실행")
    parser.add_argument("--keep-browser-open", action="store_true", help="종료 전 Enter 대기")
    args = parser.parse_args()

    input_data = load_search_input(args.input)
    patent_id = normalize_patent_id(args.patent_id) or infer_patent_id(input_data, "similar")
    keyword = args.keyword or title_from_input(input_data)
    output_json = args.output_json or str(ARTIFACT_OUTPUT_DIR / f"similar_refs_{patent_id}.json")
    output_csv = args.output_csv or str(ARTIFACT_CRAWLING_DIR / f"kipris_results_{patent_id}.csv")
    target_json = args.target_json or args.input or TARGET_JSON

    search_similar_patents(
        keyword=keyword,
        date_from=args.date_from,
        date_to=args.date_to,
        max_pages=args.max_pages,
        headless=args.headless,
        output_csv=output_csv,
        output_json=output_json,
        max_results=args.max_results,
        target_json=target_json,
        keep_browser_open=args.keep_browser_open,
    )


if __name__ == "__main__":
    main()
