#!/bin/bash
# Script para executar migrações do banco de dados no Render

echo "Iniciando migrações do banco de dados..."

# Espera o banco de dados ficar disponível
python -c "
import time
import psycopg2
import os

db_url = os.environ.get('DATABASE_URL')
max_retries = 5
retry_count = 0

while retry_count < max_retries:
    try:
        print(f'Tentativa {retry_count + 1} de conectar ao banco de dados...')
        conn = psycopg2.connect(db_url)
        conn.close()
        print('Conexão com o banco de dados estabelecida!')
        break
    except psycopg2.OperationalError as e:
        print(f'Erro ao conectar ao banco de dados: {e}')
        retry_count += 1
        if retry_count < max_retries:
            print(f'Tentando novamente em 5 segundos...')
            time.sleep(5)
        else:
            print('Máximo de tentativas atingido. Continuando mesmo assim...')
"

# Executa as migrações
echo "Executando flask db upgrade..."
flask db upgrade

echo "Migrações concluídas!" 