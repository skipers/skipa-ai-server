# AI Server Integration Guide

이 문서는 AI 서버 파트 개발자가 백엔드 비동기 작업 스펙에 맞춰 worker를 구현할 수 있도록 정리한 연동 문서입니다.

대상 기능은 세 가지입니다.

- AI 평가 보고서 생성
- 특허 원문 PDF 기반 특허 초안 생성
- 정식 출원 전 사전 평가 보고서 생성 및 채팅

## 1. 공통 규칙

### 1-1. Internal API 인증

AI 서버가 백엔드의 `/internal/**` API를 호출할 때는 반드시 아래 헤더를 포함해야 합니다.

```http
X-Internal-Api-Key: {INTERNAL_API_KEY}
```

`INTERNAL_API_KEY`는 백엔드와 AI 서버가 같은 값을 사용해야 합니다.

### 1-2. 백엔드 응답 형식

성공 응답은 기본적으로 아래 형식입니다.

```json
{
  "success": true,
  "data": {}
}
```

## 2. AI 평가 보고서 생성

### 2-1. 전체 흐름

1. 프론트가 보고서 생성을 요청합니다.
2. 백엔드는 `reports` row를 `GENERATING` 상태로 생성합니다.
3. 백엔드는 RabbitMQ에 보고서 생성 메시지를 발행합니다.
4. AI 서버의 보고서 생성 worker는 RabbitMQ 메시지를 consume합니다.
5. worker는 `reportId`, `patentId`를 기준으로 보고서를 생성합니다.
6. worker는 생성된 보고서 JSON 파일을 MinIO에 업로드합니다.
7. worker는 백엔드 internal 완료 API를 호출합니다.
8. 백엔드는 보고서 상태를 `COMPLETED`로 변경하고 `reportKey`, `totalScore`, `valueGrade`를 저장합니다.
9. 프론트는 상태 polling 후 완료된 보고서 조회 API에서 presigned URL을 받습니다.

### 2-2. 보고서 생성 요청 API

프론트가 호출하는 API입니다. AI 서버가 직접 호출하지 않습니다.

```http
POST /patents/{patentId}/reports
```

백엔드는 보고서를 생성하고 RabbitMQ 메시지를 발행합니다.

응답 예시:

```json
{
  "success": true,
  "data": {
    "id": 8,
    "patentId": 1,
    "status": "GENERATING",
    "createdAt": "2026-06-08T07:00:00Z",
    "updatedAt": "2026-06-08T07:00:00Z"
  }
}
```

`data.id`가 `reportId`입니다.

### 2-3. RabbitMQ 메시지

AI 서버는 보고서 생성 queue를 consume해야 합니다.

백엔드 설정값:

```yaml
app:
  rabbitmq:
    exchange: ${RABBITMQ_EXCHANGE:skipa.exchange}
    report:
      queue: ${REPORT_GENERATE_QUEUE:skipa.report.generate}
      routing-key: ${REPORT_GENERATE_ROUTING_KEY:report.generate}
```

메시지 payload:

```json
{
  "type": "REPORT_GENERATE",
  "reportId": 8,
  "patentId": 1
}
```

필드 설명:

| 필드 | 설명 |
| --- | --- |
| `type` | 메시지 타입. 항상 `REPORT_GENERATE` |
| `reportId` | 생성할 보고서 ID |
| `patentId` | 보고서 대상 특허 ID |

### 2-4. 보고서 생성 worker 구현 기준

보고서 생성 worker는 `REPORT_GENERATE` 메시지를 받으면 아래 작업을 수행해야 합니다.

1. 메시지에서 `reportId`, `patentId`를 읽습니다.
2. 보고서 생성에 필요한 특허 정보를 확보합니다.
3. AI 보고서 JSON을 생성합니다.
4. 생성된 보고서 JSON 파일을 MinIO에 업로드합니다.
5. 업로드한 object key인 `reportKey`와 평가 결과인 `totalScore`, `valueGrade`를 백엔드 완료 콜백에 전달합니다.

보고서 파일은 JSON 형식이며, MinIO key는 AI 서버가 결정합니다.

권장 key 형식:

```text
patents/{patentId}/reports/{reportId}/report.json
```

예시:

```text
patents/1/reports/8/report.json
```

주의사항:

- AI 서버는 presigned URL을 백엔드에 전달하지 않습니다.
- AI 서버는 presigned URL이 아닌 MinIO object key인 `reportKey`를 전달합니다.
- AI 서버는 평가 결과인 `totalScore`, `valueGrade`도 함께 전달합니다.
- 프론트에는 `reportKey`가 직접 노출되지 않습니다.
- 프론트는 완료된 보고서 조회 API에서 백엔드가 생성한 presigned URL만 받습니다.

### 2-5. 보고서 생성 완료 콜백

AI 서버가 보고서 JSON 파일 업로드를 완료한 뒤 호출합니다.

```http
PATCH /internal/reports/{reportId}/complete
X-Internal-Api-Key: {INTERNAL_API_KEY}
Content-Type: application/json
```

요청 body:

```json
{
  "reportKey": "patents/1/reports/8/report.json",
  "totalScore": 82.50,
  "valueGrade": "A"
}
```

