#!/usr/bin/env python3
"""
Script para verificar usuários no banco de dados
"""

import os
import sys

# Adicionar o diretório atual ao Python path
sys.path.insert(0, os.getcwd())

# Importar os modelos
from app import app, db
from models import User

def check_users():
    print("=== Verificando Usuários no Banco ===")
    
    with app.app_context():
        try:
            # Listar todos os usuários
            users = User.query.all()
            print(f"\nTotal de usuários: {len(users)}")
            
            print("\nUsuários encontrados:")
            print("-" * 50)
            
            for user in users:
                admin_status = "✅ ADMIN" if user.is_admin else "❌ Usuário normal"
                print(f"ID: {user.id}")
                print(f"Username: {user.username}")
                print(f"Email: {user.email}")
                print(f"Status: {admin_status}")
                print(f"Criado em: {user.joined_at}")
                print("-" * 30)
                
            # Verificar especificamente o usuário admin
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                print(f"\n✅ Usuário 'admin' encontrado!")
                print(f"   Email: {admin_user.email}")
                print(f"   É admin: {admin_user.is_admin}")
                print(f"   ID: {admin_user.id}")
            else:
                print(f"\n❌ Usuário 'admin' NÃO encontrado!")
                
            # Verificar quantos admins existem
            admin_count = User.query.filter_by(is_admin=True).count()
            print(f"\nTotal de administradores: {admin_count}")
            
        except Exception as e:
            print(f"❌ Erro ao acessar banco de dados: {e}")

if __name__ == "__main__":
    check_users()
