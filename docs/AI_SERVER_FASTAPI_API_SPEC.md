# SKIPA AI Server FastAPI API Spec

이 문서는 `skipa-ai-server` 안의 두 FastAPI 앱을 기준으로 정리한 API 명세입니다.

- Chatbot 앱: `chatbot/app/main.py`
- 재평가 보고서 앱: `eval_logic/src/apps/api/main.py`

## 공통

| 항목 | Chatbot API | 재평가 보고서 API |
| --- | --- | --- |
| 앱 타이틀 | `SKIPA Chatbot API` | `SKIPA Revaluation Report API` |
| OpenAPI | `/openapi.json` | `/openapi.json` |
| Swagger UI | `/docs` | `/docs` |
| 인증 | 현재 코드 기준 별도 인증 없음 | 현재 코드 기준 별도 인증 없음 |
| 기본 응답 포맷 | JSON | JSON |

에러는 FastAPI 기본 형식입니다.

```json
{
  "detail": "error message"
}
```

---

# 1. Chatbot FastAPI

## 1.1 System

### `GET /`

챗봇 API 루트와 주요 링크를 반환합니다.

응답 예:

```json
{
  "service": "skipa-chatbot-api",
  "ui": "/ui",
  "chat": "/chat",
  "docs": "/docs",
  "openapi": "/openapi.json"
}
```

### `GET /health`

데이터 경로와 서비스 상태를 확인합니다.

응답 주요 필드:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `status` | string | `ok` |
| `data_root` | string | 챗봇 데이터 루트 |
| `patents_root` | string | 특허 데이터 루트 |
| `patents_root_exists` | boolean | 특허 데이터 루트 존재 여부 |
| `patent_application_root` | string | 출원 도우미 데이터 루트 |
| `patent_application_root_exists` | boolean | 출원 도우미 데이터 루트 존재 여부 |

### `GET /ui`

챗봇 테스트 UI HTML을 반환합니다.

### `GET /chat`

특허 챗봇 테스트 UI HTML을 반환합니다.

## 1.2 Static File Mounts

조건부로 디렉터리가 존재할 때 mount됩니다.

| Prefix | 내용 |
| --- | --- |
| `/ui/static` | 챗봇 UI 정적 파일 |
| `/files/data` | 챗봇 데이터 파일 |
| `/files/patents` | 특허 파일 |
| `/files/business` | 업무/사업 파일 |
| `/files/application` | 특허 출원 도우미 파일 |
| `/files/pre-eval` | 사전평가 파일 |
| `/files/shared` | 공유 데이터 파일 |

## 1.3 Chatbot 데이터/검색 API

Base prefix: `/api/v1/chatbot`

### `GET /api/v1/chatbot/config`

챗봇 설정, 모델, 데이터 루트, RAG 엔진 상태를 반환합니다.

### `GET /api/v1/chatbot/data-links`

`chatbot/data` symlink 상태를 반환합니다.

### `GET /api/v1/chatbot/patents`

챗봇이 사용할 수 있는 특허 목록을 반환합니다.

응답 예:

```json
{
  "count": 10,
  "items": []
}
```

### `GET /api/v1/chatbot/patents/{patent_id}`

특허별 원문, 보고서, wiki, index 상태를 반환합니다.

Query:

| 이름 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `include_files` | boolean | `true` | 특허 폴더 파일 목록 포함 여부 |

### `GET /api/v1/chatbot/patents/{patent_id}/files`

특허 폴더 파일 목록을 반환합니다.

Query:

| 이름 | 타입 | 기본값 | 제약 |
| --- | --- | --- | --- |
| `limit` | integer | `300` | `1..1000` |

### `GET /api/v1/chatbot/patents/{patent_id}/input/latest`

특허별 최신 input JSON을 반환합니다.

### `GET /api/v1/chatbot/patents/{patent_id}/report/latest`

특허별 최신 report JSON을 반환합니다.

### `GET /api/v1/chatbot/patents/{patent_id}/chunks`

