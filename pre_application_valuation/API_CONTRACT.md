# 사전가치평가 보고서 API 계약

## 1. 보고서 생성 입력 JSON

프론트/백엔드가 AI 서버에 전달하는 최소 입력입니다. camelCase와 snake_case 모두 수용하지만, 서비스 간 계약은 camelCase를 권장합니다.

```json
{
  "patentName": "5G 기반 실시간 데이터 압축 알고리즘",
  "technologyDescription": "출원 전 아이디어/기술 설명. 해결하려는 문제, 핵심 구성, 작동 방식, 기대 효과를 포함합니다.",
  "claims": [
    "독립항 후보 문장",
    "종속항 후보 문장"
  ],
  "relatedBusiness": "적용 사업, 고객군, 수익화 가능성, 도입 환경",
  "targetCountries": ["한국", "미국", "유럽"]
}
```

필수값은 `patentName`, `technologyDescription`입니다. `claims`, `relatedBusiness`, `targetCountries`는 비어 있어도 처리하지만 보고서의 가치 판단 신뢰도는 낮아집니다.

## 2. 저장형 API 응답

동기 API로 직접 생성할 때는 아래 엔드포인트를 사용합니다.

```http
POST /pre-application/api/v1/pre-application-valuations/generate?preEvaluationId=12&userId=7
Content-Type: application/json
```

`preEvaluationId`를 주면 해당 번호로 저장하고, 생략하면 MinIO의 `pre-evaluations/{숫자}/report.json` 목록을 기준으로 다음 번호를 자동 할당합니다. 응답은 다음 형태입니다.

```json
{
  "status": "success",
  "pre_evaluation_id": 12,
  "user_id": 7,
  "report_key": "pre-evaluations/12/report.json",
  "storage": {
    "backend": "minio",
    "bucket": "skipa",
    "object_key": "pre-evaluations/12/report.json",
    "content_type": "application/json",
    "backends": ["local", "minio"],
    "local": {
      "backend": "local",
      "path": "/app/pre_application_valuation/outputs/..."
    }
  },
  "report": {
    "schema_version": "pre-application-valuation-report/v3"
  }
}
```

프론트 화면 출력은 응답의 `report` 객체를 그대로 사용하거나, 이후 백엔드가 `report_key`로 MinIO에서 읽은 `report.json` 전체를 내려주면 됩니다.

## 3. 보고서 JSON 주요 출력 형식

MinIO에는 `skipa/pre-evaluations/{preEvaluationId}/report.json`으로 아래 구조가 저장됩니다.

```json
{
  "schema_version": "pre-application-valuation-report/v3",
  "evaluation_id": "preval-...",
  "evaluated_at": "2026-06-13T13:13:13",
  "patent_title": "5G 기반 실시간 데이터 압축 알고리즘",
  "metadata": {
    "report_type": "pre_application_valuation",
    "title": "사전가치평가 보고서",
    "pre_evaluation_id": 12,
    "storage_policy": "minio_object_key"
  },
  "input": {},
  "input_summary": {},
  "executive_summary": {
    "overall_score": 3.5,
    "score_out_of_100": 70,
    "grade": "B+",
    "opinion": "종합 의견",
    "key_risks": []
  },
  "valuation_assessment": {
    "value_grade": "conditional_value",
    "value_score": 70,
    "value_summary": "출원 전 예상 가치와 그 이유",
    "positive_value_drivers": [],
    "value_constraints": [],
    "evidence_needed": []
  },
  "commercialization_assessment": {
    "target_market": "주요 시장/고객군",
    "expected_use_cases": [],
    "monetization_paths": [],
    "market_validation_gaps": []
  },
  "readiness": {},
  "dimensions": [],
  "score_items": [],
  "claim_strategy": {},
  "prior_art_search_plan": {},
  "filing_strategy": {},
  "filing_investment_decision": {
    "decision": "hold_for_value_validation",
    "rationale": "출원 비용 투입 판단 이유",
    "go_conditions": [],
    "stop_or_hold_conditions": [],
    "recommended_next_sprint": []
  },
  "next_actions": [],
  "limitations": [],
  "frontend_summary": {
    "title": "5G 기반 실시간 데이터 압축 알고리즘",
    "overall_grade": "B+",
    "overall_score": 70,
    "value_grade": "conditional_value",
    "investment_decision": "hold_for_value_validation"
  },
  "artifacts": {
    "output_path": "...",
    "object_key": "pre-evaluations/12/report.json"
  }
}
```

## 4. 비동기 RabbitMQ 흐름

서비스 운영 흐름은 백엔드가 사전평가 row를 먼저 만들고 그 id를 worker에 넘기는 방식이 가장 안전합니다.

1. 프론트가 백엔드에 사전평가 생성 요청
2. 백엔드가 `preEvaluationId`를 생성하고 RabbitMQ `skipa.pre-evaluation.generate`에 메시지 발행
3. AI worker가 보고서를 생성하고 로컬 outputs 및 MinIO `skipa/pre-evaluations/{preEvaluationId}/report.json`에 저장
4. AI worker가 `PATCH /internal/pre-evaluations/{preEvaluationId}/complete`로 `reportKey` 전달
5. 프론트는 백엔드 조회 API를 통해 저장된 보고서 JSON을 받아 렌더링

RabbitMQ 메시지 예시는 다음과 같습니다.

```json
{
  "type": "PRE_EVALUATION_GENERATE",
  "preEvaluationId": 12,
  "userId": 7,
  "patentName": "5G 기반 실시간 데이터 압축 알고리즘",
  "technologyDescription": "기술 설명",
  "claims": ["청구항"],
  "relatedBusiness": "관련 사업",
  "targetCountries": ["한국"]
}
```
