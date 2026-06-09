# SKIPA AI Server

특허 가치평가 보고서를 생성하는 FastAPI 기반 AI 백엔드입니다.

현재 핵심 구현은 `eval_logic` 아래에 있으며, 특허 JSON/PDF 입력을 표준 특허 입력으로 정규화한 뒤 근거 수집, 점수 평가, 유사 특허 분석, 구조화 보고서 생성, 보고서 신뢰도 검증까지 하나의 workflow로 실행합니다.

## 현재 버전 주요 변경

- API/CLI 실행 진입점을 `eval_logic/src/apps` 아래로 정리했습니다.
- 입력 데이터, 정적 리소스, API 테스트 산출물, 런타임 산출물을 `eval_logic/data` 아래로 통합했습니다.
- 최종 보고서 저장 파일명을 `{등록번호}.json` 형식으로 통일했습니다.
- 보고서 생성 후 자동 신뢰도 검증 단계(`verify_report`)를 추가했습니다.
- API 응답에 `report_verification`과 `report.quality_assurance`가 함께 포함됩니다.
- 기존 `src/api`, `src/cli` 경로는 하위 호환 wrapper로 남겨 기존 명령도 동작합니다.

## 디렉토리 구조

```text
skipa-ai-server/
  README.md

  eval_logic/
    requirements.txt
    .env                    # 로컬 환경변수, 커밋 금지
    STRUCTURE.md            # eval_logic 구조 요약

    src/
      apps/
        api/                # FastAPI 앱, API 스키마, Job 저장소
        cli/                # 로컬 실행, 보고서 검증, 그래프 시각화 CLI
      api/                  # 기존 API import/uvicorn 경로 유지용 wrapper
      cli/                  # 기존 CLI 실행 경로 유지용 wrapper
      agent/                # supervisor workflow, 보고서 빌더
      services/             # 가치평가, 근거 수집, 보고서 신뢰도 검증
      core/                 # 경로, 스키마, 파일명 규칙
      evaluation/           # 자동 점수, LLM 평가, KOSIS, 웹 검색
      patent_analysis/      # 유사 특허 분석
      document_processing/  # PDF/문서 처리
      business_rag/         # 사업화 문서 RAG

    data/
      samples/              # 샘플 입력 JSON, 샘플 PDF, 참조 데이터
      resources/            # 체크리스트, KSIC-IPC 매핑표, RAG 리소스
      api_test/             # Swagger/API 테스트 입력과 보고서 결과
      runtime_artifacts/    # CLI/agent 런타임 산출물
      kipris_artifacts/     # KIPRIS 유사도 검색/상세 크롤링 산출물과 캐시

    legacy/                 # 이전 코드
```

## Agent Workflow

현재 workflow는 `PatentValuationWorkflow`가 supervisor 방식으로 각 노드를 순차 조율합니다.

```text
supervisor
 -> collect_evidence
 -> validate_input
 -> run_valuation
 -> analyze_similar_patents
 -> build_report
 -> verify_report
 -> END
```

각 단계의 역할:

```text
collect_evidence
  PDF 메타데이터 추출, 사업화 RAG 등 보조 자료 수집

validate_input
  특허 ID, 제목, 청구항, 설명 요약 등 입력 검증

run_valuation
  규칙 기반 자동 점수, LLM 평가, KOSIS 시장 성장성 평가 실행

analyze_similar_patents
  유사 특허 분석 결과 조회 또는 분석 실행

build_report
  가치평가 결과를 구조화된 보고서 JSON으로 조립

verify_report
  보고서 신뢰도, 근거 커버리지, 수치 무결성, 출처 품질 검증
```

LangGraph가 설치되어 있으면 `StateGraph`로 실행하고, 없으면 같은 노드 순서를 sequential fallback runner로 실행합니다.

## 보고서 신뢰도 검증

보고서 생성 후 `ReportVerificationService`가 자동 검증을 수행합니다.

검증 항목:

- 근거 출처가 있는 평가 항목 비율
- LLM 평가 항목의 출처 누락 여부
- 4점 이상 고평가 항목의 근거 누락 여부
- 차원별 평균 점수와 보고서 점수의 수치 무결성
- 공식/전문 출처 비율
- 사업화 RAG 근거 누락
- 유사 특허 분석 누락

API 응답에는 최상위 `report_verification`이 포함됩니다.

```json
{
  "status": "needs_human_review",
  "report_verification": {
    "overall_reliability_score": 0.65,
    "reliability_grade": "C",
    "risk_level": "caution",
    "human_review_required": true,
    "numeric_integrity": "pass",
    "issues": []
  },
  "report": {
    "quality_assurance": {
      "overall_reliability_score": 0.65
    }
  }
}
```

`human_review_required`가 `true`이면 최상위 `status`는 `needs_human_review`가 됩니다.

## 보고서 저장 파일명

최종 보고서 결과 파일명은 등록번호 기준으로 통일합니다.

