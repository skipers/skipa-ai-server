# Open-source Provider Change Summary

작성일: 2026-06-17

## 목적

기존 보고서 생성/평가/인사이트 코드는 유지하면서, LLM/embedding/reranker에 해당하는 부분만 provider 오버레이로 분리했습니다.

Kubernetes나 로컬 실행에서 환경변수로 아래 모드를 바꿔 켜는 구조입니다.

```env
AI_PROVIDER=openai
```

또는

```env
AI_PROVIDER=opensource
```

또는 모드 프로필을 사용할 수 있습니다.

```env
AI_MODE=opensource
```

이 경우 `ai_runtime/modes/opensource.env`의 묶음 설정을 사용합니다.

Tavily는 웹 근거 수집용이므로 그대로 유지했습니다. 이번 변경 대상은 OpenAI API에 직접 붙던 LLM/embedding 호출부입니다.

## 새로 추가한 파일

| 파일 | 내용 |
| --- | --- |
| `ai_runtime/__init__.py` | 공통 provider 패키지 초기화 파일입니다. |
| `ai_runtime/providers.py` | OpenAI/open-source provider 공통 런타임입니다. `/chat/completions`, `/embeddings` 호환 호출, JSON 파싱, env 로딩, LLM/embedding base URL 분리를 담당합니다. |
| `ai_runtime/README.md` | OpenAI 모드와 open-source 모드의 환경변수 예시를 정리했습니다. |
| `ai_runtime/modes/README.md` | 모드 프로필 사용법을 정리했습니다. |
| `ai_runtime/modes/openai.env.example` | OpenAI 모드 프로필 예시입니다. |
| `ai_runtime/modes/opensource.env.example` | open-source 모드 프로필 예시입니다. |
| `scripts/run_ai_mode.sh` | 로컬에서 `.env`를 수정하지 않고 선택한 모드로 명령을 실행하는 wrapper입니다. |
| `pre_application_valuation/providers/__init__.py` | 사전평가 provider 패키지 초기화 파일입니다. |
| `pre_application_valuation/providers/llm.py` | 사전평가 보고서용 LLM wrapper입니다. `request_report_json()`으로 공통 runtime을 호출합니다. |
| `eval_logic/src/providers/__init__.py` | eval_logic provider 패키지 초기화 파일입니다. |
| `eval_logic/src/providers/llm.py` | eval_logic 보고서/평가/사업화 RAG용 wrapper입니다. JSON, text, embedding 요청을 공통 runtime으로 연결합니다. |
| `ai-insights/app/providers/__init__.py` | ai-insights provider 패키지 초기화 파일입니다. |
| `ai-insights/app/providers/llm.py` | 포트폴리오 인사이트용 LLM wrapper입니다. |
| `docs/opensource_provider_changes.md` | 현재 문서입니다. 수정 파일과 변경 내용을 정리합니다. |

## 수정한 파일

| 파일 | 변경 내용 |
| --- | --- |
| `pre_application_valuation/llm_comment.py` | 직접 `requests.post()`로 OpenAI Chat Completions를 호출하던 부분을 `pre_application_valuation.providers.llm` 호출로 변경했습니다. OpenAI 키 기준이 아니라 provider 설정 기준으로 동작합니다. |
| `pre_application_valuation/llm_evaluator.py` | 사전평가 체크리스트 LLM 평가 호출을 provider wrapper로 변경했습니다. LLM이 없으면 기존 fallback 흐름을 유지합니다. |
| `eval_logic/src/evaluation/llm_evaluator.py` | 특허 가치평가 항목별 LLM 평가 호출을 provider wrapper로 변경했습니다. Tavily 검색 호출(`search_patent_evidence`)은 그대로 유지했습니다. |
| `eval_logic/src/services/valuation_service.py` | LLM 단계 실행 가능 여부를 `OPENAI_API_KEY`가 아니라 `llm_configured()`로 판단하도록 바꿨습니다. |
| `eval_logic/src/document_processing/patent_pdf_extractor.py` | 특허 키워드 추출, 개요/핵심 내용 생성, 외국/스캔 특허 구조화 여부 판단을 provider 기준으로 변경했습니다. 로그 문구도 `OpenAI`에서 `LLM provider`로 정리했습니다. |
| `eval_logic/src/patent_analysis/similar_patent_analyzer.py` | 유사특허 비교 요약 LLM 호출을 provider wrapper로 변경했습니다. `--use-llm`은 provider가 설정되어 있을 때 동작합니다. |
| `eval_logic/src/business_rag/config.py` | 사업화 RAG의 LLM/embedding 모델명을 provider에서 가져오도록 변경했습니다. open-source 모드에서는 FAISS 파일 prefix 기본값을 `opensource_`로 잡습니다. |
| `eval_logic/src/business_rag/vector_store.py` | OpenAI embedding SDK 호출을 `request_embeddings()`로 변경했습니다. open-source 모드에서는 `opensource_faiss.index`, `opensource_metadata.pkl`, `opensource_bm25.pkl`를 사용합니다. |
| `eval_logic/src/business_rag/rag_engine.py` | Query expansion과 최종 JSON 답변 생성을 provider wrapper로 변경했습니다. |
| `scripts/parse_global_patents.py` | 외국 특허 OCR/번역/구조화 LLM 호출을 OpenAI SDK에서 provider wrapper로 변경했습니다. |
| `ai-insights/app/openai_client.py` | 파일명과 함수명은 호환을 위해 유지하고, 내부 구현은 `ai-insights/app/providers/llm.py`를 호출하도록 교체했습니다. |
| `ai-insights/app/service.py` | 에러 메시지를 `OpenAI` 고정 표현에서 `LLM provider` 표현으로 변경했습니다. |

