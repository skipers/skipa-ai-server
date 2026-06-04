# 특허 출원 공식 자료팩

이 폴더는 특허 출원 도우미 챗봇이 사용하는 공용 공식 자료팩과 실패특허 case 데이터를 관리합니다.

## 폴더 역할

```text
patent_application_official_pack/
  downloads/                                # 공식 PDF/웹문서 원문
  official_sources.csv
  official_sources.json
  official_download_links.html
  patent_sources.xlsx

  patent_application_process_guide.md       # 처음 출원 절차와 체크리스트
  patent_rejection_failure_response.md      # 거절/실패 후 대응 절차
  patent_rejection_notice_original_sources.md
  prior_art_search_workflow.md

  preprocessed/
    preprocess_report.md

  index/
    vectorstore/                            # 공용 공식팩 index

  failed_patent/
    <registration_number>_failed/
      input/                                # 실패특허 원본 PDF
      rejection/                            # 선택: 거절의견서/사유서
      reports/                              # 재평가 보고서, latest_report.*
      index/vectorstore/                    # 해당 실패특허 1건 전용 index
      metadata.json
```

## 공용 공식팩 index

공용 공식팩 index에는 아래 자료만 들어갑니다.

- `downloads/`
- `patent_application_process_guide.md`
- `patent_rejection_failure_response.md`
- `patent_rejection_notice_original_sources.md`
- `prior_art_search_workflow.md`

이 index는 출원 절차, 전자출원, 서식, 수수료, 선행기술조사, 거절 대응의 제도적 기준을 제공하는 용도입니다.

## 실패특허 case index

출원 도우미에서 실패/거절/평가 원인 분석을 하려면 먼저 실패특허 원본 PDF가 필요합니다. 업로드된 파일은 등록번호 기준 폴더로 저장됩니다.

```text
failed_patent/10-1959619_failed/
  input/
    10-1959619_failed.pdf
  rejection/
    rejection_notice.pdf
    rejection_reason.txt
  reports/
    latest_report.json
    latest_report.md
    latest_report.html
  index/vectorstore/
  metadata.json
```

case index에는 해당 실패특허 1건의 데이터만 들어갑니다.

- 실패특허 원본 PDF
- 선택 업로드한 거절의견서/사유서
- 해당 case의 최신 재평가 보고서

다른 실패특허, 다른 `mapped_patent_reports`, 다른 case 보고서는 절대 섞지 않습니다.

## 출원 도우미 답변 기준

출원 도우미는 질문 유형에 따라 검색 대상을 나눕니다.

| 질문 유형 | 우선 검색 대상 |
| --- | --- |
| 처음 출원 순서 | 공용 공식팩 index |
| 서식/전자출원/수수료 | 공용 공식팩 index |
| 명세서/청구항 작성 | 공용 공식팩 index + 필요 시 선택 case |
| 선행기술조사 | 공용 공식팩 index + KIPRIS/web 보강 |
| 거절/실패 원인 | 선택 실패특허 case index |
| “등록하려면 뭘 고쳐야 해?” | 선택 case index + 공용 공식팩 index |
| 시장/전략/해외출원 | 공용 공식팩 index + KOSIS/Tavily 보강 |

## 주요 API

```text
GET  /api/v1/application/status
POST /api/v1/application/preprocess
POST /api/v1/application/index/refresh
POST /api/v1/application/chat

GET  /api/v1/application/failed-patents
POST /api/v1/application/failed-patents/upload
GET  /api/v1/application/failed-patents/{case_id}
POST /api/v1/application/failed-patents/{case_id}/report/generate
POST /api/v1/application/failed-patents/{case_id}/report/save
POST /api/v1/application/failed-patents/{case_id}/index/refresh
POST /api/v1/application/failed-patents/{case_id}/chat
```

## CLI

```bash
cd /Users/kgw/skipers-ai

# 공용 공식팩 전처리와 index 갱신
bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-preprocess

# 실패특허 case 생성
bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-case \
  --original-pdf "/path/to/failed_patent.pdf" \
  --rejection-file "/path/to/rejection_notice.pdf"

# 실패특허 보고서 생성 후 해당 case index만 갱신
bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-case-generate \
  --case-id "10-1959619_failed"

# 이미 생성된 보고서를 case에 저장하고 해당 case index만 갱신
bash chatbot/scripts/preprocess_chatbot_data.sh --mode application-case-report \
  --case-id "10-1959619_failed" \
  --report-path "/path/to/report.json"
```

## 공식 자료 안내

실행환경에 따라 정부/공공기관 PDF 원문 다운로드가 제한될 수 있습니다. 이 경우 `official_sources.json`, `official_sources.csv`, `official_download_links.html`에 원문 페이지와 다운로드 URL을 남기고, 다운로드 가능한 파일만 `downloads/`에 저장합니다.

우선 확인할 자료:

1. 특허로 특허출원가이드
2. 2026 지식재산권의 손쉬운 이용
3. 특허·실용신안 심사기준
4. KIPRIS 검색도움말
5. CEO·연구자를 위한 특허출원 전략

## 답변 품질 원칙

- “처음 출원할 때 순서” 질문에는 출원 준비 순서를 먼저 답합니다.
- “거절/실패” 질문에는 현재 선택한 실패특허 case의 원문과 보고서를 먼저 봅니다.
- “평가가 어떻게 나왔어?” 질문에는 `latest_report`를 근거로 평가 요약, 문제 원인, 보정 방향을 설명합니다.
- “어떻게 하면 등록 가능성이 올라가?” 질문에는 청구항 보정, 명세서 보강, 선행기술 차별화, 의견서 제출 전략을 분리해서 답합니다.
- 답변 근거는 공식팩 파일명, 실패특허 원문, 보고서 섹션명을 제목으로 표시합니다.
