# SKIPA AI Server

특허 가치평가, 보조 자료 수집, 유사 특허 분석, 유지/포기 의사결정 보조 보고서 생성을 제공하는 FastAPI 기반 AI 백엔드 서버입니다.

현재 핵심 구현은 `eval_logic` 아래에 있으며, LangGraph 스타일의 supervisor workflow로 평가 파이프라인을 실행합니다.

## 주요 기능

- 특허 JSON 입력 기반 가치평가 및 유지/포기 의사결정 보고서 생성
- 특허 PDF 원문 업로드 기반 메타데이터, 청구항, 명세서 핵심 섹션 추출
- 규칙 기반 자동 점수 산출
- LLM 기반 평가 항목 산출
- KOSIS/KSIC/IPC 기반 시장 성장성 보조 평가
- RAG 기반 제품/사업화 현황 추정
- 유사 특허 분석 결과 통합
- Swagger UI를 통한 API 테스트
- API 테스트용 입력/출력 산출물 분리 저장

## 디렉토리 구조

```text
skipa-ai-server/
  README.md
  .gitignore

  data/                   # 챗봇과 보고서 로직이 공유하는 중앙 데이터 루트
    mapped_patent_reports/
      <patent_id>/        # 특허별 원문, 보고서 JSON, 위키, chunk/index 관리
        original/
          pdf/
          input/
        reports/
          json/
        wiki/
        extracted/
        index/
    api_test/             # Swagger/API 테스트용 입력·출력 저장소
      input/
        pdf/
        extracted/
        uploads/
      output/
        reports/
    artifacts/            # 로컬 생성 산출물/cache/report
    business_rag/         # 제품/사업화 RAG 데이터

  eval_logic/
    requirements.txt
    .env                  # 로컬 환경변수 파일, git에 올리면 안 됨

    src/
      api/                # FastAPI 엔드포인트, API 요청/응답 스키마, 인메모리 Job 저장소
      agent/              # supervisor 기반 특허 의사결정 workflow, 보고서 조립
      services/           # 가치평가 서비스, 증거/자료 수집 서비스
      core/               # 공통 경로, 표준 input/output schema, normalizer
      evaluation/         # 자동 점수, LLM 평가, KOSIS 성장률, 웹 검색
      document_processing/ # 특허 PDF 원문 파싱
      business_rag/       # 제품/사업화 현황 RAG
      patent_analysis/    # 유사 특허 분석
      cli/                # 로컬 실행/그래프 시각화 CLI

    samples/
      input/              # 테스트용 샘플 특허 JSON
      data/               # 샘플 보조 데이터
      patent_documents/   # Swagger/API 테스트용 샘플 PDF

    resources/            # 매핑표, RAG 리소스
    legacy/               # 현재 API와 직접 무관한 프로토타입/레거시 코드
```

## Agent Workflow

현재 workflow는 기능별 review node를 별도로 두지 않고, `supervisor`가 전체 상태를 점검하며 다음 worker node를 결정합니다.

```text
supervisor
 -> collect_evidence
 -> supervisor
 -> validate_input
 -> supervisor
 -> run_valuation
 -> supervisor
 -> analyze_similar_patents
 -> supervisor
 -> make_decision
 -> supervisor
 -> build_report
 -> supervisor
 -> END
```

각 node의 역할은 다음과 같습니다.

```text
collect_evidence
  PDF 메타데이터 추출, 사업화 RAG 등 보조 자료 수집

validate_input
  특허 ID, 제목, 청구항, 설명 요약 등 평가 입력 검증

run_valuation
  시장 성장성, 자동 점수, LLM 평가 실행

analyze_similar_patents
  유사 특허 분석 결과 조회 또는 분석

make_decision
  점수, 시장성, 유사 특허, 사업화 신호를 종합해 유지/포기/검토 권고 생성

build_report
  최종 의사결정 보조 보고서 JSON 생성
```

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

`skipa-ai-server/eval_logic` 기준으로 실행합니다.

```bash
cd eval_logic
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` 파일은 로컬에서만 생성합니다. 절대 GitHub에 올리면 안 됩니다.

예시:

```env
OPENAI_API_KEY=...
KOSIS_API_KEY=...
KIPRIS_API_KEY=...
KSIC_TABLE_PATH=resources/산업_KSIC_-특허_IPC__연계표.xlsx
```

## 서버 실행

`skipa-ai-server/eval_logic`에서 실행합니다.

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

### 서비스용 보고서 API

```text
POST /api/v1/reports/patent-maintenance/from-json
POST /api/v1/reports/patent-maintenance/from-json-file
POST /api/v1/reports/patent-maintenance/from-pdf
GET  /api/v1/reports/{job_id}
GET  /api/v1/reports/{job_id}/status
GET  /api/v1/reports/{job_id}/result
```

`from-json`은 request body로 특허 JSON을 받습니다.

```json
{
  "patent": {
    "patent_id": "10-0000000",
    "meta": {
      "title": "특허 제목",
      "registration_number": "10-0000000",
      "ipc": ["G06Q10/04"]
    },
    "claims_text": {
      "claim_1": {
        "type": "독립항",
        "category": "방법",
        "text": "청구항 내용"
      }
    },
    "description_summary": "발명의 요약"
  }
}
```

