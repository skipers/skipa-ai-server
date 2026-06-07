# Chatbot Business Batch Test Summary

- Generated at: 2026-06-07T15:51:59
- Execution mode: functional
- Output directory: `chatbot/data/artifacts/chatbot_business_tests/patent_100_each_20260607_1552`

## Patent Chatbot

- Total / success / failed: 1000 / 1000 / 0
- Avg elapsed: 0.005 sec
- Avg source count: 3.477
- Avg quality score: 0.4731
- Intent counts: `{"patent_original": 175, "patent_report": 400, "general": 300, "comparison": 100, "wiki": 25}`
- Answer mode counts: `{"None": 1000}`

## Patent Application Chatbot

- Total / success / failed: 0 / 0 / 0
- Avg elapsed: 0 sec
- Avg source count: 0
- Avg quality score: None
- Intent counts: `{}`
- Answer mode counts: `{}`

## Patent Application Chatbot Flow

```mermaid
flowchart TD
  A[사용자 질문] --> B[최근 대화 이력 요약]
  B --> C[가벼운 LLM 또는 룰 fallback 의도 라우팅]
  C --> D{의도 유형}
  D -->|출원 절차/서식/수수료| E[공식 출원팩 검색]
  D -->|청구항/명세서| F[작성 가이드/심사기준 검색]
  D -->|선행기술| G[KIPRIS/CPC/IPC 자료 검색]
  D -->|거절/실패| H[거절의견서/피드백 리포트 검색]
  D -->|전략/시장| I[전략 자료 + KOSIS/Tavily 보강]
  E --> J[근거 카드 생성]
  F --> J
  G --> J
  H --> J
  I --> J
  J --> K[LLM 답변 또는 guided template]
  K --> L[표/다이어그램/체크리스트 형식화]
  L --> M[품질 지표와 근거 제목 반환]
```

## Saved Files

- `patent_questions.jsonl`
- `application_questions.jsonl`
- `patent_chat_results.jsonl`
- `application_chat_results.jsonl`
- `summary.json`
- `summary.md`
