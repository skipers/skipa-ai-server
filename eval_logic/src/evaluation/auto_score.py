"""규칙 기반 특허 가치 평가 점수 계산기입니다.

이 모듈은 LLM을 호출하지 않고 입력 JSON의 정형 필드만으로 계산 가능한
평가 항목을 담당합니다. 실제 서비스 관점에서는 다음 성격을 가집니다.

1. 빠르고 비용이 들지 않는 결정론적 평가 단계입니다.
2. 외부 API나 LLM 장애와 무관하게 최소한의 점수를 산출합니다.
3. 각 항목의 ``basis``는 보고서에서 사용자에게 그대로 노출될 수 있으므로
   계산에 사용한 원천 숫자와 대체값 적용 여부를 명확히 담아야 합니다.

[자동 계산 가능 항목 - 총 5개]

권리성 (3개):
  - IP 원천성          : 심사관 인용 선행기술 수 + 피인용수
  - 권리의 충실성       : 청구항 수, 발명 카테고리, 해외출원 여부
  - 권리행사 제한 가능성 : 공유특허(발명자/권리자 수) 여부

시장성 (1개):
  - 특허출원 활성도     : IPC별 최근 5년 출원 증가율 (KIPRIS)

사업성 (1개):
  - 매출 성장성        : KOSIS 시장 성장률

[사용법]
  from Auto_score import calc_auto_scores
  scores = calc_auto_scores(patent_json)
"""


# ──────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────

def to_score(raw: float, thresholds: list) -> int:
    """
    raw 값을 thresholds 기준으로 1~5점 변환
    thresholds = [5점기준, 4점기준, 3점기준, 2점기준]  (내림차순)
    예: raw=10, thresholds=[8,5,2,0] → 5점
    """
    for i, t in enumerate(thresholds):
        if raw >= t:
            return 5 - i
    return 1


def safe_get(d: dict, *keys, default=None):
    """중첩 딕셔너리에 안전하게 접근합니다.

    프로토타입 데이터는 ``meta``, ``kipris_data`` 같은 선택 블록이 없을 수
    있습니다. 자동 점수 계산기는 필드 누락으로 전체 파이프라인을 멈추기보다
    기본값 기반 평가를 계속하도록 설계되어 있습니다.
    """
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
        if d is None:
            return default
    return d


def claim_text_value(claim: object) -> str:
    """문자열/표준 dict 청구항을 자동 점수 계산용 텍스트로 통일합니다."""
    if isinstance(claim, dict):
        return str(claim.get("text") or "")
    return str(claim or "")


# ──────────────────────────────────────────
# 권리성 자동 계산 항목
# ──────────────────────────────────────────

def score_ip_origin(patent: dict) -> dict:
    """
    IP 원천성 (권리성)
    - 심사관 인용 선행기술 수 (적을수록 원천성 높음)
    - 피인용수 (많을수록 원천성 높음)

    점수 기준:
      5점: 선행기술 0~1건 AND 피인용 5건 이상
      4점: 선행기술 1~2건 OR 피인용 1건 이상
      3점: 선행기술 3~4건, 피인용 없음
      2점: 선행기술 5~7건
      1점: 선행기술 8건 이상
    """
    # 선행기술 인용은 많을수록 기존 기술과 가까울 가능성이 있으므로 감점
    # 요소입니다. 반대로 피인용 수는 후속 특허가 이 권리를 참조했다는
    # 신호로 보고 원천성 가산 요소로 사용합니다.
    prior_arts  = safe_get(patent, "meta", "prior_art_cited", default=[])
    cited_count = safe_get(patent, "kipris_data", "cited_count", default=0) or 0
    prior_count = len(prior_arts)

    if prior_count <= 1 and cited_count >= 5:
        score = 5
    elif prior_count <= 2 or cited_count >= 1:
        score = 4
    elif prior_count <= 4:
        score = 3
    elif prior_count <= 7:
        score = 2
    else:
        score = 1

    return {
        "item":    "IP 원천성",
        "dim":     "권리성",
        "score":   score,
        "basis":   f"심사관인용선행기술 {prior_count}건, 피인용수 {cited_count}건",
        "method":  "auto"
    }


