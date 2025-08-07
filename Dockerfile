FROM python:3.11-slim

# Instalar dependências necessárias para o psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar requirements e instalar dependências primeiro (para melhor utilização de cache)
COPY requirements.txt .


# Atualizar pip, setuptools e wheel para garantir build correto do psycopg2
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Instalar SQLAlchemy explicitamente primeiro (versão 1.4.46 para compatibilidade com Flask-SQLAlchemy 2.5.1)
RUN pip install --no-cache-dir SQLAlchemy==1.4.46

# Instalar as demais dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Tornar o script de migração executável
RUN chmod +x migrate.sh

# Variáveis de ambiente
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Criar diretórios necessários
RUN mkdir -p static/uploads/posts static/uploads/profile_pics static/uploads/spots

# Expor porta
EXPOSE 5000

# Script de inicialização para executar migrações e depois iniciar a aplicação
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Executar usando o script de entrada
CMD ["/entrypoint.sh"] 