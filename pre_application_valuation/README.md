# Pre-Application Valuation

출원 전 아이디어/특허 입력을 받아 기술성, 권리성, 사업성을 빠르게 사전 평가하는 독립 모듈입니다.

## CLI

```bash
../skipa/bin/python -m pre_application_valuation.cli \
  --input-json pre_application_valuation/sample_input.json \
  --output-dir pre_application_valuation/outputs \
  --print
```

## API

```bash
../skipa/bin/uvicorn pre_application_valuation.api:app --reload --port 8010
```

Endpoint:

```text
POST /api/v1/pre-application-valuations/evaluate
GET  /api/v1/pre-application-valuations/latest
```
