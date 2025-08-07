#!/usr/bin/env python3
"""
Script para verificar usuários admin e testar acesso
"""

import requests
from bs4 import BeautifulSoup

def test_admin_access():
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("=== Verificando Acesso Admin ===")
    
    try:
        # 1. Verificar página inicial
        print("\n1. Verificando página inicial...")
        home_response = session.get(f"{base_url}/")
        print(f"Status: {home_response.status_code}")
        
        if "Mapa Colaborativo" in home_response.text:
            print("✅ Link 'Mapa Colaborativo' encontrado")
        else:
            print("❌ Link 'Mapa Colaborativo' NÃO encontrado")
            
        if "Admin" in home_response.text:
            print("✅ Link 'Admin' encontrado (sem login)")
        else:
            print("❌ Link 'Admin' NÃO encontrado (esperado sem login)")
        
        # 2. Tentar fazer login
        print("\n2. Fazendo login como admin...")
        
        # Primeiro, pegar a página de login
        login_page = session.get(f"{base_url}/login")
        print(f"Página de login: {login_page.status_code}")
        
        # Tentar login com credenciais admin
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        print(f"Login response: {login_response.status_code}")
        
        if login_response.status_code == 302:
            print(f"✅ Login redirecionou para: {login_response.headers.get('Location')}")
            
            # 3. Verificar página inicial após login
            print("\n3. Verificando página inicial após login...")
            home_after_login = session.get(f"{base_url}/")
            print(f"Status após login: {home_after_login.status_code}")
            
            # Verificar se o link Admin aparece agora
            if "Admin" in home_after_login.text:
                print("✅ Link 'Admin' encontrado após login!")
            else:
                print("❌ Link 'Admin' ainda não encontrado após login")
                
            # Verificar se menciona que é admin
            if "admin" in home_after_login.text.lower():
                print("✅ Palavra 'admin' encontrada na página")
            
            # 4. Tentar acessar diretamente a página admin
            print("\n4. Testando acesso direto ao admin...")
            admin_response = session.get(f"{base_url}/admin/")
            print(f"Admin page status: {admin_response.status_code}")
            
            if admin_response.status_code == 200:
                print("✅ Acesso ao painel admin funcionando!")
                
                # Verificar se tem link para spots
                if "Spots de Surf" in admin_response.text:
                    print("✅ Link 'Spots de Surf' encontrado no painel admin")
                else:
                    print("❌ Link 'Spots de Surf' NÃO encontrado no painel admin")
                    
            elif admin_response.status_code == 403:
                print("❌ Acesso negado (403) - usuário não é admin")
            elif admin_response.status_code == 302:
                print(f"❌ Redirecionado para: {admin_response.headers.get('Location')}")
                
        else:
            print("❌ Falha no login")
            print(f"Conteúdo da resposta: {login_response.text[:200]}...")
            
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor na porta 5001")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    test_admin_access()
