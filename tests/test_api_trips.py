"""Testes de Caronas/Viagens de surf (A8)."""
from datetime import datetime, timedelta


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def _future(days=3):
    return (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%dT%H:%M')


def _make_trip(client, headers, **over):
    payload = {
        'title': 'Rumo a Guarda do Embaú',
        'departure_location': 'Curitiba',
        'destination_text': 'Guarda do Embaú',
        'departure_time': _future(),
        'available_seats': 3,
    }
    payload.update(over)
    return client.post('/api/v1/trips', json=payload, headers=headers)


def test_create_trip(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = _make_trip(client, h)
    assert resp.status_code == 201, _json(resp)
    trip = _json(resp)['trip']
    assert trip['title'] == 'Rumo a Guarda do Embaú'
    assert trip['destination'] == 'Guarda do Embaú'
    assert trip['author']['username'] == 'leo'
    assert trip['counts']['seats_total'] == 3
    assert trip['counts']['seats_available'] == 3
    assert trip['counts']['participants'] == 0
    assert trip['viewer_state'] == {'joined': False, 'is_owner': True}
    assert trip['participants'] == []


def test_create_trip_requires_auth(client):
    assert client.post('/api/v1/trips', json={'title': 'x'}).status_code == 401


def test_create_trip_validates_fields(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/trips', json={'title': 'só título'}, headers=h)
    assert resp.status_code == 422


def test_list_trips(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    _make_trip(client, h, title='Trip A')
    _make_trip(client, h, title='Trip B')

    resp = client.get('/api/v1/trips')
    assert resp.status_code == 200
    titles = [t['title'] for t in _json(resp)['items']]
    assert 'Trip A' in titles and 'Trip B' in titles


def test_list_trips_filter_destination(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    _make_trip(client, h, title='Norte', destination_text='Praia do Rosa')
    _make_trip(client, h, title='Sul', destination_text='Joaquina')

    resp = client.get('/api/v1/trips?destination=Rosa')
    titles = [t['title'] for t in _json(resp)['items']]
    assert titles == ['Norte']


def test_trip_detail(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    tid = _json(_make_trip(client, h))['trip']['id']

    resp = client.get(f'/api/v1/trips/{tid}')
    assert resp.status_code == 200
    trip = _json(resp)['trip']
    assert trip['id'] == tid
    assert 'participants' in trip

    assert client.get('/api/v1/trips/99999').status_code == 404


def test_join_leave_idempotent(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')
    tid = _json(_make_trip(client, h_leo))['trip']['id']

    # ana participa
    resp = client.post(f'/api/v1/trips/{tid}/join', headers=h_ana)
    assert resp.status_code == 200
    trip = _json(resp)['trip']
    assert trip['viewer_state']['joined'] is True
    assert trip['counts']['participants'] == 1
    assert trip['counts']['seats_available'] == 2
    assert 'ana' in [p['username'] for p in trip['participants']]

    # join de novo é idempotente
    resp2 = client.post(f'/api/v1/trips/{tid}/join', headers=h_ana)
    assert _json(resp2)['trip']['counts']['participants'] == 1

    # ana sai
    resp3 = client.post(f'/api/v1/trips/{tid}/leave', headers=h_ana)
    assert resp3.status_code == 200
    assert _json(resp3)['trip']['viewer_state']['joined'] is False
    assert _json(resp3)['trip']['counts']['participants'] == 0

    # leave de novo é idempotente
    assert client.post(f'/api/v1/trips/{tid}/leave', headers=h_ana).status_code == 200


def test_owner_cannot_join_or_leave(client, make_user):
    make_user(username='leo')
    h_leo = _auth(client, 'leo')
    tid = _json(_make_trip(client, h_leo))['trip']['id']

    assert client.post(f'/api/v1/trips/{tid}/join', headers=h_leo).status_code == 422
    assert client.post(f'/api/v1/trips/{tid}/leave', headers=h_leo).status_code == 422


def test_join_respects_capacity(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    make_user(username='bob')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')
    h_bob = _auth(client, 'bob')
    tid = _json(_make_trip(client, h_leo, available_seats=1))['trip']['id']

    assert client.post(f'/api/v1/trips/{tid}/join', headers=h_ana).status_code == 200
    # lotado
    resp = client.post(f'/api/v1/trips/{tid}/join', headers=h_bob)
    assert resp.status_code == 409
    assert _json(resp)['error']['code'] == 'trip_full'


def test_join_requires_auth(client, make_user):
    make_user(username='leo')
    h_leo = _auth(client, 'leo')
    tid = _json(_make_trip(client, h_leo))['trip']['id']
    assert client.post(f'/api/v1/trips/{tid}/join').status_code == 401


def test_me_trips(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')

    # leo cria uma; ana cria outra e leo participa dela
    my_tid = _json(_make_trip(client, h_leo, title='Minha'))['trip']['id']
    ana_tid = _json(_make_trip(client, h_ana, title='Da Ana'))['trip']['id']
    client.post(f'/api/v1/trips/{ana_tid}/join', headers=h_leo)

    resp = client.get('/api/v1/me/trips', headers=h_leo)
    assert resp.status_code == 200
    ids = {t['id'] for t in _json(resp)['items']}
    assert my_tid in ids   # criei
    assert ana_tid in ids  # participo

    assert client.get('/api/v1/me/trips').status_code == 401
