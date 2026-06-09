# SKIPA API Specification

이 문서는 현재 브랜치 기준 Swagger API를 기능별로 정리한 명세서입니다. 실제 interactive 문서는 서버 실행 후 Swagger에서 확인합니다.

```text
Chatbot UI       http://127.0.0.1:8001/ui
Chatbot Swagger  http://127.0.0.1:8001/docs
Chatbot OpenAPI  http://127.0.0.1:8001/openapi.json

eval_logic Swagger  http://127.0.0.1:8000/docs
eval_logic OpenAPI  http://127.0.0.1:8000/openapi.json
```

## 서버와 데이터 루트

챗봇 서버:

```bash
cd /Users/kgw/skipers-ai
PYTHONPATH="$PWD" python3 -m uvicorn chatbot.app.main:app --reload --host 127.0.0.1 --port 8001
```

보고서 생성 서버:

```bash
cd /Users/kgw/skipers-ai/eval_logic
uvicorn apps.api.main:app --reload --app-dir src --port 8000
```

주요 데이터 경로:

```text
/Users/kgw/skipers-ai/data                         공유 특허 DB, wiki, 사전평가 case
/Users/kgw/skipers-ai/data/patent/<patent_id>      patent.pdf / parsed.json / report.json
/Users/kgw/skipers-ai/data/patent                  MinIO에서 동기화되는 공유 특허 cache
Qdrant collection skipa_shared_patents             공유 특허 DB index
Qdrant collection skipa_patent_visuals             원본 PDF 표/도표/도면/이미지 visual index
/Users/kgw/skipers-ai/data/wiki                    분야별 wiki gate
/Users/kgw/skipers-ai/chatbot/data                 출원팩, 챗봇 전용 데이터
/Users/kgw/skipers-ai/chatbot/data/artifacts       챗봇 검증 산출물
/Users/kgw/skipers-ai/eval_logic/data              보고서 API 테스트/런타임 산출물
```

루트 `data/artifacts`는 사용하지 않습니다. 챗봇 테스트 산출물은 `chatbot/data/artifacts`에만 저장합니다.

## 공통 응답 형태

챗봇 답변 API는 대체로 아래 구조를 반환합니다.

```json
{
  "query": "질문",
  "patent_id": "10-2886381",
  "answer": "답변 본문",
  "source_cards": [
    {
      "label": "근거 1",
      "title": "한국 등록특허 10-2886381",
      "display_title": "평가 보고서 - 의사결정 가이드",
      "source_type": "REPORT_PDF",
      "page_no": 3,
      "location_label": "의사결정 가이드",
      "source_path": "/Users/kgw/skipers-ai/data/10-2886381/report.json",
      "snippet": "근거 일부",
      "metadata": {}
    }
  ],
  "metrics": {
    "intent": "evaluation",
    "answer_mode": "RAG_LLM",
    "quality": 0.72
  }
}
```

검색 API는 아래 구조를 반환합니다.

```json
{
  "query": "질문",
  "mode": "shared_qdrant_search",
  "patent_id": "10-2886381",
  "top_k": 5,
  "hit_count": 5,
  "hits": [
    {
      "patent_id": "10-2886381",
      "score": 0.83,
      "excerpt": "검색된 문장",
      "page_content": "검색 chunk 본문",
      "metadata": {}
    }
  ]
}
```

