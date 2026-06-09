# 20260531_181425_20260529_144101_pdf.pdf_155943_676781 실패특허 재평가 보고서

## 질문/답변

실패특허 원본 PDF를 특허 재평가 에이전트에 전달해 생성한 출원 도우미용 보고서입니다.

## 평가 요약

- Case ID: 20260531_181425_20260529_144101_pdf.pdf_155943_676781
- Status: partial_success
- Workflow: langgraph
- Elapsed seconds: 0.01
- Verification grade: -
- Verification score: -
- Human review required: -

## 재평가 보고서 핵심 내용

{ "status": "partial_success", "workflow_type": "langgraph", "elapsed_seconds": 0.01, "validation": { "valid": false, "errors": [ "patent_id 또는 meta.registration_number가 필요합니다.", "meta.title 또는 title이 필요합니다." ], "patent_id": "", "title": "", "has_claims": false, "has_description": false, "has_market_data": false, "has_kipris_data": false }, "valuation": null, "similar_analysis": null, "report": null, "report_verification": null, "human_reviews": [ { "node": "supervisor:evidence", "severity": "high", "reason": "증거 수집 단계에서 오류가 발생했습니다.", "status": "flagged", "details": { "errors": [ "PDF 메타데이터 추출 실패: No module named 'pdfplumber'", "사업화 현황 RAG 추정 실패: No module named 'rank_bm25'" ] } }, { "node": "supervisor:validation", "severity": "high", "reason": "입력 검증에 실패했습니다.", "status": "flagged", "details": { "errors": [ "patent_id 또는 meta.registration_number가 필요합니다.", "meta.title 또는 title이 필요합니다." ], "validation": { "valid": false, "errors": [ "patent_id 또는 meta.registration_number가 필요합니다.", "meta.title 또는 title이 필요합니다." ], "patent_id": "", "title": "", "has_claims": false, "has_description": false, "has_market_data": false, "has_kipris_data": false } } } ], "human_review_pending": null, "interrupts": [], "node_trace": [ { "node": "supervisor", "status": "success", "elapsed_seconds": 0.0, "message": "next=collect_evidence" }, { "node": "collect_evidence", "status": "error", "elapsed_seconds": 0.0, "message": "2개 세부 단계 실행" }, { "node": "supervisor:evidence", "status": "flagged", "elapsed_seconds": 0.0, "message": "증거 수집 단계에서 오류가 발생했습니다." }, { "node": "supervisor", "status": "success", "elapsed_seconds": 0.0, "message": "next=validate_input" }, { "node": "validate_input", "status": "error", "elapsed_seconds": 0.0, "message": "patent_id 또는 meta.registration_number가 필요합니다.; meta.title 또는 title이 필요합니다." }, { "node": "supervisor:validation", "status": "flagged", "elapsed_seconds": 0.0, "message": "입력 검증에 실패했습니다." }, { "node": "supervisor", "status": "success", "elapsed_seconds": 0.0, "message": "next=end" } ], "errors": [ "PDF 메타데이터 추출 실패: No module named 'pdfplumber'", "사업화 현황 RAG 추정 실패: No module named 'rank_bm25'" ] }

## 보고서 신뢰도/검증

검증 결과가 없습니다.

## 워크플로우 메타정보

{ "workflow_type": "langgraph", "elapsed_seconds": 0.01, "node_trace": [ { "node": "supervisor", "status": "success", "elapsed_seconds": 0.0, "message": "next=collect_evidence" }, { "node": "collect_evidence", "status": "error", "elapsed_seconds": 0.0, "message": "2개 세부 단계 실행" }, { "node": "supervisor:evidence", "status": "flagged", "elapsed_seconds": 0.0, "message": "증거 수집 단계에서 오류가 발생했습니다." }, { "node": "supervisor", "status": "success", "elapsed_seconds": 0.0, "message": "next=validate_input" }, { "node": "validate_input", "status": "error", "elapsed_seconds": 0.0, "message": "patent_id 또는 meta.registration_number가 필요합니다.; meta.title 또는 title이 필요합니다." }, { "node": "supervisor:validation", "status": "flagged", "elapsed_seconds": 0.0, "message": "입력 검증에 실패했습니다." }, { "node": "supervisor", "status": "success", "elapsed_seconds": 0.0, "message": "next=end" } ], "errors": [ "PDF 메타데이터 추출 실패: No module named 'pdfplumber'", "사업화 현황 RAG 추정 실패: No module named 'rank_bm25'" ] }

## 메타정보

- saved_at: 2026-06-04T15:59:45
- vectorstore_scope: selected_failed_patent_case_only
