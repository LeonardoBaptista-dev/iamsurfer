#!/usr/bin/env python3
"""
Script para testar as rotas do admin
"""

import requests
from requests.auth import HTTPBasicAuth

def test_admin_routes():
    base_url = "http://localhost:5001"
    
    # Testar rota principal
    print("=== Testando rotas admin ===")
    
    try:
        # Teste da página principal
        print("\n1. Testando página principal...")
        response = requests.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        
        # Teste da rota admin (sem autenticação)
        print("\n2. Testando rota admin (sem auth)...")
        response = requests.get(f"{base_url}/admin/")
        print(f"Status: {response.status_code}")
        if response.status_code == 302:
            print(f"Redirect para: {response.headers.get('Location')}")
        
        # Teste da rota admin/spots (sem autenticação)
        print("\n3. Testando rota admin/spots (sem auth)...")
        response = requests.get(f"{base_url}/admin/spots")
        print(f"Status: {response.status_code}")
        if response.status_code == 302:
            print(f"Redirect para: {response.headers.get('Location')}")
            
        # Teste de login
        print("\n4. Testando login...")
        session = requests.Session()
        
        # Primeiro, pegar a página de login para obter qualquer token CSRF
        login_page = session.get(f"{base_url}/login")
        print(f"Página de login: {login_page.status_code}")
        
        # Tentar fazer login
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data)
        print(f"Login response: {login_response.status_code}")
        if login_response.status_code == 302:
            print(f"Login redirect: {login_response.headers.get('Location')}")
        
        # Agora tentar acessar admin com sessão autenticada
        print("\n5. Testando admin com sessão autenticada...")
        admin_response = session.get(f"{base_url}/admin/")
        print(f"Admin page: {admin_response.status_code}")
        
        # Tentar acessar spots com sessão autenticada
        print("\n6. Testando admin/spots com sessão autenticada...")
        spots_response = session.get(f"{base_url}/admin/spots")
        print(f"Spots page: {spots_response.status_code}")
        
        if spots_response.status_code == 200:
            print("✅ Rota admin/spots funcionando!")
        else:
            print(f"❌ Problema na rota admin/spots: {spots_response.status_code}")
            if spots_response.status_code == 302:
                print(f"Redirect para: {spots_response.headers.get('Location')}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor. Verifique se está rodando na porta 5001.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    test_admin_routes()