## System

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/` | 서비스 루트와 UI/docs 경로 확인 |
| `GET` | `/ui` | 챗봇/출원도우미/감사 테스트 UI |
| `GET` | `/chat` | `/ui`와 같은 테스트 UI |
| `GET` | `/health` | 챗봇 서버 상태와 주요 데이터 루트 확인 |

정적 파일 mount:

| URL Prefix | Local Path |
| --- | --- |
| `/files/data` | `chatbot/data` |
| `/files/patents` | `chatbot/data/mapped_patent_reports` 호환용 |
| `/files/business` | `chatbot/data/business` |
| `/files/application` | `chatbot/data/patent_application_official_pack` |
| `/files/pre-eval` | `data/pre_application_cases` |
| `/files/shared` | `data` |

## Chatbot 관리 API

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/api/v1/chatbot/config` | 데이터 루트, 모델, RAG 엔진 상태 확인 |
| `GET` | `/api/v1/chatbot/data-links` | 챗봇 데이터 링크/경로 상태 확인 |
| `GET` | `/api/v1/chatbot/patents` | 사용 가능한 특허 목록 |
| `GET` | `/api/v1/chatbot/patents/{patent_id}` | 특허별 원문/보고서/wiki/index 상태 |
| `GET` | `/api/v1/chatbot/patents/{patent_id}/files` | 특허 폴더 파일 목록 |
| `GET` | `/api/v1/chatbot/patents/{patent_id}/input/latest` | 최신 표준 input JSON |
| `GET` | `/api/v1/chatbot/patents/{patent_id}/report/latest` | 최신 보고서 JSON |
| `GET` | `/api/v1/chatbot/patents/{patent_id}/chunks` | 특허 chunk 조회 |
| `GET` | `/api/v1/chatbot/business/chunks` | 공통 business RAG chunk 조회 |
| `GET` | `/api/v1/chatbot/vectorstore/status` | vectorstore 상태 |
| `GET` | `/api/v1/chatbot/preprocess/status` | vectorstore, 출원팩, 외부 API 상태 |
| `GET` | `/api/v1/chatbot/minio/status` | MinIO `s3://skipa/patent/` 연결과 로컬 cache 상태 |
| `POST` | `/api/v1/chatbot/minio/sync` | MinIO patent prefix를 `data/patent/`로 동기화 |
| `GET` | `/api/v1/chatbot/qdrant/status` | Qdrant 연결과 dashboard URL 확인 |
| `GET` | `/api/v1/chatbot/visual-vectorstore/status` | 특허 원본 visual index 상태, 누락 특허 목록 |
| `POST` | `/api/v1/chatbot/visual-vectorstore/refresh` | 신규/누락 특허 원본 PDF의 표/도표/도면/이미지만 증분 색인 |
| `POST` | `/api/v1/chatbot/visual-vectorstore/search` | visual Qdrant collection 직접 검색 |
| `POST` | `/api/v1/chatbot/search` | RAG 검색 결과만 확인 |
| `POST` | `/api/v1/chatbot/query` | `/search`와 같은 검색 확인 |
| `POST` | `/api/v1/chatbot/answer` | 검색과 답변 생성을 한 번에 확인 |

### POST `/api/v1/chatbot/preprocess/run`

전처리, 감사, 재색인 작업을 Swagger/API에서 실행합니다.

요청:

```json
{
  "mode": "nightly_reindex",
  "use_reviewed": true,
  "refresh_application": true
}
```

지원 mode:

| Mode | 기능 |
| --- | --- |
| `normalize_wiki` | wiki 승인 Markdown 정규화 |
| `refresh_vectorstore` | 승인 데이터 기준 vectorstore refresh |
| `auto_audit_refresh` | wiki 자동 감사 후 승인 데이터만 vectorstore 반영 |
| `audit` | 나쁜 데이터 후보 감사만 실행 |
| `application_preprocess` | 출원 공식팩 전처리와 공용 index 갱신 |
| `visual_index` | `data/patent/<patent_id>/patent.pdf`에서 신규/누락 visual asset만 Qdrant에 증분 색인 |
| `nightly_reindex` | 매일 00:00 작업과 같은 전체 Qdrant 재색인 |
| `shared_index` | 루트 `data/patent/<patent_id>` 공유 특허 DB index 재생성 |
| `all` | wiki 정규화, vectorstore refresh, 출원팩 전처리 |

### Visual vectorstore 정책

`skipa_patent_visuals`는 일반 텍스트 RAG와 분리된 visual 전용 collection입니다.

```text
source: data/patent/<patent_id>/patent.pdf
assets: data/patent/<patent_id>/extracted/assets/original_pdf/*.png
manifest: data/patent/<patent_id>/extracted/visual_index_manifest.json
payload: asset_url, source_url, page_no, asset_bbox, asset_kind, section_title, caption/문맥
```

규칙:

- `report.json`이 없어도 `patent.pdf`만 있으면 visual index를 생성합니다.
- `visual_index_manifest.json`에 저장한 `patent.pdf` SHA1이 같으면 다음 refresh에서 건너뜁니다.
- Qdrant collection이 비어 있거나 없어졌으면 전체 후보를 다시 처리합니다.
- 챗봇 질문에 `도면`, `표`, `도표`, `이미지`, `다이어그램`, `차트` 의도가 있으면 visual collection을 추가 검색합니다.

