@echo off
REM Script para desenvolvimento local com Docker

echo 🐳 IAmSurfer - Ambiente de Desenvolvimento Docker
echo ================================================

REM Para e remove containers existentes
echo 📦 Parando containers existentes...
docker-compose down

REM Remove volumes órfãos (opcional - descomente se precisar)
REM docker system prune -f

REM Reconstrói e inicia os containers
echo 🔨 Reconstruindo containers...
docker-compose build --no-cache

echo 🚀 Iniciando aplicação...
docker-compose up -d

REM Aguarda um pouco para o banco estar pronto
echo ⏳ Aguardando banco de dados...
timeout /t 10 /nobreak

REM Executa migrações
echo 🗃️ Executando migrações do banco...
docker-compose exec web flask db upgrade

echo ✅ Aplicação iniciada!
echo 🌐 Acesse: http://localhost:5001
echo 📊 Admin: http://localhost:5001/admin
echo 
echo 📝 Comandos úteis:
echo   - docker-compose logs web (ver logs)
echo   - docker-compose exec web flask shell (shell Python)
echo   - docker-compose exec db psql -U iamsurfer -d iamsurfer (SQL)
echo   - docker-compose down (parar aplicação)

pause
