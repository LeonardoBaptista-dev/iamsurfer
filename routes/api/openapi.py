"""Geração do spec OpenAPI 3.1 da API (`/api/v1`) — Prompt A13.

Abordagem: os **paths** são gerados a partir do `app.url_map` em runtime (fonte
única de verdade das rotas), enquanto os **componentes** (schemas reutilizáveis)
são escritos à mão a partir dos serializers reais (`serializers.py`). Assim o spec
nunca sai de sincronia com as rotas de fato registradas.

Servido publicamente em `GET /api/v1/openapi.json` (ver `__init__.py`) e também
salvo estático em `docs/api/openapi.json` (via `scripts` de geração).
"""
import inspect
import re

# Regex dos conversores de rota do Flask: <int:post_id>, <username>, <path:p>...
_ARG_RE = re.compile(r'<(?:(int|float|string|path|uuid|any|default):)?([a-zA-Z_][a-zA-Z0-9_]*)>')

# Mapa converter Flask → schema OpenAPI.
_CONVERTER_SCHEMA = {
    'int': {'type': 'integer'},
    'float': {'type': 'number'},
    'string': {'type': 'string'},
    'path': {'type': 'string'},
    'uuid': {'type': 'string', 'format': 'uuid'},
    'any': {'type': 'string'},
    'default': {'type': 'string'},
    None: {'type': 'string'},
}

# Sub-blueprints conhecidos → tag legível. A tag também é derivada dinamicamente
# (strip do sufixo `_api`), este dict só documenta a ordem/nomes canônicos.
_TAGS = [
    'auth', 'users', 'posts', 'spots', 'media', 'ranking',
    'reels', 'stories', 'messages', 'trips', 'photos', 'meta',
]

API_PREFIX = '/api/v1'


# ── Detecção de rota protegida (exige JWT) ────────────────────────────────────

def _requires_auth(view_func):
    """True se a view exige autenticação.

    A API usa dois estilos: o decorator `@jwt_required()` ou o helper
    `current_api_user()` (sem `optional=True`). Inspecionamos o código-fonte da
    função original (desembrulhada dos decorators) para detectar qualquer um.
    """
    try:
        fn = inspect.unwrap(view_func)
        src = inspect.getsource(fn)
    except (OSError, TypeError, ValueError):
        return False
    if 'jwt_required' in src:
        return True
    for args in re.findall(r'current_api_user\s*\(([^)]*)\)', src):
        if 'optional=True' not in args:
            return True
    return False


def _summary(view_func, method, path):
    """Resumo curto: primeira linha da docstring, ou fallback `MÉTODO path`."""
    try:
        fn = inspect.unwrap(view_func)
        doc = inspect.getdoc(fn)
    except (OSError, TypeError, ValueError):
        doc = None
    if doc:
        first = doc.strip().splitlines()[0].strip()
        if first:
            return first[:120]
    return f'{method} {path}'


# ── Conversão de path e parâmetros ────────────────────────────────────────────

def _openapi_path(rule_str):
    """`/api/v1/posts/<int:post_id>` → `/posts/{post_id}` (prefixo removido)."""
    path = _ARG_RE.sub(lambda m: '{' + m.group(2) + '}', rule_str)
    if path.startswith(API_PREFIX):
        path = path[len(API_PREFIX):]
    return path or '/'


def _path_parameters(rule_str):
    """Extrai os parâmetros de path com o schema do conversor Flask."""
    params = []
    for match in _ARG_RE.finditer(rule_str):
        converter, name = match.group(1), match.group(2)
        schema = _CONVERTER_SCHEMA.get(converter, _CONVERTER_SCHEMA[None])
        params.append({
            'name': name,
            'in': 'path',
            'required': True,
            'schema': dict(schema),
        })
    return params


def _tag_for(endpoint):
    """Deriva a tag do endpoint aninhado `api.<sub>_api.<view>`.

    - `api.auth_api.login`   → 'auth'
    - `api.posts_api.feed`   → 'posts'
    - `api.ping`             → 'meta'
    """
    parts = endpoint.split('.')
    if len(parts) >= 3:
        sub = parts[1]
        return sub[:-4] if sub.endswith('_api') else sub
    return 'meta'


