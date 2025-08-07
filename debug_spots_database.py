#!/usr/bin/env python3
"""
Script para verificar o status dos spots no banco de dados
"""
import requests

def check_database_spots():
    """Verifica diretamente os spots no banco de dados"""
    # Vou criar um script que usa a própria API da aplicação
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
        print(f"❌ Erro no login: {login_response.status_code}")
        return False
    
    print("✅ Login realizado!")
    
    # Acessar o painel de spots com detalhes
    print("🔍 Verificando painel de spots...")
    spots_response = session.get(f"{base_url}/admin/spots")
    
    if spots_response.status_code == 200:
        # Vamos analisar o conteúdo da resposta
        content = spots_response.text.lower()
        
        print(f"📄 Status da página: {spots_response.status_code}")
        print(f"📏 Tamanho do conteúdo: {len(content)} caracteres")
        
        # Procurar por indicadores de spots
        if "spot" in content:
            print("✅ Palavra 'spot' encontrada na página")
            
            # Contar ocorrências de diferentes status
            pending_count = content.count('pendente') + content.count('pending')
            approved_count = content.count('aprovado') + content.count('approved')
            rejected_count = content.count('rejeitado') + content.count('rejected')
            
            print(f"📊 Estatísticas encontradas:")
            print(f"   - Pendentes: {pending_count} ocorrências")
            print(f"   - Aprovados: {approved_count} ocorrências")  
            print(f"   - Rejeitados: {rejected_count} ocorrências")
            
            # Procurar por nomes de spots específicos
            test_spots = ['spot pendente', 'pendente 1', 'pendente 2', 'pendente 3']
            for spot_name in test_spots:
                if spot_name in content:
                    print(f"🎯 Spot '{spot_name}' encontrado!")
                    
        else:
            print("⚠️  Palavra 'spot' não encontrada na página")
            
        # Procurar por possíveis mensagens de erro ou vazio
        if "nenhum" in content or "vazio" in content or "empty" in content:
            print("ℹ️  Possível indicação de lista vazia")
            
        return True
    else:
        print(f"❌ Erro ao acessar painel: {spots_response.status_code}")
        return False

if __name__ == "__main__":
    print("🔍 Verificando status dos spots no banco de dados...")
    print("="*50)
    
    check_database_spots()
    
    print("="*50)
    print("✅ Verificação concluída!")
