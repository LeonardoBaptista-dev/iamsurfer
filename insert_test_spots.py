#!/usr/bin/env python3
"""
Script para inserir spots de teste diretamente na tabela spot
"""
import subprocess

def insert_test_spots():
    """Insere spots de teste na tabela spot"""
    print("📍 Inserindo spots de teste na tabela spot...")
    
    spots_to_insert = [
        {
            'name': 'Spot Teste 1',
            'description': 'Spot criado para teste do sistema de aprovação',
            'latitude': -27.6915,
            'longitude': -48.5478,
            'city': 'Florianópolis',
            'state': 'SC',
            'country': 'Brasil',
            'status': 'pending',
            'created_by': 2  # surfista_test user
        },
        {
            'name': 'Spot Teste 2', 
            'description': 'Outro spot para teste de rejeição',
            'latitude': -23.6821,
            'longitude': -45.4092,
            'city': 'Ubatuba',
            'state': 'SP',
            'country': 'Brasil',
            'status': 'pending',
            'created_by': 2
        },
        {
            'name': 'Spot Teste 3',
            'description': 'Spot aprovado para teste',
            'latitude': -14.2800,
            'longitude': -39.0070,
            'city': 'Itacaré',
            'state': 'BA',
            'country': 'Brasil',
            'status': 'approved',
            'created_by': 1  # admin user
        }
    ]
    
    for i, spot in enumerate(spots_to_insert, 1):
        print(f"📌 Inserindo spot {i}: {spot['name']}...")
        
        insert_sql = f"""
        INSERT INTO spot (name, description, latitude, longitude, city, state, country, status, created_by, created_at, is_active)
        VALUES ('{spot['name']}', '{spot['description']}', {spot['latitude']}, {spot['longitude']}, 
                '{spot['city']}', '{spot['state']}', '{spot['country']}', '{spot['status']}', 
                {spot['created_by']}, NOW(), true);
        """
        
        cmd = [
            "docker-compose", "exec", "-T", "db",
            "psql", "-U", "iamsurfer", "-d", "iamsurfer",
            "-c", insert_sql
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {spot['name']} inserido com sucesso!")
        else:
            print(f"❌ Erro ao inserir {spot['name']}: {result.stderr}")
    
    # Verificar os spots inseridos
    print("\n🔍 Verificando spots inseridos...")
    
    verify_cmd = [
        "docker-compose", "exec", "-T", "db",
        "psql", "-U", "iamsurfer", "-d", "iamsurfer",
        "-c", "SELECT id, name, status, created_by FROM spot ORDER BY id;"
    ]
    
    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
    
    if verify_result.returncode == 0:
        print("✅ Verificação completa!")
        print("="*50)
        print(verify_result.stdout)
    else:
        print(f"❌ Erro na verificação: {verify_result.stderr}")

if __name__ == "__main__":
    print("🧪 Inserindo spots de teste para o painel administrativo...")
    print("="*60)
    
    insert_test_spots()
    
    print("="*60)
    print("✅ Processo concluído! Agora teste o painel admin em http://localhost:5001/admin/spots")
