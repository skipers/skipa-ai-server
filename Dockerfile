FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app:/app/eval_logic/src \
    HF_HOME=/models/huggingface \
    TRANSFORMERS_CACHE=/models/huggingface \
    MPLCONFIGDIR=/tmp/matplotlib \
    KMP_DUPLICATE_LIB_OK=TRUE

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
    /app/eval_logic/data/runtime_artifacts \
    /models/huggingface \
    /tmp/matplotlib

EXPOSE 8000 8001

CMD ["python", "-m", "uvicorn", "chatbot.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
