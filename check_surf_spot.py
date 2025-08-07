#!/usr/bin/env python3
"""
Script para verificar a tabela surf_spot
"""
import subprocess

def check_surf_spot_table():
    """Verifica o conteúdo da tabela surf_spot"""
    print("🏄‍♂️ Verificando tabela surf_spot...")
    
    try:
        # Consultar surf_spot
        cmd_surf_spot = [
            "docker-compose", "exec", "-T", "db", 
            "psql", "-U", "iamsurfer", "-d", "iamsurfer", 
            "-c", "SELECT id, name, difficulty_level, status FROM surf_spot ORDER BY id LIMIT 10;"
        ]
        
        result = subprocess.run(cmd_surf_spot, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Consulta surf_spot executada com sucesso!")
            print("\n" + "="*60)
            print("TABELA SURF_SPOT:")
            print("="*60)
            print(result.stdout)
        else:
            print(f"❌ Erro na consulta surf_spot: {result.stderr}")
            
        # Verificar estrutura das tabelas
        cmd_tables = [
            "docker-compose", "exec", "-T", "db",
            "psql", "-U", "iamsurfer", "-d", "iamsurfer",
            "-c", "\\dt"
        ]
        
        result_tables = subprocess.run(cmd_tables, capture_output=True, text=True)
        
        if result_tables.returncode == 0:
            print("\n" + "="*40)
            print("TODAS AS TABELAS:")
            print("="*40)
            print(result_tables.stdout)
        
    except Exception as e:
        print(f"💥 Erro: {str(e)}")

if __name__ == "__main__":
    check_surf_spot_table()
