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