```text
{등록번호}.json
```

예:

```text
10-2925867.json
10-1306409.json
```

저장 위치:

```text
eval_logic/data/api_test/output/reports/{등록번호}.json
eval_logic/data/runtime_artifacts/reports/{등록번호}.json
```

같은 등록번호로 다시 생성하면 같은 파일을 덮어씁니다.

## 표준 Input Schema

모든 API/서비스 진입점은 `src/core/schemas.py`의 `normalize_patent_input()`을 거쳐 표준 입력 형태로 정규화됩니다.

```json
{
  "schema_version": "patent-input/v1",
  "patent_id": "10-0000000",
  "meta": {
    "title": "특허 제목",
    "registration_number": "10-0000000",
    "registration_date": "2024-01-01",
    "application_number": "10-0000-0000000",
    "application_date": "2022-01-01",
    "publication_number": "10-0000-0000000",
    "publication_date": "2023-01-01",
    "legal_status": "등록",
    "assignee": ["권리자"],
    "inventors": ["발명자"],
    "ipc": ["G06Q10/04"],
    "cpc": ["G06Q10/04"],
    "prior_art_cited": [],
    "total_claims": 10,
    "deleted_claims": []
  },
  "description_summary": "초록 및 명세서 핵심 요약",
  "claims_text": {
    "claim_1": {
      "type": "독립항",
      "category": "방법",
      "text": "청구항 1 내용"
    }
  },
  "specification": {
    "technical_field": "기술분야",
    "background_art": "배경기술",
    "problem_to_solve": "해결하려는 과제",
    "solution": "과제의 해결 수단",
    "advantageous_effects": "발명의 효과",
    "implementation": "구체적인 실시 내용"
  },
  "legal": {},
  "source_pdf": "업로드 PDF 경로"
}
```

허용되는 입력 형태:

```text
표준 특허 JSON
{"patent": {...}}
{"patent_data": {...}}
{"normalized_patent": {...}}
PDF 추출 결과 JSON
```

## 환경 설정

`eval_logic` 기준으로 실행합니다.

```bash
cd skipa-ai-server/eval_logic
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` 파일은 로컬에서만 생성합니다. API 키가 들어가므로 GitHub에 올리면 안 됩니다.

예시:

```env
OPENAI_API_KEY=...
KOSIS_API_KEY=...
KIPRIS_API_KEY=...
KSIC_TABLE_PATH=data/resources/산업_KSIC_-특허_IPC__연계표.xlsx
```

## 서버 실행

권장 실행:

```bash
cd skipa-ai-server/eval_logic
uvicorn apps.api.main:app --reload --app-dir src --port 8000
```

기존 wrapper 경로도 동작합니다.

```bash
uvicorn src.api.main:app --reload --port 8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

Health check:

```text
GET /health
```

## API 엔드포인트

### 저장된 재평가 보고서 조회 API

```text
GET /api/v1/reports/patent-valuation
GET /api/v1/reports/patent-valuation/{registration_number}
```

이 API는 보고서를 실시간 생성하지 않습니다. 로컬 CLI/배치로 미리 생성한
`report.json`을 MinIO에 업로드해 두고, 화면에서는 특허 등록번호로 해당
JSON을 조회합니다.

기본 MinIO object key 규칙:

```text
patents/{registration_number}/report.json
```

예:

```text
patents/10-2142205/report.json
```

필요하면 환경변수로 key 규칙을 바꿀 수 있습니다.

```bash
EVAL_LOGIC_REPORT_OBJECT_KEY_TEMPLATE='reports/{registration_number}/report.json'
EVAL_LOGIC_REPORT_LIST_PREFIX='reports/'
```

상세 조회 응답 예:

```json
{
  "registration_number": "10-2142205",
  "report": {
    "schema_version": "patent-reevaluation-report/v1"
  },
  "storage": {
    "backend": "minio",
    "bucket": "skipa",
    "object_key": "patents/10-2142205/report.json"
  }
}
```

### 재평가 도구 API

보고서 자체를 API에서 생성하지는 않지만, 보고서를 만들 때 사용되는 개별
도구는 Swagger에서 직접 실행할 수 있습니다.

```text
POST /api/v1/tools/patent-metadata
POST /api/v1/tools/business-rag
POST /api/v1/tools/market-growth
POST /api/v1/tools/auto-score
POST /api/v1/tools/llm-evaluation
POST /api/v1/tools/similar-patents
```

`patent-metadata`는 특허 원문 PDF를 업로드하면 `raw`, `keywords`,
`brief_summary`, `normalized_patent`를 반환합니다. 업로드한 PDF는 로컬
working cache에 임시 저장됩니다.

## API 테스트 흐름

### MinIO 기반 보고서 조회

1. 서버 실행
2. MinIO에 `patents/{registration_number}/report.json` 업로드
3. `GET /api/v1/reports/patent-valuation/{registration_number}` 호출
4. 응답의 `report`, `storage.object_key` 확인

로컬 fallback 구조:

```text
eval_logic/data/{registration_number}/report.json
```

## 로컬 CLI

권장 경로:

```bash
cd skipa-ai-server/eval_logic
```

전체 기능 실행:

```bash
python3 src/apps/cli/run_agent.py data/samples/input/patent_10_1306409.json
```

외부 API 호출을 줄인 빠른 실행:

```bash
python3 src/apps/cli/run_agent.py data/samples/input/patent_10_1306409.json --profile quick
```

샘플 전체 실행:

```bash
python3 src/apps/cli/run_agent.py data/samples/input --profile quick
```

보고서 신뢰도 검증 빠른 테스트:

```bash
python3 src/apps/cli/test_report_verification.py patent_10_2925867.json
```

전체 workflow 결과 JSON까지 출력:

```bash
python3 src/apps/cli/test_report_verification.py patent_10_2925867.json --raw
```

CLI 옵션 확인:

```bash
python3 src/apps/cli/run_agent.py --help
python3 src/apps/cli/test_report_verification.py --help
```

기존 wrapper 경로도 동작합니다.

```bash
python3 src/cli/run_agent.py data/samples/input/patent_10_2925867.json --profile quick
python3 src/cli/test_report_verification.py patent_10_2925867.json
```

## 그래프 시각화

```bash
python3 src/apps/cli/visualize_agent_graph.py
```

산출물:

```text
data/runtime_artifacts/graphs/
```

## 산출물 저장 위치

```text
data/api_test/input/uploads/
  Swagger JSON 업로드 원본