요청 필드:

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reportKey` | string | Y | AI 서버가 MinIO에 업로드한 보고서 object key |
| `totalScore` | number | Y | AI 평가 총점. `0.00` 이상 `100.00` 이하, 소수 2자리까지 허용 |
| `valueGrade` | string | Y | AI 평가 등급. `S`, `A`, `B`, `C`, `D` 중 하나 |

응답 예시:

```json
{
  "success": true,
  "data": {
    "reportId": 8,
    "status": "COMPLETED",
    "totalScore": 82.50,
    "valueGrade": "A"
  }
}
```

### 2-6. 보고서 생성 실패 콜백

AI 서버가 보고서 생성에 실패한 경우 호출합니다.

```http
PATCH /internal/reports/{reportId}/fail
X-Internal-Api-Key: {INTERNAL_API_KEY}
Content-Type: application/json
```

요청 body:

```json
{
  "errorMessage": "보고서 생성 중 오류가 발생했습니다."
}
```

현재 백엔드는 `errorMessage`를 요청으로 받을 수 있지만, 보고서 엔티티에는 별도로 저장하지 않고 상태를 `FAILED`로 변경합니다.

응답 예시:

```json
{
  "success": true,
  "data": {
    "reportId": 8,
    "status": "FAILED",
    "totalScore": null,
    "valueGrade": null
  }
}
```

## 3. 특허 원문 PDF 기반 특허 초안 생성

### 3-1. 전체 흐름

1. 프론트가 백엔드에 PDF 업로드 URL 발급을 요청합니다.
2. 백엔드는 `patent_extract_jobs` row를 생성합니다.
3. 백엔드는 MinIO 업로드용 presigned URL과 `objectKey`를 반환합니다.
4. 프론트는 해당 presigned URL로 PDF를 MinIO에 업로드합니다.
5. 프론트는 백엔드에 업로드 완료 API를 호출합니다.
6. 백엔드는 MinIO object 존재 여부를 확인합니다.
7. 백엔드는 RabbitMQ에 특허 추출 메시지를 발행합니다.
8. AI 서버의 특허 추출 worker는 RabbitMQ 메시지를 consume합니다.
9. worker는 `objectKey`의 PDF를 MinIO에서 읽어 특허 정보를 추출합니다.
10. worker는 백엔드 internal 완료 API에 추출 결과 JSON을 전달합니다.
11. 프론트는 상태 polling 후 결과 조회 API로 추출 결과를 받습니다.
12. 프론트가 최종 특허 생성 시 `extractJobId`를 함께 전달합니다.
13. 백엔드는 임시 PDF를 최종 경로로 복사하고 `originalPdfKey`에 저장합니다.

### 3-2. PDF 업로드 URL 발급

프론트가 호출하는 API입니다. AI 서버가 직접 호출하지 않습니다.

```http
POST /patent-extract-jobs/upload-url
```

응답 예시:

```json
{
  "success": true,
  "data": {
    "extractJobId": 7,
    "objectKey": "tmp/patent-extract-jobs/7/original.pdf",
    "uploadUrl": "https://minio.example.com/...",
    "expiresInSeconds": 600,
    "status": "UPLOAD_PENDING",
    "createdAt": "2026-06-08T07:00:00Z",
    "updatedAt": "2026-06-08T07:00:00Z"
  }
}
```

중요 필드:

| 필드 | 설명 |
| --- | --- |
| `extractJobId` | 특허 추출 작업 ID |
| `objectKey` | 프론트가 PDF를 업로드할 MinIO object key |
| `uploadUrl` | PDF 업로드용 presigned URL |
| `expiresInSeconds` | URL 만료 시간 |

### 3-3. PDF 업로드 완료

프론트가 PDF를 MinIO에 업로드한 뒤 호출합니다.

```http
POST /patent-extract-jobs/{extractJobId}/upload-complete
```

백엔드는 `objectKey`에 파일이 실제 존재하는지 확인합니다.

파일이 존재하면 상태를 갱신하고 RabbitMQ 메시지를 발행합니다.

응답 예시:

```json
{
  "success": true,
  "data": {
    "extractJobId": 7,
    "objectKey": "tmp/patent-extract-jobs/7/original.pdf",
    "status": "ANALYZING",
    "errorMessage": null,
    "uploadedAt": "2026-06-08T07:01:00Z",
    "completedAt": null,
    "createdAt": "2026-06-08T07:00:00Z",
    "updatedAt": "2026-06-08T07:01:00Z"
  }
}
```

### 3-4. RabbitMQ 메시지

AI 서버는 특허 추출 queue를 consume해야 합니다.

백엔드 설정값:

```yaml
app:
  rabbitmq:
    exchange: ${RABBITMQ_EXCHANGE:skipa.exchange}
    patent-extract:
      queue: ${PATENT_EXTRACT_QUEUE:skipa.patent-extract}
      routing-key: ${PATENT_EXTRACT_ROUTING_KEY:patent.extract}