특허별 chunk를 조회합니다.

Query:

| 이름 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `chunk_file` | string | `all` | `all`, `original`, `report`, `original_visual`, `report_visual` |
| `source_type` | string[] | null | `ORIGINAL_PDF`, `REPORT_PDF` 등 |
| `offset` | integer | `0` | `>=0` |
| `limit` | integer | `20` | `1..100` |

### `GET /api/v1/chatbot/business/chunks`

공통 business RAG chunk를 조회합니다.

Query:

| 이름 | 타입 | 기본값 | 제약 |
| --- | --- | --- | --- |
| `offset` | integer | `0` | `>=0` |
| `limit` | integer | `20` | `1..100` |

### `GET /api/v1/chatbot/vectorstore/status`

챗봇 vectorstore 갱신 상태를 반환합니다.

### `GET /api/v1/chatbot/preprocess/status`

전처리, vectorstore, application 상태를 통합 반환합니다.

### `POST /api/v1/chatbot/preprocess/run`

전처리/wiki 정리/vectorstore/application preprocess를 실행합니다.

요청:

```json
{
  "mode": "refresh_vectorstore",
  "use_reviewed": true,
  "refresh_application": true
}
```

`mode` 값:

| 값 | 설명 |
| --- | --- |
| `normalize_wiki` | wiki context 정규화 |
| `refresh_vectorstore` | vectorstore 재생성 |
| `auto_audit_refresh` | 자동 감사 후 refresh |
| `audit` | wiki/챗봇 데이터 감사 |
| `application_preprocess` | 출원 공식팩 전처리 |
| `nightly_reindex` | 전체 nightly reindex 실행 |
| `shared_index` | `PROJECT_ROOT/data` 특허 공유 색인 |
| `all` | wiki 정규화, vectorstore, application preprocess 실행 |

### `POST /api/v1/chatbot/vectorstore/refresh`

감사 자동 적용 후 전체 vectorstore를 재생성합니다.

Query:

| 이름 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `auto_audit` | boolean | `true` | `true`면 주의/나쁜 데이터 자동 제외 후 승인본으로 refresh |

### `POST /api/v1/chatbot/search`

챗봇 RAG 검색 확인 API입니다.

요청:

```json
{
  "query": "이 특허의 핵심 기술은?",
  "patent_id": "10-2142205",
  "source_types": ["REPORT_PDF"],
  "top_k": 5
}
```

응답 모델: `SearchResponse`

```json
{
  "query": "이 특허의 핵심 기술은?",
  "mode": "search",
  "patent_id": "10-2142205",
  "top_k": 5,
  "hit_count": 1,
  "hits": [
    {
      "patent_id": "10-2142205",
      "score": 0.82,
      "excerpt": "...",
      "page_content": "...",
      "metadata": {}
    }
  ]
}
```

### `POST /api/v1/chatbot/query`

`/search`와 동일한 검색 API입니다.

### `POST /api/v1/chatbot/answer`

챗봇 답변 생성 API입니다.

요청은 `SearchRequest`와 동일합니다.

응답 모델: `AnswerResponse`

```json
{
  "query": "이 특허의 핵심 기술은?",
  "patent_id": "10-2142205",
  "answer": "...",
  "source_cards": [
    {
      "label": "S1",
      "title": "report.json",
      "display_title": "재평가 보고서",
      "source_type": "REPORT_PDF",
      "page_no": 1,
      "url": null,
      "location_label": "p.1",
      "source_path": "...",
      "match_terms": [],
      "snippet": "...",
      "metadata": {}
    }
  ],
  "metrics": {}
}
```

## 1.4 특허 챗봇 API

Base prefix: `/api/v1/patent-chat`

### `POST /api/v1/patent-chat/query`

특허 챗봇 근거 검색입니다. 요청/응답은 `SearchRequest` / `SearchResponse`입니다.

### `POST /api/v1/patent-chat/answer`

특허 챗봇 답변 생성입니다. 요청은 `SearchRequest`, 응답은 `AnswerResponse`입니다.

