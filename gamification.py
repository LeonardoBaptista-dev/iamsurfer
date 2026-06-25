"""Gamificação do IAmSurfer: XP (pontos) e patentes (níveis).

XP é ganho em ações que geram valor para a comunidade. A patente é calculada
na hora a partir do total de pontos (sem tabela extra).
"""
from extensions import db

# Quantos pontos cada evento vale
POINTS = {
    'post': 10,             # criar post
    'report': 15,           # post com pico (relato de condições)
    'spot': 50,             # criar pico (ao ser aprovado)
    'trip_create': 20,      # criar carona
    'trip_join': 10,        # participar de carona (confirmado)
    'session_log': 8,       # registrar sessão no diário de surfe
    'comment': 3,           # comentar
    'comment_received': 2,  # receber comentário
    'like_received': 2,     # receber curtida
    'follower': 5,          # ganhar seguidor
}

# (xp_mínimo, slug, nome, ícone Bootstrap) — ordem crescente.
# Ícones do Bootstrap Icons (sem emojis) renderizados como <i class="bi ...">.
LEVELS = [
    (0,    'marola',      'Marola',        'bi-droplet'),
    (100,  'surfista',    'Surfista',      'bi-water'),
    (300,  'local',       'Local',         'bi-pin-map-fill'),
    (700,  'free-surfer', 'Free Surfer',   'bi-stars'),
    (1500, 'big-rider',   'Big Rider',     'bi-fire'),
    (3000, 'lenda',       'Lenda do Pico', 'bi-trophy-fill'),
]


def award(user, event, n=1, commit=False):
    """Soma o XP do evento ao usuário.

    Por padrão NÃO faz commit — as rotas que chamam já commitam a transação.
    Use commit=True para casos isolados.
    """
    if user is None:
        return
    pts = POINTS.get(event, 0) * n
    if not pts:
        return
    user.points = (user.points or 0) + pts
    if commit:
        db.session.commit()


def patente(points):
    """Retorna a patente atual e o progresso para a próxima."""
    points = points or 0
    current = LEVELS[0]
    nxt = None
    for i, lvl in enumerate(LEVELS):
        if points >= lvl[0]:
            current = lvl
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None

    if nxt:
        span = nxt[0] - current[0]
        progress = int((points - current[0]) * 100 / span) if span else 100
        to_next = max(0, nxt[0] - points)
    else:
        progress = 100
        to_next = 0

    return {
        'slug': current[1],
        'name': current[2],
        'icon': current[3],
        'points': points,
        'progress': progress,
        'next_name': nxt[2] if nxt else None,
        'next_icon': nxt[3] if nxt else None,
        'to_next': to_next,
    }
