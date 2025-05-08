#!/bin/bash
set -e

# Aguardar o banco de dados
echo "Aguardando o banco de dados..."
# (código para aguardar o banco)

# Aplicar migrações
echo "Aplicando migrações do banco de dados..."
flask db upgrade

# Iniciar a aplicação
echo "Iniciando a aplicação..."
exec gunicorn -b 0.0.0.0:$PORT app:app 