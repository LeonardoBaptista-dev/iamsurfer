"""Fundação da API REST do app mobile — `/api/v1`.

Um blueprint novo que **convive** com o site Jinja: reaproveita os mesmos
models, DB e Cloudinary, sem tocar nas rotas existentes. O site continua usando
Flask-Login (sessão/cookie); a API usa JWT (access 15 min + refresh 30 dias
rotativo com blocklist).

Uso (em app.py, após registrar os blueprints do site):

    from routes.api import register_api
    register_api(app)
"""
import os
from datetime import timedelta

from flask import Blueprint, jsonify

from .errors import register_error_handlers, error_response

# Extensões da API — instanciadas aqui, inicializadas em register_api(app).
# Import preguiçoso para não quebrar o site caso as libs não estejam instaladas
# em algum ambiente legado (degrada com mensagem clara em vez de erro de import).
try:
    from flask_jwt_extended import JWTManager
    from flask_cors import CORS
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    _DEPS_OK = True
except ImportError as exc:  # pragma: no cover
    _DEPS_OK = False
    _IMPORT_ERROR = exc

API_VERSION = '1'

if _DEPS_OK:
    jwt = JWTManager()
    limiter = Limiter(key_func=get_remote_address, default_limits=[])
else:  # pragma: no cover
    jwt = None
    limiter = None

# Blueprint raiz da API. Sub-blueprints (auth, users, feed, ...) são aninhados.
api = Blueprint('api', __name__, url_prefix='/api/v1')


def _configure_jwt(app):
    """Configura chaves e expiração do JWT a partir do ambiente."""
    app.config.setdefault(
        'JWT_SECRET_KEY',
        os.environ.get('JWT_SECRET_KEY') or app.config.get('SECRET_KEY'),
    )
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    app.config.setdefault('JWT_TOKEN_LOCATION', ['headers'])
    jwt.init_app(app)

    @jwt.token_in_blocklist_loader
    def _check_revoked(_jwt_header, jwt_payload):
        from models import TokenBlocklist
        jti = jwt_payload['jti']
        return TokenBlocklist.query.filter_by(jti=jti).first() is not None

    # Respostas de erro do JWT no formato padrão da API.
    @jwt.unauthorized_loader
    def _missing(_reason):
        return error_response('unauthorized', 'Autenticação necessária.', 401)

    @jwt.invalid_token_loader
    def _invalid(_reason):
        return error_response('invalid_token', 'Token inválido.', 401)

    @jwt.expired_token_loader
    def _expired(_header, _payload):
        return error_response('token_expired', 'Sessão expirada. Renove o acesso.', 401)

    @jwt.revoked_token_loader
    def _revoked(_header, _payload):
        return error_response('token_revoked', 'Sessão revogada. Faça login novamente.', 401)

    @jwt.needs_fresh_token_loader
    def _needs_fresh(_header, _payload):
        return error_response('fresh_token_required', 'Reautenticação necessária.', 401)


def _configure_cors(app):
    """CORS liberado para as origins do app (env `API_CORS_ORIGINS`, csv)."""
    origins_raw = os.environ.get('API_CORS_ORIGINS', '*').strip()
    origins = '*' if origins_raw == '*' else [o.strip() for o in origins_raw.split(',') if o.strip()]
    CORS(app, resources={r'/api/*': {'origins': origins}}, supports_credentials=False)


def register_api(app):
    """Ponto de entrada: liga JWT, CORS, rate limit, rotas e handlers à app."""
    if not _DEPS_OK:  # pragma: no cover
        app.logger.error(
            'API mobile desativada: dependências ausentes (%s). '
            'Rode `pip install -r requirements.txt`.', _IMPORT_ERROR,
        )
        return

    _configure_jwt(app)
    _configure_cors(app)
    limiter.init_app(app)

    # Rate limit padrão só no blueprint da API (o site Jinja fica intocado).
    limiter.limit('120 per minute')(api)

    # Registra os sub-blueprints de cada feature.
    from .auth import auth_api
    from .spots import spots_api
    from .media import media_api
    from .users import users_api
    from .posts import posts_api
    api.register_blueprint(auth_api)
    api.register_blueprint(spots_api)
    api.register_blueprint(media_api)
    api.register_blueprint(users_api)
    api.register_blueprint(posts_api)

    register_error_handlers(app, api)
    app.register_blueprint(api)
    app.logger.info('API mobile registrada em /api/v1 (versão %s).', API_VERSION)


@api.route('/ping')
def ping():
    """Healthcheck público da API."""
    return jsonify({'ok': True, 'version': API_VERSION})
