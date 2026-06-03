"""평가 프로토타입에서 공통으로 사용하는 파일시스템 경로입니다.

실행 코드는 ``src`` 아래에 두고, 샘플 데이터·정적 리소스·생성 산출물은
import 가능한 코드 트리 밖에 분리해 둡니다.
"""

from __future__ import annotations

import os
from pathlib import Path


SRC_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = SRC_DIR.parent
PROJECT_ROOT = ROOT_DIR.parent

_RAW_DATA_ROOT = os.getenv("SKIPA_DATA_ROOT") or os.getenv("DATA_ROOT")
DATA_ROOT = Path(_RAW_DATA_ROOT).expanduser() if _RAW_DATA_ROOT else PROJECT_ROOT / "data"
if not DATA_ROOT.is_absolute():
    # Relative env values are written from eval_logic's point of view
    # (for example DATA_ROOT=../data), while the default remains repo/data.
    DATA_ROOT = (ROOT_DIR / DATA_ROOT).resolve()

CHATBOT_DATA_DIR = DATA_ROOT
PATENT_DATA_DIR = DATA_ROOT / "mapped_patent_reports"


def _resolve_data_child(raw: str | None, default: Path) -> Path:
    candidate = Path(raw).expanduser() if raw else default
    if not candidate.is_absolute():
        candidate = (ROOT_DIR / candidate).resolve()
    return candidate

RESOURCES_DIR = ROOT_DIR / "resources"
SAMPLES_DIR = ROOT_DIR / "samples"
SAMPLE_INPUT_DIR = SAMPLES_DIR / "input"
SAMPLE_DATA_DIR = SAMPLES_DIR / "data"
SAMPLE_PATENT_DOCUMENT_DIR = SAMPLES_DIR / "patent_documents"

ARTIFACTS_DIR = DATA_ROOT / "artifacts"
ARTIFACT_OUTPUT_DIR = ARTIFACTS_DIR / "output"
ARTIFACT_REPORT_DIR = ARTIFACTS_DIR / "report"
ARTIFACT_CRAWLING_DIR = ARTIFACTS_DIR / "crawling"
ARTIFACT_CACHE_DIR = ARTIFACTS_DIR / "cache"
ARTIFACT_UPLOAD_DIR = ARTIFACTS_DIR / "uploads"

API_TEST_DIR = DATA_ROOT / "api_test"
API_TEST_INPUT_DIR = API_TEST_DIR / "input"
API_TEST_INPUT_UPLOAD_DIR = API_TEST_INPUT_DIR / "uploads"
API_TEST_PDF_UPLOAD_DIR = API_TEST_INPUT_DIR / "pdf"
API_TEST_EXTRACTED_INPUT_DIR = API_TEST_INPUT_DIR / "extracted"
API_TEST_OUTPUT_DIR = API_TEST_DIR / "output"
API_TEST_REPORT_OUTPUT_DIR = API_TEST_OUTPUT_DIR / "reports"

# Keep the report/evaluation side on the same data tree that the chatbot uses.
# Older local setups may still pass BUSINESS_RAG_DATA_DIR explicitly; otherwise
# the shared business RAG root is data/business.
BUSINESS_RAG_DATA_DIR = _resolve_data_child(
    os.getenv("BUSINESS_ROOT") or os.getenv("BUSINESS_RAG_DATA_DIR"),
    DATA_ROOT / "business",
)
BUSINESS_RAG_RAW_DIR = BUSINESS_RAG_DATA_DIR / "raw"
BUSINESS_RAG_PROCESSED_DIR = BUSINESS_RAG_DATA_DIR / "processed"
BUSINESS_RAG_INDEX_DIR = BUSINESS_RAG_DATA_DIR / "index"
