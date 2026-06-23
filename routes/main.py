from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models import User, Post, Follow, SurfSpot, Notification, Spot, SpotReport
from extensions import db
from sqlalchemy import desc, or_
import random
from datetime import datetime

main = Blueprint('main', __name__)

def build_feed_items(following_ids, page=1, per_page=20):
    """
    Constrói o feed unificado aplicando a lógica de Instagram:
    - Relatos de Picos (SpotReports) são públicos e entram no feed.
    - Posts regulares entram se o usuário segue o autor ou se for público (como sugestão).
    Aqui usamos uma busca paginada e aplicamos um algoritmo de prioridade (EdgeRank).
    """
    from datetime import datetime
    import pytz
    
    now = datetime.utcnow()
    
    # 1. Busca os Posts
    # Regra: Posts de quem eu sigo + Posts públicos (limitado a um pool para não pesar)
    posts_query = Post.query.join(User).filter(
        or_(
            Post.user_id.in_(following_ids),
            User.is_public == True
        )
    ).order_by(desc(Post.created_at)).limit(per_page * 3).all()

    # 2. Busca os Spot Reports (Sempre públicos)
    spot_reports_query = SpotReport.query.order_by(desc(SpotReport.report_date)).limit(per_page * 2).all()

    # 3. Unifica e aplica o EdgeRank Score
    all_items = []
    
    for p in posts_query:
        # Horas desde a postagem
        hours_diff = max(0.1, (now - p.created_at).total_seconds() / 3600)
        # Score = (Curtidas*2 + Comentarios*3) / (Horas + 1)^1.5
        likes_ct = p.likes.count() if hasattr(p.likes, 'all') else len(p.likes)
        comments_ct = p.comments.count() if hasattr(p.comments, 'all') else len(p.comments)
        
        score = ((likes_ct * 2) + (comments_ct * 3) + 1) / (hours_diff ** 1.5)
        # Bônus para quem o usuário segue
        if p.user_id in following_ids:
            score *= 1.5
            
        all_items.append({
            'kind': 'post', 
            'obj': p, 
            'created_at': p.created_at,
            'score': score
        })

    for r in spot_reports_query:
        hours_diff = max(0.1, (now - r.report_date).total_seconds() / 3600)
        # Spot reports têm um peso maior de utilidade pública
        score = 10 / (hours_diff ** 1.5)
        if r.user_id in following_ids:
            score *= 1.5
            
        all_items.append({
            'kind': 'spot_report',
            'id': r.id,
            'author': r.user,
            'spot': r.spot,
            'conditions': r.conditions,
            'wave_height': r.wave_height,
            'notes': r.notes,
            'created_at': r.report_date,
            'crowd_level': r.crowd_level,
            'score': score
        })

    # Ordena pelo score (EdgeRank) e aplica paginação manual na memória
    # O pool foi de até 100 itens, ordenamos e pegamos os 20 da página atual
    all_items.sort(key=lambda x: x['score'], reverse=True)
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    
    return all_items[start_idx:end_idx]

@main.route('/')
def index():
    if not current_user.is_authenticated:
        # Visitante: landing page pública que apresenta e "vende" a rede
        stats = {
            'surfers': User.query.count(),
            'spots': Spot.query.filter_by(status='approved', is_active=True).count(),
            'posts': Post.query.count(),
        }
        return render_template('main/landing.html', stats=stats)
    if current_user.is_admin:
        return redirect(url_for('admin.index'))

    following_ids = [f.followed_id for f in current_user.followed.all()]
    following_ids.append(current_user.id)

    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1

    feed_items = build_feed_items(following_ids, page=page)

    users_not_following = User.query.filter(~User.id.in_(following_ids), User.id != current_user.id).all()
    suggested_users = random.sample(users_not_following, min(5, len(users_not_following))) if users_not_following else []

    # Lista de picos para o formulário de novo post (spot tagging)
    spots = Spot.query.filter_by(status='approved', is_active=True).order_by(Spot.name).all()

    from routes.stories import build_story_bar
    story_bar = build_story_bar(current_user)

    return render_template('main/index.html',
                           feed_items=feed_items,
                           suggested_users=suggested_users,
                           spots=spots,
                           story_bar=story_bar)

@main.route('/home')
@login_required
def home():
    following_ids = [f.followed_id for f in current_user.followed.all()]
    following_ids.append(current_user.id)
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
        
    feed_items = build_feed_items(following_ids, page=page)
    users_not_following = User.query.filter(~User.id.in_(following_ids), User.id != current_user.id).all()
    suggested_users = random.sample(users_not_following, min(5, len(users_not_following))) if users_not_following else []
    spots = Spot.query.filter_by(status='approved', is_active=True).order_by(Spot.name).all()
    from routes.stories import build_story_bar
    story_bar = build_story_bar(current_user)
    return render_template('main/index.html',
                           feed_items=feed_items,
                           suggested_users=suggested_users,
                           spots=spots,
                           story_bar=story_bar)

@main.route('/api/feed')
@login_required
def api_feed():
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
        
    following_ids = [f.followed_id for f in current_user.followed.all()]
    following_ids.append(current_user.id)
    
    feed_items = build_feed_items(following_ids, page=page)
    
    # Return directly the HTML of the rendered items
    html = ""
    for item in feed_items:
        html += render_template('main/feed_item.html', item=item, current_user=current_user)
        
    return jsonify({'html': html, 'has_more': len(feed_items) > 0})

@main.route('/explore')
def explore():
    posts = Post.query.order_by(desc(Post.created_at)).limit(50).all()
    return render_template('main/explore.html', posts=posts)

@main.route('/ranking')
def ranking():
    """Ranking de surfistas por XP (gamificação): pódio + lista."""
    top = User.query.order_by(desc(User.points), User.username).limit(50).all()
    my_rank = None
    if current_user.is_authenticated:
        my_rank = User.query.filter(User.points > (current_user.points or 0)).count() + 1
    return render_template('main/ranking.html', top=top, my_rank=my_rank)

@main.route('/reels')
@login_required
def reels():
    """Feed vertical dedicado de Reels (vídeos 9:16), estilo Instagram/TikTok."""
    reel_posts = Post.query.filter(
        Post.post_type == 'reel',
        Post.video_url.isnot(None),
    ).order_by(desc(Post.created_at)).all()
    return render_template('main/reels.html', reels=reel_posts)

@main.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = Post.query.filter_by(user_id=user.id).order_by(desc(Post.created_at)).all()

    is_following = False
    if current_user.is_authenticated:
        is_following = current_user.is_following(user)

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
    # Gamificação: quem ganhou um seguidor recebe XP
    from gamification import award
    award(user, 'follower')
    db.session.commit()
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
    users = User.query.filter(User.username.ilike(f'%{query}%')).all()
    return render_template('main/search.html', results=users, query=query)