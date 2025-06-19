FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HF_HOME=/tmp/models \
    TRANSFORMERS_CACHE=/tmp/models \
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

# Railway usa PORT dinâmico
EXPOSE $PORT

# Usar variável PORT da Railway
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT