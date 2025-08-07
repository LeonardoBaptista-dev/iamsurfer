#!/usr/bin/env python3
"""
Script para testar a página de spots com detalhes de erro
"""
import requests
import sys

def detailed_admin_test():
    """Teste detalhado da página de administração"""
    base_url = "http://localhost:5001"
    session = requests.Session()
    
    print("🔐 Fazendo login...")
    
    # Login
    login_data = {'username': 'admin', 'password': 'admin123'}
    login_response = session.post(f"{base_url}/login", data=login_data)
    
    if login_response.status_code != 200:
        print(f"❌ Erro no login: {login_response.status_code}")
        return False
    
    print(f"✅ Login OK - Redirecionado para: {login_response.url}")
    
    # Testar página principal do admin
    print("\n🏠 Testando página principal do admin...")
    admin_response = session.get(f"{base_url}/admin/")
    print(f"Status: {admin_response.status_code}")
    print(f"Conteúdo: {len(admin_response.text)} caracteres")
    
    if admin_response.status_code != 200:
        print(f"❌ Erro na página admin: {admin_response.status_code}")
        print(f"Conteúdo do erro: {admin_response.text[:500]}")
        return False
    
    if len(admin_response.text) < 100:
        print("⚠️  Página admin com pouco conteúdo")
        print(f"Conteúdo: {admin_response.text}")
    else:
        print("✅ Página admin carregada corretamente")
    
    # Testar página de spots
    print("\n🏖️ Testando página de spots...")
    spots_response = session.get(f"{base_url}/admin/spots")
    print(f"Status: {spots_response.status_code}")
    print(f"Conteúdo: {len(spots_response.text)} caracteres")
    print(f"Headers: {dict(spots_response.headers)}")
    
    if spots_response.status_code != 200:
        print(f"❌ Erro na página spots: {spots_response.status_code}")
        print(f"Conteúdo do erro: {spots_response.text[:500]}")
        return False
    
    if len(spots_response.text) == 0:
        print("❌ Página de spots retornando vazio!")
        print("Isso pode indicar erro no template ou na função")
    elif len(spots_response.text) < 100:
        print("⚠️  Página spots com pouco conteúdo")
        print(f"Conteúdo completo: {spots_response.text}")
    else:
        print("✅ Página spots com conteúdo")
        # Verificar se tem as palavras chave
        content_lower = spots_response.text.lower()
        has_spot = 'spot' in content_lower
        has_pending = 'pendente' in content_lower or 'pending' in content_lower
        has_table = 'table' in content_lower
        has_admin = 'admin' in content_lower
        
        print(f"   - Contém 'spot': {has_spot}")
        print(f"   - Contém 'pending': {has_pending}")
        print(f"   - Contém 'table': {has_table}")
        print(f"   - Contém 'admin': {has_admin}")
    
    # Testar outras URLs relacionadas
    print("\n🔗 Testando outras URLs...")
    test_urls = [
        f"{base_url}/admin/users",
        f"{base_url}/admin/posts"
    ]
    
    for url in test_urls:
        try:
            resp = session.get(url)
            print(f"   {url}: {resp.status_code} ({len(resp.text)} chars)")
        except Exception as e:
            print(f"   {url}: ERRO - {str(e)}")
    
    return True

if __name__ == "__main__":
    print("🔬 Teste detalhado do painel administrativo")
    print("="*60)
    
    detailed_admin_test()
    
    print("="*60)
    print("✅ Teste concluído")
