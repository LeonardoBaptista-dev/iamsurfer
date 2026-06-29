"""Auth da API (`/api/v1/auth/*`) — registro, login, refresh, logout, eu.

Reaproveita as regras do site (`routes/auth.py`): senha >= 8, login por e-mail
OU username case-insensitive. A senha nunca volta no JSON.
"""
import re

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func

from extensions import db
from . import limiter
from .deps import body, require_fields, issue_tokens, current_api_user, revoke_token
from .errors import ApiError
from .serializers import me_full, user_full

auth_api = Blueprint('auth_api', __name__, url_prefix='/auth')

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# ── Registro ────────────────────────────────────────────────────────────────

@auth_api.route('/register', methods=['POST'])
@limiter.limit('5 per minute')
def register():
    from models import User

    data = body()
    require_fields(data, 'username', 'email', 'password')

    username = data['username'].strip()
    email = data['email'].strip().lower()
    password = data['password']

    fields = {}
    if len(username) < 3:
        fields['username'] = 'Use ao menos 3 caracteres.'
    if not _EMAIL_RE.match(email):
        fields['email'] = 'E-mail inválido.'
    if len(password) < 8:
        fields['password'] = 'A senha precisa ter ao menos 8 caracteres.'
    if fields:
        raise ApiError('validation_error', 'Verifique os campos informados.', 422, fields)

    # Unicidade case-insensitive (igual ao login).
    if User.query.filter(func.lower(User.username) == username.lower()).first():
        raise ApiError('username_taken', 'Esse nome de usuário já está em uso.', 409,
                       {'username': 'Já está em uso.'})
    if User.query.filter(func.lower(User.email) == email).first():
        raise ApiError('email_taken', 'Esse e-mail já está cadastrado.', 409,
                       {'email': 'Já cadastrado.'})

    user = User(username=username, email=email)
    user.set_password(password)
    if User.query.count() == 0:  # primeiro usuário é admin (igual à web)
        user.is_admin = True
    db.session.add(user)
    db.session.commit()

    tokens = issue_tokens(user)
    return jsonify({**tokens, 'user': me_full(user)}), 201


# ── Login ────────────────────────────────────────────────────────────────────

@auth_api.route('/login', methods=['POST'])
@limiter.limit('5 per minute')
def login():
    from models import User

    data = body()
    require_fields(data, 'identifier', 'password')
    identifier = data['identifier'].strip().lower()
    password = data['password']

    user = User.query.filter(
        db.or_(
            func.lower(User.username) == identifier,
            func.lower(User.email) == identifier,
        )
    ).first()

    if not user or not user.check_password(password):
        # Mensagem genérica de propósito (não revela se o usuário existe).
        raise ApiError('invalid_credentials', 'Credenciais inválidas.', 401)

    tokens = issue_tokens(user)
    return jsonify({**tokens, 'user': me_full(user)})


# ── Refresh (rotação) ────────────────────────────────────────────────────────

@auth_api.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Gera novo access + refresh e revoga o refresh usado (rotação)."""
    user = current_api_user(verify=False)  # @jwt_required(refresh=True) já validou
    revoke_token()  # invalida o refresh atual
    db.session.commit()
    tokens = issue_tokens(user)
    return jsonify(tokens)


# ── Logout ───────────────────────────────────────────────────────────────────

@auth_api.route('/logout', methods=['POST'])
@jwt_required(refresh=True)
def logout():
    """Revoga o refresh atual. O access expira sozinho em até 15 min."""
    revoke_token()
    db.session.commit()
    return jsonify({'ok': True})


# ── Eu ───────────────────────────────────────────────────────────────────────

@auth_api.route('/me', methods=['GET'])
@jwt_required()
def me():
    user = current_api_user()
    return jsonify({'user': me_full(user)})


# ── Expo push token ──────────────────────────────────────────────────────────

@auth_api.route('/push-token', methods=['POST'])
@jwt_required()
def register_push_token():
    """Upsert do Expo push token do device atual."""
    from models import DeviceToken

    user = current_api_user()
    data = body()
    require_fields(data, 'token')
    token = data['token'].strip()
    platform = (data.get('platform') or '').strip().lower() or None

    existing = DeviceToken.query.filter_by(token=token).first()
    if existing:
        existing.user_id = user.id  # device pode ter trocado de dono
        existing.platform = platform
    else:
        db.session.add(DeviceToken(user_id=user.id, token=token, platform=platform))
    db.session.commit()
    return jsonify({'ok': True})