검색 예:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/chatbot/visual-vectorstore/search \
  -H "Content-Type: application/json" \
  -d '{"patent_id":"10-1959619","query":"대표도와 결함 시각화 흐름","top_k":4}'
```

### MinIO patent sync

Kubernetes 내부에서는 아래 환경변수 기준으로 MinIO를 사용합니다.

```env
MINIO_ENDPOINT=http://skipa-minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=...
MINIO_BUCKET=skipa
MINIO_PATENT_PREFIX=patent
```

로컬 노트북/맥에서 UI를 직접 띄울 때는 먼저 port-forward를 열고 endpoint를 바꿉니다.

```bash
kubectl -n skala3-finalproj-class2-team8 port-forward svc/skipa-minio 19000:9000
export MINIO_ENDPOINT=http://127.0.0.1:19000
```

상태 확인:

```bash
curl http://127.0.0.1:8001/api/v1/chatbot/minio/status
```

동기화와 공유 index 재생성:

```bash
curl -X POST "http://127.0.0.1:8001/api/v1/chatbot/minio/sync?rebuild_index=true"
```

### POST `/api/v1/chatbot/vectorstore/refresh`

query parameter:

```text
auto_audit=true
```

`true`면 주의/나쁜 데이터 후보를 자동 제외하고 승인본으로 refresh합니다.

## 통합 특허 챗봇 API

공개 기준 기능명은 `patent-chat`입니다. `/api/v1/rag`와 `/rag`는 호환 alias이며 Swagger schema에서는 숨겨져 있습니다.

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/api/v1/patent-chat/patents` | 특허 목록과 RAG 엔진 상태 |
| `GET` | `/api/v1/patent-chat/patent-summary-cards` | UI용 특허 요약 카드 |
| `GET` | `/api/v1/patent-chat/engine/status` | Hybrid retrieval 엔진 상태 |
| `POST` | `/api/v1/patent-chat/query` | 선택 특허 근거 검색 |
| `POST` | `/api/v1/patent-chat/answer` | 선택 특허 검색+답변 |
| `POST` | `/api/v1/patent-chat/chat` | 선택 특허 기준 챗봇 답변 |
| `POST` | `/api/v1/patent-chat/global/chat` | 전체 특허 기준 챗봇 답변 |
| `POST` | `/api/v1/patent-chat/reindex` | 선택 특허 index 재생성 |
| `POST` | `/api/v1/patent-chat/global/reindex` | 전체 특허 global index 재생성 |
| `POST` | `/api/v1/patent-chat/business/reindex` | business/common index 재생성 |
| `POST` | `/api/v1/patent-chat/feedback` | 답변 피드백 저장 |
| `GET` | `/api/v1/patent-chat/page-image` | PDF page image 렌더링 |
| `GET` | `/api/v1/patent-chat/chat/mermaid` | 특허 챗봇 LangGraph Mermaid |
| `GET` | `/api/v1/patent-chat/ingestion/mermaid` | 전처리/재색인 Mermaid |

ChatRequest:

```json
{
  "patent_id": "10-2886381",
  "question": "CMP Pad 물류 관리 시스템의 유지 판단 근거를 알려줘",
  "user_id": "demo",
  "chat_history": [
    {"role": "user", "content": "이 특허의 리스크를 알려줘"},
    {"role": "assistant", "content": "주요 리스크는 ..."}
  ],
  "context_patent_id": "10-2886381"
}
```

SearchRequest:

```json
{
  "query": "청구항 1의 핵심 구성을 표로 정리해줘",
  "patent_id": "10-2886381",
  "source_types": ["ORIGINAL_PDF", "REPORT_PDF"],
  "top_k": 6
}
```

ReindexRequest:

```json
{
  "patent_id": "10-2886381",
  "force_rebuild": true,
  "refresh_reviewed_vectorstore": false
}
```

