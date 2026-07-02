"""Testes de contrato da API (A13): spec OpenAPI + formato de erro/paginação.

Estilo igual a test_api_posts.py (fixtures client/make_user; login via
POST /api/v1/auth/login). Não valida o corpo de cada endpoint, e sim os
contratos transversais: o spec servido, o envelope de erro, a paginação e a
cobertura de rotas.
"""
import re


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login',
                       json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


# ── Spec OpenAPI servido ──────────────────────────────────────────────────────

def test_openapi_served(client):
    resp = client.get('/api/v1/openapi.json')
    assert resp.status_code == 200, _json(resp)
    spec = _json(resp)
    assert spec['openapi'] == '3.1.0'
    assert isinstance(spec['paths'], dict) and spec['paths']  # não-vazio
    assert spec['components']['securitySchemes']['bearerAuth']['type'] == 'http'
    assert spec['components']['securitySchemes']['bearerAuth']['scheme'] == 'bearer'
    assert spec['info']['version'] == '1'
    assert spec['servers'][0]['url'] == '/api/v1'


def test_openapi_has_core_schemas(client):
    spec = _json(client.get('/api/v1/openapi.json'))
    schemas = spec['components']['schemas']
    for name in ('Error', 'Pagination', 'UserBrief', 'User', 'Post', 'Comment', 'Spot'):
        assert name in schemas, name
    # Error tem o shape do contrato.
    err_props = schemas['Error']['properties']['error']['properties']
    assert 'code' in err_props and 'message' in err_props and 'fields' in err_props


def test_openapi_marks_protected_routes(client):
    spec = _json(client.get('/api/v1/openapi.json'))
    # Rota protegida traz security bearerAuth; rota pública não.
    assert spec['paths']['/feed']['get'].get('security') == [{'bearerAuth': []}]
    assert 'security' not in spec['paths']['/auth/login']['post']


# ── Formato de erro padrão ────────────────────────────────────────────────────

def test_protected_route_without_token_is_401(client):
    resp = client.get('/api/v1/feed')
    assert resp.status_code == 401
    body = _json(resp)
    assert set(body.keys()) == {'error'}
    assert 'code' in body['error']
    assert 'message' in body['error']
    assert isinstance(body['error']['code'], str)
    assert isinstance(body['error']['message'], str)


def test_404_standard_format(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.get('/api/v1/users/inexistente', headers=h)
    assert resp.status_code == 404
    body = _json(resp)
    assert body['error']['code'] == 'not_found'
    assert isinstance(body['error']['message'], str)


# ── Paginação ─────────────────────────────────────────────────────────────────

def test_paginated_envelope(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    client.post('/api/v1/posts', json={'content': 'onda'}, headers=h)

    resp = client.get('/api/v1/feed', headers=h)
    assert resp.status_code == 200
    body = _json(resp)
    assert isinstance(body['items'], list)
    assert 'next_cursor' in body  # presente (pode ser null)


# ── Sanidade: url_map ⊆ spec ──────────────────────────────────────────────────

_ARG_RE = re.compile(r'<(?:[a-zA-Z_]+:)?([a-zA-Z_][a-zA-Z0-9_]*)>')
_PREFIX = '/api/v1'


def _url_map_paths(app):
    paths = set()
    for rule in app.url_map.iter_rules():
        if not rule.endpoint.startswith('api.'):
            continue
        if rule.endpoint.endswith('.static'):
            continue
        if not rule.rule.startswith(_PREFIX):
            continue
        p = _ARG_RE.sub(lambda m: '{' + m.group(1) + '}', rule.rule)
        p = p[len(_PREFIX):] or '/'
        paths.add(p)
    return paths


def test_all_api_routes_in_spec(client, app):
    spec = _json(client.get('/api/v1/openapi.json'))
    spec_paths = set(spec['paths'].keys())
    map_paths = _url_map_paths(app)
    missing = map_paths - spec_paths
    assert not missing, f'rotas fora do spec: {sorted(missing)}'
