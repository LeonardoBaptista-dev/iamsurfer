@echo off
echo Iniciando IAmSurfer em modo de desenvolvimento...

:: Ativar ambiente virtual
call venv\Scripts\activate

:: Definir variáveis de ambiente
set FLASK_APP=app.py
set FLASK_ENV=development
set FLASK_DEBUG=1

:: Iniciar a aplicação
flask run

echo Aplicação IAmSurfer encerrada. 