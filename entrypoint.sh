#!/bin/bash
set -e

# Aplica migrações (Alembic via flask_migrate) e semeia dados iniciais.
# Não usa o CLI `flask db` (que está quebrado neste ambiente); usa a API Python.
echo "Aplicando migrações do banco de dados..."
python migrate_db.py

# Inicia a aplicação usando gunicorn.
# Worker class 'gthread': cada worker tem várias threads, então enquanto uma
# thread espera o ffmpeg (subprocess libera o GIL) ou o upload ao Cloudinary
# (I/O de rede), as outras threads continuam atendendo requisições. Isso evita
# que o app "congele" para todo mundo quando alguém posta um vídeo pesado.
# Auto-dimensiona pelos núcleos da VPS; ajustável via env sem mudar código.
WORKERS="${GUNICORN_WORKERS:-$(( $(nproc) + 1 ))}"
THREADS="${GUNICORN_THREADS:-4}"
TIMEOUT="${GUNICORN_TIMEOUT:-300}"

echo "Iniciando a aplicação (workers=$WORKERS threads=$THREADS timeout=${TIMEOUT}s)..."
exec gunicorn --bind 0.0.0.0:5000 \
    --worker-class gthread --workers "$WORKERS" --threads "$THREADS" \
    --timeout "$TIMEOUT" --graceful-timeout 30 --keep-alive 5 \
    --max-requests 800 --max-requests-jitter 200 \
    --access-logfile - --error-logfile - \
    app:app