```

메시지 payload:

```json
{
  "type": "PATENT_EXTRACT",
  "extractJobId": 7,
  "objectKey": "tmp/patent-extract-jobs/7/original.pdf"
}
```

필드 설명:

| 필드 | 설명 |
| --- | --- |
| `type` | 메시지 타입. 항상 `PATENT_EXTRACT` |
| `extractJobId` | 특허 추출 작업 ID |
| `objectKey` | AI 서버가 읽어야 하는 원문 PDF MinIO object key |

### 3-5. 특허 추출 worker 구현 기준

특허 추출 worker는 `PATENT_EXTRACT` 메시지를 받으면 아래 작업을 수행해야 합니다.

1. 메시지에서 `extractJobId`, `objectKey`를 읽습니다.
2. MinIO에서 `objectKey`의 PDF를 다운로드합니다.
3. PDF에서 특허 메타데이터와 초안 정보를 추출합니다.
4. 추출 결과를 JSON으로 구성합니다.
5. 백엔드 internal 완료 API를 호출합니다.

PDF 다운로드 대상 key:

```text
tmp/patent-extract-jobs/{extractJobId}/original.pdf
```

예시:

```text
tmp/patent-extract-jobs/7/original.pdf
```

### 3-6. 특허 추출 완료 콜백

AI 서버가 추출을 완료하면 호출합니다.

```http
PATCH /internal/patent-extract-jobs/{extractJobId}/complete
X-Internal-Api-Key: {INTERNAL_API_KEY}
Content-Type: application/json
```

요청 body:

```json
{
  "result": {
    "title": "반도체 패키지 구조",
    "applicationNumber": "10-2026-0000000",
    "registrationNumber": "10-1234567",
    "publicationNumber": "10-2026-0000001",
    "announcementNumber": "10-2026-0000002",
    "applicationDate": "2026-05-26",
    "registrationDate": "2026-05-26",
    "publicationDate": "2026-05-26",
    "announcementDate": "2026-05-26",
    "ipcCodes": ["H01L 21/00"],
    "cpcCodes": ["H01L 21/00"],
    "applicant": "SK",
    "inventor": "홍길동",
    "expiryDate": "2046-05-26",
    "citationCount": 10,
    "examinationClaimCount": 12,
    "managementNumber": "MNG-2026-0001",
    "businessField": "반도체",
    "techField": "패키징",
    "relatedProducts": ["제품A", "제품B"],
    "filingCountry": "KR",
    "isJointApplication": false,
    "jointApplicant": null,
    "initialDepartment": "반도체",
    "keywords": ["패키지", "반도체"],
    "summary": "특허 요약"
  }
}
```

`result`는 프론트가 최종 특허 생성 API에 채워 넣을 초안 데이터입니다. 가능한 한 백엔드 `POST /patents` 요청 필드명과 맞춰야 합니다.

주요 필드:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `title` | string | 특허명 |
| `applicationNumber` | string | 출원번호 |
| `registrationNumber` | string | 등록번호 |
| `publicationNumber` | string | 공개번호 |
| `announcementNumber` | string | 공고번호 |
| `applicationDate` | string | 출원일, `yyyy-MM-dd` |
| `registrationDate` | string | 등록일, `yyyy-MM-dd` |
| `publicationDate` | string | 공개일, `yyyy-MM-dd` |
| `announcementDate` | string | 공고일, `yyyy-MM-dd` |
| `ipcCodes` | string[] | IPC 코드 목록 |
| `cpcCodes` | string[] | CPC 코드 목록 |
| `applicant` | string | 출원인 |
| `inventor` | string | 발명자 |
| `expiryDate` | string | 예상 소멸일, `yyyy-MM-dd` |
| `citationCount` | number | 피인용 수 |
| `examinationClaimCount` | number | 심사청구항수 |
| `managementNumber` | string | 관리번호 |
| `businessField` | string | 관련사업 분야 |
| `techField` | string | 관련기술 분야 |
| `relatedProducts` | string[] | 관련제품 |
| `filingCountry` | string | 출원국가 |
| `isJointApplication` | boolean | 공동출원 여부 |
| `jointApplicant` | string | 공동출원인 |
| `initialDepartment` | string | 최초 담당 부서 |
| `keywords` | string[] | 키워드 |
| `summary` | string | 요약 |

응답 예시:

```json
{
  "success": true,
  "data": {
    "extractJobId": 7,
    "objectKey": "tmp/patent-extract-jobs/7/original.pdf",
    "status": "COMPLETED",
    "errorMessage": null,
    "uploadedAt": "2026-06-08T07:01:00Z",
    "completedAt": "2026-06-08T07:05:00Z",
    "createdAt": "2026-06-08T07:00:00Z",
    "updatedAt": "2026-06-08T07:05:00Z"
  }
}
```

### 3-7. 특허 추출 실패 콜백

AI 서버가 추출에 실패하면 호출합니다.

```http
PATCH /internal/patent-extract-jobs/{extractJobId}/fail
X-Internal-Api-Key: {INTERNAL_API_KEY}
Content-Type: application/json
```

요청 body:

```json
{
  "errorMessage": "PDF 파싱에 실패했습니다."
}
```

응답 예시:

```json
{
  "success": true,
  "data": {
    "extractJobId": 7,
    "objectKey": "tmp/patent-extract-jobs/7/original.pdf",
    "status": "FAILED",
    "errorMessage": "PDF 파싱에 실패했습니다.",
    "uploadedAt": "2026-06-08T07:01:00Z",
    "completedAt": null,
    "createdAt": "2026-06-08T07:00:00Z",
    "updatedAt": "2026-06-08T07:05:00Z"
  }
}