data/api_test/input/pdf/
  Swagger PDF 업로드 원본

data/api_test/input/extracted/
  PDF에서 추출한 표준 input JSON

data/api_test/output/reports/
  API 보고서 결과 JSON

data/runtime_artifacts/reports/
  CLI workflow 결과 JSON

data/runtime_artifacts/analysis/
  현재 workflow가 생성한 유사 특허 분석 JSON

data/runtime_artifacts/graphs/
  LangGraph 시각화 결과

data/runtime_artifacts/uploads/
  PDF 보고서 API가 처리 중 저장하는 로컬 업로드 파일

data/kipris_artifacts/
  KIPRIS 유사도 검색/상세 크롤링 산출물과 캐시
```

## 로컬 검증 명령

문법/컴파일 확인:

```bash
cd skipa-ai-server/eval_logic
python3 -m compileall src/apps src/api src/cli src/core src/agent src/services src/evaluation src/patent_analysis src/document_processing
```

빠른 보고서 검증:

```bash
python3 src/apps/cli/test_report_verification.py patent_10_2925867.json
```

빠른 workflow 실행:

```bash
python3 src/apps/cli/run_agent.py data/samples/input/patent_10_2925867.json --profile quick
```

API import 확인:

```bash
python3 -c "import sys; sys.path.insert(0, 'src'); from apps.api.main import app; print(app.title)"
```

## Git 관리 주의사항

다음 파일은 커밋하면 안 됩니다.

```text
eval_logic/.env
eval_logic/.env.*
```

다음 디렉토리는 생성 산출물/캐시 성격입니다. 필요 시 비우거나 gitignore 대상으로 관리합니다.

```text
eval_logic/data/runtime_artifacts/
eval_logic/data/api_test/input/uploads/
eval_logic/data/api_test/input/pdf/
eval_logic/data/api_test/input/extracted/
eval_logic/data/api_test/output/reports/
eval_logic/data/kipris_artifacts/
eval_logic/data/resources/business_rag/index/
eval_logic/data/resources/business_rag/raw/
eval_logic/data/resources/business_rag/processed/
```

다음은 개발/테스트 재현에 필요한 데이터입니다.

```text
eval_logic/data/samples/
eval_logic/data/resources/checklist_fixed.md
eval_logic/data/resources/산업_KSIC_-특허_IPC__연계표.xlsx
```

민감한 고객 원문, 내부 PDF, API 키, 비공개 회사명/고객명은 샘플이나 API 테스트 산출물에 넣지 않습니다.

커밋 전 확인:

```bash
git status --short
git check-ignore -v eval_logic/.env
```

## Legacy

현재 API/서비스와 직접 무관한 이전 코드는 아래에 보관합니다.

```text
eval_logic/legacy/
```

KIPRIS 유사도 검색/상세 크롤링 산출물과 캐시는 아래에 보관합니다.

```text
eval_logic/data/kipris_artifacts/
```

신규 API/서비스 코드는 `legacy`에 의존하지 않도록 관리합니다. 다만 KIPRIS 유사 특허 크롤러는 현재 `legacy/src/crawling` 구현을 사용하며, 유사 특허 분석은 `data/kipris_artifacts`의 수집 결과와 캐시를 생성/조회합니다.
