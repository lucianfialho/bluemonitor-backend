FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Instalar apenas o essencial
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry com timeout maior
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

WORKDIR /app

# Copiar arquivos Poetry
COPY pyproject.toml poetry.lock* ./

# Configurar Poetry para ambiente Railway
RUN poetry config virtualenvs.create false && \
    poetry config installer.max-workers 1 && \
    poetry config installer.parallel false

# Instalar apenas dependências principais (SEM dev dependencies)
RUN poetry install --no-root --only=main --no-interaction --no-ansi --timeout=600

# Copiar aplicação
COPY . .

# Usuário não-root
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 --no-create-home --disabled-password --group appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]