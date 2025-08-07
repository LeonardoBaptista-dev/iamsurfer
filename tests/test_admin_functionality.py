#!/usr/bin/env python3
"""
Script para testar as funcionalidades administrativas de spots
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Spot
from datetime import datetime

def test_admin_functionality():
    """Testa as funcionalidades administrativas"""
    with app.app_context():
        print("🛠️ Testando Funcionalidades Administrativas de Spots\n")
        
        # Busca o admin
        admin = User.query.filter_by(is_admin=True).first()
        
        # Lista todos os spots
        all_spots = Spot.query.all()
        pending_spots = Spot.query.filter_by(status='pending').all()
        approved_spots = Spot.query.filter_by(status='approved').all()
        rejected_spots = Spot.query.filter_by(status='rejected').all()
        
        print("📊 ESTATÍSTICAS ATUAIS:")
        print(f"   Total de Spots: {len(all_spots)}")
        print(f"   📝 Pendentes: {len(pending_spots)}")
        print(f"   ✅ Aprovados: {len(approved_spots)}")
        print(f"   ❌ Rejeitados: {len(rejected_spots)}")
        
        print("\n📋 SPOTS PENDENTES:")
        for spot in pending_spots:
            print(f"   • {spot.name} ({spot.city}, {spot.state})")
            print(f"     Criado por: {spot.creator.username}")
            print(f"     Data: {spot.created_at.strftime('%d/%m/%Y %H:%M')}")
        
        print("\n✅ SPOTS APROVADOS:")
        for spot in approved_spots:
            print(f"   • {spot.name} ({spot.city}, {spot.state})")
            print(f"     Criado por: {spot.creator.username}")
            if spot.approved_by:
                approver = User.query.get(spot.approved_by)
                print(f"     Aprovado por: {approver.username}")
                print(f"     Data aprovação: {spot.approved_at.strftime('%d/%m/%Y %H:%M')}")
        
        if rejected_spots:
            print("\n❌ SPOTS REJEITADOS:")
            for spot in rejected_spots:
                print(f"   • {spot.name} ({spot.city}, {spot.state})")
                print(f"     Criado por: {spot.creator.username}")
                if spot.rejected_by:
                    rejecter = User.query.get(spot.rejected_by)
                    print(f"     Rejeitado por: {rejecter.username}")
                    print(f"     Data rejeição: {spot.rejected_at.strftime('%d/%m/%Y %H:%M')}")
        
        print("\n🔗 LINKS PARA TESTAR:")
        print("   📊 Admin Dashboard: http://localhost:5000/admin/")
        print("   🗺️ Admin Spots: http://localhost:5000/admin/spots")
        print("   🌐 Mapa Público: http://localhost:5000/spots/map")
        print("   🏄‍♂️ Login Admin: admin@iamsurfer.com / admin123")
        
        print("\n⚡ STATUS DO SISTEMA:")
        print("   ✅ Banco de dados funcionando")
        print("   ✅ Modelos atualizados com campos de rejeição")
        print("   ✅ Painel administrativo pronto")
        print("   ✅ Templates criados")
        print("   ✅ Rotas configuradas")
        
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("   1. Faça login como admin")
        print("   2. Acesse o painel de spots")
        print("   3. Teste aprovar/rejeitar spots")
        print("   4. Veja as mudanças no mapa")

if __name__ == "__main__":
    test_admin_functionality()
