# eval-logic: 특허 평가 자동화 파이프라인

특허의 **기술성(10개), 권리성(12개), 시장성(12개), 사업성(9개)** 총 **43개 항목**을 종합적으로 평가하는 Python 파이프라인입니다.

**세 가지 평가 방식을 병렬 실행**:
- 🔴 **Auto_score**: 규칙 기반 자동 점수 (9개 항목)
- 📊 **시장성**: KOSIS API 경제통계 (1개 점수)
- 🧠 **LLM 평가**: OpenAI GPT-4o-mini 기반 분석 + 웹 검색 근거 (43개 항목)

**한 번의 실행으로** auto + market + llm 점수를 모두 계산하고 `artifacts/output/*_output.json`으로 통합 저장합니다.

---

## 📊 전체 실행 흐름

```
🚀 파이프라인 시작: 2026-05-03 14:30:15
┌─────────────────────────────────────┐
│  입력 JSON 로드                      │
│  (patent_10_2212093.json)            │
└──────────┬──────────────────────────┘
           │
    ┌──────┴────────────┬──────────────┬──────────────┐
    │                   │              │              │
    ▼                   ▼              ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌────────────┐
│ [1/3] 자동  │  │ [2/3] 시장성 │  │[3/3] LLM평가 │  │ .env 로드  │
│ Auto_score  │  │  KOSIS API   │  │  OpenAI    │  │ (API키)   │
│ (9개 항목)  │  │ (성장률점수) │  │ (43개항목) │  │           │
└─────┬───────┘  └──────┬───────┘  └────┬────────┘  └────────────┘
      │                 │               │
      │             ┌───┴───────────────┤
      │             │                   │
      │        ┌────▼──────────┐        │
      │        │IPC→KSIC→C2변환│        │
      │        │(ipc_ksic_     │        │
      │        │ mapper)       │        │
      │        └────┬──────────┘        │
      │             │                   │
      │        ┌────▼──────────┐        │
      │        │KOSIS API 조회 │        │
      │        │(성장률계산)   │        │
      │        └────┬──────────┘        │
      │             │                   │
      │        ┌────▼──────────────┐   │
      │        │웹 검색(Tavily API)│   │
      │        │근거 자료 수집     │   │
      │        └────┬──────────────┘   │
      │             │                   │
      └─────┬───────┴───────────────┬──┘
            │                       │
            │    ┌──────────────────┘
            │    │
            ▼    ▼
      ┌─────────────────────────────────────┐
      │ 통합 및 차원별 요약                  │
      │ • auto_scores (9개)                 │
      │ • llm_scores (43개)                 │
      │ • llm_sources (웹출처)              │
      │ • market_growth (1개)               │
      │ • summary (차원별 통계)             │
      └─────────────┬───────────────────────┘
                    │
      ┌─────────────▼───────────────────────┐
      │ 파일 저장 및 결과 출력              │
      │ artifacts/output/*_output.json      │
      └─────────────────────────────────────┘
```

**실행 시간**: 약 70~80초 (자동: ~0.2초, 시장: ~2초, LLM: ~70초)

---

## 📂 디렉토리 구조

```text
eval_logic/
├─ src/                 # 실행 코드
│  ├─ run_pipeline.py
│  ├─ Auto_score.py
│  ├─ llm_evaluator.py
│  ├─ report_generator.py
│  └─ crawling/
├─ resources/           # 평가 기준/매핑 테이블 등 정적 리소스
├─ samples/             # 샘플 입력 및 참조 데이터
│  ├─ input/
│  └─ data/
├─ artifacts/           # 실행 산출물, 캐시, 보고서 (gitignore 대상)
│  ├─ output/
│  ├─ report/
│  ├─ crawling/
│  └─ cache/
├─ requirements.txt
├─ .env.example
└─ README.md
```

`src/paths.py`가 위 경로를 공통 상수로 제공합니다. 새 코드에서는 상대 경로를 직접 쓰기보다 이 경로 상수를 사용합니다.

---

## 📁 파일 역할

### 🔴 핵심 실행 파일