## 그대로 둔 것

| 항목 | 상태 |
| --- | --- |
| Tavily 웹 검색 | 그대로 유지했습니다. `eval_logic/src/evaluation/web_searcher.py`는 수정하지 않았습니다. |
| Tavily env | `TAVILY_API_KEY`, `TAVILY_URL` 사용 방식 그대로입니다. |
| 웹 근거 수집 흐름 | `llm_evaluator.py`에서 `search_patent_evidence()`를 호출하는 구조 그대로입니다. |
| 기존 OpenAI 모드 | `AI_PROVIDER=openai`이면 기존 OpenAI API 계열 env를 사용합니다. |
| 기존 fallback | LLM 설정이 없거나 실패하는 경우 기존 rule/local fallback 흐름을 유지합니다. |

## 로컬/open-source 모드 주요 환경변수

로컬에서 먼저 예시 파일을 복사합니다.

```bash
cp ai_runtime/modes/openai.env.example ai_runtime/modes/openai.env
cp ai_runtime/modes/opensource.env.example ai_runtime/modes/opensource.env
```

그 다음 루트 `.env`에서 아래처럼 모드를 선택하거나:

```env
AI_MODE=opensource
```

명령 실행 시 wrapper로 선택합니다.

```bash
scripts/run_ai_mode.sh opensource -- python3 -m uvicorn pre_application_valuation.api:app --reload --port 8010
```

LLM과 embedding 서버가 같은 OpenAI-compatible endpoint이면:

```env
AI_PROVIDER=opensource
OPEN_SOURCE_BASE_URL=http://127.0.0.1:8000/v1
OPEN_SOURCE_API_KEY=EMPTY
OPEN_SOURCE_LLM_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507
OPEN_SOURCE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
OPEN_SOURCE_RERANKER_MODEL=Qwen/Qwen3-Reranker-4B
```

LLM과 embedding 서버가 분리되어 있으면:

```env
AI_PROVIDER=opensource
OPEN_SOURCE_LLM_BASE_URL=http://127.0.0.1:8000/v1
OPEN_SOURCE_EMBEDDING_BASE_URL=http://127.0.0.1:8001/v1
OPEN_SOURCE_LLM_API_KEY=EMPTY
OPEN_SOURCE_EMBEDDING_API_KEY=EMPTY
```

vLLM/SGLang 배포가 `response_format`을 지원하지 않으면:

```env
LLM_REQUEST_JSON_RESPONSE_FORMAT=false
```

## 검증한 내용

아래 명령으로 Python 컴파일 검증을 통과했습니다.

```bash
python3 -m compileall -q ai_runtime pre_application_valuation eval_logic/src ai-insights/app scripts/parse_global_patents.py
```

아래 검색에서 보고서 관련 경로의 직접 OpenAI SDK/Responses 호출이 나오지 않는 것도 확인했습니다.

```bash
rg -n "from openai|openai\\.OpenAI|OpenAI\\(|/responses|chat\\.completions|embeddings\\.create" \
  pre_application_valuation eval_logic/src ai-insights/app scripts/parse_global_patents.py ai_runtime
```