## Wiki 감사 API

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/api/v1/wiki/topics` | 분야별 wiki vectorstore 목록 및 상태 |
| `GET` | `/api/v1/wiki/topics/{topic_slug}` | 특정 분야 approved preview와 최근 draft |
| `POST` | `/api/v1/wiki/topics/refresh` | 모든 분야 wiki Qdrant vectorstore 재빌드 |
| `POST` | `/api/v1/wiki/topics/reclassify` | 전체 특허 분야 재분류 |
| `GET` | `/api/v1/wiki/topics/{topic_slug}/patent` | 특허 ID가 매핑된 분야 조회 |
| `POST` | `/api/v1/wiki/audit` | wiki/챗봇 데이터 감사 실행 |
| `GET` | `/api/v1/wiki/audit-review` | 사람 검토용 감사 Markdown 조회 |
| `GET` | `/api/v1/wiki/audit-report` | 최신 감사 리포트 |
| `POST` | `/api/v1/wiki/audit-apply` | 사람 검토 결과 적용 및 vectorstore refresh |
| `POST` | `/api/v1/wiki/audit-auto-refresh` | 자동 감사로 주의/나쁜 데이터 제외 후 refresh |
| `POST` | `/api/v1/wiki/agent/run` | Wiki LangGraph agent 직접 실행 |
| `GET` | `/api/v1/wiki/agent/mermaid` | Wiki LangGraph Mermaid |

AuditApplyRequest:

```json
{
  "audit_id": "20260607_120000",
  "exclude_finding_ids": ["finding_001", "finding_002"],
  "reviewer": "kgw",
  "notes": "관련 없는 웹검색 draft 제외",
  "refresh_vectorstore": true
}
```

WikiAgentRunRequest:

```json
{
  "mode": "auto_refresh",
  "audit_id": null,
  "exclude_finding_ids": null,
  "reviewer": "auto-auditor",
  "notes": "nightly",
  "refresh_vectorstore": true
}
```

## 특허 출원 도우미 API

출원 도우미는 공용 공식팩 index와 현재 선택한 실패특허 case index를 함께 사용합니다. 실패특허 case를 선택하지 않으면 실패 원인/거절 대응 채팅은 시작하지 않고 업로드/선택을 요청합니다.

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/api/v1/application/status` | 출원 공식팩/index 상태 |
| `GET` | `/api/v1/application/external/status` | KIPRIS/KOSIS/Tavily 연결 상태 |
| `POST` | `/api/v1/application/preprocess` | 출원 공식팩 전처리 리포트 생성 및 index 갱신 |
| `POST` | `/api/v1/application/index/refresh` | 출원 공식팩 vectorstore 갱신 |
| `POST` | `/api/v1/application/sources/download` | 공식 자료 다운로드/크롤링 |
| `GET` | `/api/v1/application/sources/download-report` | 다운로드/크롤링 리포트 |
| `POST` | `/api/v1/application/chat` | 출원 도우미 챗봇 |
| `GET` | `/api/v1/application/chat/mermaid` | 출원 도우미 LangGraph Mermaid |
| `POST` | `/api/v1/application/feedback/create` | 의견서/기존 보고서 기반 피드백 리포트 생성 |
| `POST` | `/api/v1/application/feedback/upload` | 의견서 파일 업로드 후 피드백 HTML 생성 |
| `POST` | `/api/v1/application/report/generate` | 호환용 전역 출원 피드백 리포트 생성 |

PatentApplicationChatRequest:

```json
{
  "question": "이 실패특허는 왜 거절됐고 무엇을 보정해야 해?",
  "user_id": "demo",
  "failed_patent_id": "10-1959619_failed",
  "chat_history": [],
  "top_k": 8,
  "refresh_index": false
}
```

PatentApplicationPreprocessRequest:

```json
{
  "refresh_index": true
}
```

PatentApplicationDownloadRequest:

```json
{
  "force": false,
  "timeout": 20,
  "limit": 20,
  "include_embedded": true
}
```