### `POST /api/v1/patent-chat/chat`

특허별 챗봇 답변입니다.

요청:

```json
{
  "patent_id": "10-2142205",
  "question": "이 특허의 차별점은?",
  "user_id": "user-1",
  "chat_history": [],
  "context_patent_id": "10-2142205"
}
```

응답: `AnswerResponse`

### `POST /api/v1/patent-chat/global/chat`

전체 특허를 대상으로 챗봇 답변을 생성합니다. 요청은 `ChatRequest`입니다.

### `GET /api/v1/patent-chat/chat/mermaid`

특허 챗봇 LangGraph workflow Mermaid를 반환합니다.

### `GET /api/v1/patent-chat/engine/status`

Hybrid Retrieval 엔진 상태를 반환합니다.

### `GET /api/v1/patent-chat/patents`

특허 챗봇용 특허 목록을 반환합니다.

### `GET /api/v1/patent-chat/patent-summary-cards`

특허 요약 카드 목록을 반환합니다.

### `POST /api/v1/patent-chat/reindex`

특허별 검색 인덱스를 재생성합니다.

요청:

```json
{
  "patent_id": "10-2142205",
  "force_rebuild": true,
  "refresh_reviewed_vectorstore": false
}
```

### `POST /api/v1/patent-chat/global/reindex`

전체 특허 검색 인덱스를 재생성합니다.

요청:

```json
{
  "force_rebuild": true,
  "refresh_reviewed_vectorstore": false
}
```

### `POST /api/v1/patent-chat/business/reindex`

업무/공통 검색 인덱스를 재생성합니다. 요청은 `BusinessReindexRequest`입니다.

### `GET /api/v1/patent-chat/ingestion/mermaid`

전처리/재색인 LangGraph Mermaid를 반환합니다.

### `POST /api/v1/patent-chat/feedback`

챗봇 답변 피드백을 저장합니다.

요청:

```json
{
  "question": "질문",
  "answer": "답변",
  "rating": "good",
  "reason": "근거가 충분함",
  "user_id": "user-1",
  "patent_id": "10-2142205",
  "metrics": {}
}
```

### `GET /api/v1/patent-chat/page-image`

특허 PDF page image를 렌더링합니다.

Query:

| 이름 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `patent_id` | string | 필수 | 특허 ID |
| `file_name` | string | `original.pdf` | PDF 파일명 |
| `page_no` | integer | `1` | `>=1` |

## 1.5 Agent Alias API

Base prefix: `/api/v1/agent`

| Method | Path | 설명 | 모델 |
| --- | --- | --- | --- |
| `POST` | `/api/v1/agent/query` | 검색 alias | `SearchRequest` -> `SearchResponse` |
| `POST` | `/api/v1/agent/answer` | 답변 alias | `SearchRequest` -> `AnswerResponse` |
| `GET` | `/api/v1/agent/chat/mermaid` | 챗봇 LangGraph Mermaid | JSON |

## 1.6 RAG Compatibility Alias

아래 라우터는 코드상 include되어 있으나 `include_in_schema=False`입니다. Swagger에는 숨겨질 수 있습니다.