```

### 3-8. 프론트 polling/result 조회

프론트가 호출하는 API입니다. AI 서버가 직접 호출하지 않습니다.

상태 조회:

```http
GET /patent-extract-jobs/{extractJobId}/status
```

결과 조회:

```http
GET /patent-extract-jobs/{extractJobId}/result
```

결과 조회 응답 예시:

```json
{
  "success": true,
  "data": {
    "extractJobId": 7,
    "objectKey": "tmp/patent-extract-jobs/7/original.pdf",
    "status": "COMPLETED",
    "result": {
      "title": "반도체 패키지 구조",
      "applicationNumber": "10-2026-0000000"
    },
    "uploadedAt": "2026-06-08T07:01:00Z",
    "completedAt": "2026-06-08T07:05:00Z",
    "createdAt": "2026-06-08T07:00:00Z",
    "updatedAt": "2026-06-08T07:05:00Z"
  }
}
```

### 3-9. 최종 특허 생성 시 MinIO key 처리

프론트는 추출 결과를 확인한 뒤 최종 특허 생성 API를 호출합니다.

```http
POST /patents
```

이때 `extractJobId`를 함께 전달하면 백엔드는 특허 row를 생성한 뒤, 생성된 `patentId`를 기준으로 임시 PDF를 최종 경로로 복사합니다.

요청 예시:

```json
{
  "title": "반도체 패키지 구조",
  "applicationNumber": "10-2026-0000000",
  "registrationNumber": "10-1234567",
  "applicationDate": "2026-05-26",
  "ipcCodes": ["H01L 21/00"],
  "cpcCodes": ["H01L 21/00"],
  "applicant": "SK",
  "inventor": "홍길동",
  "extractJobId": 7,
  "examinationClaimCount": 12,
  "businessField": "반도체",
  "techField": "패키징",
  "keywords": ["패키지", "반도체"],
  "summary": "특허 요약"
}
```

MinIO key 규칙:

임시 PDF:

```text
tmp/patent-extract-jobs/{extractJobId}/original.pdf
```

최종 PDF:

```text
patents/{patentId}/original.pdf
```

예시:

```text
patents/1/original.pdf
```

최종 PDF key는 특허의 `originalPdfKey`에 저장됩니다.

`extractJobId` 기반으로 특허를 생성하면 백엔드는 추출 결과 JSON을 아래 최종 key로 저장하고, 해당 key를 특허의 `parsedJsonKey`에 저장합니다.

```text
patents/{patentId}/parsed.json
```

보고서 JSON의 최종 key:

```text
patents/{patentId}/reports/{reportId}/report.json
```

## 4. 사전 평가 보고서 생성 및 채팅

### 4-1. 전체 흐름

사전 평가는 정식 특허 출원 전 아이디어의 가치와 심사 통과 가능성을 확인하는 기능입니다.

1. 프론트가 백엔드에 사전 평가 시작을 요청합니다.
2. 백엔드는 `pre_evaluations` row를 `PROCESSING` 상태로 생성합니다.
3. 백엔드는 RabbitMQ에 사전 평가 보고서 생성 메시지를 발행합니다.
4. AI 서버의 사전 평가 worker는 RabbitMQ 메시지를 consume합니다.
5. worker는 메시지에 포함된 임시 특허 정보를 기준으로 사전 평가 보고서를 생성합니다.
6. worker는 생성된 보고서를 MinIO에 업로드합니다.
7. worker는 백엔드 internal 완료 API를 호출합니다.
8. 백엔드는 사전 평가 상태를 `COMPLETED`로 변경하고 `reportKey`를 저장합니다.
9. 프론트는 상태 polling 후 상세 조회에서 백엔드가 생성한 `reportUrl`로 보고서를 확인합니다.
10. 사전 평가별 채팅은 RabbitMQ가 아니라 백엔드가 AI 서버 HTTP API를 직접 호출합니다.

### 4-2. 사전 평가 시작 API

프론트가 호출하는 API입니다. AI 서버가 직접 호출하지 않습니다.

```http
POST /pre-evaluations
```

백엔드는 사전 평가 row를 생성하고 RabbitMQ 메시지를 발행합니다.

요청 예시:

```json
{
  "title": "배터리 열폭주 감지 시스템",
  "technicalDescription": "센서 데이터를 기반으로 배터리 열폭주 가능성을 조기에 감지하는 기술",
  "claims": [
    "센서부를 포함하는 배터리 열폭주 감지 시스템",
    "분석부가 센서 데이터를 기반으로 위험도를 산출하는 시스템"
  ],
  "relatedBusiness": "전기차 배터리 안전 관리",
  "targetCountries": "한국, 미국"
}
```

응답 예시:

```json
{
  "success": true,
  "data": {
    "id": 12,
    "userId": 10,
    "status": "PROCESSING",
    "createdAt": "2026-06-11T07:00:00Z",
    "updatedAt": "2026-06-11T07:00:00Z"
  }
}
```

`data.id`가 `preEvaluationId`입니다.

### 4-3. RabbitMQ 메시지

AI 서버는 사전 평가 생성 queue를 consume해야 합니다.

백엔드 설정값:

```yaml
app:
  rabbitmq:
    exchange: ${RABBITMQ_EXCHANGE:skipa.exchange}
    pre-evaluation:
      queue: ${PRE_EVALUATION_GENERATE_QUEUE:skipa.pre-evaluation.generate}
      routing-key: ${PRE_EVALUATION_GENERATE_ROUTING_KEY:pre-evaluation.generate}
