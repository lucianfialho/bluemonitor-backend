# 🐳 DOCKERFILE ROBUSTO PARA RAILWAY - BlueMonitor
# Com correções para Hugging Face cache e permissões

# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="${PYTHONPATH}:/app" \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    ENVIRONMENT=production

# 🔧 RAILWAY + HUGGING FACE: Configurar cache directories
ENV HF_HOME=/app/models \
    TRANSFORMERS_CACHE=/app/models/transformers \
    HF_DATASETS_CACHE=/app/models/datasets \
    HUGGINGFACE_HUB_CACHE=/app/models/hub \
    TOKENIZERS_PARALLELISM=false

# Install system dependencies (otimizado para Railway + AI models)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Set working directory
WORKDIR /app

# 🚀 RAILWAY ROBUST: Create all necessary directories with correct permissions
RUN mkdir -p /app/logs \
    /app/models \
    /app/models/transformers \
    /app/models/datasets \
    /app/models/hub \
    /app/temp \
    && chmod -R 755 /app/logs \
    && chmod -R 755 /app/models \
    && chmod -R 755 /app/temp

# Copy poetry files first (Docker cache optimization)
COPY pyproject.toml poetry.lock* ./

# 🚀 RAILWAY OPTIMIZATION: Install dependencies with production settings
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-interaction --no-ansi --only=main

# Copy the rest of the application
COPY . .

# 🔧 RAILWAY SPECIFIC: Install app in production mode
RUN poetry install --no-interaction --no-ansi --only=main

# 🔒 SECURITY: Create non-root user but maintain access to cache directories
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 --no-create-home --disabled-password --group appuser && \
    chown -R appuser:appuser /app

# 🚀 HUGGING FACE: Pre-create cache structure and set permissions
RUN mkdir -p /app/models/transformers/models--facebook--bart-large-cnn \
    && mkdir -p /app/models/transformers/models--cardiffnlp--twitter-xlm-roberta-base-sentiment \
    && mkdir -p /app/models/transformers/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2 \
    && chown -R appuser:appuser /app/models \
    && chmod -R 755 /app/models

# Switch to non-root user
USER appuser

# 🌐 RAILWAY: Expose port (Railway will auto-detect)
EXPOSE 8000

# 🚀 RAILWAY OPTIMIZED: Health check with timeout
HEALTHCHECK --interval=30s --timeout=15s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 🎯 RAILWAY SPECIFIC: Command with production optimizations + AI model support
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--loop", "uvloop", "--access-log"]