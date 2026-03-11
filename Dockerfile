FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema MÍNIMAS
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar em camadas para melhor cache
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Camada 1: Dependências leves (sempre em cache)
RUN pip install --no-cache-dir \
    flask==2.3.3 \
    flask-cors==4.0.0 \
    pg8000==1.30.5 \
    requests==2.31.0 \
    websocket-client==1.7.0 \
    numpy==1.24.3 \
    python-dotenv==1.0.0 \
    tqdm==4.65.0

# Camada 2: PyTorch (CPU only - mais leve)
RUN pip install --no-cache-dir torch==2.1.0 --index-url https://download.pytorch.org/whl/cpu

# Camada 3: EvoTorch e dependências
RUN pip install --no-cache-dir cma==4.4.4 gym==0.26.2 packaging pandas && \
    pip install --no-cache-dir evotorch==0.3.0 --no-deps

# Camada 4: Ray
RUN pip install --no-cache-dir ray==2.9.0

# Limpeza
RUN pip cache purge && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . .

CMD ["python", "main.py"]