```

메시지 payload:

```json
{
  "type": "PRE_EVALUATION_GENERATE",
  "preEvaluationId": 12,
  "userId": 10,
  "title": "배터리 열폭주 감지 시스템",
  "technicalDescription": "센서 데이터를 기반으로 배터리 열폭주 가능성을 조기에 감지하는 기술",
  "claims": [
    "센서부를 포함하는 배터리 열폭주 감지 시스템",
    "분석부가 센서 데이터를 기반으로 위험도를 산출하는 시스템"
  ],
  "relatedBusiness": "전기차 배터리 안전 관리",
  "targetCountries": "한국, 미국"
}
```

필드 설명:

| 필드 | 설명 |
| --- | --- |
| `type` | 메시지 타입. 항상 `PRE_EVALUATION_GENERATE` |
| `preEvaluationId` | 생성할 사전 평가 보고서 대상 ID |
| `userId` | 사전 평가를 요청한 사용자 ID |
| `title` | 특허명 |
| `technicalDescription` | 기술 설명 |
| `claims` | 청구항 목록. `string[]` |
| `relatedBusiness` | 관련 사업 |
| `targetCountries` | 출원 예정 국가. 예: `한국, 미국` |

### 4-4. 사전 평가 worker 구현 기준

사전 평가 worker는 `PRE_EVALUATION_GENERATE` 메시지를 받으면 아래 작업을 수행해야 합니다.

1. 메시지에서 `preEvaluationId`와 임시 특허 입력 정보를 읽습니다.
2. `title`, `technicalDescription`, `claims`, `relatedBusiness`, `targetCountries`를 기반으로 사전 평가 보고서를 생성합니다.
3. 생성된 보고서를 MinIO에 업로드합니다.
4. 업로드한 object key를 `reportKey`로 결정합니다.
5. `reportKey`로 백엔드 완료 콜백을 호출합니다.

권장 key 형식:

```text
pre-evaluations/{preEvaluationId}/report.json
```

예시:

```text
pre-evaluations/12/report.json
```

주의사항:

- AI 서버는 presigned URL이 아닌 MinIO object key인 `reportKey`를 전달합니다.
- 백엔드는 callback으로 받은 `reportKey`를 DB에 저장합니다.
- 프론트에는 `reportKey`가 직접 노출되지 않습니다.
- 프론트가 사전 평가 상세를 조회하면 백엔드가 `reportKey`로 presigned URL을 생성해 `reportUrl`로 반환합니다.
- `claims`는 문자열 하나가 아니라 문자열 배열입니다.

### 4-5. 사전 평가 완료 콜백

AI 서버가 사전 평가 보고서 업로드를 완료한 뒤 호출합니다.

```http
PATCH /internal/pre-evaluations/{preEvaluationId}/complete
X-Internal-Api-Key: {INTERNAL_API_KEY}
Content-Type: application/json
```

요청 body:

```json
{
  "reportKey": "pre-evaluations/12/report.json"
}
```

요청 필드:

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reportKey` | string | Y | AI 서버가 MinIO에 업로드한 사전 평가 보고서 object key |

응답 예시:

```json
{
  "success": true,
  "data": {
    "preEvaluationId": 12,
    "status": "COMPLETED",
    "completedAt": "2026-06-11T07:05:00Z"
  }
}
```

### 4-6. 사전 평가 실패 콜백

AI 서버가 사전 평가 보고서 생성에 실패한 경우 호출합니다.

```http
PATCH /internal/pre-evaluations/{preEvaluationId}/fail
X-Internal-Api-Key: {INTERNAL_API_KEY}
Content-Type: application/json
```

요청 body:

```json
{
  "errorMessage": "사전 평가 보고서 생성 중 오류가 발생했습니다."
}
```

현재 백엔드는 `errorMessage`를 요청으로 받을 수 있지만, 사전 평가 엔티티에는 별도로 저장하지 않고 상태를 `FAILED`로 변경합니다.

응답 예시:

```json
{
  "success": true,
  "data": {
    "preEvaluationId": 12,
    "status": "FAILED",
    "completedAt": "2026-06-11T07:05:00Z"
  }
}
```

### 4-7. 사전 평가 채팅 API

사전 평가 채팅은 RabbitMQ 메시지를 사용하지 않습니다.

백엔드가 사용자 메시지를 DB에 저장한 뒤 AI 서버 HTTP API를 직접 호출합니다. AI 서버는 아래 endpoint를 제공해야 합니다.

백엔드 설정값:

```yaml
app:
  ai-server:
    base-url: ${AI_SERVER_BASE_URL:http://localhost:8000}
    pre-evaluation-chat-path: ${AI_PRE_EVALUATION_CHAT_PATH:/pre-evaluations/chat}
```

백엔드가 호출하는 URL:

```http
POST {AI_SERVER_BASE_URL}{AI_PRE_EVALUATION_CHAT_PATH}
Content-Type: application/json
```

기본값 기준:

```http
POST http://localhost:8000/pre-evaluations/chat
Content-Type: application/json
```

요청 body:

```json
{
  "preEvaluationId": 12,
  "userId": 10,
  "title": "배터리 열폭주 감지 시스템",
  "technicalDescription": "센서 데이터를 기반으로 배터리 열폭주 가능성을 조기에 감지하는 기술",
  "claims": [
    "센서부를 포함하는 배터리 열폭주 감지 시스템",
    "분석부가 센서 데이터를 기반으로 위험도를 산출하는 시스템"
  ],
  "relatedBusiness": "전기차 배터리 안전 관리",
  "targetCountries": "한국, 미국",
  "message": "등록 가능성을 높이려면 어떤 부분을 보완해야 하나요?",
  "history": [
    {
      "role": "USER",
      "content": "등록 가능성을 높이려면 어떤 부분을 보완해야 하나요?"
    }
  ]
}
```

