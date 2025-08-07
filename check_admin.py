#!/usr/bin/env python3
"""
Script para verificar se o painel administrativo está funcionando
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Spot

def check_admin_functionality():
    """Verifica se o painel administrativo está funcionando"""
    with app.app_context():
        # Verifica spots pendentes
        pending_spots = Spot.query.filter_by(status='pending').all()
        approved_spots = Spot.query.filter_by(status='approved').all()
        rejected_spots = Spot.query.filter_by(status='rejected').all()
        
        print("📊 Status atual dos Spots:")
        print(f"⏳ Pendentes: {len(pending_spots)}")
        print(f"✅ Aprovados: {len(approved_spots)}")
        print(f"❌ Rejeitados: {len(rejected_spots)}")
        
        print("\n📋 Spots Pendentes:")
        for spot in pending_spots:
            print(f"- {spot.name} ({spot.city}, {spot.state}) - Criado por: {spot.creator.username}")
        
        print("\n📋 Spots Aprovados:")
        for spot in approved_spots:
            print(f"- {spot.name} ({spot.city}, {spot.state}) - Criado por: {spot.creator.username}")
        
        # Verifica usuários admin
        admins = User.query.filter_by(is_admin=True).all()
        print(f"\n👤 Administradores ({len(admins)}):")
        for admin in admins:
            print(f"- {admin.username} ({admin.email})")
        
        print("\n🌐 URLs para testar:")
        print("- Mapa de Spots: http://localhost:5000/spots/map")
        print("- Admin Spots: http://localhost:5000/admin/spots")
        print("- Login: http://localhost:5000/login")
        print("- Adicionar Spot: http://localhost:5000/spots/add")

if __name__ == "__main__":
    check_admin_functionality()
