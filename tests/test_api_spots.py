"""Testes de Picos (SurfMap) da API (`/api/v1/spots`)."""


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def _approve(spot_id):
    from extensions import db
    from models import Spot
    Spot.query.get(spot_id).status = 'approved'
    db.session.commit()


def test_create_spot_pending_and_normalizes(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/spots', headers=h, json={
        'name': 'Pico Teste', 'latitude': -25.43, 'longitude': -48.5,
        'state': 'PR', 'best_tide': ['Enchendo', 'Cheia'],
        'best_season': ['Verão'], 'water_temp': 'Quente só no verão',
        'crowd_level': 'Cheio nos fins de semana',
    })
    assert resp.status_code == 201
    j = _json(resp)
    assert j['status'] == 'pending'
    assert j['state'] == 'Paraná'                 # sigla -> nome canônico
    assert j['best_tide'] == 'Enchendo, Cheia'    # múltiplos -> string
    assert j['best_season'] == 'Verão'
    assert j['water_temp'] == 'Quente só no verão'


def test_create_requires_auth_and_coords(client, make_user):
    make_user(username='leo')
    assert client.post('/api/v1/spots', json={'name': 'x'}).status_code == 401
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/spots', headers=h, json={'name': 'x'})
    assert resp.status_code == 422


def test_list_only_approved_and_state_filter(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    r1 = client.post('/api/v1/spots', headers=h, json={'name': 'Aprovado', 'latitude': -25, 'longitude': -48, 'state': 'PR'})
    client.post('/api/v1/spots', headers=h, json={'name': 'Pendente', 'latitude': -27, 'longitude': -48, 'state': 'SC'})
    _approve(_json(r1)['id'])

    names = [s['name'] for s in _json(client.get('/api/v1/spots'))['items']]
    assert 'Aprovado' in names and 'Pendente' not in names
    # filtro por estado aceita sigla (normaliza)
    assert _json(client.get('/api/v1/spots?state=PR'))['total'] == 1


def test_detail_follow_and_pending_404(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    r = client.post('/api/v1/spots', headers=h, json={'name': 'Pico', 'latitude': -25, 'longitude': -48})
    sid = _json(r)['id']

    # pendente: detalhe 404
    assert client.get(f'/api/v1/spots/{sid}').status_code == 404

    _approve(sid)
    assert client.get(f'/api/v1/spots/{sid}').status_code == 200

    f = client.post(f'/api/v1/spots/{sid}/follow', headers=h)
    assert _json(f)['following'] is True
    assert _json(f)['followers_count'] == 1