def _operation_id(endpoint, method):
    """operationId único e estável por (endpoint, método)."""
    base = endpoint.replace('.', '_')
    return f'{method.lower()}_{base}'


# ── Montagem do spec ──────────────────────────────────────────────────────────

def _iter_api_rules(app):
    """Itera as regras do url_map que pertencem ao blueprint da API (`api.`)."""
    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint
        if not endpoint.startswith('api.'):
            continue
        if endpoint.endswith('.static') or endpoint == 'api.static':
            continue
        if not rule.rule.startswith(API_PREFIX):
            continue
        yield rule


def build_paths(app):
    """Constrói o objeto `paths` do OpenAPI a partir do url_map."""
    paths = {}
    for rule in _iter_api_rules(app):
        oapi_path = _openapi_path(rule.rule)
        view_func = app.view_functions.get(rule.endpoint)
        protected = _requires_auth(view_func) if view_func else False
        parameters = _path_parameters(rule.rule)
        tag = _tag_for(rule.endpoint)

        item = paths.setdefault(oapi_path, {})
        for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
            operation = {
                'operationId': _operation_id(rule.endpoint, method),
                'tags': [tag],
                'summary': _summary(view_func, method, oapi_path),
                'responses': {
                    '200': {
                        'description': 'OK',
                        'content': {
                            'application/json': {'schema': {'type': 'object'}},
                        },
                    },
                    'default': {
                        'description': 'Erro no formato padrão da API.',
                        'content': {
                            'application/json': {
                                'schema': {'$ref': '#/components/schemas/Error'},
                            },
                        },
                    },
                },
            }
            if parameters:
                operation['parameters'] = list(parameters)
            if protected:
                operation['security'] = [{'bearerAuth': []}]
                operation['responses']['401'] = {
                    'description': 'Autenticação necessária ou token inválido.',
                    'content': {
                        'application/json': {
                            'schema': {'$ref': '#/components/schemas/Error'},
                        },
                    },
                }
            item[method.lower()] = operation
    return paths