요청 필드:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `preEvaluationId` | number | 사전 평가 ID |
| `userId` | number | 요청 사용자 ID |
| `title` | string | 특허명 |
| `technicalDescription` | string | 기술 설명 |
| `claims` | string[] | 청구항 목록 |
| `relatedBusiness` | string | 관련 사업 |
| `targetCountries` | string | 출원 예정 국가 |
| `message` | string | 사용자가 이번에 보낸 메시지 |
| `history` | object[] | 해당 사전 평가의 이전 대화 이력과 현재 사용자 메시지 |
| `history[].role` | string | `USER` 또는 `ASSISTANT` |
| `history[].content` | string | 메시지 내용 |

응답 body:

```json
{
  "message": "청구항에서 센서 데이터 처리 알고리즘의 차별성을 더 구체화하는 것이 좋습니다."
}
```

응답 필드:

| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `message` | string | Y | AI 서버가 생성한 답변. 빈 문자열이면 백엔드는 `AI_SERVER_ERROR`로 처리 |

주의사항:

- 백엔드는 사용자 메시지를 먼저 저장한 뒤 AI 서버를 호출합니다.
- AI 서버 응답이 성공하면 백엔드는 응답 메시지를 `ASSISTANT` 역할로 저장합니다.
- AI 서버가 4xx/5xx를 반환하거나 `message`가 비어 있으면 백엔드는 `AI_SERVER_ERROR`를 반환합니다.
- 채팅 endpoint에는 현재 별도 internal api key를 붙이지 않습니다. 네트워크 레벨 접근 제한 또는 AI 서버 측 인증이 필요하면 별도 협의가 필요합니다.

### 4-8. 프론트 polling/채팅 조회

프론트가 호출하는 API입니다. AI 서버가 직접 호출하지 않습니다.

목록 조회:

```http
GET /pre-evaluations
```

상태 조회:

```http
GET /pre-evaluations/{preEvaluationId}/status
```

상세 조회:

```http
GET /pre-evaluations/{preEvaluationId}
```

채팅 이력 조회:

```http
GET /pre-evaluations/{preEvaluationId}/chat/messages
```

채팅 메시지 전송:

```http
POST /pre-evaluations/{preEvaluationId}/chat/messages
```

채팅 초기화:

```http
DELETE /pre-evaluations/{preEvaluationId}/chat/messages
```

평가 이력 삭제:

```http
DELETE /pre-evaluations/{preEvaluationId}
```

## 5. 상태값

### 5-1. 보고서 상태

| 상태 | 설명 |
| --- | --- |
| `GENERATING` | 보고서 생성 중 |
| `COMPLETED` | 보고서 생성 완료 |
| `FAILED` | 보고서 생성 실패 |

### 5-2. 특허 추출 상태

| 상태 | 설명 |
| --- | --- |
| `UPLOAD_PENDING` | 업로드 URL 발급 후 PDF 업로드 대기 |
| `ANALYZING` | PDF 업로드 완료, AI 분석 중 |
| `COMPLETED` | AI 추출 완료 |
| `FAILED` | AI 추출 실패 |

### 5-3. 사전 평가 상태

| 상태 | 설명 |
| --- | --- |
| `PROCESSING` | 사전 평가 보고서 생성 중 |
| `COMPLETED` | 사전 평가 보고서 생성 완료 |
| `FAILED` | 사전 평가 보고서 생성 실패 |

### 5-4. 사전 평가 채팅 role

| role | 설명 |
| --- | --- |
| `USER` | 사용자 메시지 |
| `ASSISTANT` | AI 서버 응답 메시지 |

## 6. AI 서버 구현 체크리스트

### 6-1. 보고서 생성 worker

- [ ] RabbitMQ `REPORT_GENERATE` 메시지 consume
- [ ] `reportId`, `patentId` 파싱
- [ ] 보고서 JSON 생성
- [ ] 생성된 보고서 JSON 파일을 MinIO에 업로드
- [ ] 업로드 object key를 `reportKey`로 결정
- [ ] 평가 결과 `totalScore`, `valueGrade` 산출
- [ ] `reportKey`, `totalScore`, `valueGrade`로 `PATCH /internal/reports/{reportId}/complete` 호출
- [ ] 실패 시 `PATCH /internal/reports/{reportId}/fail` 호출
- [ ] 모든 internal API 요청에 `X-Internal-Api-Key` 포함

### 6-2. 특허 추출 worker

- [ ] RabbitMQ `PATENT_EXTRACT` 메시지 consume
- [ ] `extractJobId`, `objectKey` 파싱
- [ ] MinIO에서 `objectKey` PDF 다운로드
- [ ] 특허 초안 JSON 추출
- [ ] `PATCH /internal/patent-extract-jobs/{extractJobId}/complete` 호출
- [ ] 실패 시 `PATCH /internal/patent-extract-jobs/{extractJobId}/fail` 호출
- [ ] 모든 internal API 요청에 `X-Internal-Api-Key` 포함

### 6-3. 사전 평가 worker

- [ ] RabbitMQ `PRE_EVALUATION_GENERATE` 메시지 consume
- [ ] `preEvaluationId`, `userId`, `title`, `technicalDescription`, `claims`, `relatedBusiness`, `targetCountries` 파싱
- [ ] `claims`를 문자열 배열로 처리
- [ ] 사전 평가 보고서 생성
- [ ] 생성된 보고서를 MinIO에 업로드
- [ ] 업로드 object key를 `reportKey`로 결정
- [ ] `reportKey`로 `PATCH /internal/pre-evaluations/{preEvaluationId}/complete` 호출
- [ ] 실패 시 `PATCH /internal/pre-evaluations/{preEvaluationId}/fail` 호출
- [ ] 모든 internal API 요청에 `X-Internal-Api-Key` 포함

