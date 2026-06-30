"""Usuários, perfis e follow da API (`/api/v1`) — Prompt A2.

Reaproveita as regras do site (`routes/main.py`): não seguir a si mesmo nem
admins; XP de 'follower' e notificação ao seguir; admins fora das listas/busca.
Respeita `is_public` (perfil privado só mostra posts a seguidores/dono).

Endpoints:
- GET    /users/:username                → perfil + counts + viewer_state
- GET    /users/:username/posts          → posts (cursor, respeita privacidade)
- GET    /users/:username/followers      → seguidores (cursor)
- GET    /users/:username/following      → seguindo (cursor)
- POST   /users/:username/follow         → seguir (idempotente)
- DELETE /users/:username/follow         → deixar de seguir (idempotente)
- GET    /me                             → próprio perfil (= /auth/me)
- PATCH  /me                             → editar bio/location/is_public
- PATCH  /me/avatar                      → trocar avatar (via mídia A11)
- GET    /search/users?q=                → busca por username
"""
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from extensions import db
from .deps import body, current_api_user
from .errors import ApiError
from .pagination import paginate_query, clamp_limit, decode_cursor, encode_cursor
from .serializers import user_full, user_brief, post_card, me_full, can_view_content

users_api = Blueprint('users_api', __name__)


def _get_user_or_404(username):
    from models import User
    user = User.query.filter(func.lower(User.username) == username.lower()).first()
    if user is None:
        raise ApiError('not_found', 'Usuário não encontrado.', 404)
    return user


# ── Perfil ───────────────────────────────────────────────────────────────────

@users_api.route('/users/<username>', methods=['GET'])
def get_profile(username):
    viewer = current_api_user(optional=True)
    user = _get_user_or_404(username)
    return jsonify({'user': user_full(user, viewer=viewer)})


@users_api.route('/users/<username>/posts', methods=['GET'])
def get_user_posts(username):
    from models import Post

    viewer = current_api_user(optional=True)
    user = _get_user_or_404(username)

    if not can_view_content(user, viewer):
        raise ApiError('forbidden', 'Este perfil é privado.', 403)

    cursor = request.args.get('cursor')
    limit = clamp_limit(request.args.get('limit'))
    query = Post.query.filter_by(user_id=user.id)
    items, next_cursor = paginate_query(query, Post, cursor=cursor, limit=limit)
    return jsonify({
        'items': [post_card(p, viewer=viewer) for p in items],
        'next_cursor': next_cursor,
    })


# ── Listas (seguidores/seguindo) ─────────────────────────────────────────────

