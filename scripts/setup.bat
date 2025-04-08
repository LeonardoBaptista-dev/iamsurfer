@echo off
echo Inicializando o ambiente IAmSurfer...

:: Criar ambiente virtual
echo Criando ambiente virtual...
python -m venv venv
call venv\Scripts\activate

:: Instalar dependências
echo Instalando dependências...
pip install -r requirements.txt

:: Inicializar banco de dados
echo Inicializando banco de dados...
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

:: Criar diretórios de upload se não existirem
if not exist "static\uploads\posts" mkdir static\uploads\posts
if not exist "static\uploads\profile_pics" mkdir static\uploads\profile_pics

echo.
echo Configuração concluída com sucesso!
echo Para iniciar a aplicação, execute: flask run
echo. 