| Method | Path | 대응 대표 API |
| --- | --- | --- |
| `POST` | `/api/v1/rag/query` | `/api/v1/patent-chat/query` |
| `POST` | `/api/v1/rag/answer` | `/api/v1/patent-chat/answer` |
| `POST` | `/api/v1/rag/chat` | `/api/v1/patent-chat/chat` |
| `POST` | `/api/v1/rag/global/chat` | `/api/v1/patent-chat/global/chat` |
| `GET` | `/api/v1/rag/engine/status` | `/api/v1/patent-chat/engine/status` |
| `GET` | `/api/v1/rag/patents` | `/api/v1/patent-chat/patents` |
| `GET` | `/api/v1/rag/patent-summary-cards` | `/api/v1/patent-chat/patent-summary-cards` |
| `POST` | `/api/v1/rag/reindex` | `/api/v1/patent-chat/reindex` |
| `POST` | `/api/v1/rag/global/reindex` | `/api/v1/patent-chat/global/reindex` |
| `POST` | `/api/v1/rag/business/reindex` | `/api/v1/patent-chat/business/reindex` |
| `GET` | `/api/v1/rag/ingestion/mermaid` | `/api/v1/patent-chat/ingestion/mermaid` |
| `POST` | `/api/v1/rag/feedback` | `/api/v1/patent-chat/feedback` |
| `GET` | `/api/v1/rag/page-image` | `/api/v1/patent-chat/page-image` |
| `GET` | `/rag/engine/status` | legacy alias |
| `GET` | `/rag/patents` | legacy alias |
| `GET` | `/rag/patent-summary-cards` | legacy alias |
| `POST` | `/rag/chat` | legacy alias |
| `POST` | `/rag/global/chat` | legacy alias |
| `POST` | `/rag/reindex` | legacy alias |
| `POST` | `/rag/global/reindex` | legacy alias |
| `POST` | `/rag/business/reindex` | legacy alias |
| `GET` | `/rag/ingestion/mermaid` | legacy alias |
| `POST` | `/rag/feedback` | legacy alias |
| `GET` | `/rag/page-image` | legacy alias |

## 1.7 Wiki API

Base prefix: `/api/v1/wiki`

### `GET /api/v1/wiki/audit-report`

wiki 감사 리포트를 반환합니다.

### `POST /api/v1/wiki/audit`

wiki/챗봇 데이터 감사를 실행합니다.

Query:

| 이름 | 타입 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `refresh_vectorstore` | boolean | `false` | 감사 전 raw vectorstore 강제 갱신 여부 |

### `GET /api/v1/wiki/audit-review`

사람 검토용 감사 Markdown을 조회합니다.

Query:

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `audit_id` | string? | 비우면 최신 감사 |

### `POST /api/v1/wiki/audit-apply`

사람 검토 결과를 적용하고 승인 Markdown 저장 및 vectorstore 갱신을 수행합니다.

요청:

```json
{
  "audit_id": null,
  "exclude_finding_ids": null,
  "reviewer": "reviewer",
  "notes": "확인 완료",
  "refresh_vectorstore": true
}
```

### `POST /api/v1/wiki/audit-auto-refresh`

자동 감사로 주의/나쁜 데이터를 제외하고 승인 vectorstore를 갱신합니다.

### `GET /api/v1/wiki/topics`

분야별 wiki vectorstore 목록 및 상태를 반환합니다.

### `GET /api/v1/wiki/topics/{topic_slug}`

특정 분야 wiki 상태, approved context preview, 최근 draft 목록을 반환합니다.

### `POST /api/v1/wiki/topics/refresh`

분야별 wiki vectorstore 전체를 blue/green 방식으로 재빌드합니다.

### `POST /api/v1/wiki/topics/reclassify`

전체 특허 분야를 재분류합니다.

### `GET /api/v1/wiki/topics/{topic_slug}/patent`

특허 ID가 어떤 분야에 매핑되는지 조회합니다.

Query:

| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `patent_id` | string | 매핑 확인 대상 특허 ID |

### `POST /api/v1/wiki/agent/run`

Wiki LangGraph agent를 직접 실행합니다.

요청:

```json
{
  "mode": "audit",
  "audit_id": null,
  "exclude_finding_ids": null,
  "reviewer": null,
  "notes": null,
  "refresh_vectorstore": null
}
```

`mode`: `audit`, `review`, `apply`, `auto_refresh`, `refresh`, `status`

### `GET /api/v1/wiki/agent/mermaid`

Wiki LangGraph agent Mermaid를 반환합니다.

## 1.8 Wiki Audit Legacy Paths

동일 기능이 `/api/v1/chatbot/wiki-audit/*` 아래에도 노출됩니다.