### 6-4. 사전 평가 채팅 API

- [ ] `POST {AI_SERVER_BASE_URL}{AI_PRE_EVALUATION_CHAT_PATH}` endpoint 제공
- [ ] 백엔드 요청 body의 사전 평가 입력 정보와 `history` 처리
- [ ] 응답 body를 `{ "message": "..." }` 형식으로 반환
- [ ] 빈 `message`를 반환하지 않도록 검증
- [ ] 오류 발생 시 적절한 4xx/5xx 응답 반환

## 7. Worker 구현 및 실행 기준

### 7-1. AI 서버 실행 구조

AI 서버는 백엔드 애플리케이션 내부에서 실행하지 않습니다.

별도의 장기 실행 프로세스 또는 컨테이너로 실행하고, RabbitMQ queue를 계속 consume하는 worker service로 구성합니다.

권장 실행 구조:

```text
Backend API Server
  - HTTP API 제공
  - RabbitMQ 메시지 발행
  - internal callback API 제공

RabbitMQ
  - report generate queue
  - patent extract queue
  - pre evaluation generate queue

AI Worker Server
  - report worker
  - patent extract worker
  - pre evaluation worker
  - pre evaluation chat API
  - RabbitMQ consume
  - MinIO read/write
  - Backend internal callback 호출

MinIO
  - 원문 PDF 저장
  - AI 보고서 JSON 파일 저장
```

AI 서버는 아래 worker를 실행해야 합니다.

- 보고서 생성 worker
- 특허 추출 worker
- 사전 평가 worker

또한 사전 평가 채팅을 위해 백엔드에서 직접 호출할 수 있는 HTTP API를 제공해야 합니다.

각 worker는 하나의 AI 서버 프로세스 안에서 동시에 실행해도 되고, 별도 프로세스/컨테이너로 분리해도 됩니다.

운영 관점에서는 장애 격리와 스케일링을 위해 아래처럼 분리하는 것을 권장합니다.

```text
ai-report-worker
ai-patent-extract-worker
ai-pre-evaluation-worker
ai-pre-evaluation-api
```

### 7-2. Worker 시작 시 동작

AI worker 프로세스가 시작되면 다음 작업을 수행합니다.

1. 환경 변수 로드
2. RabbitMQ 연결
3. MinIO 연결
4. Backend internal API base URL 설정
5. 대상 queue 구독 시작
6. 메시지를 받을 때까지 대기

worker는 일회성 배치가 아니라 계속 떠 있는 daemon 형태로 실행합니다.

예시:

```text
start worker
  -> connect RabbitMQ
  -> connect MinIO
  -> subscribe queue
  -> wait message
  -> process message
  -> ack/nack
  -> wait next message
```

### 7-3. 필수 환경 변수

AI 서버는 최소한 아래 설정을 가져야 합니다.

```text
RABBITMQ_HOST
RABBITMQ_PORT
RABBITMQ_USERNAME
RABBITMQ_PASSWORD

REPORT_GENERATE_QUEUE
PATENT_EXTRACT_QUEUE
PRE_EVALUATION_GENERATE_QUEUE

MINIO_ENDPOINT
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
MINIO_BUCKET
MINIO_REGION

BACKEND_INTERNAL_BASE_URL
INTERNAL_API_KEY

AI_PRE_EVALUATION_CHAT_PATH
```

예시:

```text
BACKEND_INTERNAL_BASE_URL=http://skipa-backend:8080
INTERNAL_API_KEY=shared-internal-key

REPORT_GENERATE_QUEUE=skipa.report.generate
PATENT_EXTRACT_QUEUE=skipa.patent-extract
PRE_EVALUATION_GENERATE_QUEUE=skipa.pre-evaluation.generate
AI_PRE_EVALUATION_CHAT_PATH=/pre-evaluations/chat
```

### 7-4. 메시지 처리 기본 규칙

worker는 메시지 처리 시 아래 규칙을 따라야 합니다.

1. 메시지를 받으면 payload schema를 검증합니다.
2. 필수 필드가 없으면 실패 처리하고 메시지는 재처리하지 않습니다.
3. 작업이 성공하면 백엔드 complete callback을 호출합니다.
4. 작업이 실패하면 백엔드 fail callback을 호출합니다.
5. 백엔드 callback까지 성공하면 RabbitMQ 메시지를 ack 처리합니다.
6. 일시적인 장애라면 메시지를 nack/requeue하거나 retry 정책을 적용합니다.

권장 처리 순서:

```text
consume message
  -> validate payload
  -> run AI task
  -> upload/read MinIO
  -> call backend complete/fail callback
  -> ack message
```

주의사항:

- AI 작업은 오래 걸릴 수 있으므로 HTTP request 안에서 처리하지 말고 worker에서 처리합니다.
- 단, 사전 평가 채팅은 짧은 대화 응답용 HTTP API로 처리합니다.
- RabbitMQ 메시지는 중복 전달될 수 있다고 가정합니다.
- 같은 `reportId`, `extractJobId`, `preEvaluationId` 메시지를 중복 처리해도 큰 문제가 없도록 구현하는 것이 좋습니다.
- callback API가 실패하면 메시지를 바로 ack하지 말고 재시도해야 합니다.

