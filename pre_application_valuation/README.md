# Pre-Application Valuation

출원 전 아이디어/특허 입력을 받아 출원 준비도, 권리화 가능성, 사업 가설, 보완 액션을 평가하는 독립 모듈입니다.

현재는 로컬 개발을 기준으로 결과 보고서를 JSON 파일로 저장합니다. 재평가 보고서와 달리 등록 후 지표
(피인용, 심판이력, 존속기간 등)는 사용하지 않고, 출원 전 입력으로 판단 가능한 준비도와 리스크를 중심으로
평가합니다.

## Pipeline

```text
input
  -> local diagnostics
  -> IPC/keyword estimate
  -> checklist LLM evaluation or local fallback
  -> pre-application report builder
  -> local JSON outputs
```

Main files:

- `resources/pre_application_checklist.md`: 사전가치평가 전용 평가 기준
- `diagnostics.py`: 입력 완성도, 청구항 형태, 사업/출원 전략 로컬 진단
- `llm_evaluator.py`: 체크리스트 기반 LLM 평가와 로컬 fallback
- `report_builder.py`: 서비스 화면용 보고서 JSON 조립
- `service.py`: 전체 오케스트레이션

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
