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

# Worker de processamento de mídia (RQ). Só sobe se houver Redis configurado;
# sem REDIS_URL, os uploads são processados de forma síncrona (comportamento
# antigo). Roda no mesmo container (compartilha o disco com a web, então lê os
# arquivos temporários gravados pelo request). Reinicia sozinho se cair.
if [ -n "$REDIS_URL" ]; then
    echo "Iniciando worker de mídia (RQ)..."
    ( while true; do
        rq worker iamsurfer-media --url "$REDIS_URL" || true
        echo "rq worker encerrou; reiniciando em 3s..."
        sleep 3
      done ) &
fi

echo "Iniciando a aplicação (workers=$WORKERS threads=$THREADS timeout=${TIMEOUT}s)..."
exec gunicorn --bind 0.0.0.0:5000 \
    --worker-class gthread --workers "$WORKERS" --threads "$THREADS" \
    --timeout "$TIMEOUT" --graceful-timeout 30 --keep-alive 5 \
    --max-requests 800 --max-requests-jitter 200 \
    --access-logfile - --error-logfile - \
    app:app
