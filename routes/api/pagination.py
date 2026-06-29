"""Paginação cursor-based para os feeds da API.

Em vez de `OFFSET` (lento em listas grandes), usamos um cursor opaco que aponta
para a última linha vista. Para feeds ordenados por id desc (o caso comum:
posts, comentários, notificações), o cursor é só o `id` da última linha,
codificado em base64 para o cliente tratá-lo como opaco.

    GET /api/v1/feed?cursor=<opaco>&limit=20
    → { "items": [...], "next_cursor": "..." | null }

`next_cursor` é null quando não há mais páginas.
"""
import base64

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def encode_cursor(value):
    """Codifica um valor (id) num cursor opaco. None → None."""
    if value is None:
        return None
    raw = str(value).encode('utf-8')
    return base64.urlsafe_b64encode(raw).decode('ascii')


def decode_cursor(cursor):
    """Decodifica o cursor opaco de volta pra um int. Inválido → None."""
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode('ascii'))
        return int(raw.decode('utf-8'))
    except (ValueError, TypeError, Exception):
        return None


def clamp_limit(raw_limit):
    """Normaliza o `limit` do cliente para [1, MAX_LIMIT]."""
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def paginate_query(query, model, cursor=None, limit=DEFAULT_LIMIT, order_column=None):
    """Pagina uma query por id decrescente (mais novo primeiro).

    - `query`: SQLAlchemy query já filtrada (sem order_by/limit).
    - `model`: a classe do model (para acessar a coluna de ordenação).
    - `order_column`: coluna de ordenação; default `model.id`.

    Retorna `(items, next_cursor)`. Busca `limit + 1` para saber se há próxima
    página sem um COUNT extra.
    """
    col = order_column if order_column is not None else model.id
    limit = clamp_limit(limit)

    last_id = decode_cursor(cursor)
    if last_id is not None:
        query = query.filter(col < last_id)

    rows = query.order_by(col.desc()).limit(limit + 1).all()

    has_more = len(rows) > limit
    items = rows[:limit]
    next_cursor = encode_cursor(getattr(items[-1], 'id')) if has_more and items else None
    return items, next_cursor


def paginated_response(items, next_cursor, serializer):
    """Monta o corpo `{ "items": [...], "next_cursor": ... }`."""
    return {
        'items': [serializer(item) for item in items],
        'next_cursor': next_cursor,
    }
