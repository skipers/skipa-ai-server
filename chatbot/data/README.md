# Chatbot Data Layout

이 폴더는 챗봇이 직접 읽는 데이터 루트입니다. 특허 챗봇, 출원 도우미, wiki 감사, vectorstore refresh는 이 폴더 아래의 구조를 기준으로 동작합니다.

## 전체 구조

```text
chatbot/data/
  mapped_patent_reports/
    <patent_id>/
      manifest.json
      original/
        pdf/
        input/
      reports/
        json/
        application_feedback/
      extracted/
        all_chunks.jsonl
      index/
        vectorstore/
      wiki/
        approved_context.md
        web_search_drafts/
        vectorstore/

  business/

  patent_application_official_pack/
    downloads/
    patent_application_process_guide.md
    patent_rejection_failure_response.md
    patent_rejection_notice_original_sources.md
    prior_art_search_workflow.md
    index/vectorstore/
    failed_patent/
      <registration_number>_failed/
        input/
        rejection/
        reports/
        index/vectorstore/
        metadata.json
```

## 특허 폴더 계약

특허 하나는 반드시 `mapped_patent_reports/<patent_id>` 하나의 폴더로 관리합니다.

```text
mapped_patent_reports/<patent_id>/
  original/pdf/       # 등록특허 원문 PDF
  original/input/     # eval_logic 또는 전처리에서 만든 표준 input JSON
  reports/json/       # 평가/재평가 보고서 JSON
  extracted/          # 원문/보고서 chunk, 표, 이미지, page metadata
  index/vectorstore/  # 원문+보고서 core vectorstore
  wiki/               # 특허별 승인 wiki와 wiki 전용 vectorstore
```

`latest.*` 파일은 최신 원문, 최신 입력, 최신 보고서를 가리키는 편의 파일입니다. timestamp 파일은 재현성을 위해 보관할 수 있습니다.

## core vectorstore와 wiki vectorstore

core vectorstore:

- 원문 PDF
- 표준 input JSON
- 평가 보고서 JSON
- 보고서 HTML/Markdown에서 추출한 chunk

wiki vectorstore:

- `wiki/approved_context.md`
- 감사 후 승인된 web 검색 보강 자료

중요한 규칙:

- wiki 문서는 core vectorstore에 넣지 않습니다.
- wiki는 외부검색이 필요한 질문에서 web 검색 전에만 확인합니다.
- web 검색 draft는 `wiki/web_search_drafts`에 저장되며, 감사/승인 전에는 wiki vectorstore에 반영하지 않습니다.
- 승인 wiki에 충분한 근거가 있으면 web 검색을 생략합니다.

## 출원 도우미 데이터

출원 도우미는 `patent_application_official_pack`을 기준으로 동작합니다.

공용 공식팩 vectorstore에 들어가는 데이터:

- `downloads/`
- `patent_application_process_guide.md`
- `patent_rejection_failure_response.md`
- `patent_rejection_notice_original_sources.md`
- `prior_art_search_workflow.md`

실패특허 case vectorstore에 들어가는 데이터:

- 해당 case의 실패특허 원본 PDF
- 선택 업로드된 거절의견서/사유서
- 해당 case의 최신 재평가 보고서(`reports/latest_report.*`)

여러 실패특허 case는 절대 같은 vectorstore에 섞지 않습니다. 출원 도우미 답변은 “공용 공식팩 index + 현재 선택한 실패특허 case index + 필요 시 web 검색”만 사용합니다.

## eval_logic과의 연결

`eval_logic`은 보고서 생성 결과를 `eval_logic/data/api_test` 또는 `eval_logic/data/runtime_artifacts`에 저장합니다. 챗봇에서 특허별로 계속 쓰려면 해당 보고서가 `mapped_patent_reports/<patent_id>/reports/json` 또는 실패특허 case의 `reports/`에 저장되어야 합니다.

출원 도우미의 실패특허 보고서 생성 API는 보고서 생성 후 자동으로 해당 case 폴더에 저장하고, 그 case vectorstore만 refresh합니다.

## 전처리와 refresh

```bash
cd /Users/kgw/skipers-ai

# 전체 상태
bash chatbot/scripts/preprocess_chatbot_data.sh --mode status

# 특허 원문/보고서 core와 wiki 승인 데이터 refresh
bash chatbot/scripts/preprocess_chatbot_data.sh --mode refresh

# 감사 후 승인 데이터만 wiki vectorstore에 반영
bash chatbot/scripts/preprocess_chatbot_data.sh --mode auto-audit

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

공식팩 guide Markdown, 샘플 성격의 공개 자료, 발표용 README는 커밋 대상입니다.
