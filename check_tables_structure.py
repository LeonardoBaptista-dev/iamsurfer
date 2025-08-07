#!/usr/bin/env python3
"""
Script para verificar estrutura das tabelas de spots
"""
import subprocess

def check_tables_structure():
    """Verifica a estrutura das tabelas spot e surf_spot"""
    print("🔍 Verificando estrutura das tabelas...")
    
    try:
        # Estrutura da tabela spot
        cmd_spot = [
            "docker-compose", "exec", "-T", "db", 
            "psql", "-U", "iamsurfer", "-d", "iamsurfer", 
            "-c", "\\d spot"
        ]
        
        result_spot = subprocess.run(cmd_spot, capture_output=True, text=True)
        
        if result_spot.returncode == 0:
            print("✅ Estrutura da tabela SPOT:")
            print("="*50)
            print(result_spot.stdout)
        else:
            print(f"❌ Erro na consulta tabela spot: {result_spot.stderr}")
            
        # Estrutura da tabela surf_spot
        cmd_surf_spot = [
            "docker-compose", "exec", "-T", "db",
            "psql", "-U", "iamsurfer", "-d", "iamsurfer",
            "-c", "\\d surf_spot"
        ]
        
        result_surf_spot = subprocess.run(cmd_surf_spot, capture_output=True, text=True)
        
        if result_surf_spot.returncode == 0:
            print("\n✅ Estrutura da tabela SURF_SPOT:")
            print("="*50)
            print(result_surf_spot.stdout)
        else:
            print(f"❌ Erro na consulta tabela surf_spot: {result_surf_spot.stderr}")
            
        # Conteúdo da tabela surf_spot (sem campo status)
        cmd_content = [
            "docker-compose", "exec", "-T", "db",
            "psql", "-U", "iamsurfer", "-d", "iamsurfer",
            "-c", "SELECT id, name, difficulty_level FROM surf_spot LIMIT 5;"
        ]
        
        result_content = subprocess.run(cmd_content, capture_output=True, text=True)
        
        if result_content.returncode == 0:
            print("\n✅ Conteúdo da tabela SURF_SPOT:")
            print("="*50)
            print(result_content.stdout)
        
    except Exception as e:
        print(f"💥 Erro: {str(e)}")

if __name__ == "__main__":
    check_tables_structure()
