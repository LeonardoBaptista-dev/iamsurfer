#!/usr/bin/env python3
"""
Script para consultar diretamente o banco de dados via container
"""
import subprocess
import sys

def query_database():
    """Executa consultas SQL diretamente no banco"""
    print("🗄️  Consultando banco de dados...")
    
    try:
        # Consultar todos os spots
        cmd_spots = [
            "docker-compose", "exec", "-T", "db", 
            "psql", "-U", "iamsurfer", "-d", "iamsurfer", 
            "-c", "SELECT id, name, status, created_by, created_at FROM spot ORDER BY created_at DESC LIMIT 10;"
        ]
        
        print("📊 Executando consulta de spots...")
        result_spots = subprocess.run(cmd_spots, capture_output=True, text=True)
        
        if result_spots.returncode == 0:
            print("✅ Consulta de spots executada com sucesso!")
            print("\n" + "="*60)
            print("SPOTS NO BANCO DE DADOS:")
            print("="*60)
            print(result_spots.stdout)
        else:
            print(f"❌ Erro na consulta de spots: {result_spots.stderr}")
            
        # Consultar contagens por status
        cmd_count = [
            "docker-compose", "exec", "-T", "db",
            "psql", "-U", "iamsurfer", "-d", "iamsurfer",
            "-c", "SELECT status, COUNT(*) FROM spot GROUP BY status;"
        ]
        
        print("\n📈 Executando consulta de contagens...")
        result_count = subprocess.run(cmd_count, capture_output=True, text=True)
        
        if result_count.returncode == 0:
            print("✅ Consulta de contagens executada com sucesso!")
            print("\n" + "="*40)
            print("CONTAGENS POR STATUS:")
            print("="*40)
            print(result_count.stdout)
        else:
            print(f"❌ Erro na consulta de contagens: {result_count.stderr}")
            
        # Consultar usuários
        cmd_users = [
            "docker-compose", "exec", "-T", "db",
            "psql", "-U", "iamsurfer", "-d", "iamsurfer",
            "-c", "SELECT id, username, is_admin FROM \"user\" ORDER BY id;"
        ]
        
        print("\n👥 Executando consulta de usuários...")
        result_users = subprocess.run(cmd_users, capture_output=True, text=True)
        
        if result_users.returncode == 0:
            print("✅ Consulta de usuários executada com sucesso!")
            print("\n" + "="*40)
            print("USUÁRIOS NO BANCO:")
            print("="*40)
            print(result_users.stdout)
        else:
            print(f"❌ Erro na consulta de usuários: {result_users.stderr}")
            
    except Exception as e:
        print(f"💥 Erro ao executar consultas: {str(e)}")
        return False
        
    return True

if __name__ == "__main__":
    print("🔍 Verificando dados diretamente no banco PostgreSQL...")
    print("="*60)
    
    success = query_database()
    
    print("\n" + "="*60)
    if success:
        print("✅ Consultas concluídas!")
    else:
        print("❌ Algumas consultas falharam.")