def score_right_faithfulness(patent: dict) -> dict:
    """
    권리의 충실성 (권리성)
    - 발명 카테고리 수 (청구항 내 장치/방법/시스템 등 구분)
    - 전체 청구항 수
    - 해외출원 여부 (family_patents)

    점수 기준:
      5점: 해외출원 있음 + 청구항 10개 이상
      4점: 해외출원 있음 OR 청구항 7개 이상
      3점: 청구항 4~6개
      2점: 청구항 2~3개
      1점: 청구항 1개 이하
    """
    # 청구항 수와 해외 패밀리 여부는 권리 포트폴리오의 충실도를 판단하는
    # 대표 정형 지표입니다. 청구항 텍스트가 있으면 장치/방법 등 카테고리도
    # 간단히 추정해 근거 문장에 포함합니다.
    total_claims  = safe_get(patent, "meta", "total_claims",  default=0) or 0
    family_patents = safe_get(patent, "kipris_data", "family_patents", default=[])
    has_overseas   = len(family_patents) > 0

    # 청구항 텍스트에서 카테고리 추정 (장치/방법/시스템)
    claims_text = safe_get(patent, "claims_text", default={})
    categories  = set()
    for text in claims_text.values():
        t = claim_text_value(text)
        if any(k in t for k in ["시스템", "장치", "서버", "단말"]):
            categories.add("장치")
        if any(k in t for k in ["방법", "단계", "수행하는"]):
            categories.add("방법")
    cat_count = max(len(categories), 1)

    if has_overseas and total_claims >= 10:
        score = 5
    elif has_overseas or total_claims >= 7:
        score = 4
    elif total_claims >= 4:
        score = 3
    elif total_claims >= 2:
        score = 2
    else:
        score = 1

    return {
        "item":   "권리의 충실성",
        "dim":    "권리성",
        "score":  score,
        "basis":  f"청구항 {total_claims}개, 카테고리 {cat_count}개, 해외출원 {'있음' if has_overseas else '없음'}",
        "method": "auto"
    }


def score_right_restriction(patent: dict) -> dict:
    """
    권리행사 제한 가능성 (권리성)
    - 공동 출원인/발명자 수 → 공유특허 여부
    - 심판이력 내 실시권 설정 여부

    점수 기준:
      5점: 단독 출원인, 심판이력 없음
      4점: 공동 출원인 2인, 심판이력 없음
      3점: 공동 출원인 3인 이하
      2점: 공동 출원인 4인 이상 or 심판이력 있음
      1점: 실시권 설정 이력 있음
    """
    # 공동 권리자가 많거나 심판/실시권 관련 이력이 있으면 단독으로 권리를
    # 행사하기 어려워질 수 있으므로 제한 가능성 점수를 낮춥니다.
    assignee       = safe_get(patent, "meta", "assignee", default=[])
    dispute_history = safe_get(patent, "kipris_data", "dispute_history", default=[])

    assignee_count = len(assignee) if isinstance(assignee, list) else 1
    has_dispute    = len(dispute_history) > 0

    # 실시권 관련 심판 여부
    has_license_dispute = any(
        "실시" in str(d) or "license" in str(d).lower()
        for d in dispute_history
    )

    if has_license_dispute:
        score = 1
    elif assignee_count >= 4 or has_dispute:
        score = 2
    elif assignee_count == 3:
        score = 3
    elif assignee_count == 2:
        score = 4
    else:
        score = 5

    return {
        "item":   "권리행사 제한 가능성",
        "dim":    "권리성",
        "score":  score,
        "basis":  f"출원인 {assignee_count}명, 심판이력 {len(dispute_history)}건",
        "method": "auto"
    }


# ──────────────────────────────────────────
# 시장성 자동 계산 항목
# ──────────────────────────────────────────

def score_patent_activity(patent: dict) -> dict:
    """
    특허출원 활성도 (시장성)
    체크리스트 기준: 최근 5년간 해당 기술분야 특허출원 증가율 vs 전체 특허출원 증가율 비교

    점수 기준:
      5점: 해당 기술분야 증가율이 전체의 4~5배 이상
      4점: 해당 기술분야 증가율이 전체의 2~3배
      3점: 유사하거나 낮음
      2점: 완만히 감소
      1점: 급격히 감소

    데이터 소스: patent["patent_filing_growth"] (run_pipeline이 KIPRIS 데이터로 주입)
    해당 필드 없으면 기본값 3점.
    """
    # 현재 프로토타입에서는 IPC별 출원 증가율 수집 단계가 완전히 통합되어
    # 있지 않습니다. 데이터가 없으면 명시적으로 기본값 3점을 적용합니다.
    pg = patent.get("patent_filing_growth") or {}
    score        = pg.get("score")
    growth_rate  = pg.get("growth_rate")
    total_rate   = pg.get("total_growth_rate")
    is_fallback  = pg.get("fallback", True)

    if score is not None and not is_fallback and growth_rate is not None:
        score = int(score)
        rate_str  = f"{growth_rate:.1f}" if isinstance(growth_rate, float) else str(growth_rate)
        total_str = f"{total_rate:.1f}" if isinstance(total_rate, float) else str(total_rate)
        basis = f"KIPRIS IPC 출원 증가율 {rate_str}% (전체 {total_str}%)"
    else:
        score = 3
        basis = "KIPRIS 특허출원 증가율 데이터 없음 → 기본값"

    return {
        "item":   "특허출원 활성도",
        "dim":    "시장성",
        "score":  score,
        "basis":  basis,
        "method": "auto"
    }


