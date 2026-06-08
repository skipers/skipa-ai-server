# Chatbot Data Layout

`chatbot/data`는 챗봇 앱이 직접 관리하는 전용 데이터 루트입니다. 특허 원문/보고서처럼 `eval_logic`과 함께 쓰는 공유 DB는 루트 `data` 폴더에 있고, 출원 공식팩과 챗봇 검증 산출물은 이 폴더 아래에 둡니다.

## 폴더 역할

```text
/Users/kgw/skipers-ai/data/
  patent/
    <patent_id>/
      patent.pdf            # 특허 원문 PDF
      parsed.json           # 표준 input JSON
      report.json           # eval_logic 보고서 JSON
  Qdrant: skipa_shared_patents
  wiki/                     # 분야별 wiki gate와 approved_context
  pre_application_cases/    # 출원 전 사전평가 케이스

/Users/kgw/skipers-ai/chatbot/data/
  patent_application_official_pack/
    downloads/              # 공식 출원 자료 PDF/웹 문서
    patent_application_process_guide.md
    patent_rejection_failure_response.md
    patent_rejection_notice_original_sources.md
    prior_art_search_workflow.md
    index/qdrant/           # 공용 공식팩 Qdrant manifest
    failed_patent/
      <registration_number>_failed/
        input/              # 실패특허 원본 PDF
        rejection/          # 선택 거절의견서/사유서
        reports/            # latest_report.* 및 생성 보고서
        index/qdrant/       # 해당 실패특허 1건 전용 Qdrant manifest
        metadata.json

  artifacts/
    chatbot_business_tests/ # 챗봇 기능/사업부 시나리오 테스트 결과
```

## 공유 특허 DB

일반 특허 챗봇과 보고서 생성 로직은 루트 `data/patent/<patent_id>`를 기준으로 원문과 보고서를 공유합니다.

- `patent.pdf`: 특허 원문
- `parsed.json`: 전처리된 표준 특허 입력
- `report.json`: 평가/재평가 보고서
- Qdrant `skipa_shared_patents`: 특허 원문과 보고서 기반 통합 검색 index

`chatbot/data/mapped_patent_reports`는 호환용 legacy RAG 경로로 남아 있을 수 있지만, 신규 공유 기준은 루트 `data/patent/<patent_id>`입니다.

MinIO를 사용하는 환경에서는 `s3://skipa/patent/`를 이 경로로 동기화합니다. UI의 데이터 탭에서 `MinIO 상태`와 `MinIO에서 가져오기` 버튼으로 확인/동기화할 수 있습니다.

## wiki와 web 검색

wiki는 루트 `data/wiki/<topic_slug>`에 저장됩니다. 특허 원문/보고서 vectorstore에 섞지 않고 외부검색 전 gate로만 사용합니다.

```text
data/wiki/<topic_slug>/
  web_search_data/          # Tavily/web 검색 draft Markdown
  approved_context.md       # 감사 후 승인된 자연어 context
  draft_index.json
  Qdrant collection: skipa_wiki_topic_<topic_slug>
```

동작 규칙:

- 내부 특허 질문은 먼저 Qdrant `skipa_shared_patents`와 해당 특허 보고서/원문을 검색합니다.
- 최신 시장, 외부 자료, 웹 근거가 필요한 질문만 wiki gate로 넘어갑니다.
- wiki에 충분한 승인 근거가 있으면 web 검색을 생략합니다.
- wiki가 부족하면 web 검색 결과를 draft로 저장하고, 감사 후 승인된 내용만 vectorstore에 반영합니다.
- 매일 00:00 KST 재색인은 MinIO/local cache와 승인 wiki를 기준으로 Qdrant collection을 재빌드합니다.

## 출원 도우미 데이터

출원 도우미는 두 index를 함께 봅니다.

- 공용 공식팩 index: `downloads/`와 4개 guide Markdown
- 실패특허 case index: 현재 선택한 실패특허 원본 PDF, 선택 사유서, 최신 보고서만 포함

여러 실패특허 case는 절대 같은 vectorstore에 섞지 않습니다. 사용자가 `10-1959619_failed`를 선택하면 그 case 폴더와 공용 공식팩만 검색합니다.

## artifacts 정책

챗봇 기능 테스트와 대량 질의 검증 결과는 `chatbot/data/artifacts`에 저장합니다.

```text
chatbot/data/artifacts/chatbot_business_tests/
  final_status_*/
  patent_chat_*/
  application_chat_*/
```

루트 `data/artifacts`는 사용하지 않습니다. 기존 명령이나 스크립트가 `data/artifacts/...`를 output dir로 받아도 `chatbot/data/artifacts/...`로 리다이렉트되도록 관리합니다.

## eval_logic과의 연결

`eval_logic`은 API 테스트와 런타임 산출물을 자체적으로 `eval_logic/data`에 저장합니다.

```text
eval_logic/data/api_test/
eval_logic/data/runtime_artifacts/
```

챗봇에서 계속 검색해야 하는 보고서는 최종적으로 루트 `data/patent/<patent_id>/report.json` 또는 출원 도우미 실패특허 case의 `reports/`에 저장되어야 합니다. 출원 도우미의 실패특허 보고서 생성 API는 보고서 생성 후 해당 case 폴더에 저장하고 그 case vectorstore만 refresh합니다.

## 전처리와 refresh

```bash
cd /Users/kgw/skipers-ai

# 전체 상태
bash chatbot/scripts/preprocess_chatbot_data.sh --mode status

# 공유 특허 DB index 생성/갱신은 API/Swagger에서 실행
curl -X POST http://127.0.0.1:8001/api/v1/chatbot/preprocess/run \
  -H "Content-Type: application/json" \
  -d '{"mode":"shared_index"}'

# wiki 자동 감사 후 승인 데이터만 반영
bash chatbot/scripts/preprocess_chatbot_data.sh --mode auto-audit

# Kubernetes CronJob과 같은 전체 nightly 작업
bash chatbot/scripts/preprocess_chatbot_data.sh --mode nightly-reindex

# 출원 공식팩 전처리
bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-preprocess

# 실패특허 case 생성
bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-case \
  --original-pdf "/path/to/failed.pdf" \
  --rejection-file "/path/to/rejection.pdf"

# 실패특허 case 보고서 생성 및 case index refresh
bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-case-generate \
  --case-id "10-1959619_failed"
```

## 커밋 주의

커밋하면 안 되는 항목:

```text
chatbot/.env
chatbot/logs/
대용량 비공개 고객 원문
API key가 포함된 임시 파일
```

공식팩 guide Markdown, 샘플 성격의 공개 자료, 발표용 README/API 문서는 커밋 대상입니다.
