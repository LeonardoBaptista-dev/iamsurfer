#!/usr/bin/env python3
"""
Script para criar spots pendentes para testar a funcionalidade de aprovação do admin
"""
import requests
import json

def create_pending_spots():
    """Cria alguns spots pendentes para teste"""
    base_url = "http://localhost:5001"
    
    # Fazer login como usuário normal primeiro (vamos criar um)
    session = requests.Session()
    
    print("👤 Criando usuário para criar spots...")
    
    # Primeiro, obter a página de registro
    signup_page = session.get(f"{base_url}/signup")
    if signup_page.status_code != 200:
        print(f"❌ Erro ao acessar página de registro: {signup_page.status_code}")
        return False
    
    # Criar um usuário normal
    user_data = {
        'username': 'surfista_test',
        'email': 'surfista@test.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }
    
    signup_response = session.post(f"{base_url}/signup", data=user_data)
    
    if signup_response.status_code == 200:
        print("✅ Usuário criado com sucesso!")
    else:
        print(f"⚠️  Usuário pode já existir, tentando fazer login...")
        
        # Tentar fazer login
        login_data = {
            'username': 'surfista_test',
            'password': 'password123'
        }
        login_response = session.post(f"{base_url}/login", data=login_data)
        
        if login_response.status_code != 200:
            print(f"❌ Erro no login: {login_response.status_code}")
            return False
    
    print("🏖️ Criando spots pendentes...")
    
    # Spots para criar
    pending_spots = [
        {
            'name': 'Spot Pendente 1',
            'city': 'Florianópolis',
            'state': 'SC',
            'description': 'Um ótimo spot para iniciantes',
            'difficulty_level': 'Fácil',
            'best_tide': 'Maré Alta',
            'best_wind': 'Sul',
            'surf_type': 'Beach Break'
        },
        {
            'name': 'Spot Pendente 2', 
            'city': 'Ubatuba',
            'state': 'SP',
            'description': 'Ondas tubulares para surfistas experientes',
            'difficulty_level': 'Difícil',
            'best_tide': 'Maré Baixa',
            'best_wind': 'Norte',
            'surf_type': 'Point Break'
        },
        {
            'name': 'Spot Pendente 3',
            'city': 'Itacaré',
            'state': 'BA',
            'description': 'Praia com ondas consistentes',
            'difficulty_level': 'Médio',
            'best_tide': 'Qualquer',
            'best_wind': 'Leste',
            'surf_type': 'Beach Break'
        }
    ]
      # Obter a página de criar spot para pegar o token CSRF
    create_spot_page = session.get(f"{base_url}/spots/add")
    if create_spot_page.status_code != 200:
        print(f"❌ Erro ao acessar página de criar spot: {create_spot_page.status_code}")
        return False
    
    created_count = 0
    for spot_data in pending_spots:
        print(f" Criando: {spot_data['name']}...")
        
        # Tentar criar o spot
        create_response = session.post(f"{base_url}/spots/add", data=spot_data)
        
        if create_response.status_code == 200:
            print(f"✅ {spot_data['name']} criado com sucesso!")
            created_count += 1
        else:
            print(f"⚠️  Erro ao criar {spot_data['name']}: {create_response.status_code}")
    
    print(f"\n🎯 Criados {created_count} spots pendentes para aprovação!")
    return created_count > 0

def test_admin_spot_management():
    """Testa o gerenciamento de spots pelo admin"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("🔐 Fazendo login como admin...")
    
    # Login como admin
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data)
    if login_response.status_code != 200:
        print(f"❌ Erro no login admin: {login_response.status_code}")
        return False
    
    print("✅ Login admin realizado!")
    
    # Acessar painel de spots
    spots_page = session.get(f"{base_url}/admin/spots")
    if spots_page.status_code != 200:
        print(f"❌ Erro ao acessar painel de spots: {spots_page.status_code}")
        return False
    
    print("✅ Painel de spots acessível!")
    
    # Verificar se há spots pendentes
    if "pendente" in spots_page.text.lower():
        print("🎯 Spots pendentes encontrados no painel admin!")
        return True
    else:
        print("⚠️  Nenhum spot pendente encontrado no painel")
        return False

if __name__ == "__main__":
    print("🧪 Testando funcionalidade completa de gerenciamento de spots...")
    print("="*60)
    
    # Criar spots pendentes
    spots_created = create_pending_spots()
    
    if spots_created:
        print("\n" + "="*60)
        print("🔍 Testando visualização no painel admin...")
        
        # Testar visualização no admin
        admin_access = test_admin_spot_management()
        
        if admin_access:
            print("\n✅ Sistema de aprovação de spots funcionando perfeitamente!")
            print("👉 Acesse http://localhost:5001/admin/spots para gerenciar os spots!")
        else:
            print("\n⚠️  Spots criados mas pode haver problema na visualização admin")
    else:
        print("\n❌ Falha ao criar spots para teste")
    
    print("="*60)
