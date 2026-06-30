"""Serializers da API (`to_dict`) — contrato de dados estável (doc seção 2).

Cada função converte um model num dict JSON-serializável com shape fixo. O
`viewer` (usuário autenticado) é sempre opcional e usado para preencher
`viewer_state` (ex.: "eu sigo essa pessoa?") sem N+1 no app.

Princípios:
- URLs de mídia sempre absolutas (o app não sabe o host do backend).
- Datas em ISO-8601 UTC com sufixo Z.
- Nunca expor `password_hash`, e-mail de terceiros, ou campos internos.
"""
from flask import url_for


# ── Helpers ──────────────────────────────────────────────────────────────────

def iso(dt):
    """datetime → ISO-8601 UTC ('2026-06-26T14:30:00Z'). None → None."""
    if dt is None:
        return None
    # Os timestamps do projeto são naive em UTC (datetime.utcnow); marcamos Z.
    return dt.replace(microsecond=0).isoformat() + 'Z'


def media_url(path):
    """Resolve uma URL de mídia para absoluta.

    - Cloudinary / http(s): devolve como está.
    - Caminho local (ex.: 'uploads/...'): vira URL absoluta de /static.
    - Vazio: None.
    """
    if not path:
        return None
    if path.startswith('http://') or path.startswith('https://') or 'cloudinary.com' in path:
        return path
    try:
        return url_for('static', filename=path, _external=True)
    except Exception:
        # Fora de um request context (ex.: testes unitários puros).
        return '/static/' + path


def avatar_url(user):
    """Melhor URL de avatar disponível para o usuário (absoluta)."""
    urls = user.profile_image_urls if isinstance(user.profile_image_urls, dict) else None
    if urls:
        path = urls.get('small') or urls.get('thumbnail') or urls.get('medium')
        if path:
            return media_url(path)
    return media_url(user.profile_image or 'uploads/default_profile.jpg')


# ── User ─────────────────────────────────────────────────────────────────────

def user_brief(user):
    """Versão enxuta do usuário (autor de post, item de lista, etc.)."""
    if user is None:
        return None
    return {
        'id': user.id,
        'username': user.username,
        'avatar_url': avatar_url(user),
        'patente': _patente_brief(user),
    }


def user_full(user, viewer=None):
    """Serializer canônico de User (doc seção 2)."""
    if user is None:
        return None
    pat = user.patente  # dict completo da gamificação
    return {
        'id': user.id,
        'username': user.username,
        'avatar_url': avatar_url(user),
        'bio': user.bio or '',
        'location': user.location or '',
        'is_public': bool(user.is_public),
        'points': user.points or 0,
        'patente': {'slug': pat['slug'], 'name': pat['name'], 'icon': pat['icon']},
        'counts': {
            'posts': user.posts.count(),
            'followers': user.followers.count(),
            'following': user.followed.count(),
        },
        'viewer_state': _viewer_state(user, viewer),
        'joined_at': iso(user.joined_at),
    }


def me_full(user):
    """Serializer do próprio usuário (inclui campos privados como e-mail)."""
    data = user_full(user, viewer=user)
    data['email'] = user.email
    data['is_admin'] = bool(user.is_admin)
    return data


def _patente_brief(user):
    pat = user.patente
    return {'slug': pat['slug'], 'name': pat['name'], 'icon': pat['icon']}


def _viewer_state(user, viewer):
    if viewer is None:
        return {'is_following': False, 'is_self': False}
    is_self = viewer.id == user.id
    return {
        'is_following': (not is_self) and viewer.is_following(user),
        'is_self': is_self,
    }


# ── Privacidade ──────────────────────────────────────────────────────────────

def can_view_content(user, viewer):
    """True se `viewer` pode ver o conteúdo (posts) de `user`.

    Perfil público: todos veem. Privado: só o próprio dono ou quem já o segue.
    Espelha a regra de privacidade da web aplicada à API (doc seção 5).
    """
    if user.is_public:
        return True
    if viewer is None:
        return False
    return viewer.id == user.id or viewer.is_following(user)


