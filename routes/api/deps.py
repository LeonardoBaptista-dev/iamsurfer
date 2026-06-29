"""Helpers compartilhados pelas rotas da API: tokens, usuário atual, parsing.

Mantém as rotas enxutas e o comportamento de auth consistente em todo `/api/v1`.
"""
from functools import wraps

from flask import request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)

from extensions import db
from .errors import ApiError


def issue_tokens(user):
    """Gera o par (access, refresh) para um usuário. Identity = id (string)."""
    identity = str(user.id)
    return {
        'access_token': create_access_token(identity=identity),
        'refresh_token': create_refresh_token(identity=identity),
    }


def current_api_user(optional=False):
    """Retorna o User autenticado pelo JWT do request, ou levanta 401.

    Com `optional=True`, retorna None quando não há token (rota pública que
    enriquece a resposta se logado).
    """
    from models import User

    verify_jwt_in_request(optional=optional)
    identity = get_jwt_identity()
    if identity is None:
        if optional:
            return None
        raise ApiError('unauthorized', 'Autenticação necessária.', 401)

    user = User.query.get(int(identity))
    if user is None:
        raise ApiError('unauthorized', 'Sessão inválida.', 401)
    return user


def revoke_token():
    """Revoga o token atual (adiciona o jti à blocklist). Idempotente."""
    from models import TokenBlocklist

    claims = get_jwt()
    jti = claims['jti']
    if TokenBlocklist.query.filter_by(jti=jti).first() is None:
        db.session.add(TokenBlocklist(
            jti=jti,
            token_type=claims.get('type', 'refresh'),
            user_id=int(get_jwt_identity()) if get_jwt_identity() else None,
        ))


def body():
    """JSON do corpo do request como dict (vazio se ausente/ inválido)."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def require_fields(data, *names):
    """Valida presença de campos não-vazios; levanta ApiError 422 com `fields`."""
    missing = {}
    for name in names:
        value = data.get(name)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing[name] = 'Campo obrigatório.'
    if missing:
        raise ApiError('validation_error', 'Verifique os campos informados.', 422, missing)
