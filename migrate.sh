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

# Verificar se as tabelas já existem no banco de dados
python -c "
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

db_url = os.environ.get('DATABASE_URL')
try:
    conn = psycopg2.connect(db_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Consulta para verificar tabelas existentes
    cursor.execute(\"\"\"
        SELECT tablename FROM pg_catalog.pg_tables 
        WHERE schemaname = 'public'
    \"\"\")
    
    tables = cursor.fetchall()
    table_names = [table[0] for table in tables]
    
    if 'user' in table_names and 'post' in table_names:
        print('As tabelas principais já existem no banco de dados.')
        print('Pulando inicialização de migrações, apenas aplicando upgrades se houver.')
        exists = True
    else:
        print('Tabelas principais não encontradas no banco de dados.')
        exists = False
    
    cursor.close()
    conn.close()
    
    # Criar arquivo para comunicar com o script bash
    with open('/tmp/tables_exist', 'w') as f:
        f.write('yes' if exists else 'no')
    
except Exception as e:
    print(f'Erro ao verificar tabelas: {e}')
    # Em caso de erro, assumir que precisamos criar as tabelas
    with open('/tmp/tables_exist', 'w') as f:
        f.write('no')
"

# Lê o resultado da verificação
TABLES_EXIST=$(cat /tmp/tables_exist)

if [ "$TABLES_EXIST" = "yes" ]; then
    echo "Aplicando apenas possíveis atualizações de migração..."
    flask db stamp head || echo "Falha ao marcar migrações atuais, mas continuando..."
    flask db migrate -m "Automatic migration" || echo "Migração falhou, possivelmente sem alterações."
    flask db upgrade || echo "Upgrade falhou, mas continuando..."
else
    # Verifica se já existe uma pasta de migrações
    if [ -d "migrations" ]; then
        echo "Diretório de migrações encontrado. Executando flask db upgrade..."
        flask db upgrade || echo "Upgrade falhou, mas continuando..."
    else
        echo "Inicializando sistema de migrações..."
        # Tenta inicializar as migrações - se falhar, prossegue mesmo assim
        flask db init || echo "Inicialização de migrações falhou, possivelmente já existem."
        
        # Tenta criar a primeira migração
        flask db migrate -m "Initial migration" || echo "Migração inicial falhou, possivelmente já existe."
        
        # Executa as migrações
        flask db upgrade || echo "Upgrade falhou, mas continuando..."
    fi
fi

echo "Aplicando migrações do banco de dados..."
flask db upgrade

echo "Processo de migração concluído!" 