# ── Post ─────────────────────────────────────────────────────────────────────

def post_media(post):
    """Lista de mídias do post (imagens + vídeo), com URLs absolutas.

    Shape de cada item: { type: 'image'|'video', url, thumb_url }.
    """
    media = []
    urls = post.image_urls if isinstance(post.image_urls, dict) else None
    if urls:
        full = urls.get('large') or urls.get('medium') or urls.get('small') or urls.get('original')
        thumb = urls.get('small') or urls.get('thumbnail') or full
        if full:
            media.append({'type': 'image', 'url': media_url(full), 'thumb_url': media_url(thumb)})
    elif post.image_url:
        media.append({'type': 'image', 'url': media_url(post.image_url), 'thumb_url': media_url(post.image_url)})

    if post.video_url:
        thumb = None
        if urls:
            thumb = urls.get('small') or urls.get('thumbnail')
        media.append({'type': 'video', 'url': media_url(post.video_url),
                      'thumb_url': media_url(thumb) if thumb else None})
    return media


def post_card(post, viewer=None):
    """Serializer de Post para feed/grid de perfil (doc A3).

    Traz `media[]`, `author`, `counts` e `viewer_state.liked`. Os comentários em
    si vêm paginados por endpoint próprio (A3).
    """
    from models import Like

    liked = False
    if viewer is not None:
        liked = Like.query.filter_by(user_id=viewer.id, post_id=post.id).first() is not None

    media = post_media(post)
    return {
        'id': post.id,
        'content': post.content or '',
        'created_at': iso(post.created_at),
        'author': user_brief(post.author),
        'media': media,
        'media_status': post.media_status or 'ready',
        'is_reel': post.is_reel,
        'spot': spot_brief(post.spot) if post.spot else None,
        'counts': {
            'likes': len(post.likes),
            'comments': len(post.comments),
        },
        'viewer_state': {'liked': liked},
    }


# ── Spot (pico) ──────────────────────────────────────────────────────────────

def _spot_cover_url(spot):
    """URL absoluta da foto de capa do pico (ou None)."""
    from models import SpotPhotoNew
    cover = SpotPhotoNew.query.filter_by(spot_id=spot.id, is_cover=True).first()
    if cover:
        return media_url('uploads/spots/' + cover.filename)
    return None


def spot_brief(spot):
    """Versão enxuta do pico (item de lista / marcador no mapa)."""
    from br_states import normalize_state
    return {
        'id': spot.id,
        'name': spot.name,
        'city': spot.city or '',
        'state': normalize_state(spot.state) or '',
        'country': spot.country or 'Brasil',
        'lat': spot.latitude,
        'lng': spot.longitude,
        'difficulty': spot.difficulty or None,
        'wave_type': spot.wave_type or None,
        'cover_url': _spot_cover_url(spot),
    }


def spot_full(spot, viewer=None):
    """Serializer completo do pico (tela de detalhe)."""
    from models import SpotFollow
    data = spot_brief(spot)
    data.update({
        'address': spot.address or '',
        'description': spot.description or '',
        'bottom_type': spot.bottom_type or None,
        'crowd_level': spot.crowd_level or None,
        'best_wind_direction': spot.best_wind_direction or None,
        'best_swell_direction': spot.best_swell_direction or None,
        'best_tide': spot.best_tide or None,
        'best_season': spot.best_season or None,
        'water_temp': spot.water_temp or None,
        'min_swell_size': spot.min_swell_size,
        'max_swell_size': spot.max_swell_size,
        'status': spot.status,
        'followers_count': SpotFollow.query.filter_by(spot_id=spot.id).count(),
        'created_at': iso(spot.created_at),
        'viewer_state': {
            'is_following': bool(viewer) and SpotFollow.query.filter_by(
                user_id=viewer.id, spot_id=spot.id).first() is not None,
        },
    })
    return data
