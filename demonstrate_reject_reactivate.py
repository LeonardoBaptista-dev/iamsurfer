#!/usr/bin/env python3
"""
Script para demonstrar rejeição e reativação de spots
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Spot
from datetime import datetime

def demonstrate_reject_reactivate():
    """Demonstra rejeição e reativação de spots"""
    with app.app_context():
        print("🛠️ Demonstração: Rejeitar e Reativar Spots\n")
        
        # Busca o admin
        admin = User.query.filter_by(is_admin=True).first()
        
        # Busca um spot pendente para rejeitar
        spot_to_reject = Spot.query.filter_by(status='pending').first()
        
        if spot_to_reject and admin:
            print(f"🔴 REJEITANDO SPOT: {spot_to_reject.name}")
            print(f"   Admin: {admin.username}")
            
            # Rejeita o spot
            spot_to_reject.status = 'rejected'
            spot_to_reject.rejected_by = admin.id
            spot_to_reject.rejected_at = datetime.utcnow()
            
            db.session.commit()
            
            print("   ✅ Spot rejeitado com sucesso!")
            
            # Mostra status atualizado
            pending_count = Spot.query.filter_by(status='pending').count()
            approved_count = Spot.query.filter_by(status='approved').count()
            rejected_count = Spot.query.filter_by(status='rejected').count()
            
            print(f"\n📊 Status após rejeição:")
            print(f"   ⏳ Pendentes: {pending_count}")
            print(f"   ✅ Aprovados: {approved_count}")
            print(f"   ❌ Rejeitados: {rejected_count}")
            
            # Agora vamos reativar o spot
            print(f"\n🔄 REATIVANDO SPOT: {spot_to_reject.name}")
            
            spot_to_reject.status = 'pending'
            spot_to_reject.rejected_by = None
            spot_to_reject.rejected_at = None
            
            db.session.commit()
            
            print("   ✅ Spot reativado e está pendente novamente!")
            
            # Status final
            pending_count = Spot.query.filter_by(status='pending').count()
            approved_count = Spot.query.filter_by(status='approved').count()
            rejected_count = Spot.query.filter_by(status='rejected').count()
            
            print(f"\n📊 Status após reativação:")
            print(f"   ⏳ Pendentes: {pending_count}")
            print(f"   ✅ Aprovados: {approved_count}")
            print(f"   ❌ Rejeitados: {rejected_count}")
            
        else:
            print("❌ Nenhum spot pendente encontrado ou admin não existe!")
        
        print("\n🎯 FUNCIONALIDADES IMPLEMENTADAS:")
        print("   ✅ Aprovar spots pendentes")
        print("   ✅ Rejeitar spots pendentes")
        print("   ✅ Reativar spots rejeitados")
        print("   ✅ Excluir spots permanentemente")
        print("   ✅ Filtrar por status")
        print("   ✅ Paginação")
        print("   ✅ Confirmação de exclusão")
        
        print("\n🌐 Acesse o painel: http://localhost:5000/admin/spots")

if __name__ == "__main__":
    demonstrate_reject_reactivate()
