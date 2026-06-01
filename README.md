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
- 챗봇 RAG용 특허별 원문/보고서/wiki/index 데이터 관리
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

  chatbot/
    .env.example          # 챗봇 실행 환경변수 예시
    app/                  # 챗봇 FastAPI/RAG 애플리케이션 소스 위치
      routers/            # rag, agent, wiki, page 라우터
      rag/                # retrieval, answer generation, source handling
      agents/             # patent/wiki/router/merge agent 흐름
      ingestion/          # PDF/보고서/wiki chunk 생성 파이프라인
      wiki/               # wiki archive/vectorstore 연동
      search/             # web search provider 연동
      core/               # chatbot pipeline orchestration
      utils/              # path/config helper
    data/
      mapped_patent_reports -> ../../data/mapped_patent_reports
      business -> ../../data/business
    wiki_auditor/         # wiki 감사 결과와 대화 이력
    logs/                 # 로컬 실행 로그, git 제외
    patents_backup_*/     # 이전 특허 데이터 backup, git 제외
```

## 전체 아키텍처

전체 시스템은 `data/`를 중심에 두고, 보고서 생성 로직과 챗봇 RAG가 같은 특허별
폴더를 바라보는 구조입니다.

```text
사용자 / Swagger / CLI
        |
        v
eval_logic FastAPI
  - PDF 업로드
  - JSON 업로드
  - tool API
  - 보고서 생성 API
        |
        v
전처리 / 정규화
  - PDF 원문 파싱
  - normalize_patent_input()
  - 표준 특허 input JSON 생성
        |
        v
PatentDecisionWorkflow
  - collect_evidence
  - validate_input
  - run_valuation
  - analyze_similar_patents
  - make_decision
  - build_report
        |
        v
data/
  - api_test/                         Swagger/API 재현용 입출력
  - mapped_patent_reports/<patent_id> 특허별 원문, 보고서, 위키, index
        ^
        |
chatbot
  - 특허별 원문 chunk
  - 보고서 chunk
  - wiki/vectorstore
  - FAISS index 기반 질의 응답
```

역할 분리는 다음과 같습니다.

```text
eval_logic
  PDF/JSON 입력을 받아 평가 workflow를 실행하고 보고서 JSON을 생성합니다.

chatbot
  특허별 원문, 보고서, wiki, vector index를 읽어 질의 응답에 사용합니다.

data
  두 시스템이 공유하는 단일 데이터 루트입니다. 특허 하나는
  data/mapped_patent_reports/<patent_id> 하나의 폴더에서 관리합니다.
```

기존 경로와의 호환성을 위해 `chatbot/data/mapped_patent_reports`,
`chatbot/data/business`, `eval_logic/api_test`는 중앙 `data/` 아래의 실제 폴더를
가리키도록 연결되어 있습니다.

## Chatbot 디렉토리

`chatbot`은 보고서 생성 결과와 특허 원문 데이터를 RAG로 검색해 사용자의 질문에
답하는 영역입니다. 이 repository에서 커밋으로 관리되는 핵심은 실행 환경 예시,
중앙 데이터 폴더 연결, wiki 감사 결과입니다.

```text
chatbot/
  .env.example
    DATA_ROOT, PATENTS_ROOT, embedding model, LLM model, web search, API key
    변수 예시를 제공합니다. 실제 키는 chatbot/.env에만 둡니다.

  data/mapped_patent_reports
    ../../data/mapped_patent_reports를 가리키는 연결입니다.
    챗봇은 여기서 특허별 original, reports, wiki, extracted, index를 읽습니다.

  data/business
    ../../data/business를 가리키는 연결입니다.
    제품/사업화 RAG에 필요한 공통 business index를 읽습니다.

  wiki_auditor/
    wiki 문서 구조, 고아 페이지, 모순 여부를 점검한 결과를 보관합니다.
```

챗봇 앱 소스가 포함된 환경에서는 `chatbot/app` 아래가 다음 역할을 담당합니다.

```text
app/routers
  외부 API 라우터입니다. rag 질의, agent 질의, wiki 조회, page/file 제공을 담당합니다.

