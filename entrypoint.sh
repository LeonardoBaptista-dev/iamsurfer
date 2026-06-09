#!/bin/bash
set -e

# Aplica migrações (Alembic via flask_migrate) e semeia dados iniciais.
# Não usa o CLI `flask db` (que está quebrado neste ambiente); usa a API Python.
echo "Aplicando migrações do banco de dados..."
python migrate_db.py

# Inicia a aplicação usando gunicorn
echo "Iniciando a aplicação..."
exec gunicorn --bind 0.0.0.0:5000 --workers 3 --timeout 120 app:app
