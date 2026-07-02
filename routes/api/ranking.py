"""Ranking e selos (gamificação) da API (`/api/v1`) — Prompt A10.

Reaproveita `gamification.py` (XP/patente já vêm no serializer de User) e
`badges.py`/`UserBadge` (selos de papel). Ranking exclui admins, igual à web.
"""
from flask import Blueprint, jsonify, request

from .deps import current_api_user
from .errors import ApiError
from .serializers import user_brief

ranking_api = Blueprint('ranking_api', __name__)

MAX_LIMIT = 50
DEFAULT_LIMIT = 20


def _clamp(raw, default, hi):
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return default
    return max(0, min(v, hi))


@ranking_api.route('/ranking', methods=['GET'])
def ranking():
    """Ranking por XP (offset/limit). Cada item traz `rank` e `points`.

    Offset-based (e não cursor) porque é um placar limitado e ordenado por
    pontuação: o cliente pede páginas fixas e mostra a posição absoluta.
    """
    from models import User

    limit = _clamp(request.args.get('limit'), DEFAULT_LIMIT, MAX_LIMIT)
    offset = _clamp(request.args.get('offset'), 0, 100_000)

    base = User.query.filter(User.is_admin == False)  # noqa: E712
    total = base.count()
    rows = (base.order_by(User.points.desc(), User.username.asc())
            .offset(offset).limit(limit).all())

    items = []
    for i, u in enumerate(rows):
        item = user_brief(u)
        item['points'] = u.points or 0
        item['rank'] = offset + i + 1
        items.append(item)

    # Posição do próprio usuário (se autenticado e não-admin).
    viewer = current_api_user(optional=True)
    my_rank = None
    if viewer is not None and not viewer.is_admin:
        ahead = User.query.filter(
            User.is_admin == False,  # noqa: E712
            User.points > (viewer.points or 0),
        ).count()
        my_rank = ahead + 1

    return jsonify({
        'items': items,
        'total': total,
        'my_rank': my_rank,
        'next_offset': offset + limit if offset + limit < total else None,
    })


@ranking_api.route('/users/<username>/badges', methods=['GET'])
def user_badges(username):
    """Selos de papel ativos do usuário (fotógrafo, atleta, etc.)."""
    from datetime import datetime
    from sqlalchemy import func
    from badges import info
    from models import User, UserBadge

    user = User.query.filter(func.lower(User.username) == username.lower()).first()
    if user is None:
        raise ApiError('not_found', 'Usuário não encontrado.', 404)

    now = datetime.utcnow()
    rows = UserBadge.query.filter_by(user_id=user.id, status='active').all()
    badges = []
    for b in rows:
        if b.expires_at is not None and b.expires_at < now:
            continue
        meta = info(b.type) or {}
        badges.append({
            'type': b.type,
            'label': meta.get('label', b.type),
            'icon': meta.get('icon'),
            'desc': meta.get('desc'),
            'granted_at': b.granted_at.replace(microsecond=0).isoformat() + 'Z' if b.granted_at else None,
        })

    return jsonify({'badges': badges})
