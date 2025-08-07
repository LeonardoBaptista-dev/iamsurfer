#!/usr/bin/env python3
"""
Script para criar spots de exemplo no banco de dados
"""
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, Spot
from datetime import datetime

def create_sample_spots():
    """Cria spots de exemplo para testar o sistema"""
    with app.app_context():
        # Verifica se já existe um usuário admin
        admin = User.query.filter_by(is_admin=True).first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@iamsurfer.com",
                is_admin=True
            )
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Usuário admin criado!")
        
        # Cria um usuário comum para ser o criador dos spots
        user = User.query.filter_by(username="surfista_test").first()
        if not user:
            user = User(
                username="surfista_test",
                email="surfista@test.com",
                bio="Surfista apaixonado por descobrir novos picos!"
            )
            user.set_password("123456")
            db.session.add(user)
            db.session.commit()
            print("Usuário de teste criado!")
        
        # Spot 1: Praia do Rosa - SC
        spot1 = Spot.query.filter_by(name="Praia do Rosa").first()
        if not spot1:
            spot1 = Spot(
                name="Praia do Rosa",
                description="Uma das praias mais bonitas de Santa Catarina, com ondas consistentes e um visual incrível. Ideal para surfistas intermediários e avançados. A praia oferece diferentes tipos de ondas dependendo das condições.",
                latitude=-28.4833,
                longitude=-48.7833,
                address="Estrada Geral da Praia do Rosa, Imbituba - SC",
                city="Imbituba",
                state="SC",
                country="Brasil",
                bottom_type="areia",
                wave_type="beach_break",
                difficulty="intermediário",
                crowd_level="médio",
                best_wind_direction="SW",
                best_swell_direction="S",
                best_tide="todas",
                min_swell_size=1.0,
                max_swell_size=4.0,
                status="pending",  # Pendente para teste de aprovação
                created_by=user.id,
                created_at=datetime.utcnow()
            )
            db.session.add(spot1)
            print("Spot 'Praia do Rosa' criado (pendente de aprovação)!")
        
        # Spot 2: Joaquina - SC
        spot2 = Spot.query.filter_by(name="Joaquina").first()
        if not spot2:
            spot2 = Spot(
                name="Joaquina",
                description="Praia icônica de Florianópolis, famosa por suas dunas e ondas tubulares. Local de competições internacionais de surf. Ondas consistentes e um dos spots mais tradicionais do Brasil.",
                latitude=-27.6367,
                longitude=-48.4419,
                address="Praia da Joaquina, Florianópolis - SC",
                city="Florianópolis",
                state="SC",
                country="Brasil",
                bottom_type="areia",
                wave_type="beach_break",
                difficulty="avançado",
                crowd_level="alto",
                best_wind_direction="NW",
                best_swell_direction="S",
                best_tide="baixa",
                min_swell_size=1.5,
                max_swell_size=5.0,
                status="pending",  # Pendente para teste de aprovação
                created_by=user.id,
                created_at=datetime.utcnow()
            )
            db.session.add(spot2)
            print("Spot 'Joaquina' criado (pendente de aprovação)!")
        
        # Spot 3: Maresias - SP (já aprovado para exemplo)
        spot3 = Spot.query.filter_by(name="Maresias").first()
        if not spot3:
            spot3 = Spot(
                name="Maresias",
                description="Uma das praias mais famosas de São Paulo para o surf. Conhecida por suas ondas constantes e pela vida noturna agitada. Ideal para todos os níveis de surfistas.",
                latitude=-23.7833,
                longitude=-45.5667,
                address="Praia de Maresias, São Sebastião - SP",
                city="São Sebastião",
                state="SP",
                country="Brasil",
                bottom_type="areia",
                wave_type="beach_break",
                difficulty="intermediário",
                crowd_level="alto",
                best_wind_direction="NE",
                best_swell_direction="S",
                best_tide="média",
                min_swell_size=1.0,
                max_swell_size=3.5,
                status="approved",  # Já aprovado
                created_by=user.id,
                created_at=datetime.utcnow(),
                approved_by=admin.id,
                approved_at=datetime.utcnow()
            )
            db.session.add(spot3)
            print("Spot 'Maresias' criado (já aprovado)!")
        
        try:
            db.session.commit()
            print("\n✅ Spots de exemplo criados com sucesso!")
            print("\n📋 Resumo:")
            print("- Praia do Rosa: PENDENTE (precisa ser aprovado pelo admin)")
            print("- Joaquina: PENDENTE (precisa ser aprovado pelo admin)")
            print("- Maresias: APROVADO (já visível no mapa)")
            print("\n🔑 Credenciais de acesso:")
            print("Admin: admin@iamsurfer.com / admin123")
            print("Usuário: surfista@test.com / 123456")
            print("\n🌐 Acesse: http://localhost:5000/admin/spots para gerenciar")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao criar spots: {e}")

if __name__ == "__main__":
    create_sample_spots()