| 파일 | 역할 | 입력 | 출력 |
|------|------|------|------|
| **src/run_pipeline.py** | 🎯 **전체 파이프라인 진입점** | JSON 파일 경로 또는 `samples/input` | `artifacts/output/*_output.json` + 콘솔 출력 |
| **src/Auto_score.py** | 규칙 기반 점수 (권리성, 시장성, 사업성) | patent JSON | auto_scores 배열 |
| **src/kosis_growth_fetcher.py** | KOSIS 시장 성장률 조회 & 점수 변환 | patent JSON | market_growth (1~5점) |
| **src/ipc_ksic_mapper.py** | IPC 코드 → KSIC → C2 산업분류 매핑 | IPC 코드 리스트 | KSIC 코드, C2 코드 |
| **src/llm_evaluator.py** | OpenAI LLM 기반 상세 평가 | patent JSON + 웹 검색 | llm_scores + 출처 |
| **src/web_searcher.py** | Tavily API를 통한 웹 검색 (RAG) | 평가 쿼리 | URL + 제목 + 날짜 + 스니펫 |
| **src/similar_patent_analyzer.py** | 대상 특허와 유사 특허 비교 분석 | 대상/유사 특허 JSON | 유사 특허 분석 JSON |
| **src/report_generator.py** | HTML 보고서 생성 | 평가 output JSON | `artifacts/report/*.html` |
| **src/schemas.py** | 특허 평가 입력/출력 스키마 | raw patent JSON | typed schema/dataclass |
| **src/valuation_service.py** | 특허 가치 평가 서비스 레이어 | patent dict | canonical output |

### 📄 설정/참고 파일

