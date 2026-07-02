"""Stories (efêmeros, 24h) da API (`/api/v1/stories`) — Prompt A4.

Espelha a story bar do site (`routes/stories.build_story_bar`): agrupada por
usuário, "eu" primeiro, depois quem tem story não visto. A mídia vem do
Cloudinary (upload assinado A11). Expira em 24h (regra atual).

Endpoints:
- GET    /stories            → story bar agrupada (de quem sigo + eu)
- POST   /stories            → cria story (imagem/vídeo)
- POST   /stories/:id/seen   → marca visto (idempotente)
- DELETE /stories/:id        → apaga story próprio
"""
from datetime import datetime, timedelta

from flask import Blueprint, jsonify

from extensions import db
from .deps import body, current_api_user, require_fields
from .errors import ApiError
from .serializers import avatar_url, iso, media_url

stories_api = Blueprint('stories_api', __name__, url_prefix='/stories')

STORY_TTL_HOURS = 24
ALLOWED_TYPES = {'image', 'video'}


def _story_media_url(story):
    """URL absoluta da mídia do story (Cloudinary como está; local via /static)."""
    return media_url(story.media_url)


@stories_api.route('', methods=['GET'])
def story_bar():
    """Story bar agrupada por usuário (mesmo comportamento do site)."""
    from routes.stories import cleanup_expired_stories
    from models import Story, StoryView

    viewer = current_api_user()
    cleanup_expired_stories()
    now = datetime.utcnow()

    following_ids = [f.followed_id for f in viewer.followed.all()]
    relevant_ids = set(following_ids + [viewer.id])

    active = (Story.query
             .filter(Story.user_id.in_(relevant_ids), Story.expires_at > now)
             .order_by(Story.created_at.asc())
             .all())

    viewed_ids = {v.story_id for v in StoryView.query.filter_by(user_id=viewer.id).all()}

    grouped = {}
    for s in active:
        grouped.setdefault(s.user_id, []).append(s)

    bar = []
    for uid, items in grouped.items():
        author = items[0].author
        is_self = uid == viewer.id
        bar.append({
            'user_id': uid,
            'username': author.username,
            'avatar_url': avatar_url(author),
            'is_self': is_self,
            'has_unseen': any(s.id not in viewed_ids for s in items),
            'stories': [
                {
                    'id': s.id,
                    'url': _story_media_url(s),
                    'type': s.media_type,
                    'created_at': iso(s.created_at),
                    'seen': s.id in viewed_ids,
                    'can_delete': is_self,
                }
                for s in items
            ],
        })

    # Eu primeiro, depois quem tem story não visto, depois o resto.
    bar.sort(key=lambda b: (not b['is_self'], not b['has_unseen']))
    return jsonify({'items': bar})


@stories_api.route('', methods=['POST'])
def create_story():
    """Cria um story a partir de uma mídia já enviada ao Cloudinary (A11)."""
    from models import Story

    viewer = current_api_user()
    data = body()
    require_fields(data, 'media_url')

    media_type = (data.get('media_type') or 'image').strip().lower()
    if media_type not in ALLOWED_TYPES:
        raise ApiError('validation_error', 'Tipo de mídia inválido.', 422,
                       {'media_type': 'Use "image" ou "video".'})

    now = datetime.utcnow()
    story = Story(
        user_id=viewer.id,
        media_url=data['media_url'].strip(),
        media_type=media_type,
        cloud_public_id=(data.get('public_id') or '').strip() or None,
        cloud_resource_type=media_type,
        created_at=now,
        expires_at=now + timedelta(hours=STORY_TTL_HOURS),
    )
    db.session.add(story)
    db.session.commit()

    return jsonify({
        'story': {
            'id': story.id,
            'url': _story_media_url(story),
            'type': story.media_type,
            'created_at': iso(story.created_at),
            'expires_at': iso(story.expires_at),
        },
    }), 201


@stories_api.route('/<int:story_id>/seen', methods=['POST'])
def mark_seen(story_id):
    """Marca um story como visto (idempotente)."""
    from models import Story, StoryView

    viewer = current_api_user()
    story = Story.query.get(story_id)
    if story is None:
        raise ApiError('not_found', 'Story não encontrado.', 404)

    if StoryView.query.filter_by(story_id=story_id, user_id=viewer.id).first() is None:
        db.session.add(StoryView(story_id=story_id, user_id=viewer.id))
        db.session.commit()

    return jsonify({'ok': True})


@stories_api.route('/<int:story_id>', methods=['DELETE'])
def delete_story(story_id):
    """Apaga um story próprio (também remove a mídia do Cloudinary)."""
    from routes.stories import _delete_story_media
    from models import Story

    viewer = current_api_user()
    story = Story.query.get(story_id)
    if story is None:
        raise ApiError('not_found', 'Story não encontrado.', 404)
    if story.user_id != viewer.id and not viewer.is_admin:
        raise ApiError('forbidden', 'Você não pode apagar este story.', 403)

    try:
        _delete_story_media(story)
    except Exception:
        pass  # best-effort: mesmo se a mídia não sair, remove o registro
    db.session.delete(story)
    db.session.commit()
    return jsonify({'ok': True})