def _paginate_follows(follow_query, related_attr, viewer):
    """Pagina uma query de Follow por id desc, devolvendo os usuários (brief).

    `related_attr`: 'follower' ou 'followed' — qual ponta do Follow extrair.
    Exclui admins (igual à web). Cursor sobre o id do Follow.
    """
    from models import Follow

    cursor_id = decode_cursor(request.args.get('cursor'))
    limit = clamp_limit(request.args.get('limit'))
    if cursor_id is not None:
        follow_query = follow_query.filter(Follow.id < cursor_id)

    rows = follow_query.order_by(Follow.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor(rows[-1].id) if has_more and rows else None

    users = []
    for f in rows:
        u = getattr(f, related_attr)
        if u and not u.is_admin:
            users.append(user_brief(u))
    return users, next_cursor


@users_api.route('/users/<username>/followers', methods=['GET'])
def get_followers(username):
    from models import Follow

    viewer = current_api_user(optional=True)
    user = _get_user_or_404(username)
    query = Follow.query.filter_by(followed_id=user.id)
    items, next_cursor = _paginate_follows(query, 'follower', viewer)
    return jsonify({'items': items, 'next_cursor': next_cursor})


@users_api.route('/users/<username>/following', methods=['GET'])
def get_following(username):
    from models import Follow

    viewer = current_api_user(optional=True)
    user = _get_user_or_404(username)
    query = Follow.query.filter_by(follower_id=user.id)
    items, next_cursor = _paginate_follows(query, 'followed', viewer)
    return jsonify({'items': items, 'next_cursor': next_cursor})


# ── Follow / Unfollow ────────────────────────────────────────────────────────

@users_api.route('/users/<username>/follow', methods=['POST'])
def follow_user(username):
    from gamification import award
    from models import Notification

    viewer = current_api_user()
    target = _get_user_or_404(username)

    if target.id == viewer.id:
        raise ApiError('cannot_follow_self', 'Você não pode seguir a si mesmo.', 422)
    if target.is_admin or viewer.is_admin:
        raise ApiError('cannot_follow', 'Este perfil não pode ser seguido.', 422)

    if not viewer.is_following(target):  # idempotente
        viewer.follow(target)
        award(target, 'follower')
        db.session.commit()
        Notification.create_follow_notification(viewer, target)

    return jsonify({'user': user_full(target, viewer=viewer)})


@users_api.route('/users/<username>/follow', methods=['DELETE'])
def unfollow_user(username):
    viewer = current_api_user()
    target = _get_user_or_404(username)

    if target.id == viewer.id:
        raise ApiError('cannot_follow_self', 'Você não pode deixar de seguir a si mesmo.', 422)

    if viewer.is_following(target):  # idempotente
        viewer.unfollow(target)
        db.session.commit()

    return jsonify({'user': user_full(target, viewer=viewer)})


# ── Próprio perfil ───────────────────────────────────────────────────────────

@users_api.route('/me', methods=['GET'])
def get_me():
    viewer = current_api_user()
    return jsonify({'user': me_full(viewer)})


@users_api.route('/me', methods=['PATCH'])
def update_me():
    viewer = current_api_user()
    data = body()

    if 'bio' in data:
        viewer.bio = (data.get('bio') or '').strip() or None
    if 'location' in data:
        viewer.location = (data.get('location') or '').strip() or None
    if 'is_public' in data:
        viewer.is_public = bool(data.get('is_public'))

    db.session.commit()
    return jsonify({'user': me_full(viewer)})


@users_api.route('/me/avatar', methods=['PATCH'])
def update_avatar():
    """Atualiza o avatar a partir de uma mídia já enviada ao Cloudinary (A11).

    O app sobe a imagem assinada e manda aqui o `url` (e opcionalmente as
    variantes em `urls`). Guardamos no mesmo formato do site.
    """
    viewer = current_api_user()
    data = body()
    url = (data.get('url') or data.get('secure_url') or '').strip()
    if not url:
        raise ApiError('validation_error', 'URL do avatar ausente.', 422,
                       {'url': 'Obrigatório.'})

    urls = data.get('urls') if isinstance(data.get('urls'), dict) else None
    if urls:
        viewer.profile_image_urls = urls
        viewer.profile_image = urls.get('small') or urls.get('thumbnail') or url
    else:
        # URL única: preenche todas as variantes com a mesma imagem.
        viewer.profile_image_urls = {k: url for k in ('thumbnail', 'small', 'medium', 'large')}
        viewer.profile_image = url

    db.session.commit()
    return jsonify({'user': me_full(viewer)})


# ── Busca ────────────────────────────────────────────────────────────────────

@users_api.route('/search/users', methods=['GET'])
def search_users():
    from models import User

    viewer = current_api_user(optional=True)
    q = (request.args.get('q') or '').strip()
    if not q:
        return jsonify({'items': [], 'next_cursor': None})

    limit = clamp_limit(request.args.get('limit'))
    rows = (User.query
            .filter(User.username.ilike(f'%{q}%'), User.is_admin == False)  # noqa: E712
            .order_by(User.username.asc())
            .limit(limit)
            .all())
    return jsonify({'items': [user_brief(u) for u in rows], 'next_cursor': None})
