import os
from core.env import load_runtime_env
from core.paths import BUSINESS_RAG_DATA_DIR
from providers.llm import embedding_model, provider, report_model

load_runtime_env()

DATA_DIR = BUSINESS_RAG_DATA_DIR
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INDEX_DIR = DATA_DIR / "index"

SKAX_BASE_URL = os.getenv("SKAX_BASE_URL", "https://www.skax.com")
CRAWL_DELAY = float(os.getenv("CRAWL_DELAY", "1.5"))
MAX_PAGES_PER_KEYWORD = int(os.getenv("MAX_PAGES_PER_KEYWORD", "5"))

EMBEDDING_MODEL = embedding_model("BUSINESS_RAG_EMBEDDING_MODEL")
LLM_MODEL = report_model("BUSINESS_RAG_LLM_MODEL")
INDEX_FILE_PREFIX = os.getenv(
    "BUSINESS_RAG_INDEX_PREFIX",
    "opensource_" if provider() in {"opensource", "open_source", "openai_compatible", "vllm", "sglang"} else "",
)
TOP_K = int(os.getenv("TOP_K", "5"))
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "300"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# 하이브리드 검색 설정
CANDIDATE_K_MULTIPLIER = int(os.getenv("CANDIDATE_K_MULTIPLIER", "3"))
MMR_LAMBDA = float(os.getenv("MMR_LAMBDA", "0.6"))  # 높을수록 관련성 우선, 낮을수록 다양성 우선

PRODUCTS = [
    "로보어드바이저", "ChainZ", "EAP", "DiFlow", "RE100",
    "MarketCaster", "AccuInsight+", "Aibril", "mTworks",
    "Aiden", "AKS", "iclue-tdmd", "WAU", "watz eye",
    "containment", "nexcore", "TOMS",
]