def _components():
    """Schemas reutilizáveis, escritos à mão a partir dos serializers reais."""
    schemas = {
        'Error': {
            'type': 'object',
            'description': 'Formato de erro único da API.',
            'required': ['error'],
            'properties': {
                'error': {
                    'type': 'object',
                    'required': ['code', 'message'],
                    'properties': {
                        'code': {'type': 'string',
                                 'description': 'Código estável, legível por máquina.'},
                        'message': {'type': 'string',
                                    'description': 'Mensagem humana (pt-BR).'},
                        'fields': {
                            'type': 'object',
                            'description': 'Erros de validação por campo.',
                            'additionalProperties': {'type': 'string'},
                        },
                    },
                },
            },
        },
        'Pagination': {
            'type': 'object',
            'description': 'Envelope de paginação cursor-based.',
            'required': ['items', 'next_cursor'],
            'properties': {
                'items': {'type': 'array', 'items': {}},
                'next_cursor': {
                    'type': ['string', 'null'],
                    'description': 'Cursor opaco da próxima página; null no fim.',
                },
            },
        },
        'Patente': {
            'type': 'object',
            'properties': {
                'slug': {'type': 'string'},
                'name': {'type': 'string'},
                'icon': {'type': 'string'},
            },
        },
        'UserBrief': {
            'type': 'object',
            'description': 'Versão enxuta do usuário (autor, item de lista).',
            'properties': {
                'id': {'type': 'integer'},
                'username': {'type': 'string'},
                'avatar_url': {'type': ['string', 'null']},
                'patente': {'$ref': '#/components/schemas/Patente'},
            },
        },
        'User': {
            'type': 'object',
            'description': 'Serializer canônico de usuário.',
            'properties': {
                'id': {'type': 'integer'},
                'username': {'type': 'string'},
                'avatar_url': {'type': ['string', 'null']},
                'bio': {'type': 'string'},
                'location': {'type': 'string'},
                'is_public': {'type': 'boolean'},
                'points': {'type': 'integer'},
                'patente': {'$ref': '#/components/schemas/Patente'},
                'counts': {
                    'type': 'object',
                    'properties': {
                        'posts': {'type': 'integer'},
                        'followers': {'type': 'integer'},
                        'following': {'type': 'integer'},
                    },
                },
                'viewer_state': {
                    'type': 'object',
                    'properties': {
                        'is_following': {'type': 'boolean'},
                        'is_self': {'type': 'boolean'},
                    },
                },
                'joined_at': {'type': ['string', 'null'], 'format': 'date-time'},
                'email': {'type': 'string',
                          'description': 'Só presente no próprio usuário (/auth/me).'},
                'is_admin': {'type': 'boolean',
                             'description': 'Só presente no próprio usuário.'},
            },
        },
        'Media': {
            'type': 'object',
            'properties': {
                'type': {'type': 'string', 'enum': ['image', 'video']},
                'url': {'type': ['string', 'null']},
                'thumb_url': {'type': ['string', 'null']},
            },
        },
        'Post': {
            'type': 'object',
            'description': 'Serializer de post para feed/grid.',
            'properties': {
                'id': {'type': 'integer'},
                'content': {'type': 'string'},
                'created_at': {'type': ['string', 'null'], 'format': 'date-time'},
                'author': {'$ref': '#/components/schemas/UserBrief'},
                'media': {'type': 'array',
                          'items': {'$ref': '#/components/schemas/Media'}},
                'media_status': {'type': 'string'},
                'is_reel': {'type': 'boolean'},
                'spot': {'oneOf': [{'$ref': '#/components/schemas/Spot'},
                                   {'type': 'null'}]},
                'counts': {
                    'type': 'object',
                    'properties': {
                        'likes': {'type': 'integer'},
                        'comments': {'type': 'integer'},
                    },
                },
                'viewer_state': {
                    'type': 'object',
                    'properties': {'liked': {'type': 'boolean'}},
                },
            },
        },
        'Comment': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'content': {'type': 'string'},
                'created_at': {'type': ['string', 'null'], 'format': 'date-time'},
                'author': {'$ref': '#/components/schemas/UserBrief'},
            },
        },
        'Spot': {
            'type': 'object',
            'description': 'Pico de surf (SurfMap).',
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'city': {'type': 'string'},
                'state': {'type': 'string'},
                'country': {'type': 'string'},
                'lat': {'type': ['number', 'null']},
                'lng': {'type': ['number', 'null']},
                'difficulty': {'type': ['string', 'null']},
                'wave_type': {'type': ['string', 'null']},
                'cover_url': {'type': ['string', 'null']},
                'address': {'type': 'string'},
                'description': {'type': 'string'},
                'bottom_type': {'type': ['string', 'null']},
                'crowd_level': {'type': ['string', 'null']},
                'best_wind_direction': {'type': ['string', 'null']},
                'best_swell_direction': {'type': ['string', 'null']},
                'best_tide': {'type': ['string', 'null']},
                'best_season': {'type': ['string', 'null']},
                'water_temp': {'type': ['string', 'null']},
                'min_swell_size': {'type': ['number', 'null']},
                'max_swell_size': {'type': ['number', 'null']},
                'status': {'type': 'string'},
                'followers_count': {'type': 'integer'},
                'created_at': {'type': ['string', 'null'], 'format': 'date-time'},
                'viewer_state': {
                    'type': 'object',
                    'properties': {'is_following': {'type': 'boolean'}},
                },
            },
        },
        'AuthTokens': {
            'type': 'object',
            'description': 'Par de tokens JWT (login/registro/refresh).',
            'properties': {
                'access_token': {'type': 'string'},
                'refresh_token': {'type': 'string'},
                'user': {'$ref': '#/components/schemas/User'},
            },
        },
    }
    return {
        'securitySchemes': {
            'bearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            },
        },
        'schemas': schemas,
    }


def build_openapi_spec(app):
    """Monta o documento OpenAPI 3.1 completo da API."""
    tags = [{'name': t} for t in _TAGS]
    return {
        'openapi': '3.1.0',
        'info': {
            'title': 'IAmSurfer API',
            'version': '1',
            'description': (
                'API REST versionada (/api/v1) do app mobile IAmSurfer. '
                'Autenticação via JWT Bearer (access 15min + refresh 30d rotativo). '
                'Erros no formato { "error": { "code", "message", "fields" } }. '
                'Feeds paginados por cursor: { "items": [...], "next_cursor": ... }.'
            ),
        },
        'servers': [{'url': API_PREFIX}],
        'tags': tags,
        'paths': build_paths(app),
        'components': _components(),
    }
