#!/usr/bin/env python3
"""
Script para demonstrar aprovação de spots via admin
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Spot
from datetime import datetime

def approve_spot_example():
    """Aprova um spot de exemplo para demonstrar o funcionamento"""
    with app.app_context():
        # Busca o admin
        admin = User.query.filter_by(is_admin=True).first()
        
        # Busca um spot pendente (Praia do Rosa)
        spot = Spot.query.filter_by(name="Praia do Rosa", status="pending").first()
        
        if spot and admin:
            print(f"📋 Aprovando spot: {spot.name}")
            print(f"👤 Admin: {admin.username}")
            
            # Aprova o spot
            spot.status = 'approved'
            spot.approved_by = admin.id
            spot.approved_at = datetime.utcnow()
            
            db.session.commit()
            
            print("✅ Spot aprovado com sucesso!")
            print("🌐 Agora ele aparecerá no mapa colaborativo!")
            
            # Mostra status atualizado
            pending_count = Spot.query.filter_by(status='pending').count()
            approved_count = Spot.query.filter_by(status='approved').count()
            
            print(f"\n📊 Status atualizado:")
            print(f"⏳ Pendentes: {pending_count}")
            print(f"✅ Aprovados: {approved_count}")
        else:
            print("❌ Spot ou admin não encontrado!")

if __name__ == "__main__":
    approve_spot_example()
