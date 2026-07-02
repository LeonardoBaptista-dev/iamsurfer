"""Reels (vídeos verticais) da API (`/api/v1/reels`) — Prompt A5.

Reels são `Post` com `post_type='reel'` e `video_url` (mesma fonte de
`main.reels`). Like e comentário reutilizam os endpoints de posts (A3), já que
um reel é um post. A mídia (vídeo) vem do Cloudinary via upload assinado (A11).
"""
from flask import Blueprint, jsonify, request

from extensions import db
from .deps import body, current_api_user
from .errors import ApiError
from .pagination import clamp_limit, paginate_query
from .serializers import post_card

reels_api = Blueprint('reels_api', __name__, url_prefix='/reels')


@reels_api.route('', methods=['GET'])
def list_reels():
    """Feed de reels (cursor), mais recentes primeiro, de perfis públicos."""
    from models import Post, User

    viewer = current_api_user(optional=True)
    query = (Post.query.join(User, Post.user_id == User.id)
             .filter(Post.post_type == 'reel',
                     Post.video_url.isnot(None),
                     User.is_public == True,  # noqa: E712
                     User.is_admin == False))  # noqa: E712
    items, next_cursor = paginate_query(
        query, Post, cursor=request.args.get('cursor'),
        limit=clamp_limit(request.args.get('limit')),
    )
    return jsonify({
        'items': [post_card(p, viewer=viewer) for p in items],
        'next_cursor': next_cursor,
    })


@reels_api.route('', methods=['POST'])
def create_reel():
    """Cria um reel. Exige um vídeo (via mídia do Cloudinary)."""
    from gamification import award
    from models import Post

    viewer = current_api_user()
    data = body()
    content = (data.get('content') or '').strip()
    media = data.get('media') or []

    video_url = None
    if isinstance(media, list):
        for m in media:
            if isinstance(m, dict) and (m.get('type') or 'image') == 'video':
                video_url = (m.get('url') or m.get('secure_url') or '').strip() or None
                if video_url:
                    break
    if not video_url:
        raise ApiError('validation_error', 'Um reel precisa de um vídeo.', 422,
                       {'media': 'Envie um vídeo.'})

    reel = Post(content=content, user_id=viewer.id, post_type='reel',
                video_url=video_url, media_status='ready')
    db.session.add(reel)
    award(viewer, 'post')
    db.session.commit()

    return jsonify({'reel': post_card(reel, viewer=viewer)}), 201