## 실패특허 Case API

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/api/v1/application/failed-patents` | 실패특허 case 목록 |
| `GET` | `/api/v1/application/failed-patents/{case_id}` | case 파일/index 상태 |
| `POST` | `/api/v1/application/failed-patents/upload` | 실패특허 PDF와 선택 사유서 업로드 |
| `POST` | `/api/v1/application/failed-patents/create` | 서버 로컬 PDF 경로로 case 생성 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/report/generate` | eval_logic 보고서 생성 후 case `reports/` 저장 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/report/save` | 외부 생성 보고서 저장 후 case index 갱신 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/index/refresh` | 선택 case 1건 전용 vectorstore 갱신 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/chat` | 선택 case 기준 출원 도우미 답변 |

파일 업로드 API는 `multipart/form-data`입니다.

```text
original_pdf: 실패특허 원본 PDF, 필수
rejection_file: 거절의견서/사유서, 선택
case_id: 직접 지정할 case ID, 선택
title: case 제목, 선택
rejection_reason_text: 거절/실패 사유 텍스트, 선택
reviewer: 등록자, 선택
notes: 메모, 선택
refresh_index: true
```

서버 로컬 PDF 경로로 case 생성:

```json
{
  "case_id": "10-1959619_failed",
  "title": "10-1959619 실패특허 분석",
  "original_pdf_path": "/Users/kgw/skipers-ai/chatbot/data/patent_application_official_pack/failed_patent/source/10-1959619.pdf",
  "rejection_reason_text": "진보성 거절 가능성",
  "rejection_file_path": null,
  "reviewer": "kgw",
  "notes": "발표 시연용",
  "refresh_index": true
}
```

보고서 생성:

```json
{
  "title": "10-1959619 실패특허 재평가 보고서",
  "enable_market": true,
  "enable_auto": true,
  "enable_llm": true,
  "enable_pdf_metadata_extraction": true,
  "enable_business_rag": true,
  "enable_similar_analysis": true,
  "similar_use_llm": true,
  "rag_top_k": 5,
  "fail_on_validation_error": true,
  "enable_human_review": false,
  "refresh_index": true
}
```

보고서 저장:

```json
{
  "title": "외부 재평가 보고서",
  "report": {"summary": "보고서 JSON"},
  "report_text": null,
  "source_report_path": null,
  "refresh_index": true
}
```

## 출원 전 사전평가 API

사전평가는 아직 출원하지 않은 아이디어/청구항을 받아 케이스 보고서를 생성하고, 그 보고서 전용 vectorstore로 채팅합니다.

| Method | Path | 기능 |
| --- | --- | --- |
| `POST` | `/api/v1/pre-eval/evaluate` | 출원 전 사전평가 실행 및 케이스 생성 |
| `GET` | `/api/v1/pre-eval/cases` | 사전평가 케이스 목록 |
| `GET` | `/api/v1/pre-eval/cases/{case_id}` | 케이스 상태 및 vectorstore 정보 |
| `GET` | `/api/v1/pre-eval/cases/{case_id}/report` | 사전평가 보고서 원본 JSON |
| `POST` | `/api/v1/pre-eval/cases/{case_id}/index/refresh` | 케이스 vectorstore 재빌드 |
| `POST` | `/api/v1/pre-eval/cases/{case_id}/chat` | 사전평가 보고서 기반 챗봇 |
| `POST` | `/api/v1/pre-eval/cases/{case_id}/search` | 케이스 vectorstore 직접 검색 |
| `GET` | `/api/v1/pre-eval/graph/mermaid` | 사전평가 LangGraph Mermaid |

평가 요청 예시:

```json
{
  "patentName": "AI 기반 물류 설비 이상 감지 시스템",
  "technologyDescription": "센서 데이터와 공정 로그를 결합해 설비 이상을 사전 탐지한다.",
  "claims": [
    "설비 센서 데이터를 수집하는 단계",
    "공정 로그와 센서 데이터를 결합해 이상 점수를 산출하는 단계"
  ],
  "relatedBusiness": "반도체 생산 설비 운영",
  "targetCountries": ["KR", "US"],
  "enable_llm": true,
  "run_web_search": true
}
```

채팅 요청 예시:

```json
{
  "question": "이 아이디어가 거절될 가능성이 높은 부분과 보강 방향을 알려줘",
  "user_id": "demo",
  "chat_history": [],
  "top_k": 8
}
```

## eval_logic 보고서 생성 API

`eval_logic` 서버는 포트 `8000`에서 실행합니다.

| Method | Path | 기능 |
| --- | --- | --- |
| `GET` | `/health` | 보고서 서버 상태 확인 |
| `POST` | `/api/v1/reports/patent-valuation/from-json` | JSON body로 보고서 생성 |
| `POST` | `/api/v1/reports/patent-valuation/from-json-file` | JSON 파일 업로드로 보고서 생성 |
| `POST` | `/api/v1/reports/patent-valuation/from-pdf` | PDF 업로드 후 input 추출과 보고서 생성 |
| `GET` | `/api/v1/reports/{job_id}` | Job 상태 요약 |
| `GET` | `/api/v1/reports/{job_id}/status` | Job 상태 |
| `GET` | `/api/v1/reports/{job_id}/result` | 보고서 결과와 검증 정보 |

Tool API:

| Method | Path | 기능 |
| --- | --- | --- |
| `POST` | `/api/v1/tools/patent-metadata` | PDF 메타데이터/입력 추출 |
| `POST` | `/api/v1/tools/business-rag` | 사업화 RAG 평가 |
| `POST` | `/api/v1/tools/market-growth` | KOSIS/시장 성장률 평가 |
| `POST` | `/api/v1/tools/auto-score` | 규칙 기반 자동 점수 |
| `POST` | `/api/v1/tools/llm-evaluation` | LLM 평가 |
| `POST` | `/api/v1/tools/similar-patents` | 유사 특허 분석 |

Dev API:

| Method | Path | 기능 |
| --- | --- | --- |
| `POST` | `/api/v1/dev/patent-valuation/evaluate` | 개발용 평가 실행 |
| `POST` | `/api/v1/dev/patent-valuation/evaluate-sample/{sample_name}` | 샘플 파일 기준 평가 실행 |

## Swagger 테스트 순서

1. `GET /api/v1/chatbot/config`로 데이터 루트와 모델 설정을 확인합니다.
2. `GET /api/v1/chatbot/preprocess/status`로 vectorstore와 출원팩 상태를 확인합니다.
3. MinIO 데이터를 먼저 확인하려면 `GET /api/v1/chatbot/minio/status`를 호출합니다.
4. 필요하면 `POST /api/v1/chatbot/minio/sync?rebuild_index=true`로 `s3://skipa/patent/`를 `data/patent/`에 동기화합니다.
5. 필요하면 `POST /api/v1/chatbot/preprocess/run`에 `{"mode":"shared_index"}`를 보내 공유 특허 DB index만 다시 갱신합니다.
6. 도면/표/이미지 검색까지 확인하려면 `POST /api/v1/chatbot/visual-vectorstore/refresh`를 한 번 실행합니다.
7. wiki 데이터 검증은 `POST /api/v1/wiki/audit-auto-refresh` 또는 `{"mode":"auto_audit_refresh"}`로 실행합니다.
8. 일반 특허 질문은 `POST /api/v1/patent-chat/chat`으로 테스트합니다.
9. 출원 도우미는 먼저 `/api/v1/application/failed-patents/upload`로 실패특허 PDF를 올리고, case ID를 받은 뒤 `/failed-patents/{case_id}/chat`을 호출합니다.
10. 실패특허 보고서가 필요하면 `/failed-patents/{case_id}/report/generate`를 호출한 뒤 같은 case chat으로 결과를 확인합니다.
11. 출원 전 아이디어 평가는 `/api/v1/pre-eval/evaluate`로 케이스를 만들고 `/pre-eval/cases/{case_id}/chat`으로 질문합니다.

## CLI 대응표

| 목적 | CLI |
| --- | --- |
| 챗봇 서버 실행 | `bash chatbot/scripts/start_chatbot_server.sh` |
| 상태 확인 | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode status` |
| 원본 visual 증분 색인 | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode visual-index` |
| 원본 visual 강제 재색인 | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode visual-index --force` |
| wiki 자동 감사와 refresh | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode auto-audit` |
| 전체 nightly 재색인 | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode nightly-reindex` |
| 출원 공식팩 전처리 | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-preprocess` |
| 실패특허 case 생성 | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-case --original-pdf "/path/to/failed.pdf"` |
| 실패특허 보고서 생성 | `bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-case-generate --case-id "10-1959619_failed"` |

공유 특허 DB index만 단독 갱신하려면 API를 사용합니다.

```bash
curl -X POST http://127.0.0.1:8001/api/v1/chatbot/preprocess/run \
  -H "Content-Type: application/json" \
  -d '{"mode":"shared_index"}'
```
