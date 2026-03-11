# Dockerfile
FROM python:3.11-slim

# Instalar dependências do sistema (incluindo para TensorFlow)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar apenas requirements primeiro (para cache)
COPY requirements.txt .

# Instalar dependências Python (TensorFlow incluso)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar o resto do código
COPY . .

# Comando para rodar
CMD ["python", "main.py"]