`from-json-file`은 Swagger에서 JSON 파일을 업로드합니다. `samples/input/*.json` 또는 `data/api_test/input/extracted/*.json` 파일을 그대로 사용할 수 있습니다.

`from-pdf`는 Swagger에서 특허 PDF 파일을 업로드합니다. PDF에서 input JSON을 추출한 뒤 보고서 workflow까지 실행합니다.

### 개발/디버그용 통합 API

```text
POST /api/v1/dev/patent-decision/evaluate
POST /api/v1/dev/patent-decision/evaluate-sample/{sample_name}
```

`evaluate`는 옵션을 직접 제어하며 전체 workflow를 실행합니다.

```json
{
  "patent_data": {
    "patent_id": "10-0000000",
    "meta": {
      "title": "특허 제목",
      "registration_number": "10-0000000"
    },
    "claims_text": {
      "claim_1": {
        "type": "독립항",
        "text": "청구항 내용"
      }
    },
    "description_summary": "발명의 요약"
  },
  "options": {
    "enable_market": true,
    "enable_auto": true,
    "enable_llm": true,
    "enable_pdf_metadata_extraction": false,
    "enable_business_rag": true,
    "enable_similar_analysis": true,
    "similar_use_llm": true,
    "rag_top_k": 5,
    "fail_on_validation_error": true,
    "enable_human_review": false
  }
}
```

샘플 파일 실행:

```text
POST /api/v1/dev/patent-decision/evaluate-sample/patent_10_1306409
```

### 기능별 Tool API

```text
POST /api/v1/tools/patent-metadata
POST /api/v1/tools/business-rag
POST /api/v1/tools/market-growth
POST /api/v1/tools/auto-score
POST /api/v1/tools/llm-evaluation
POST /api/v1/tools/similar-patents
```

`patent-metadata`는 Swagger에서 PDF 파일을 직접 업로드합니다.

결과:

```text
data/api_test/input/pdf/        업로드된 PDF
data/api_test/input/extracted/  PDF에서 추출된 표준 input JSON
data/mapped_patent_reports/<patent_id>/original/pdf/
data/mapped_patent_reports/<patent_id>/original/input/
```

나머지 tool API는 대체로 다음 형태를 사용합니다.

```json
{
  "patent": {
    "patent_id": "10-0000000",
    "meta": {
      "title": "특허 제목",
      "registration_number": "10-0000000",
      "ipc": ["G06Q10/04"]
    },
    "claims_text": {
      "claim_1": {
        "type": "독립항",
        "text": "청구항 내용"
      }
    },
    "description_summary": "발명의 요약"
  }
}
```

## API 테스트 흐름

### JSON 파일 기반 보고서 생성

1. 서버 실행
2. Swagger 접속
3. `POST /api/v1/reports/patent-maintenance/from-json-file`
4. `samples/input/*.json` 또는 `data/api_test/input/extracted/*.json` 선택
5. 응답의 `job_id`, `status_url`, `result_url` 확인
6. `GET /api/v1/reports/{job_id}/result` 호출

### PDF 기반 input JSON 추출

1. `POST /api/v1/tools/patent-metadata`
2. PDF 파일 업로드
3. 응답의 `normalized_patent`, `extracted_input_path` 확인
4. 생성된 JSON은 `data/api_test/input/extracted/`와 `data/mapped_patent_reports/<patent_id>/original/input/` 아래 저장됨

### PDF 기반 보고서 생성

1. `POST /api/v1/reports/patent-maintenance/from-pdf`
2. PDF 파일 업로드
3. 응답의 `input_path`, `output_path`, `result_url` 확인
4. 생성된 보고서 결과는 `data/api_test/output/reports/`와 `data/mapped_patent_reports/<patent_id>/reports/json/` 아래 저장됨

## 로컬 CLI

샘플 JSON workflow 실행:

```bash
cd eval_logic
python src/cli/run_agent.py samples/input/patent_10_1306409.json
```

LangGraph 시각화:

```bash
python src/cli/visualize_agent_graph.py --skip-png
```

## Git 관리 주의사항

다음 파일/디렉토리는 GitHub에 올리지 않습니다.

```text
eval_logic/.env
eval_logic/.env.*
data/artifacts/
data/business_rag/index/
data/business_rag/raw/
data/business_rag/processed/
```

특히 `.env`에는 API 키가 들어가므로 절대 커밋하면 안 됩니다.

`data/api_test`와 `eval_logic/samples/patent_documents`는 다른 사람이 Swagger/API
테스트를 바로 재현할 수 있도록 커밋 대상에 포함합니다. 다만 실제 기업 내부 PDF,
API 키, 비공개 원문, 고객명 등 민감정보가 포함된 JSON/PDF는 넣지 말고 공개 가능한
테스트 fixture만 유지합니다.

커밋 전 확인:

```bash
git status --short
git check-ignore -v eval_logic/.env
```

## 현재 Legacy 영역

현재 API와 직접 무관한 프로토타입/실험용 코드는 `eval_logic/legacy` 아래에 보관합니다.

```text
eval_logic/legacy/src/crawling
eval_logic/legacy/src/reporting
eval_logic/legacy/src/agent/patent_valuation_agent.py
eval_logic/legacy/src/cli/run_pipeline.py
```

신규 API/서비스 코드는 `legacy`에 의존하지 않도록 관리합니다.
