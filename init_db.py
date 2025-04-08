from app import app, db
from models import User, Post, Follow
import random
from datetime import datetime, timedelta

def create_test_data():
    print("Criando dados de teste para o banco de dados...")
    
    with app.app_context():
        # Limpa os dados existentes
        db.session.query(Follow).delete()
        db.session.query(Post).delete()
        # Mantém usuários existentes
        
        # Verifica se já existem usuários
        if User.query.count() < 2:  # Se só tiver o admin ou menos
            # Criar alguns usuários de teste
            test_users = [
                {
                    'username': 'joaosurf',
                    'email': 'joao@exemplo.com',
                    'password': 'senha123',
                    'location': 'Rio de Janeiro, RJ',
                    'bio': 'Surfista apaixonado pelas ondas do Rio. 5 anos de experiência.',
                    'profile_image': 'uploads/default_profile.jpg'
                },
                {
                    'username': 'mariasurfista',
                    'email': 'maria@exemplo.com',
                    'password': 'senha123',
                    'location': 'Florianópolis, SC',
                    'bio': 'Surfista profissional, competidora de campeonatos estaduais.',
                    'profile_image': 'uploads/default_profile.jpg'
                },
                {
                    'username': 'pedrowaves',
                    'email': 'pedro@exemplo.com',
                    'password': 'senha123',
                    'location': 'Ubatuba, SP',
                    'bio': 'Surfista de fim de semana e fotógrafo amador.',
                    'profile_image': 'uploads/default_profile.jpg'
                },
                {
                    'username': 'anacosta',
                    'email': 'ana@exemplo.com',
                    'password': 'senha123',
                    'location': 'Salvador, BA',
                    'bio': 'Surfista e instrutora de surf para iniciantes.',
                    'profile_image': 'uploads/default_profile.jpg'
                }
            ]
            
            users = []
            for user_data in test_users:
                user = User(
                    username=user_data['username'],
                    email=user_data['email'],
                    location=user_data['location'],
                    bio=user_data['bio'],
                    profile_image=user_data['profile_image']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                users.append(user)
            
            db.session.commit()
            print(f"Criados {len(users)} usuários de teste.")
        else:
            # Usar usuários existentes
            users = User.query.all()
            print(f"Usando {len(users)} usuários existentes.")
        
        # Criar alguns posts
        post_contents = [
            "Dia incrível hoje na praia! Ondas perfeitas para surf. #surf #praia",
            "Compartilhando minha nova prancha. O que vocês acham?",
            "Dia de competição. Nervoso mas confiante!",
            "Alguém quer surfar este fim de semana? O tempo vai estar perfeito.",
            "Uma dica para iniciantes: comece com uma prancha maior, é mais fácil para equilibrar.",
            "Sunset surf é simplesmente o melhor momento do dia.",
            "Ontem aprendi uma nova manobra. Ainda preciso praticar muito!",
            "Dica de local: a praia X tem as melhores ondas nesta época do ano.",
            "Finalmente consegui fazer o tubo perfeitamente!",
            "Nada como surfar para limpar a mente após uma semana estressante."
        ]
        
        # Cria posts para cada usuário
        for user in users:
            for _ in range(random.randint(1, 3)):  # Cada usuário tem 1-3 posts
                content = random.choice(post_contents)
                post = Post(
                    content=content,
                    user_id=user.id,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
                )
                db.session.add(post)
        
        db.session.commit()
        print(f"Posts criados com sucesso.")
        
        # Estabelecer algumas relações de seguidores
        for user in users:
            for other_user in users:
                if user != other_user and random.random() < 0.5:  # 50% de chance de seguir
                    if not user.is_following(other_user):
                        user.follow(other_user)
        
        db.session.commit()
        print("Relações de seguidor estabelecidas.")
        
        print("Dados de teste criados com sucesso!")

if __name__ == "__main__":
    create_test_data() 