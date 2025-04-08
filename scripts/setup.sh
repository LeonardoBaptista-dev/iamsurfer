#!/bin/bash

# Inicializa o banco de dados
echo "Inicializando o banco de dados..."
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Cria dados de teste (descomente se necessário)
# echo "Criando dados de teste..."
# python init_db.py

echo "Instalação concluída com sucesso!"
echo "Execute 'flask run' para iniciar a aplicação." 