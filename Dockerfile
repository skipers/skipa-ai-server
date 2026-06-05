FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/app/eval_logic/src \
    HF_HOME=/models/huggingface \
    TRANSFORMERS_CACHE=/models/huggingface \
    MPLCONFIGDIR=/tmp/matplotlib \
    KMP_DUPLICATE_LIB_OK=TRUE \
    INTENT_PROVIDER=openai \
    ANSWER_PROVIDER=openai \
    EMBEDDING_PROVIDER=openai \
    OPENAI_INTENT_MODEL=gpt-4.1-mini \
    OPENAI_ANSWER_MODEL=gpt-4.1 \
    OPENAI_VLM_MODEL=gpt-4.1-mini \
    OPENAI_EMBEDDING_MODEL=text-embedding-3-large \
    EMBEDDING_MODEL=text-embedding-3-large \
    ENABLE_OLLAMA_INTENT_FALLBACK=false \
    ENABLE_WEB_SEARCH=true \
    NIGHTLY_REINDEX_SCHEDULE="0 0 * * *" \
    WIKI_ROOT=/app/chatbot/data/wiki \
    PRE_EVAL_ROOT=/app/chatbot/data/pre_application_cases

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    chromium \
    chromium-driver \
    curl \
    fonts-nanum \
    fonts-noto-cjk \
    g++ \
    gcc \
    git \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libmagic1 \
    libnss3 \
    libsm6 \
    libxext6 \
    libxrender1 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-kor \
    wget \
  && rm -rf /var/lib/apt/lists/*

ARG INSTALL_LOCAL_EMBEDDINGS=false

COPY chatbot/requirements.txt /tmp/chatbot-requirements.txt
COPY eval_logic/requirements.txt /tmp/eval-logic-requirements.txt

RUN set -eux; \
    grep -vE '^(sentence-transformers|bert-score|langchain-huggingface)($|[<>=])' /tmp/chatbot-requirements.txt > /tmp/chatbot-docker-requirements.txt; \
    python -m pip install --upgrade pip setuptools wheel; \
    python -m pip install \
      -r /tmp/eval-logic-requirements.txt \
      -r /tmp/chatbot-docker-requirements.txt; \
    if [ "$INSTALL_LOCAL_EMBEDDINGS" = "true" ]; then \
      python -m pip install 'langchain-huggingface>=0.0.3' 'sentence-transformers>=3.0.0' 'bert-score>=0.3.13'; \
    fi

COPY . /app

RUN mkdir -p \
    /app/chatbot/logs/wiki_auditor \
    /app/chatbot/data \
    /app/chatbot/data/wiki/_global \
    /app/chatbot/data/pre_application_cases \
    /app/eval_logic/data/runtime_artifacts \
    /models/huggingface \
    /tmp/matplotlib \
  && chmod +x /app/docker/entrypoint.sh

EXPOSE 8000 8001

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["chatbot"]