| Method | Path | 대응 Wiki API |
| --- | --- | --- |
| `GET` | `/api/v1/chatbot/wiki-audit/report` | `/api/v1/wiki/audit-report` |
| `POST` | `/api/v1/chatbot/wiki-audit/run` | `/api/v1/wiki/audit` |
| `GET` | `/api/v1/chatbot/wiki-audit/review` | `/api/v1/wiki/audit-review` |
| `POST` | `/api/v1/chatbot/wiki-audit/apply` | `/api/v1/wiki/audit-apply` |
| `POST` | `/api/v1/chatbot/wiki-audit/auto-refresh` | `/api/v1/wiki/audit-auto-refresh` |

## 1.9 특허 출원 도우미 API

Base prefix: `/api/v1/application`

### 상태/전처리

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/api/v1/application/status` | 공식팩/index 상태 |
| `GET` | `/api/v1/application/external/status` | KIPRIS/KOSIS/Tavily 외부 보강 연결 상태 |
| `POST` | `/api/v1/application/preprocess` | 공식팩 전처리 리포트 생성 및 vectorstore 갱신 |
| `POST` | `/api/v1/application/index/refresh` | 출원 공식팩 vectorstore 갱신 |
| `GET` | `/api/v1/application/chat/mermaid` | 출원 도우미 LangGraph Mermaid |

`POST /api/v1/application/preprocess` 요청:

```json
{
  "refresh_index": true
}
```

### 출원 피드백 리포트

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/v1/application/feedback/create` | 의견서/거절사유/기존 평가 보고서 연결 피드백 리포트 생성 |
| `POST` | `/api/v1/application/report/generate` | 호환용 전역 출원 피드백 리포트 생성 |
| `POST` | `/api/v1/application/feedback/upload` | 의견서 PDF/문서 업로드 후 HTML 생성 및 vectorstore 갱신 |

`feedback/create` 요청:

```json
{
  "title": "특허 출원 실패/거절 대응 피드백",
  "patent_id": "10-2142205",
  "opinion_text": "거절 사유 텍스트",
  "opinion_file_path": null,
  "source_report_path": null,
  "reviewer": "reviewer",
  "notes": null,
  "refresh_index": true
}
```

`feedback/upload`는 `multipart/form-data`입니다.

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `file` | file | O | 의견서, 거절이유 통지서, 출원 실패 분석 문서 |
| `title` | string | X | 기본값 `특허 출원 실패/거절 대응 피드백` |
| `patent_id` | string | X | 기존 특허 ID |
| `source_report_path` | string | X | 기존 보고서 경로 |
| `reviewer` | string | X | 검토자 |
| `notes` | string | X | 메모 |
| `refresh_index` | boolean | X | 기본값 `true` |

### 실패특허 케이스

