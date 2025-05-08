#!/bin/bash
set -e

# Executar migrações do banco de dados
echo "Executando migrações do banco de dados..."
./migrate.sh

# Iniciar a aplicação usando gunicorn
echo "Iniciando a aplicação..."
exec gunicorn --bind 0.0.0.0:5000 app:app 