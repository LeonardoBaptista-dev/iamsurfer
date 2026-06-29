"""Testes da fundação da API (A0) e do fluxo de auth (A1)."""


def _json(resp):
    return resp.get_json()


# ── A0: fundação ─────────────────────────────────────────────────────────────

def test_ping_ok(client):
    resp = client.get('/api/v1/ping')
    assert resp.status_code == 200
    assert _json(resp) == {'ok': True, 'version': '1'}


def test_protected_route_without_token_returns_401_in_standard_format(client):
    resp = client.get('/api/v1/auth/me')
    assert resp.status_code == 401
    data = _json(resp)
    assert 'error' in data
    assert data['error']['code'] == 'unauthorized'
    assert isinstance(data['error']['message'], str)


# ── A1: fluxo completo register → login → refresh → me → logout ──────────────

def test_full_auth_flow(client):
    # register
    resp = client.post('/api/v1/auth/register', json={
        'username': 'surfer1', 'email': 'Surfer1@test.com', 'password': 'supersafe123',
    })
    assert resp.status_code == 201, _json(resp)
    data = _json(resp)
    assert data['access_token'] and data['refresh_token']
    assert data['user']['username'] == 'surfer1'
    assert 'password' not in str(data['user'])  # senha nunca volta
    assert data['user']['email'] == 'surfer1@test.com'

    # login por email case-insensitive
    resp = client.post('/api/v1/auth/login', json={
        'identifier': 'SURFER1@TEST.COM', 'password': 'supersafe123',
    })
    assert resp.status_code == 200, _json(resp)
    tokens = _json(resp)
    access, refresh = tokens['access_token'], tokens['refresh_token']

    # me com access token
    resp = client.get('/api/v1/auth/me', headers={'Authorization': f'Bearer {access}'})
    assert resp.status_code == 200
    assert _json(resp)['user']['username'] == 'surfer1'

    # refresh rotaciona o token
    resp = client.post('/api/v1/auth/refresh', headers={'Authorization': f'Bearer {refresh}'})
    assert resp.status_code == 200
    new_tokens = _json(resp)
    assert new_tokens['access_token'] and new_tokens['refresh_token']

    # o refresh antigo foi revogado (blocklist)
    resp = client.post('/api/v1/auth/refresh', headers={'Authorization': f'Bearer {refresh}'})
    assert resp.status_code == 401
    assert _json(resp)['error']['code'] == 'token_revoked'

    # logout revoga o refresh novo
    resp = client.post('/api/v1/auth/logout',
                       headers={'Authorization': f'Bearer {new_tokens["refresh_token"]}'})
    assert resp.status_code == 200

    resp = client.post('/api/v1/auth/refresh',
                       headers={'Authorization': f'Bearer {new_tokens["refresh_token"]}'})
    assert resp.status_code == 401


def test_login_with_username(client, make_user):
    make_user(username='Leo Baptista', email='leo@test.com', password='supersafe123')
    resp = client.post('/api/v1/auth/login', json={
        'identifier': 'leo baptista', 'password': 'supersafe123',
    })
    assert resp.status_code == 200, _json(resp)


def test_login_wrong_password_is_generic_401(client, make_user):
    make_user(username='leo', password='supersafe123')
    resp = client.post('/api/v1/auth/login', json={'identifier': 'leo', 'password': 'wrong'})
    assert resp.status_code == 401
    assert _json(resp)['error']['code'] == 'invalid_credentials'


def test_register_validation_errors(client):
    resp = client.post('/api/v1/auth/register', json={
        'username': 'ab', 'email': 'bad', 'password': 'short',
    })
    assert resp.status_code == 422
    fields = _json(resp)['error']['fields']
    assert set(fields) == {'username', 'email', 'password'}


def test_register_duplicate_email(client, make_user):
    make_user(username='leo', email='dup@test.com')
    resp = client.post('/api/v1/auth/register', json={
        'username': 'other', 'email': 'DUP@test.com', 'password': 'supersafe123',
    })
    assert resp.status_code == 409
    assert _json(resp)['error']['code'] == 'email_taken'


def test_push_token_upsert(client, make_user):
    make_user(username='leo', password='supersafe123')
    login = client.post('/api/v1/auth/login', json={'identifier': 'leo', 'password': 'supersafe123'})
    access = _json(login)['access_token']
    headers = {'Authorization': f'Bearer {access}'}

    resp = client.post('/api/v1/auth/push-token',
                       json={'token': 'ExponentPushToken[abc]', 'platform': 'ios'}, headers=headers)
    assert resp.status_code == 200

    # upsert: mesmo token não duplica
    resp = client.post('/api/v1/auth/push-token',
                       json={'token': 'ExponentPushToken[abc]', 'platform': 'android'}, headers=headers)
    assert resp.status_code == 200

    from models import DeviceToken
    assert DeviceToken.query.filter_by(token='ExponentPushToken[abc]').count() == 1
    assert DeviceToken.query.filter_by(token='ExponentPushToken[abc]').first().platform == 'android'
