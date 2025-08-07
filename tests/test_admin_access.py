#!/usr/bin/env python3
"""
Script para testar o acesso ao painel administrativo dos spots
"""
import requests
import sys

def test_admin_panel():
    """Testa o acesso ao painel administrativo"""
    base_url = "http://localhost:5001"
    
    # Criar uma sessão para manter cookies
    session = requests.Session()
    
    print("🔐 Testando login como administrador...")
    
    # Primeiro, obter o token CSRF da página de login
    login_page = session.get(f"{base_url}/login")
    if login_page.status_code != 200:
        print(f"❌ Erro ao acessar página de login: {login_page.status_code}")
        return False
    
    # Fazer login como admin
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    login_response = session.post(f"{base_url}/login", data=login_data)
    
    if login_response.status_code == 200 and "dashboard" in login_response.url.lower() or "admin" in login_response.url.lower():
        print("✅ Login como administrador realizado com sucesso!")
    elif login_response.status_code == 200:
        print("⚠️  Login realizado, mas pode não ter redirecionado corretamente")
        print(f"URL atual: {login_response.url}")
    else:
        print(f"❌ Erro no login: {login_response.status_code}")
        return False
    
    print("\n🏄‍♂️ Testando acesso ao painel administrativo...")
    
    # Testar acesso ao painel principal de admin
    admin_response = session.get(f"{base_url}/admin/")
    print(f"Status do painel admin: {admin_response.status_code}")
    
    if admin_response.status_code == 200:
        print("✅ Painel administrativo principal acessível!")
        
        # Verificar se a página contém elementos esperados
        if "admin" in admin_response.text.lower():
            print("✅ Página do admin carregada corretamente!")
        else:
            print("⚠️  Página carregada mas conteúdo pode estar incorreto")
    else:
        print(f"❌ Erro ao acessar painel admin: {admin_response.status_code}")
        return False
    
    print("\n🏖️ Testando acesso ao gerenciamento de spots...")
    
    # Testar acesso ao gerenciamento de spots
    spots_response = session.get(f"{base_url}/admin/spots")
    print(f"Status do gerenciamento de spots: {spots_response.status_code}")
    
    if spots_response.status_code == 200:
        print("✅ Painel de gerenciamento de spots acessível!")
        
        # Verificar se a página contém spots
        if "spot" in spots_response.text.lower() and ("pendente" in spots_response.text.lower() or "aprovado" in spots_response.text.lower()):
            print("✅ Página de spots carregada com dados!")
        else:
            print("⚠️  Página carregada mas pode não ter spots ou conteúdo incorreto")
    else:
        print(f"❌ Erro ao acessar gerenciamento de spots: {spots_response.status_code}")
        return False
    
    print("\n✅ Todos os testes de acesso administrativo passaram!")
    return True

if __name__ == "__main__":
    print("🧪 Iniciando testes do painel administrativo...")
    print("="*50)
    
    success = test_admin_panel()
    
    print("="*50)
    if success:
        print("🎉 Todos os testes passaram! O painel administrativo está funcionando.")
    else:
        print("💥 Alguns testes falharam. Verifique os logs da aplicação.")
        sys.exit(1)