| Method | Path | 설명 |
| --- | --- | --- |
| `GET` | `/api/v1/application/failed-patents` | 실패특허 케이스 목록 |
| `GET` | `/api/v1/application/failed-patents/{case_id}` | 케이스 파일/index 상태 |
| `POST` | `/api/v1/application/failed-patents/create` | 서버 로컬 PDF 경로로 케이스 생성 |
| `POST` | `/api/v1/application/failed-patents/upload` | PDF 업로드로 케이스 생성 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/index/refresh` | 케이스 전용 vectorstore 갱신 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/report/save` | 재평가 API 결과를 케이스 폴더에 저장 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/report/generate` | 보고서 생성 에이전트 실행 후 케이스 폴더에 저장 |
| `POST` | `/api/v1/application/failed-patents/{case_id}/chat` | 선택 실패특허 기준 출원 도우미 챗봇 |

`failed-patents/create` 요청:

```json
{
  "case_id": null,
  "title": "실패특허 케이스",
  "original_pdf_path": "/server/path/patent.pdf",
  "rejection_reason_text": "거절 사유",
  "rejection_file_path": null,
  "reviewer": "reviewer",
  "notes": null,
  "refresh_index": true
}
```

`failed-patents/upload`는 `multipart/form-data`입니다.

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `original_pdf` | file | O | 실패특허 원본 PDF |
| `rejection_file` | file | X | 거절의견서/사유서 |
| `case_id` | string | X | 직접 지정 케이스 ID |
| `title` | string | X | 케이스 제목 |
| `rejection_reason_text` | string | X | 거절/실패 사유 |
| `reviewer` | string | X | 등록자/검토자 |
| `notes` | string | X | 메모 |
| `refresh_index` | boolean | X | 기본값 `true` |

`report/save` 요청:

```json
{
  "title": "재평가 보고서",
  "report": {},
  "report_text": null,
  "source_report_path": null,
  "refresh_index": true
}
```

`report/generate` 요청:

```json
{
  "title": "실패특허 재평가 보고서",
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

### 공식 자료 다운로드/챗봇

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/v1/application/sources/download` | 특허 출원 공식 자료 다운로드/크롤링 |
| `GET` | `/api/v1/application/sources/download-report` | 다운로드/크롤링 리포트 조회 |
| `POST` | `/api/v1/application/chat` | 특허 출원 도우미 챗봇 |

`sources/download` 요청:

```json
{
  "force": false,
  "timeout": 20,
  "limit": null,
  "include_embedded": true
}
```

`application/chat` 요청:

```json
{
  "question": "거절 대응 전략을 알려줘",
  "user_id": "user-1",
  "failed_patent_id": "case-1",
  "chat_history": [],
  "top_k": 6,
  "refresh_index": false
}
```

응답: `AnswerResponse`

## 1.10 출원 전 사전평가 API

Base prefix: `/api/v1/pre-eval`

### `POST /api/v1/pre-eval/evaluate`

특허명, 기술설명, 청구항 등을 받아 사전평가를 실행하고 케이스 폴더를 생성합니다.

요청:

```json
{
  "patentName": "AI 기반 불량 검출 시스템",
  "technologyDescription": "카메라 영상과 모델을 이용해 제조 불량을 검출",
  "claims": ["청구항 1 ..."],
  "relatedBusiness": "스마트팩토리",
  "targetCountries": ["KR"],
  "enable_llm": true,
  "run_web_search": true
}
```

### `GET /api/v1/pre-eval/cases`

사전평가 케이스 목록을 반환합니다.

### `GET /api/v1/pre-eval/cases/{case_id}`

사전평가 케이스 상태 및 vectorstore 정보를 반환합니다.

### `GET /api/v1/pre-eval/cases/{case_id}/report`

사전평가 보고서 원본 JSON을 반환합니다.

### `POST /api/v1/pre-eval/cases/{case_id}/index/refresh`

사전평가 케이스 vectorstore를 재빌드합니다.

### `POST /api/v1/pre-eval/cases/{case_id}/chat`

사전평가 보고서 기반 챗봇입니다.

요청:

```json
{
  "question": "이 출원의 위험 요소는?",
  "user_id": "user-1",
  "chat_history": [],
  "top_k": 8
}
```

### `POST /api/v1/pre-eval/cases/{case_id}/search`

사전평가 케이스 vectorstore 직접 검색입니다.

요청:

```json
{
  "query": "선행기술 위험",
  "top_k": 8
}
```

### `GET /api/v1/pre-eval/graph/mermaid`

사전평가 챗봇 LangGraph Mermaid를 반환합니다.

---

# 2. 재평가 보고서 FastAPI

재평가 보고서 API는 보고서를 실시간 생성하는 API가 아니라, 로컬 CLI 또는 배치에서 생성된 `report.json`을 MinIO 또는 로컬 디렉터리에서 조회하는 API입니다.

현재 로컬 fallback 구조:

```text
skipa-ai-server/data/{registration_number}/report.json
```

MinIO object key 후보:

```text
patents/{registration_number}/report.json
reports/{registration_number}/report.json
{registration_number}/report.json
```

환경변수로 조정 가능한 값:

| 환경변수 | 설명 |
| --- | --- |
| `EVAL_LOGIC_REPORT_OBJECT_KEY_TEMPLATE` | 기본 object key template |
| `EVAL_LOGIC_REPORT_OBJECT_KEY_CANDIDATES` | 추가 후보 template, comma-separated |
| `EVAL_LOGIC_REPORT_OBJECT_PREFIX` | object key prefix |
| `EVAL_LOGIC_REPORT_LIST_PREFIX` | 목록 조회 prefix. 기본값 `patents/` |
| `EVAL_LOGIC_REPORT_STRICT_MINIO` | MinIO 실패를 502로 노출할지 여부 |

## 2.1 Health

### `GET /health`

응답:

```json
{
  "status": "ok"
}
```

## 2.2 Reports

### `GET /api/v1/reports/patent-valuation`

미리 저장된 재평가 보고서 목록을 조회합니다. MinIO가 설정되어 있으면 MinIO를 먼저 보고, 로컬 `data/*/report.json`을 fallback으로 함께 조회합니다.

응답:

```json
{
  "reports": [
    {
      "registration_number": "10-2142205",
      "report_id": "report-...",
      "title": "특허명",
      "schema_version": "v...",
      "generated_at": "2026-06-09T12:00:00",
      "report_url": "/api/v1/reports/patent-valuation/10-2142205",
      "storage": {
        "backend": "local",
        "bucket": null,
        "object_key": null,
        "path": "/path/to/report.json"
      }
    }
  ]
}
```

응답 모델:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `reports` | array | 보고서 목록 |
| `reports[].registration_number` | string | 등록번호 |
| `reports[].report_id` | string? | 보고서 ID |
| `reports[].title` | string? | 특허명 |
| `reports[].schema_version` | string? | 보고서 schema version |
| `reports[].generated_at` | string? | 생성 시각 |
| `reports[].report_url` | string | 상세 조회 URL |
| `reports[].storage` | object | 저장 위치 |

### `GET /api/v1/reports/patent-valuation/{registration_number}`

특허 등록번호로 미리 저장된 재평가 보고서 JSON을 반환합니다.

응답:

```json
{
  "registration_number": "10-2142205",
  "report": {},
  "storage": {
    "backend": "local",
    "bucket": null,
    "object_key": null,
    "path": "/path/to/report.json"
  }
}
```

상태 코드:

| 코드 | 조건 |
| --- | --- |
| `200` | 조회 성공 |
| `400` | 등록번호 누락/공백 |
| `404` | 저장된 보고서 없음 |
| `500` | 로컬 JSON 파싱 실패 또는 저장 파일 형식 오류 |
| `502` | strict MinIO 모드에서 MinIO 조회 실패 |

## 2.3 Tools

도구 API는 재평가 보고서 구성 요소를 개별 실행하거나 확인하기 위한 API입니다.

### `POST /api/v1/tools/patent-metadata`

특허 원문 PDF를 업로드해 재평가 입력 JSON 형태로 정규화합니다.

Content-Type: `multipart/form-data`

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `file` | file | O | PDF 파일 |

응답 주요 필드:

| 필드 | 설명 |
| --- | --- |
| `normalized_patent` | 정규화된 특허 JSON |
| `raw` | 추출 원문/중간 데이터 |
| `uploaded_pdf_path` | 서버에 저장된 업로드 PDF 경로 |

### `POST /api/v1/tools/business-rag`

제품/사업화 현황 RAG 추정을 실행합니다.

요청:

```json
{
  "patent": {},
  "query": "사업화 가능성을 알려줘",
  "top_k": 5
}
```

요청 필드:

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `patent` | object | O | 특허 입력 JSON |
| `query` | string? | X | 직접 지정할 RAG 질의 |
| `top_k` | integer? | X | 검색 결과 수. 기본값 `5` |

### `POST /api/v1/tools/market-growth`

KOSIS/KSIC 기반 시장 성장률 점수를 조회합니다.

요청:

```json
{
  "patent": {}
}
```

응답은 `get_growth_score_from_json()` 결과를 그대로 반환합니다.

### `POST /api/v1/tools/auto-score`

규칙 기반 자동 평가 점수를 계산합니다.

요청:

```json
{
  "patent": {}
}
```

응답:

```json
{
  "scores": []
}
```

### `POST /api/v1/tools/llm-evaluation`

LLM 기반 평가 항목을 실행합니다.

요청:

```json
{
  "patent": {}
}
```

응답:

```json
{
  "scores": []
}
```

### `POST /api/v1/tools/similar-patents`

KIPRIS 유사도 검색 기반 유사 특허 분석을 실행합니다.

현재 워크플로 옵션은 코드상 다음 의미로 고정되어 있습니다.

| 옵션 | 값 | 의미 |
| --- | --- | --- |
| `enable_similar_analysis` | `true` | 유사 특허 분석 항상 실행 |
| `similar_use_kipris_crawler` | `true` | 레거시 KIPRIS 크롤러 기반 후보 수집 |
| `similar_force_refresh` | `true` | 기존 캐시만 재사용하지 않고 새로 수집 |
| `similar_use_llm` | `false` | 도구 API에서는 유사 특허 요약 LLM 미사용 |

요청:

```json
{
  "patent": {
    "patent_id": "10-2142205",
    "meta": {
      "registration_number": "10-2142205",
      "title": "특허명"
    }
  }
}
```

응답:

```json
{
  "similar_analysis": {
    "meta": {
      "target_patent_id": "10-2142205",
      "source_search": {
        "source": "KIPRIS",
        "method": "legacy_kipris_crawler",
        "candidate_details": ".../similar_details_10_2142205.json",
        "target_input": ".../patent_10_2142205_input.json",
        "force_refresh": true,
        "max_pages": 5,
        "max_results": 10,
        "date_range": {
          "from": "2015-01-01",
          "to": ""
        }
      }
    },
    "ecosystem_summary": {},
    "target_position": {},
    "top_comparisons": [],
    "interpretation": {},
    "similar_patents": []
  },
  "errors": []
}
```

주의:

- KIPRIS 크롤러는 Selenium/ChromeDriver 기반입니다.
- 실행 환경에 브라우저와 네트워크 접근이 필요합니다.
- KIPRIS Plus 상세 보강은 `KIPRIS_API_KEY`가 있으면 API enrichment를 수행하고, 없으면 후보 데이터 기반 normalized details를 생성합니다.

---

# 3. 주요 요청 모델 요약

## `SearchRequest`

```json
{
  "query": "검색 또는 질의 문장",
  "patent_id": "10-2142205",
  "source_types": ["ORIGINAL_PDF", "REPORT_PDF", "WIKI"],
  "top_k": 5
}
```

## `ChatRequest`

```json
{
  "patent_id": "10-2142205",
  "question": "사용자 질문",
  "user_id": "user-1",
  "chat_history": [],
  "context_patent_id": "10-2142205"
}
```

## `AnswerResponse`

```json
{
  "query": "사용자 질문",
  "patent_id": "10-2142205",
  "answer": "답변",
  "source_cards": [],
  "metrics": {}
}
```

## `PatentToolRequest`

```json
{
  "patent": {}
}
```

## `BusinessRagToolRequest`

```json
{
  "patent": {},
  "query": "직접 지정할 RAG 질의",
  "top_k": 5
}
```

---

# 4. 실행 참고

## Chatbot API

일반적인 실행 형태:

```bash
cd skipa-ai-server/chatbot
uvicorn app.main:app --reload --port 8000
```

## 재평가 보고서 API

일반적인 실행 형태:

```bash
cd skipa-ai-server/eval_logic
uvicorn src.apps.api.main:app --reload --port 8001
```

## 재평가 보고서 CLI 생성

등록번호 폴더 1건:

```bash
cd skipa-ai-server
python3 eval_logic/src/apps/cli/run_agent.py data/10-2142205
```

전체 등록번호 폴더:

```bash
cd skipa-ai-server
python3 eval_logic/src/apps/cli/run_agent.py data
```

생성 결과:

```text
data/{registration_number}/report.json
```