| 파일 | 설명 |
|------|------|
| **resources/checklist_fixed.md** | **LLM 평가 체크리스트** (기술성 10, 권리성 12, 시장성 12, 사업성 9 = 총 43개 항목) |
| **resources/산업_KSIC_-특허_IPC__연계표.xlsx** | IPC ↔ KSIC 매핑 테이블 (엑셀) |
| **samples/input/*.json** | 테스트용 특허 입력 데이터 |
| **samples/data/*.json** | 유사 특허/참조 데이터 샘플 |
| **.env.example** | API 키 환경변수 예시 |
| **.env** | 로컬 API 키 관리 파일 (gitignore 대상) |
| **requirements.txt** | Python 의존성 패키지 |

### 📊 결과 파일

| 파일 | 설명 |
|------|------|
| **artifacts/output/*_output.json** | 최종 통합 결과 (auto + llm + market 점수 + 실행시간) |
| **artifacts/output/similar_*.json** | 유사 특허 후보/상세/분석 결과 |
| **artifacts/report/*.html** | HTML 보고서 |
| **artifacts/cache/** | 외부 API 응답 캐시 |

---

## 🧩 서비스 레이어와 스키마

실제 서비스 통합 시에는 `src/run_pipeline.py`를 직접 호출하지 않고 `PatentValuationService`를 사용합니다.

```python
from valuation_service import PatentValuationService

service = PatentValuationService()
result = service.evaluate(patent_json)
response_body = result.to_dict()
```

### 입력 스키마

`src/schemas.py`의 `PatentEvaluationInput`이 현재 표준 입력입니다. 기존 프로토타입 JSON과의 호환을 위해 선택 필드는 유연하게 허용합니다.

필수:
- `patent_id` 또는 `meta.registration_number`
- `meta.title` 또는 `title`

주요 선택 필드:
- `description_summary`: LLM 평가용 명세서 요약
- `claims_text`: 청구항 기반 권리성/기술성 평가
- `market_data.related_industry_code`: KOSIS C2 산업코드
- `market_data.ksic_code`: KSIC 코드
- `meta.ipc`: IPC 기반 KSIC fallback 매핑
- `kipris_data`: 피인용, 패밀리, 심판 이력 등 자동 평가 보조 데이터

### 출력 스키마

`PatentEvaluationOutput.to_dict()`는 기존 보고서 생성기가 읽을 수 있는 JSON 구조를 유지합니다.

주요 필드:
- `patent_id`, `title`
- `auto_scores`: 규칙 기반 점수 목록
- `llm_scores`: LLM 기반 점수 목록
- `market_growth`: KOSIS 시장 성장률 결과
- `llm_sources`: LLM 평가에 인용된 웹 출처
- `summary.auto`, `summary.llm`, `summary.market`: 단계별 요약
- `summary.steps`: 각 단계의 성공/스킵/fallback/error 상태와 실행 시간

---

## 🔄 각 단계별 상세 설명

### 1️⃣ 자동 점수 (Auto_score.py) - ~0.2초
**규칙 기반 점수 계산** - JSON 구조화 데이터에서 자동 추출

```
계산 항목 (9개):
├─ IP 원천성 (심사관 인용 선행기술 수)       → 점수: 1~5점
├─ 권리의 충실성 (청구항 수, 카테고리, 해외)  → 점수: 1~5점
├─ 권리행사 제한 가능성 (공유특허 여부)      → 점수: 1~5점
├─ 출원경과 (심판 이력)                      → 점수: 1~5점
├─ 진부화 가능성 (잔존 존속기간)             → 점수: 1~5점
└─ ... (추가 5개 항목)

예시 JSON:
{
  "meta": {
    "prior_art_cited": [...],      // 선행기술 수
    "total_claims": 7,             // 청구항 수
    "independent_claims": 3        // 독립항 수
  },
  "legal": {
    "legal_remaining_years": 12.7  // 잔존 존속기간
  }
}
```

**점수 범위**: 1~5점 (5단계: 1=매우미흡 ~ 5=매우우수)

---

### 2️⃣ 시장 성장률 (kosis_growth_fetcher.py) - ~2초
**KOSIS 경제통계 API** - 산업별 5년 성장률 조회

```
입력 JSON의 산업 정보 추출
  ↓
C2 코드 결정 (3단계 우선순위):
  1️⃣ market_data.related_industry_code (직접 입력)
  2️⃣ market_data.ksic_code → KSIC_TO_C2 변환
  3️⃣ meta.ipc[] → ipc_ksic_mapper로 IPC→KSIC→C2 매핑
  ↓
KOSIS API (DT_1K52F08) 호출
  • 테이블: 산업별 부가가치, 매출액 등
  • 기간: 5년 롤링 윈도우 (현재년도-1 기준)
  ↓
최근 5년 평균 성장률 계산
  ↓
성장률 → 점수 변환 (1~5점):
  5점: ≥ 10%    (고성장)
  4점: 5~10%    (양호)
  3점: 0~5%     (보통)
  2점: -5~0%    (정체)
  1점: < -5%    (감소)

예시:
{
  "market_growth": {
    "c2_code": "J63",
    "sector_name": "정보서비스업",
    "growth_rate": 12.3,           // %
    "score": 5,
    "years_analyzed": 5            // 2020-2024
  }
}
```

---

### 3️⃣ 웹 검색 (web_searcher.py) - ~3초
**Tavily API** - LLM 평가의 근거 자료 수집 (RAG)

```
각 평가 차원별 검색 쿼리 생성:
  • 기술성: "기술 동향, 혁신성, 개척성"
  • 권리성: "특허 침해 사례, 무효 소송"
  • 시장성: "시장 성장, 경쟁, 수요"
  • 사업성: "사업화 환경, 매출 전망"
  ↓
Tavily API로 각각 2회 검색
  → 총 8개 쿼리 × 최대 10개 결과
  ↓
결과 포맷:
  {
    "title": "기사 제목",
    "url": "https://...",
    "snippet": "요약 텍스트",
    "published_date": "2026-05-01"
  }
  ↓
중복 제거 (URL 기준)
  ↓
결과: 보통 5~15개 유니크 URL

신뢰할 수 있는 도메인:
  • 뉴스: 조선일보, 중앙일보, 한국경제
  • 학술: 논문, 학회지, 대학 보도
  • 정부: 통계청, 산업부, 특허청
  • 리서치: 마켓리서치, 산업분석
```

---

### 4️⃣ LLM 평가 (llm_evaluator.py) - ~70초
**OpenAI GPT-4o-mini** - 특허 명세서 기반 상세 평가

```
프로세스:
  1️⃣ checklist_fixed.md 파싱
     └─ 43개 항목 추출 (기술성 10 + 권리성 12 + 시장성 12 + 사업성 9)
  
  2️⃣ 웹 검색 결과 수집
     └─ 최대 15개 참고 자료 준비
  
  3️⃣ 프롬프트 구성 (차원별):
     • 특허 기본정보 (제목, 요약)
     • 명세서 요약 (description_summary)
     • 청구항 내용 (claims_text)
     • 평가 기준 및 예시
     • 웹 검색 근거 자료 (URL, 제목, 스니펫)
  
  4️⃣ OpenAI API 호출
     • 모델: gpt-4o-mini (비용 효율적)
     • 응답 포맷: JSON (자동 파싱)
  
  5️⃣ 응답 파싱:
     [
       {
         "item": "차별성",
         "dim": "기술성",
         "score": 4,              // 1~5점
         "reason": "상세 평가 설명",
         "sources": [             // 인용된 웹 출처
           {
             "title": "...",
             "url": "https://..."
           }
         ]
       },
       ...
     ]

예시 응답:
{
  "item": "차별성",
  "dim": "기술성",
  "score": 4,
  "reason": "해당 기술은 오디오북 제작 및 품질 검수에 있어 
           독창적인 기능을 제공하며 기존 시스템 대비 우수한 
           사용자 경험을 제공합니다.",
  "sources": [
    {
      "title": "AI 기술을 활용한 오디오북 제작...",
      "url": "https://www.odiro.ai/blog/?idx=18290716"
    }
  ]
}
```

**점수 범위**: 1~5점 (체크리스트 기준)

---

### 5️⃣ 결과 통합 (run_pipeline.py)
**세 가지 점수 병합 & 차원별 요약**

```json
{
  "patent_id": "10-2212093",
  "title": "인공지능 대화형 홈쇼핑 전화 주문 시스템",
  
  "auto_scores": [           // 규칙 기반 (9개)
    {
      "item": "IP 원천성",
      "dim": "권리성",
      "score": 4,
      "basis": "선행기술 3건 인용"
    },
    ...
  ],
  
  "llm_scores": [            // LLM 기반 (43개)
    {
      "item": "차별성",
      "dim": "기술성",
      "score": 4,
      "reason": "...",
      "sources": [...]
    },
    ...
  ],
  
  "llm_sources": [           // 전체 참고 출처 (중복 제거)
    {
      "title": "AI 기술 동향",
      "url": "https://...",
      "snippet": "...",
      "published_date": "2026-05-01"
    },
    ...
  ],
  
  "market_growth": {         // 시장성 점수 (1개)
    "c2_code": "J63",
    "growth_rate": 12.3,
    "score": 5
  },
  
  "summary": {               // 차원별 통계
    "auto": {
      "by_dimension": {
        "권리성": {"total": 8, "count": 4, "average": 2.0},
        ...
      },
      "total": 20,
      "count": 9,
      "average": 2.22
    },
    "llm": {
      "by_dimension": {...},
      "total": 141,
      "count": 43,
      "average": 3.28
    },
    "execution_time_seconds": 73.45,
    "start_time": "2026-05-03 14:30:15"
  }
}
```

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성 및 활성화 (Python 3.11+)
python -m venv venv

# Windows
venv\Scripts\activate
# or macOS/Linux
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

## 리포지토리 요약 (자동 생성된 개요)

다음 파일/모듈은 문서 자동 생성 시 참고한 핵심 구성입니다.

- **코어 실행**: [src/run_pipeline.py](src/run_pipeline.py#L1)
- **자동 점수 규칙**: [src/Auto_score.py](src/Auto_score.py#L1)
- **LLM 평가 엔진**: [src/llm_evaluator.py](src/llm_evaluator.py#L1)
- **웹 검색(RAG)**: [src/web_searcher.py](src/web_searcher.py#L1)
- **IPC↔KSIC 매핑 테이블 + 유틸**: [src/ipc_ksic_mapper.py](src/ipc_ksic_mapper.py#L1) and [resources/산업_KSIC_-특허_IPC__연계표.xlsx](resources/산업_KSIC_-특허_IPC__연계표.xlsx)
- **KOSIS 연동**: [src/kosis_growth_fetcher.py](src/kosis_growth_fetcher.py#L1)
- **환경/의존성**: [requirements.txt](requirements.txt#L1), [.env.example](.env.example#L1)

---

### 변경점 (최근)

- IPC→KSIC 매핑에서 `fallback_ambiguous`/`exact_ambiguous` 케이스를 허용하여 기본 우선순위(첫 후보)를 선택하도록 `src/kosis_growth_fetcher.py`에 반영했습니다. 관련 로직은 [src/kosis_growth_fetcher.py](src/kosis_growth_fetcher.py#L1)와 [src/ipc_ksic_mapper.py](src/ipc_ksic_mapper.py#L1)를 참조하세요.

---

원하시면 이 README에 더 상세한 예시(입출력 샘플, 전체 옵션 플래그, 개발자 노트)를 추가해 드리겠습니다.

### 2. API 키 설정

`.env` 파일 생성 (프로젝트 루트):

```env
# OpenAI
OPENAI_API_KEY=sk-proj-abc123xyz...
OPENAI_MODEL=gpt-4o-mini

# KOSIS (한국 통계청)
KOSIS_API_KEY=your_kosis_key_base64

# Tavily (웹 검색)
TAVILY_API_KEY=tvly-abc123xyz...
```

**API 획득:**
- **OpenAI**: https://platform.openai.com/api-keys
- **KOSIS**: https://kosis.kr/openapi (자동화된 신청)
- **Tavily**: https://tavily.com (API 키 복사)

### 3. 실행

```bash
# 기본 실행 (samples/input/*.json 전체 처리)
python src/run_pipeline.py

# 특정 파일 지정
python src/run_pipeline.py samples/input/patent_10_2212093.json
python src/run_pipeline.py samples/input
```

### 4. 결과 확인

```
⏱️  [1/3] 자동 점수 계산 중...
  ✅ 완료 (0.18초)

⏱️  [2/3] 시장 성장률 조회 중...
  ✅ 완료 (2.45초)

⏱️  [3/3] LLM 평가 중...
  ✅ 완료 (70.32초)

=== 결과 요약 ===
특허 ID: 10-2212093
제목: 인공지능 대화형 홈쇼핑 전화 주문 시스템

📊 점수 통계:
  • 자동 점수: 5개 항목, 평균 2.40점
  • LLM 평가: 43개 항목, 평균 3.28점
  • 시장 성장률: 5점 (12.3% 성장)

⏱️  총 실행 시간: 72.95초
📁 결과 저장: artifacts/output/{input_stem}_output.json
```

**출력 파일**: 
- `artifacts/output/*_output.json` - 전체 점수 & 분석 결과
- 콘솔 - 포맷된 요약 정보

---

## 📝 체크리스트 커스터마이징

[resources/checklist_fixed.md](resources/checklist_fixed.md)는 **43개 평가 항목의 기준**을 정의합니다.

**구조**:

```markdown
## 차원명 (항목 수)

### 1. 항목명
평가 설명...
- **5점**: 최고 수준 (이전 +2점)
- **4점**: 우수 (이전 +1점)
- **3점**: 보통 (이전 0점)
- **2점**: 미흡 (이전 -1점)
- **1점**: 매우 미흡 (이전 -2점)
```

**점수 척도** (1~5점):
- **5점** (매우 우수): 기준을 완벽히 충족
- **4점** (우수): 기준을 충분히 충족
- **3점** (보통): 기준을 부분적으로 충족
- **2점** (미흡): 기준을 거의 충족하지 못함
- **1점** (매우 미흡): 기준을 충족하지 못함

**⚠️ 주의**: 체크리스트를 수정하면 LLM 평가 프롬프트도 자동으로 업데이트됩니다!

---

## ⚙️ 설정 옵션

### run_pipeline.py

```python
# 기본 입력 디렉토리
DEFAULT_INPUT_DIR = samples/input

# 결과 저장 디렉토리
OUTPUT_DIR = artifacts/output
```

### kosis_growth_fetcher.py

```python
# 시장성 데이터 설정
base_year = None              # None = 현재년도 - 1 (동적)
lookback_years = 5            # 성장률 계산 기간 (5년 롤링)

# 성장률 → 점수 매핑 함수
def growth_rate_to_score(rate):
    if rate >= 10: return 5      # 고성장
    elif rate >= 5: return 4     # 양호
    elif rate >= 0: return 3     # 보통
    elif rate >= -5: return 2    # 정체
    else: return 1               # 감소
```

### llm_evaluator.py

```python
# LLM 모델 설정
OPENAI_MODEL = "gpt-4o-mini"  # 또는 "gpt-4o", "gpt-4" 등

# 평가 프롬프트
DIMENSION_NAMES = ["기술성", "권리성", "시장성", "사업성"]
```

### web_searcher.py

```python
# 신뢰할 수 있는 도메인 (추가 가능)
CREDIBLE_DOMAINS = [
    "news.naver.com", "news.joins.com", "news.chosun.com",
    "research.google.com", "scholar.google.com",
    "kipo.go.kr", "kosis.kr", ...
]

# 검색 결과 개수
MAX_RESULTS_PER_QUERY = 10
```

---

## 🔍 트러블슈팅

| 문제 | 원인 | 해결 방법 |
|------|------|----------|
| `FileNotFoundError: JSON 파일을 찾을 수 없습니다` | patent_10_2212093.json, example_input.json 없음 | 파일 생성 또는 경로 지정 |
| `OPENAI_API_KEY 없음` | .env 파일 미생성 또는 키 누락 | `.env` 파일 생성 후 키 입력 |
| `ModuleNotFoundError: openai` | 패키지 설치 누락 | `pip install -r requirements.txt` 재실행 |
| `KOSIS API 에러 (C2 코드 유효하지 않음)` | 산업분류 코드 오류 | ipc_ksic_mapper 매핑 테이블 확인 |
| `IPC 매핑 실패 (IndexError)` | 엑셀 파일 손상 | `산업_KSIC_-특허_IPC__연계표.xlsx` 파일 복구 |
| `LLM 점수 생략 (llm_skipped)` | description_summary 또는 claims_text 필드 부족 | 입력 JSON의 필수 필드 확인 |
| 웹 검색 결과 0개 | Tavily API 키 오류 또는 요청 쿼리 문제 | TAVILY_API_KEY 확인, Tavily API 상태 확인 |
| `UnicodeDecodeError` | 파일 인코딩 문제 | 파일을 UTF-8로 재저장 |
| 실행 시간 초과 (>120초) | LLM API 응답 지연 | OpenAI API 상태 확인, 네트워크 확인 |
| `KeyError: 'auto_scores'` 또는 `llm_scores` | 결과 JSON 구조 오류 | run_pipeline.py에서 필드 생성 확인 |

**로그 확인:**
```bash
# 자세한 디버그 정보 출력 (파이썬 로깅 추가)
python -u src/run_pipeline.py 2>&1 | tee debug.log
```

---

## 📚 입력 JSON 구조

**필수 필드** (LLM 평가를 위해):

```json
{
  "patent_id": "10-2212093",
  
  "meta": {
    "title": "인공지능 대화형 홈쇼핑 전화 주문 시스템",
    "ipc": ["G06Q30/06", "G10L15/26"],              // 주분류/부분류
    "application_date": "2019-01-04",
    "application_number": "10-2019-0001092",
    "registration_date": "2021-01-29",
    "registration_number": "10-2212093",
    "legal_status": "등록",
    "total_claims": 7,
    "independent_claims": 3,
    "prior_art_cited": ["KR101575276 B1", "KR101925147 B1"]  // 인용 선행기술
  },
  
  "legal": {
    "legal_status": "등록",
    "legal_remaining_years": 12.7                  // 잔존 존속기간
  },
  
  "description_summary": "발명의 요약. 인공지능 대화형 홈쇼핑 
                         전화 주문 방법 및 시스템이 제공된다...",
  
  "claims_text": {
    "claim_1": {
      "type": "독립항",
      "category": "방법",
      "text": "청구항 1: 시스템이, 현재 홈쇼핑 방송중인 상품의..."
    },
    "claim_2": {
      "type": "종속항",
      "depends_on": 1,
      "text": "청구항 2: 청구항 1에 있어서..."
    }
  },
  
  "market_data": {
    "related_industry_code": "J63",                // [선택1] 직접 C2 코드
    // 또는
    "ksic_code": "62",                             // [선택2] KSIC 코드 (→ C2 변환)
    // 또는
    "ipc_primary": "G06Q30/06"                     // [선택3] IPC (→ KSIC → C2)
  },
  
  "kipris_data": {
    "cited_count": 5,
    "citing_count": 2,
    "family_patents": [],
    "dispute_history": []
  }
}
```

**필드 설명:**

| 필드 | 필수 | 역할 |
|------|------|------|
| `patent_id` | ✅ | 특허 고유 번호 |
| `meta.title` | ✅ | 특허 제목 (LLM 평가에 사용) |
| `meta.ipc` | ✅ | IPC 분류 (시장성 자동 조회 시) |
| `description_summary` | ✅ | 명세서 요약 (LLM 평가에 필수) |
| `claims_text` | ✅ | 청구항 상세 (LLM 평가에 필수) |
| `market_data` | ⚠️ | 시장성 평가용 (1개 이상 필요) |
| `legal.legal_remaining_years` | ⚠️ | 자동 점수 계산용 (잔존기간) |
| `meta.prior_art_cited` | ⚠️ | 자동 점수 계산용 (인용선행기술) |

**주의사항:**
- `description_summary` 또는 `claims_text`가 없으면 LLM 평가 스킵됨
- `market_data`는 3단계 우선순위: `related_industry_code` > `ksic_code` > `ipc`
- 모든 날짜는 `YYYY-MM-DD` 형식

---

## � 실행 예시 (로그)

```
🚀 파이프라인 시작: 2026-05-03 14:30:15

🎯 입력 파일: patent_10_2212093.json
특허 ID: 10-2212093
제목: 인공지능 대화형 홈쇼핑 전화 주문 시스템

⏱️  [1/3] 자동 점수 계산 중...
  └─ IP 원천성: 4/5 (선행기술 3건 인용)
  └─ 권리의 충실성: 3/5 (청구항 7개)
  └─ 권리행사 제한: 4/5
  └─ 출원경과: 3/5
  └─ 진부화 가능성: 4/5 (잔존 12.7년)
  └─ ... (총 9개 항목)
  ✅ 완료 (0.18초)

⏱️  [2/3] 시장 성장률 조회 중...
  └─ IPC: G06Q30/06
  └─ KSIC: 62 (정보서비스업)
  └─ C2: J63
  └─ KOSIS API: 2020-2024 성장률 12.3%
  └─ 점수: 5/5 (≥10%)
  ✅ 완료 (2.45초)

⏱️  [3/3] LLM 평가 중...
  └─ 웹 검색: 9개 참고 자료 수집
  └─ 기술성 (10개 항목) 평가 중...
  └─ 권리성 (12개 항목) 평가 중...
  └─ 시장성 (12개 항목) 평가 중...
  └─ 사업성 (9개 항목) 평가 중...
  ✅ 완료 (70.32초)

=== 결과 요약 ===

📊 점수 통계:
  • 자동 점수: 9개 항목, 평균 3.56점 (총 32점)
  • LLM 평가: 43개 항목, 평균 3.28점 (총 141점)
  • 시장 성장률: 5점 (12.3% 성장)
  • 전체 합계: 178점 (최대 295점)

📚 참고 출처:
  1. https://www.odiro.ai/blog/?idx=18290716
  2. https://selvas.ai/...
  3. https://www.marketsandmarkets.com/...
  ...

⏱️  총 실행 시간: 72.95초
📁 결과 저장: artifacts/output/{input_stem}_output.json
```

---

## 🔗 관련 자료

- [특허청 KIPRIS](https://www.kipris.or.kr/) - 특허 명세서
- [통계청 KOSIS](https://kosis.kr/) - 산업 통계
- [Tavily AI](https://tavily.com/) - 웹 검색 API
- [OpenAI API](https://platform.openai.com/) - LLM 평가

---

## 📄 라이센스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 📞 지원

문제 발생 시:
1. 트러블슈팅 섹션 확인
2. 로그 파일 검토 (debug.log)
3. API 키 및 네트워크 상태 확인

---

**마지막 업데이트**: 2026-05-03
