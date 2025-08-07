#!/usr/bin/env python3
"""
Script para verificar o status de admin do usuário
"""

import requests
from bs4 import BeautifulSoup

def check_admin_status():
    base_url = "http://localhost:5001"
    
    print("=== Verificando Status Admin ===")
    
    try:
        session = requests.Session()
        
        # 1. Acessar a página de login
        print("\n1. Acessando página de login...")
        login_page = session.get(f"{base_url}/login")
        soup = BeautifulSoup(login_page.content, 'html.parser')
        
        # 2. Fazer login com admin
        print("2. Fazendo login como admin...")
        login_data = {
            'username': 'admin',
            'password': 'admin123'
        }
        
        login_response = session.post(f"{base_url}/login", data=login_data)
        print(f"Status do login: {login_response.status_code}")
        
        if login_response.status_code == 302:
            print(f"Redirecionado para: {login_response.headers.get('Location')}")
        
        # 3. Acessar a página principal e verificar se o link Admin aparece
        print("\n3. Verificando página principal...")
        home_response = session.get(f"{base_url}/")
        
        if home_response.status_code == 200:
            soup = BeautifulSoup(home_response.content, 'html.parser')
            
            # Procurar pelo link Admin
            admin_link = soup.find('a', href='/admin/')
            if admin_link:
                print("✅ Link 'Admin' encontrado na navegação!")
                print(f"Texto do link: {admin_link.get_text().strip()}")
            else:
                print("❌ Link 'Admin' NÃO encontrado na navegação")
                
                # Verificar se está logado
                username_element = soup.find('a', class_='dropdown-toggle')
                if username_element:
                    print(f"Usuário logado: {username_element.get_text().strip()}")
                else:
                    print("❌ Usuário não parece estar logado")
                
                # Verificar todos os links na navegação
                nav_links = soup.find_all('a', class_='nav-link')
                print("\nLinks encontrados na navegação:")
                for link in nav_links:
                    print(f"  - {link.get_text().strip()} -> {link.get('href')}")
        
        # 4. Tentar acessar o painel admin diretamente
        print("\n4. Tentando acessar painel admin diretamente...")
        admin_response = session.get(f"{base_url}/admin/")
        print(f"Status do acesso admin: {admin_response.status_code}")
        
        if admin_response.status_code == 200:
            soup_admin = BeautifulSoup(admin_response.content, 'html.parser')
            
            # Procurar pelo link de Spots no painel admin
            spots_link = soup_admin.find('a', href='/admin/spots')
            if spots_link:
                print("✅ Link 'Spots de Surf' encontrado no painel admin!")
            else:
                print("❌ Link 'Spots de Surf' NÃO encontrado no painel admin")
                
                # Listar todos os links do painel admin
                admin_links = soup_admin.find_all('a', class_='nav-link')
                print("\nLinks encontrados no painel admin:")
                for link in admin_links:
                    print(f"  - {link.get_text().strip()} -> {link.get('href')}")
        
        # 5. Tentar acessar admin/spots diretamente
        print("\n5. Tentando acessar admin/spots diretamente...")
        spots_response = session.get(f"{base_url}/admin/spots")
        print(f"Status do acesso admin/spots: {spots_response.status_code}")
        
        if spots_response.status_code == 200:
            print("✅ Página admin/spots acessível!")
        else:
            print(f"❌ Problema ao acessar admin/spots: {spots_response.status_code}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao servidor.")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    check_admin_status()
