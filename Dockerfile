FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema MÍNIMAS
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python (sem warnings de root)
RUN pip install --no-cache-dir --root-user-action=ignore --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --root-user-action=ignore \
    flask==2.3.3 \
    flask-cors==4.0.0 \
    pg8000==1.30.5 \
    requests==2.31.0 \
    websocket-client==1.7.0 \
    numpy==1.24.3 \
    python-dotenv==1.0.0 \
    tqdm==4.65.0

# PyTorch CPU only
RUN pip install --no-cache-dir --root-user-action=ignore torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu

# EvoTorch e dependências
RUN pip install --no-cache-dir --root-user-action=ignore cma==4.4.4 gym==0.26.2 packaging pandas && \
    pip install --no-cache-dir --root-user-action=ignore evotorch==0.3.0 --no-deps

# Ray
RUN pip install --no-cache-dir --root-user-action=ignore ray==2.9.0

# Limpeza
RUN pip cache purge && apt-get clean

# Copiar código
COPY . .

# EXPOR a porta (importante!)
EXPOSE ${PORT:-5000}

# Healthcheck explícito
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

# Comando para iniciar (com timeout maior para carregar modelos)
CMD ["sh", "-c", "python main.py"]
