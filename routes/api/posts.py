"""Feed, posts, comentários e likes da API (`/api/v1`) — Prompt A3.

Reaproveita as regras do site (`routes/posts.py`/`main.py`): gamificação e
notificações em like/comentário; privacidade de perfil no detalhe do post. A
mídia já vem do Cloudinary (upload assinado A11) — o app manda só as URLs.

Endpoints:
- GET    /feed                       → posts de quem o user segue + próprios (cursor)
- GET    /explore                    → descoberta: posts públicos recentes (cursor)
- GET    /posts/:id                  → detalhe (respeita privacidade do autor)
- POST   /posts                      → cria post (texto + mídia[] + spot opcional)
- DELETE /posts/:id                  → remove (autor ou admin)
- POST   /posts/:id/like             → curtir (idempotente)
- DELETE /posts/:id/like             → descurtir (idempotente)
- GET    /posts/:id/comments         → comentários (cursor)
- POST   /posts/:id/comments         → comenta
- DELETE /comments/:id               → remove comentário (autor, autor do post ou admin)
"""
from flask import Blueprint, jsonify, request

from extensions import db
from .deps import body, current_api_user, require_fields
from .errors import ApiError
from .pagination import clamp_limit, decode_cursor, encode_cursor, paginate_query
from .serializers import comment_card, post_card, can_view_content

posts_api = Blueprint('posts_api', __name__)

IMAGE_SIZES = ('thumbnail', 'small', 'medium', 'large', 'original')


def _get_post_or_404(post_id):
    from models import Post
    post = Post.query.get(post_id)
    if post is None:
        raise ApiError('not_found', 'Post não encontrado.', 404)
    return post


def _apply_media(post, media):
    """Aplica a mídia (lista do Cloudinary) ao post: 1 imagem e/ou 1 vídeo.

    O model guarda uma imagem (image_url/image_urls) e um vídeo (video_url),
    espelhando o site. Itens extras são ignorados.
    """
    if not isinstance(media, list):
        return
    for item in media:
        if not isinstance(item, dict):
            continue
        url = (item.get('url') or item.get('secure_url') or '').strip()
        if not url:
            continue
        mtype = (item.get('type') or 'image').lower()
        if mtype == 'video' and not post.video_url:
            post.video_url = url
        elif mtype == 'image' and not post.image_url:
            post.image_url = url
            # Sem variantes do Cloudinary aqui; usamos a mesma URL para os tamanhos
            # (o Cloudinary serve responsivo por transformação na própria URL).
            post.image_urls = {size: url for size in IMAGE_SIZES}


# ── Feed / Explore ────────────────────────────────────────────────────────────

@posts_api.route('/feed', methods=['GET'])
def feed():
    from models import Post

    viewer = current_api_user()
    following_ids = [f.followed_id for f in viewer.followed.all()]
    following_ids.append(viewer.id)

    query = Post.query.filter(Post.user_id.in_(following_ids))
    items, next_cursor = paginate_query(
        query, Post, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [post_card(p, viewer=viewer) for p in items],
        'next_cursor': next_cursor,
    })


@posts_api.route('/explore', methods=['GET'])
def explore():
    from models import Post, User

    viewer = current_api_user(optional=True)
    # Descoberta: posts de perfis públicos, mais recentes primeiro.
    query = Post.query.join(User, Post.user_id == User.id).filter(
        User.is_public == True, User.is_admin == False,  # noqa: E712
    )
    items, next_cursor = paginate_query(
        query, Post, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [post_card(p, viewer=viewer) for p in items],
        'next_cursor': next_cursor,
    })


# ── Post (detalhe / criação / remoção) ────────────────────────────────────────

@posts_api.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    viewer = current_api_user(optional=True)
    post = _get_post_or_404(post_id)
    if not can_view_content(post.author, viewer):
        raise ApiError('forbidden', 'Este post é de um perfil privado.', 403)
    return jsonify({'post': post_card(post, viewer=viewer)})


