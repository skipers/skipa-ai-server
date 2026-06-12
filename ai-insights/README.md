# AI Portfolio Insights

백엔드가 포트폴리오 추이, 분포, 유지/포기 결정 데이터를 모아 직접 호출하는 AI 서버 API입니다.

## Run

```bash
cd /Users/kgw/skipers-ai
python3 -m uvicorn app.main:app --app-dir ai-insights --host 127.0.0.1 --port 8000
```

환경변수:

```text
OPENAI_API_KEY=...
OPENAI_PORTFOLIO_INSIGHTS_MODEL=gpt-4.1-mini
```

`OPENAI_PORTFOLIO_INSIGHTS_MODEL`을 지정하지 않으면 `gpt-4.1-mini`를 사용합니다.

## API

```text
POST /portfolio/insights
Content-Type: application/json
```

요청 body는 백엔드의 포트폴리오 추이, 분포, 결정 비율 데이터를 그대로 묶은 형태입니다.
AI 서버는 고정 문장이나 fallback 템플릿을 반환하지 않고, 입력 데이터마다 OpenAI가 생성한 인사이트를 검증해 반환합니다.
OpenAI 응답이 비어 있거나 3개 문장 형식에 맞지 않으면 `502`를 반환합니다.

샘플 요청 기준 응답 예시:

```json
{
  "insights": [
    "2024년 출원 대비 등록 비중이 66.7%로 나타나 권리화 전환 흐름은 확인되지만, 소멸 1건까지 함께 보면 핵심 권리의 유지 가치 점검이 필요합니다.",
    "S/A 34.1%, C/D 20.5%, 반도체 사업부 100%, 반도체 100% 구조는 특정 사업부 의존도가 높다는 신호이므로 핵심 사업부 보호와 비핵심 영역 리밸런싱을 함께 검토해야 합니다.",
    "2026년 2분기(2026Q2) 포기 비율이 23.1%로 제한적이어서 유지 중심 운영 속에서도 연차료 부담이 커지는 저가치 특허를 별도 관리해야 합니다."
  ]
}
```

## Smoke Test

```bash
curl -X POST http://127.0.0.1:8000/portfolio/insights \
  -H 'Content-Type: application/json' \
  --data @ai-insights/sample_request.json
```