### 7-5. Ack/Nack 권장 정책

성공 처리:

```text
AI 작업 성공
  -> MinIO 업로드 또는 결과 생성 성공
  -> backend complete callback 성공
  -> RabbitMQ ack
```

실패 처리:

```text
AI 작업 실패
  -> backend fail callback 성공
  -> RabbitMQ ack
```

일시 장애:

```text
MinIO 연결 실패
Backend callback 실패
RabbitMQ 일시 장애
  -> retry
  -> retry 초과 시 nack 또는 dead-letter queue 사용
```

권장 retry 기준:

- MinIO 다운로드/업로드 실패: retry 대상
- Backend callback 5xx: retry 대상
- Backend callback 401/403: 설정 오류이므로 즉시 운영 알림
- Backend callback 404: 잘못된 job id 가능성이 높으므로 fail 또는 ack 후 로그 기록
- AI 파싱/생성 실패: fail callback 후 ack

### 7-6. 보고서 생성 worker 예시 흐름

```text
REPORT_GENERATE 메시지 수신
  -> reportId, patentId 확인
  -> 보고서 생성에 필요한 데이터 준비
  -> AI 보고서 JSON 생성
  -> MinIO에 patents/{patentId}/reports/{reportId}/report.json 업로드
  -> reportKey, totalScore, valueGrade로 PATCH /internal/reports/{reportId}/complete 호출
  -> RabbitMQ ack
```

실패 시:

```text
REPORT_GENERATE 메시지 수신
  -> AI 보고서 생성 실패
  -> PATCH /internal/reports/{reportId}/fail 호출
  -> RabbitMQ ack
```

### 7-7. 특허 추출 worker 예시 흐름

```text
PATENT_EXTRACT 메시지 수신
  -> extractJobId, objectKey 확인
  -> MinIO에서 objectKey PDF 다운로드
  -> PDF 파싱 및 AI 추출 수행
  -> result JSON 생성
  -> PATCH /internal/patent-extract-jobs/{extractJobId}/complete 호출
  -> RabbitMQ ack
```

실패 시:

```text
PATENT_EXTRACT 메시지 수신
  -> PDF 다운로드 또는 AI 추출 실패
  -> PATCH /internal/patent-extract-jobs/{extractJobId}/fail 호출
  -> RabbitMQ ack
```

### 7-8. 사전 평가 worker 예시 흐름

```text
PRE_EVALUATION_GENERATE 메시지 수신
  -> preEvaluationId와 임시 특허 입력 정보 확인
  -> 사전 평가 보고서 생성
  -> MinIO에 pre-evaluations/{preEvaluationId}/report.json 업로드
  -> reportKey로 PATCH /internal/pre-evaluations/{preEvaluationId}/complete 호출
  -> RabbitMQ ack
```

실패 시:

```text
PRE_EVALUATION_GENERATE 메시지 수신
  -> 사전 평가 보고서 생성 실패
  -> PATCH /internal/pre-evaluations/{preEvaluationId}/fail 호출
  -> RabbitMQ ack
```

### 7-9. 사전 평가 채팅 API 예시 흐름

```text
POST /pre-evaluations/chat 요청 수신
  -> preEvaluationId와 임시 특허 입력 정보 확인
  -> history와 message를 기반으로 AI 답변 생성
  -> { "message": "..." } 응답 반환
```

실패 시:

```text
POST /pre-evaluations/chat 요청 수신
  -> AI 답변 생성 실패
  -> 4xx 또는 5xx 응답 반환
```

### 7-10. 배포 및 실행 방식

AI worker는 배포 환경에서 별도 서비스로 실행하는 것을 권장합니다.

Docker Compose 예시 구조:

```text
services:
  skipa-backend
  rabbitmq
  minio
  ai-report-worker
  ai-patent-extract-worker
  ai-pre-evaluation-worker
  ai-pre-evaluation-api
```

Kubernetes 사용 시 권장 구조:

```text
Deployment: ai-report-worker
Deployment: ai-patent-extract-worker
Deployment: ai-pre-evaluation-worker
Deployment: ai-pre-evaluation-api
Secret: INTERNAL_API_KEY, RabbitMQ credentials, MinIO credentials
ConfigMap: queue names, backend URL, MinIO endpoint
```

worker replica를 늘리면 같은 queue를 여러 consumer가 나눠 처리할 수 있습니다.

단, 같은 작업이 중복 처리될 수 있으므로 worker는 중복 메시지 가능성을 고려해야 합니다.

### 7-11. 로컬 개발 실행

백엔드 `local` profile은 RabbitMQ/MinIO 없이 동작할 수 있는 local 대체 구현을 포함합니다.

하지만 AI 서버 worker 연동을 실제로 테스트하려면 로컬에서도 RabbitMQ와 MinIO를 실행하는 것을 권장합니다.

로컬 연동 테스트에 필요한 구성:

```text
RabbitMQ
MinIO
Backend non-local profile 또는 RabbitMQ/MinIO가 활성화된 실행 환경
AI worker process
AI pre-evaluation chat API process
```

백엔드가 `local` profile로 실행되면 RabbitMQ 메시지가 실제 queue로 발행되지 않을 수 있습니다.

AI worker와 end-to-end 연동을 확인하려면 RabbitMQ publisher와 MinIO storage가 활성화된 profile로 백엔드를 실행해야 합니다.
