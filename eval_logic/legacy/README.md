# Legacy Prototype Code

이 디렉토리는 현재 FastAPI 기반 특허 유지/포기 의사결정 workflow에서 직접
사용하지 않는 프로토타입/실험용 코드를 보관합니다.

현재 운영 흐름의 주요 코드는 `src/api`, `src/agent`, `src/services`,
`src/evaluation`, `src/document_processing`, `src/business_rag`,
`src/patent_analysis`, `src/core` 아래에 있습니다.

## 이동된 코드

- `legacy/src/crawling`: KIPRIS 크롤링/수집 실험 스크립트
- `legacy/src/reporting`: 이전 HTML/PDF 보고서 생성 프로토타입
- `legacy/src/agent/patent_valuation_agent.py`: LangGraph 이전 에이전트형 래퍼
- `legacy/src/cli/run_pipeline.py`: 로컬 평가 파이프라인 CLI 어댑터

필요하면 참고용으로 유지하되, 신규 API/서비스 코드는 이 디렉토리에 의존하지
않도록 관리합니다.
