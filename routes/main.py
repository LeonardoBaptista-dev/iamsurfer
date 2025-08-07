from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import User, Post, Follow, SurfSpot, Notification
from app import db
from sqlalchemy import desc
import random
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    # Se o usuário não está logado, redireciona para login
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    
    # Se o usuário é admin, redireciona para o dashboard admin
    if current_user.is_admin:
        return redirect(url_for('admin.index'))
    
    # Usuário comum logado - mostrar página inicial de usuário
    following_ids = [f.followed_id for f in current_user.followed.all()]
    following_ids.append(current_user.id)
    posts = Post.query.filter(Post.user_id.in_(following_ids)).order_by(desc(Post.created_at)).all()
    users_not_following = User.query.filter(~User.id.in_(following_ids)).all()
    suggested_users = random.sample(users_not_following, min(3, len(users_not_following))) if users_not_following else []
    
    return render_template('main/index.html', 
                          posts=posts, 
                          suggested_users=suggested_users)

@main.route('/home')
@login_required
def home():
    """Página inicial de usuário comum (sem redirecionamentos automáticos)"""
    following_ids = [f.followed_id for f in current_user.followed.all()]
    following_ids.append(current_user.id)
    posts = Post.query.filter(Post.user_id.in_(following_ids)).order_by(desc(Post.created_at)).all()
    users_not_following = User.query.filter(~User.id.in_(following_ids)).all()
    suggested_users = random.sample(users_not_following, min(3, len(users_not_following))) if users_not_following else []
    
    return render_template('main/index.html', 
                          posts=posts, 
                          suggested_users=suggested_users)

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
    
    # Cria notificação de novo seguidor
    Notification.create_follow_notification(current_user, user)
    
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