@posts_api.route('/posts', methods=['POST'])
def create_post():
    from gamification import award
    from models import Post, Spot

    viewer = current_api_user()
    data = body()

    content = (data.get('content') or '').strip()
    media = data.get('media') or []
    spot_id = data.get('spot_id')

    has_media = isinstance(media, list) and any(
        isinstance(m, dict) and (m.get('url') or m.get('secure_url')) for m in media
    )
    if not content and not has_media:
        raise ApiError('validation_error', 'O post precisa de texto ou mídia.', 422,
                       {'content': 'Escreva algo ou anexe uma mídia.'})

    # Valida o spot (se informado e aprovado).
    if spot_id in ('', None):
        spot_id = None
    else:
        try:
            spot_id = int(spot_id)
        except (TypeError, ValueError):
            raise ApiError('validation_error', 'Pico inválido.', 422, {'spot_id': 'ID inválido.'})
        if Spot.query.get(spot_id) is None:
            raise ApiError('not_found', 'Pico não encontrado.', 404)

    post = Post(content=content, user_id=viewer.id, spot_id=spot_id, post_type='regular')
    _apply_media(post, media)
    post.media_status = 'ready'

    db.session.add(post)
    award(viewer, 'report' if spot_id else 'post')  # relato (com pico) vale mais
    db.session.commit()

    return jsonify({'post': post_card(post, viewer=viewer)}), 201


@posts_api.route('/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    viewer = current_api_user()
    post = _get_post_or_404(post_id)
    if post.user_id != viewer.id and not viewer.is_admin:
        raise ApiError('forbidden', 'Você não pode remover este post.', 403)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'ok': True})


# ── Likes ─────────────────────────────────────────────────────────────────────

@posts_api.route('/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    from gamification import award
    from models import Like, Notification

    viewer = current_api_user()
    post = _get_post_or_404(post_id)

    existing = Like.query.filter_by(user_id=viewer.id, post_id=post_id).first()
    if existing is None:  # idempotente
        db.session.add(Like(user_id=viewer.id, post_id=post_id))
        if viewer.id != post.user_id:
            award(post.author, 'like_received')
        db.session.commit()
        if viewer.id != post.user_id:
            Notification.create_like_notification(viewer, post)

    likes = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'liked': True, 'likes': likes})


@posts_api.route('/posts/<int:post_id>/like', methods=['DELETE'])
def unlike_post(post_id):
    from models import Like

    viewer = current_api_user()
    _get_post_or_404(post_id)

    existing = Like.query.filter_by(user_id=viewer.id, post_id=post_id).first()
    if existing is not None:  # idempotente
        db.session.delete(existing)
        db.session.commit()

    likes = Like.query.filter_by(post_id=post_id).count()
    return jsonify({'liked': False, 'likes': likes})


# ── Comentários ───────────────────────────────────────────────────────────────

@posts_api.route('/posts/<int:post_id>/comments', methods=['GET'])
def list_comments(post_id):
    from models import Comment

    current_api_user(optional=True)
    _get_post_or_404(post_id)
    query = Comment.query.filter_by(post_id=post_id)
    items, next_cursor = paginate_query(
        query, Comment, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [comment_card(c) for c in items],
        'next_cursor': next_cursor,
    })


@posts_api.route('/posts/<int:post_id>/comments', methods=['POST'])
def add_comment(post_id):
    from gamification import award
    from models import Comment, Notification

    viewer = current_api_user()
    post = _get_post_or_404(post_id)
    data = body()
    require_fields(data, 'content')
    content = data['content'].strip()
    if not content:
        raise ApiError('validation_error', 'O comentário não pode ser vazio.', 422,
                       {'content': 'Escreva algo.'})

    comment = Comment(content=content, user_id=viewer.id, post_id=post_id)
    db.session.add(comment)
    award(viewer, 'comment')
    if viewer.id != post.user_id:
        award(post.author, 'comment_received')
    db.session.commit()

    if viewer.id != post.user_id:
        Notification.create_comment_notification(viewer, post, content)

    return jsonify({'comment': comment_card(comment)}), 201


@posts_api.route('/comments/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    from models import Comment

    viewer = current_api_user()
    comment = Comment.query.get(comment_id)
    if comment is None:
        raise ApiError('not_found', 'Comentário não encontrado.', 404)
    if (comment.user_id != viewer.id
            and comment.post.user_id != viewer.id
            and not viewer.is_admin):
        raise ApiError('forbidden', 'Você não pode remover este comentário.', 403)
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'ok': True})
