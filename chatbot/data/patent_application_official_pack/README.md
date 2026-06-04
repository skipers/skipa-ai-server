# 특허 출원 공식 자료 다운로드 팩

생성일: 2026-06-01

이 폴더는 한국 특허 출원 준비를 위해 공식 출처 중심으로 정리한 자료 묶음입니다.

## 포함 파일

- `official_sources.csv` / `official_sources.json`: 공식 출처 데이터셋
- `official_download_links.html`: 공식 문서·PDF 다운로드 링크 모음
- `patent_application_process_guide.md`: 특허 출원 절차와 실무 체크리스트
- `prior_art_search_workflow.md`: 선행기술조사 절차
- `patent_rejection_failure_response.md`: 거절/실패 후 대응 절차
- `patent_sources.xlsx`: 엑셀형 데이터셋

## 중요한 안내

실행환경에서 정부/공공기관 PDF 원문을 직접 파일로 내려받는 작업은 DNS/접속 제한으로 실패했습니다. 대신 각 공식 문서의 원문 페이지와 직접 다운로드 URL을 데이터 파일과 HTML 파일에 저장했습니다. 링크를 브라우저에서 열면 원문 PDF/문서를 내려받을 수 있습니다.

## 가장 먼저 볼 공식 자료

1. 특허로 특허출원가이드
2. 2026 지식재산권의 손쉬운 이용
3. 특허·실용신안 심사기준
4. KIPRIS 검색도움말
5. CEO·연구자를 위한 특허출원 전략

## 실패특허 케이스 관리

출원 도우미 채팅은 실패특허 원본 PDF가 있는 케이스를 먼저 선택해야 시작됩니다.
케이스는 `failed_patent/{case_id}` 단위로 저장되고, 서로 다른 실패특허는 절대 같은
vectorstore에 섞지 않습니다.

```text
failed_patent/{case_id}/
  input/              # 실패특허 원본 PDF
  rejection/          # 선택: 거절의견서, 사유서, 사람이 입력한 실패 사유
  reports/            # 선택: 특허 재평가 API 결과, 피드백 보고서
  index/vectorstore/  # 해당 실패특허 1건 전용 검색 인덱스
  metadata.json
```

답변은 항상 공용 공식팩 vectorstore와 현재 선택한 `failed_patent/{case_id}` 전용
vectorstore만 함께 사용합니다. 공용 공식팩 vectorstore에는 `downloads/`와 아래 4개 Markdown만
들어갑니다.

- `patent_application_process_guide.md`
- `patent_rejection_failure_response.md`
- `patent_rejection_notice_original_sources.md`
- `prior_art_search_workflow.md`

새 재평가 보고서는 `POST /api/v1/application/failed-patents/{case_id}/report/generate`
또는 CLI `--mode application-case-generate`로 생성합니다. 결과는 같은 케이스의 `reports/`에
저장되고, 그 케이스 index만 refresh합니다. 다른 실패특허 폴더나 공용 공식팩 index에는
절대 섞지 않습니다.
