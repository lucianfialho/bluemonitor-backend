FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/cache \
    TRANSFORMERS_CACHE=/app/cache \
    HUGGINGFACE_HUB_CACHE=/app/cache \
    HF_DATASETS_CACHE=/app/cache \
    TOKENIZERS_PARALLELISM=false

# Só o essencial
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependências python básicas primeiro
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretório de cache com permissões
RUN mkdir -p /app/cache && chmod -R 755 /app/cache

# Railway usa PORT dinâmico
EXPOSE $PORT

# Usar variável PORT da Railway
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT