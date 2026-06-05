# eval_logic 구조

## 실행 진입점

- `src/apps/api`: FastAPI 서버 진입점과 API 전용 스키마/Job 저장소
- `src/apps/cli`: 로컬 실행, 보고서 검증, 그래프 시각화 CLI

## 공통 업무 로직

- `src/agent`: 특허 가치평가 workflow와 보고서 빌더
- `src/services`: 평가, 근거 수집, 보고서 신뢰도 검증 서비스
- `src/evaluation`: 자동 점수, LLM 평가, KOSIS/검색 기반 평가 로직
- `src/patent_analysis`: 유사 특허 분석
- `src/document_processing`: PDF/문서 처리
- `src/business_rag`: 사업화 문서 RAG
- `src/core`: 공통 경로, 스키마, 파일명 규칙

## 하위 호환 경로

- `src/api`: 기존 API import/uvicorn 경로를 유지하는 wrapper
- `src/cli`: 기존 CLI 실행 경로를 유지하는 wrapper

## 데이터와 산출물

- `data/samples`: 샘플 입력과 테스트 데이터
- `data/resources`: RAG, 매핑표 등 정적 리소스
- `data/runtime_artifacts`: 신규 workflow 런타임 산출물
- `data/api_test`: API 테스트 입력/출력 산출물
- `legacy`: 이전 코드
- `data/legacy_artifacts`: 이전 프로토타입 산출물과 캐시

권장 실행 예:

```bash
uvicorn apps.api.main:app --reload --app-dir src
python3 src/apps/cli/run_agent.py data/samples/input/patent_10_2925867.json --profile quick
python3 src/apps/cli/test_report_verification.py patent_10_2925867.json
```

기존 실행 예도 wrapper를 통해 계속 동작합니다:

```bash
uvicorn src.api.main:app --reload
python3 src/cli/run_agent.py data/samples/input/patent_10_2925867.json --profile quick
```