app/rag
  FAISS 검색, context 구성, 답변 생성, source 정리, report 기반 빠른 답변 로직을 담당합니다.

app/agents
  질문을 patent/wiki/web/search 경로로 분기하고, 여러 검색 결과를 병합하는 agent 흐름을 담당합니다.

app/ingestion
  원문 PDF, 보고서, wiki 문서를 chunk로 만들고 vector index를 재생성하는 전처리 파이프라인입니다.

app/wiki
  특허별 wiki 문서와 wiki vectorstore를 관리합니다.

app/search
  웹 검색 fallback 또는 외부 evidence provider를 연결합니다.
```

현재 커밋에는 챗봇 데이터 연결 파일과 감사 결과는 포함되어 있지만,
`chatbot/app/*.py` 소스 파일은 포함되어 있지 않습니다. 따라서 이 repository만
clone한 상태에서는 챗봇 서버 실행까지는 검증할 수 없고, 데이터 경로와 RAG 산출물
존재 여부를 확인할 수 있습니다. 챗봇 소스가 별도 배포물로 제공되는 경우에는
`chatbot/.env.example`을 기준으로 `DATA_ROOT=../data`,
`PATENTS_ROOT=../data/mapped_patent_reports`를 맞춘 뒤 실행합니다.

## 중앙 데이터 저장 규칙

보고서 생성 로직과 챗봇은 모두 `SKIPA_DATA_ROOT` 또는 `DATA_ROOT`를 먼저 확인하고,
값이 없으면 repository 루트의 `data/`를 기본값으로 사용합니다.

특허별 표준 폴더 구조:

```text
data/mapped_patent_reports/<patent_id>/
  manifest.json
  original/
    pdf/
      latest.pdf
      <timestamp>_<source>.pdf
    input/
      latest.json
      <timestamp>_<kind>_<source>.json
  reports/
    json/
      latest.json
      <timestamp>_<job_id>.json
  wiki/
    vectorstore/
  extracted/
    all_chunks.jsonl
    original_pdf_chunks.jsonl
    report_pdf_chunks.jsonl
    original_visual_chunks.jsonl
    report_visual_chunks.jsonl
    assets/
  index/
    faiss/
```

`manifest.json`에는 특허 ID, 제목, 최신 input, 최신 PDF, 최신 보고서, wiki/index
위치, 저장 이력이 기록됩니다. 발표나 디버깅 때는 이 파일을 보면 해당 특허에 어떤
데이터가 연결되어 있는지 빠르게 확인할 수 있습니다.

이 구조로 통합한 이유:

- 보고서 생성 결과가 곧바로 챗봇 질의 응답 데이터가 됩니다.
- `eval_logic/api_test`와 `chatbot/data`에 흩어져 있던 입출력을 한곳에서 추적합니다.
- 특허별로 원문, 보고서, wiki, vector index를 같이 보관해 재현성이 좋아집니다.
- `latest.*` 파일을 두어 API나 챗봇이 가장 최근 데이터를 쉽게 찾을 수 있습니다.

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

## 챗봇 전처리 방식

챗봇은 보고서 생성 로직이 저장한 특허별 폴더를 그대로 사용합니다. 전처리 결과는
`data/mapped_patent_reports/<patent_id>/extracted`, `index`, `wiki` 아래에
저장됩니다.

전처리 대상:

```text
특허 원문 PDF
  명세서, 청구항, 도면/이미지, 페이지 단위 텍스트

보고서 PDF 또는 보고서 JSON
  평가 항목, 표, 유지/포기 판단 근거, 점수, 코멘트

wiki 데이터
  특허별 배경 지식, 용어 설명, 외부/내부 정리 문서
```

전처리 산출물:

```text
extracted/all_chunks.jsonl
  원문, 보고서, 시각 자료 chunk를 통합한 검색 단위

extracted/original_pdf_chunks.jsonl
  특허 원문 텍스트 chunk

extracted/report_pdf_chunks.jsonl
  보고서 텍스트 chunk

extracted/original_visual_chunks.jsonl
extracted/report_visual_chunks.jsonl
  도면, 이미지, 표 같은 시각 자료 chunk

extracted/assets/
  PDF에서 추출한 이미지, 표 HTML/PNG, thumbnail

index/faiss/
  특허별 RAG 검색용 FAISS index

wiki/vectorstore/faiss/
  특허별 wiki 검색용 FAISS index
```

이 방식으로 전처리한 이유:

- 원문과 보고서의 출처를 chunk metadata로 유지해 답변 근거를 추적할 수 있습니다.
- 긴 PDF를 한 번에 LLM에 넣지 않고 검색 가능한 작은 단위로 쪼개 응답 품질을 높입니다.
- 표, 도면, 페이지 이미지 같은 시각 자료도 별도 asset으로 남겨 챗봇이 근거 자료를 연결할 수 있습니다.
- 특허별 index를 분리해 다른 특허의 내용이 섞이는 문제를 줄입니다.
- `_global` index를 같이 두어 전체 특허를 대상으로 한 검색도 확장할 수 있습니다.

보고서 생성 API가 새 input/output을 만들면 `patent_data_store.py`가 같은 특허 폴더의
`original/input`과 `reports/json`에 최신 파일을 저장합니다. 이후 챗봇 전처리 또는
index 재생성 단계에서 이 파일들을 읽으면 새 보고서가 RAG에 반영됩니다.

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
PYTHONPATH=src uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
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

## 통합 워크플로우

### PDF에서 보고서와 챗봇 데이터까지

```text
1. 사용자가 Swagger에서 특허 PDF 업로드
2. eval_logic이 PDF를 data/api_test/input/pdf/에 저장
3. document_processing이 PDF에서 특허번호, 제목, 청구항, 명세서 섹션 추출
4. normalize_patent_input()이 표준 input JSON으로 정규화
5. 추출 JSON을 data/api_test/input/extracted/에 저장
6. 같은 input을 data/mapped_patent_reports/<patent_id>/original/input/에 저장
7. 원본 PDF를 data/mapped_patent_reports/<patent_id>/original/pdf/에 저장
8. PatentDecisionWorkflow가 평가와 의사결정 보고서 생성
9. 보고서 JSON을 data/api_test/output/reports/에 저장
10. 같은 보고서를 data/mapped_patent_reports/<patent_id>/reports/json/에 저장
11. 챗봇은 해당 특허 폴더의 original, reports, wiki, index 데이터를 사용
```

### JSON에서 보고서 생성

```text
1. 사용자가 표준 특허 JSON 또는 PDF 추출 JSON 업로드
2. normalize_patent_input()으로 입력 형태 통일
3. data/api_test/input/uploads/에 업로드 원본 저장
4. data/mapped_patent_reports/<patent_id>/original/input/에 특허별 input 저장
5. workflow 실행 후 보고서 생성
6. data/api_test/output/reports/와 특허별 reports/json/에 결과 저장
```

### 챗봇 조회 흐름

```text
1. 사용자가 특정 특허에 대해 질문
2. 챗봇이 data/mapped_patent_reports/<patent_id>를 찾음
3. index/faiss, wiki/vectorstore/faiss, extracted/*.jsonl에서 관련 chunk 검색
4. 원문 chunk, 보고서 chunk, wiki chunk를 context로 구성
5. 답변과 함께 근거가 되는 원문/보고서/wiki 정보를 반환
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

## 기능별 검증 방법

### GitHub 반영 확인

```bash
cd /Users/kgw/skipers-ai
git log -1 --oneline --decorate
git status --short
```

정상 기준:

```text
HEAD와 origin/<current-branch>가 같은 커밋을 가리킴
git status --short 출력이 비어 있음
```

### 공통 데이터 폴더 확인

```bash
cd /Users/kgw/skipers-ai
ls data
find data/mapped_patent_reports -maxdepth 2 -name manifest.json
```

정상 기준:

```text
data/api_test
data/mapped_patent_reports
data/business
특허별 manifest.json
```

### 챗봇 데이터 연결 확인

```bash
cd /Users/kgw/skipers-ai
readlink chatbot/data/mapped_patent_reports
readlink chatbot/data/business
find data/mapped_patent_reports -path '*index/faiss/*' -type f
find data/mapped_patent_reports -path '*wiki/vectorstore/faiss/*' -type f
find chatbot/app -name '*.py' -type f
```

정상 기준:

```text
chatbot/data/mapped_patent_reports -> ../../data/mapped_patent_reports
chatbot/data/business -> ../../data/business
FAISS index.faiss, index.pkl 파일 존재
챗봇 서버 실행 검증을 하려면 chatbot/app 아래 Python source 파일이 존재해야 함
```

### Python import와 문법 확인

```bash
cd /Users/kgw/skipers-ai
python3 -m compileall eval_logic/src
```

정상 기준:

```text
compile error 없이 종료
```

### PDF 추출 API 확인

서버 실행:

```bash
cd /Users/kgw/skipers-ai/eval_logic
PYTHONPATH=src uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger에서 실행:

```text
POST /api/v1/tools/patent-metadata
파일 예시: ../data/api_test/input/pdf/20260529_144101_pdf.pdf
```

정상 기준:

```text
응답에 normalized_patent, extracted_input_path 포함
data/api_test/input/extracted/에 JSON 생성
data/mapped_patent_reports/<patent_id>/original/pdf/latest.pdf 생성
data/mapped_patent_reports/<patent_id>/original/input/latest.json 생성
```

### JSON 보고서 생성 API 확인

Swagger에서 실행:

```text
POST /api/v1/reports/patent-maintenance/from-json-file
파일 예시: ../data/api_test/input/extracted/20260529_144106_10-1959619_20260529_144101_pdf.json
GET /api/v1/reports/{job_id}/result
```

정상 기준:

```text
status가 success
data/api_test/output/reports/에 보고서 JSON 생성
data/mapped_patent_reports/<patent_id>/reports/json/latest.json 생성
응답 artifacts에 patent_data_dir, patent_report_output_path 포함
```

### PDF 기반 보고서 생성 API 확인

Swagger에서 실행:

```text
POST /api/v1/reports/patent-maintenance/from-pdf
파일 예시: ../data/api_test/input/pdf/20260529_144101_pdf.pdf
GET /api/v1/reports/{job_id}/result
```

정상 기준:

```text
PDF 추출 JSON과 보고서 JSON이 모두 생성됨
특허별 original/pdf, original/input, reports/json이 모두 갱신됨
```

### CLI workflow 확인

```bash
cd /Users/kgw/skipers-ai/eval_logic
python3 src/cli/run_agent.py samples/input/patent_10_1306409.json
```

정상 기준:

```text
Workflow: langgraph
Status: success
결과 저장 경로 출력
```

### 챗봇 서버 확인 시 주의

현재 이 repository에서는 챗봇 데이터 연결과 RAG 산출물 경로를 확인할 수 있습니다.
챗봇 앱 소스가 별도 repository 또는 별도 배포물에 있을 경우, source를 `chatbot/app`
아래에 둔 뒤 해당 앱의 실행 명령으로 서버를 띄웁니다.

예상 실행 형태:

```bash
cd /Users/kgw/skipers-ai/chatbot
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

확인할 환경변수:

```text
DATA_ROOT=../data
PATENTS_ROOT=../data/mapped_patent_reports
PUBLIC_FILE_BASE_URL=http://localhost:8000/files
EMBEDDING_MODEL=BAAI/bge-m3
TOP_K=10
```

정상 기준:

```text
챗봇이 data/mapped_patent_reports/<patent_id>/index/faiss를 읽음
특허 원문 chunk, 보고서 chunk, wiki chunk를 context로 사용함
질문 로그는 chatbot/logs/rag_query_log.jsonl에 기록됨
```

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
