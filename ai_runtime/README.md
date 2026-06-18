# AI Provider Modes

공통 provider 오버레이입니다. Kubernetes에서는 같은 이미지/코드를 두고 환경변수만 바꿔 OpenAI 모드와 open-source 모드를 전환합니다.

모드 프로필을 쓰면 루트 `.env`에는 아래 한 줄만 둬서 묶음 설정을 고를 수 있습니다.

```env
AI_MODE=opensource
```

실제 묶음 값은 `ai_runtime/modes/opensource.env` 또는 `ai_runtime/modes/openai.env`에 둡니다.

## OpenAI mode

```env
AI_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
OPENAI_REPORT_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Open-source mode

```env
AI_PROVIDER=opensource
OPEN_SOURCE_LLM_BASE_URL=http://skipa-llm:8000/v1
OPEN_SOURCE_EMBEDDING_BASE_URL=http://skipa-embedding:8001/v1
OPEN_SOURCE_LLM_API_KEY=EMPTY
OPEN_SOURCE_EMBEDDING_API_KEY=EMPTY
OPEN_SOURCE_LLM_MODEL=Qwen/Qwen2.5-1.5B-Instruct
OPEN_SOURCE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
OPEN_SOURCE_RERANKER_MODEL=Qwen/Qwen3-Reranker-4B
EMBEDDING_REQUEST_DIMENSIONS=false
LLM_REQUEST_JSON_RESPONSE_FORMAT=true
```

`OPEN_SOURCE_LLM_BASE_URL`과 `OPEN_SOURCE_EMBEDDING_BASE_URL`은 vLLM/SGLang/FastAPI model server의 OpenAI-compatible `/v1` 주소를 넣습니다. 클러스터 안에서는 Kubernetes service DNS를 쓰고, 로컬에서는 port-forward 주소를 씁니다.

현재 클러스터 기준:

```env
OPEN_SOURCE_LLM_BASE_URL=http://skipa-llm:8000/v1
OPEN_SOURCE_EMBEDDING_BASE_URL=http://skipa-embedding:8001/v1
```

로컬 port-forward 기준:

```env
OPEN_SOURCE_LLM_BASE_URL=http://127.0.0.1:18000/v1
OPEN_SOURCE_EMBEDDING_BASE_URL=http://127.0.0.1:18001/v1
```

배포가 `response_format`을 지원하지 않으면 `LLM_REQUEST_JSON_RESPONSE_FORMAT=false`로 바꿉니다.

## Vector store separation

Qdrant를 공유할 때는 컬렉션 충돌을 피하기 위해 open-source 모드에서 아래 값을 함께 사용합니다.

```env
QDRANT_COLLECTION_PREFIX=opensource
QDRANT_VECTOR_SIZE=2560
```

FAISS 파일을 쓰는 `eval_logic/src/business_rag`는 open-source 모드에서 자동으로 `opensource_faiss.index`, `opensource_metadata.pkl`, `opensource_bm25.pkl` 파일명을 사용합니다.
