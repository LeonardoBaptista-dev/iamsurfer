from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import User, Post, Follow, SurfSpot
from app import db
from sqlalchemy import desc
import random
from datetime import datetime

main = Blueprint('main', __name__)

# Dados de exemplo para as previsões de surf
SURF_SPOTS = [
    {"name": "Campeche", "location": "Florianópolis, SC", "slug": "campeche"},
    {"name": "Joaquina", "location": "Florianópolis, SC", "slug": "joaquina"},
    {"name": "Praia da Vila", "location": "Imbituba, SC", "slug": "praia-da-vila"},
    {"name": "Silveira", "location": "Garopaba, SC", "slug": "silveira"},
    {"name": "Rosa Norte", "location": "Imbituba, SC", "slug": "rosa"},
    {"name": "Matinhos", "location": "Matinhos, PR", "slug": "matinhos"},
    {"name": "Itamambuca", "location": "Ubatuba, SP", "slug": "itamambuca"}
]

# Função para gerar previsão aleatória
def get_random_forecast():
    # Escolhe um spot aleatório
    spot = random.choice(SURF_SPOTS)
    
    # Gera dados aleatórios para a previsão
    wave_height = round(random.uniform(0.5, 2.5), 1)  # Altura de onda entre 0.5m e 2.5m
    period = random.randint(6, 12)  # Período entre 6s e 12s
    
    # Direções possíveis
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    wave_direction = random.choice(directions)
    
    # Velocidade do vento
    wind_speed = random.randint(5, 25)  # km/h
    wind_direction = random.choice(directions)
    
    # Temperatura
    temperature = random.randint(18, 30)  # °C
    
    # Mensagem sobre condições
    messages = [
        "Ondas boas para iniciantes",
        "Ondas perfeitas para surfistas experientes",
        "Condições ideais para surf",
        "Mar agitado, cuidado redobrado",
        "Ondas pequenas, dia tranquilo"
    ]
    condition_message = random.choice(messages)
    
    # Horário da maré baixa (formato HH:MM)
    hour = random.randint(5, 21)
    minute = random.choice([0, 15, 30, 45])
    tide_time = f"{hour:02d}:{minute:02d}h"
    
    return {
        "spot": spot,
        "wave_height": wave_height,
        "period": period,
        "wave_direction": wave_direction,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "temperature": temperature,
        "condition_message": condition_message,
        "tide_time": tide_time,
        "forecast_url": f"https://www.surf-forecast.com/breaks/{spot['slug']}/forecasts/latest/six_day"
    }

@main.route('/')
def index():
    if current_user.is_authenticated:
        # Obtém os IDs dos usuários seguidos pelo usuário atual
        following_ids = [f.followed_id for f in current_user.followed.all()]
        following_ids.append(current_user.id)  # Inclui os próprios posts do usuário
        
        # Busca posts dos usuários seguidos e do próprio usuário
        posts = Post.query.filter(Post.user_id.in_(following_ids)).order_by(desc(Post.created_at)).all()
        
        # Busca usuários que o usuário atual não segue
        users_not_following = User.query.filter(~User.id.in_(following_ids)).all()
        # Seleciona aleatoriamente até 3 usuários para sugerir
        suggested_users = random.sample(users_not_following, min(3, len(users_not_following))) if users_not_following else []
    else:
        # Para usuários não logados, mostra os posts mais recentes
        posts = Post.query.order_by(desc(Post.created_at)).limit(10).all()
        
        # Para usuários não logados, seleciona usuários aleatórios
        all_users = User.query.all()
        suggested_users = random.sample(all_users, min(3, len(all_users))) if all_users else []
    
    # Gera previsão de surf aleatória
    surf_forecast = get_random_forecast()
    
    return render_template('main/index.html', 
                          posts=posts, 
                          suggested_users=suggested_users,
                          surf_forecast=surf_forecast)

@main.route('/explore')
def explore():
    # Mostra os posts mais recentes de todos os usuários
    posts = Post.query.order_by(desc(Post.created_at)).limit(50).all()
    return render_template('main/explore.html', posts=posts)

@main.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(desc(Post.created_at)).all()
    
    # Verifica se o usuário atual segue este perfil
    is_following = False
    if current_user.is_authenticated:
        is_following = current_user.is_following(user)
    
    # Contadores
    followers_count = user.followers.count()
    following_count = user.followed.count()
    
    return render_template('main/user_profile.html', 
                          user=user, 
                          posts=posts, 
                          is_following=is_following,
                          followers_count=followers_count,
                          following_count=following_count)

@main.route('/follow/<username>', methods=['GET', 'POST'])
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    if user == current_user:
        flash('Você não pode seguir a si mesmo!', 'danger')
        return redirect(url_for('main.user_profile', username=username))
    
    current_user.follow(user)
    db.session.commit()
    flash(f'Você começou a seguir {username}!', 'success')
    return redirect(url_for('main.user_profile', username=username))

@main.route('/unfollow/<username>', methods=['GET', 'POST'])
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    if user == current_user:
        flash('Você não pode deixar de seguir a si mesmo!', 'danger')
        return redirect(url_for('main.user_profile', username=username))
    
    current_user.unfollow(user)
    db.session.commit()
    flash(f'Você deixou de seguir {username}.', 'info')
    return redirect(url_for('main.user_profile', username=username))

@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    follows = user.followers.all()
    followers = [follow.follower for follow in follows]
    
    return render_template('main/followers.html', user=user, followers=followers)

@main.route('/following/<username>')
def following(username):
    user = User.query.filter_by(username=username).first_or_404()
    follows = user.followed.all()
    following = [follow.followed for follow in follows]
    
    return render_template('main/following.html', user=user, following=following)

@main.route('/search')
def search():
    query = request.args.get('q', '')
    
    if not query:
        return render_template('main/search.html', results=None, query=None)
    
    # Busca por usuários
    users = User.query.filter(User.username.ilike(f'%{query}%')).all()
    
    return render_template('main/search.html', results=users, query=query) 