# ──────────────────────────────────────────
# 사업성 자동 계산 항목
# ──────────────────────────────────────────

def score_revenue_growth(patent: dict) -> dict:
    """
    매출 성장성 (사업성) ← KOSIS 자동화
    run_pipeline이 patent["market_growth"]에 주입한 KOSIS 결과를 그대로 사용.
    fallback=True이면 KOSIS 데이터 미수신 → 기본값 3점.
    """
    # KOSIS 조회는 서비스 레이어에서 먼저 수행되어 patent["market_growth"]에
    # 주입됩니다. 여기서는 그 결과를 평가 항목 점수로 변환해 자동 점수 목록에
    # 포함시키는 역할만 합니다.
    mg          = patent.get("market_growth") or {}
    growth_score = mg.get("score")
    growth_rate  = mg.get("growth_rate")
    sector       = mg.get("sector") or ""
    is_fallback  = mg.get("fallback", True)

    if growth_score is not None and not is_fallback and growth_rate is not None:
        score = int(growth_score)
        rate_str = f"{growth_rate:.2f}" if isinstance(growth_rate, float) else str(growth_rate)
        basis = f"KOSIS {sector} 5년 평균 성장률 {rate_str}%"
    else:
        score = 3
        basis = "KOSIS 데이터 없음 → 기본값"

    return {
        "item":   "매출 성장성",
        "dim":    "사업성",
        "score":  score,
        "basis":  basis,
        "method": "auto_kosis"
    }


# ──────────────────────────────────────────
# 통합 실행
# ──────────────────────────────────────────

def calc_auto_scores(patent: dict) -> list[dict]:
    """
    JSON 정형 데이터로 자동 계산 가능한 항목 전체 실행
    반환: [{item, dim, score, basis, method}, ...]
    """
    calculators = [
        # 권리성
        score_ip_origin,
        score_right_faithfulness,
        score_right_restriction,
        # 시장성
        score_patent_activity,
        # 사업성
        score_revenue_growth,
    ]

    results = []
    for fn in calculators:
        try:
            r = fn(patent)
            results.append(r)
        except Exception as e:
            # 개별 자동 계산 실패가 전체 평가 실패로 번지지 않도록 항목 단위로
            # 오류 점수를 남깁니다. 서비스 출력의 단계 정보에서 이런 대체값 적용을
            # 추적할 수 있습니다.
            results.append({
                "item":   fn.__name__,
                "dim":    "unknown",
                "score":  3,
                "basis":  f"계산 오류: {e}",
                "method": "error"
            })
    return results


# ──────────────────────────────────────────
# 테스트
# ──────────────────────────────────────────

if __name__ == "__main__":
    import json, os

    # 로컬 JSON 파일 로드
    for fname in ["patent_10_2212093.json", "example_input.json"]:
        if os.path.exists(fname):
            with open(fname, encoding="utf-8") as f:
                patent = json.load(f)

            print(f"\n{'='*60}")
            print(f"특허: {patent.get('patent_id')} | {patent.get('meta', {}).get('title', '')[:30]}")
            print(f"{'='*60}")
            print(f"{'항목':<22} {'차원':<8} {'점수':>4}  {'근거'}")
            print(f"{'-'*70}")

            results = calc_auto_scores(patent)
            for r in results:
                bar = "█" * r["score"] + "░" * (5 - r["score"])
                print(f"{r['item']:<22} {r['dim']:<8} {r['score']:>2}/5 [{bar}]  {r['basis']}")

            # 차원별 소계
            print(f"\n{'차원별 자동화 점수':}")
            from collections import defaultdict
            dim_scores = defaultdict(list)
            for r in results:
                dim_scores[r["dim"]].append(r["score"])

            DIM_MAX = {"기술성": 25, "권리성": 50, "시장성": 30, "사업성": 30}
            for dim, scores in dim_scores.items():
                total = sum(scores)
                items = len(scores)
                print(f"  {dim}: {total}점 / {items*5}점 (자동화 {items}개 항목)")
            break
