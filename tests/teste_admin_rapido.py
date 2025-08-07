"""
Teste simplificado para verificar se o admin funciona
"""
import requests

def test_admin_simple():
    print("🔍 Testando acesso ao painel admin...")
    
    # Criar sessão
    session = requests.Session()
    
    # 1. Tentar login
    print("1. Fazendo login como admin...")
    login_data = {
        'username': 'admin',
        'password': 'admin123'
    }
    
    try:
        login_response = session.post('http://localhost:5001/login', data=login_data, timeout=10)
        print(f"   Status do login: {login_response.status_code}")
        
        # 2. Tentar acessar painel de spots
        print("2. Acessando painel de spots...")
        spots_response = session.get('http://localhost:5001/admin/spots', timeout=10)
        print(f"   Status do painel: {spots_response.status_code}")
        
        if spots_response.status_code == 200:
            content = spots_response.text
            
            # Verificar se tem o conteúdo esperado
            if "Gerenciar Spots" in content:
                print("   ✅ Painel de spots carregado com sucesso!")
                
                # Verificar se tem spots pendentes
                if "Pico de Matinhos" in content:
                    print("   ✅ Spot 'Pico de Matinhos' encontrado no painel!")
                    print("   ✅ Você pode aprovar este spot clicando no botão verde!")
                else:
                    print("   ⚠️  Spot 'Pico de Matinhos' não aparece no painel")
                
                # Verificar estatísticas
                if "3" in content and "Pendentes" in content:
                    print("   ✅ Mostra 3 spots pendentes corretamente")
                
                return True
            else:
                print("   ❌ Conteúdo do painel não encontrado")
                print("   Primeira linha do HTML:")
                print(f"   {content.split('\\n')[0] if content else 'Vazio'}")
        else:
            print(f"   ❌ Erro HTTP: {spots_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Erro de conexão: {e}")
        print("   Verifique se a aplicação está rodando em http://localhost:5001")
    
    return False

if __name__ == "__main__":
    success = test_admin_simple()
    if success:
        print("\\n🎉 PAINEL ADMIN FUNCIONA!")
        print("   Acesse: http://localhost:5001")
        print("   Login: admin / admin123")  
        print("   Painel: http://localhost:5001/admin/spots")
    else:
        print("\\n❌ Problema detectado - verifique os containers")
