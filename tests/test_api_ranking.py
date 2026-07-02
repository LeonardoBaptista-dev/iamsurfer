"""Testes de Ranking e Badges (A10)."""


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def test_ranking_orders_by_points_and_excludes_admin(client, make_user):
    from extensions import db

    a = make_user(username='alta')
    a.points = 500
    b = make_user(username='media')
    b.points = 200
    c = make_user(username='baixa')
    c.points = 50
    adm = make_user(username='chefe')
    adm.is_admin = True
    adm.points = 9999
    db.session.commit()

    resp = client.get('/api/v1/ranking')
    assert resp.status_code == 200
    data = _json(resp)
    names = [i['username'] for i in data['items']]
    assert names == ['alta', 'media', 'baixa']  # admin fora, ordem por pontos
    assert data['items'][0]['rank'] == 1
    assert data['items'][0]['points'] == 500
    assert data['total'] == 3


def test_ranking_my_rank(client, make_user):
    from extensions import db

    a = make_user(username='alta')
    a.points = 500
    b = make_user(username='eu')
    b.points = 100
    db.session.commit()

    h = _auth(client, 'eu')
    data = _json(client.get('/api/v1/ranking', headers=h))
    assert data['my_rank'] == 2


def test_ranking_pagination(client, make_user):
    from extensions import db

    for i in range(5):
        u = make_user(username=f'u{i}')
        u.points = i * 10
    db.session.commit()

    data = _json(client.get('/api/v1/ranking?limit=2&offset=0'))
    assert len(data['items']) == 2
    assert data['next_offset'] == 2
    assert data['items'][0]['rank'] == 1

    data2 = _json(client.get('/api/v1/ranking?limit=2&offset=2'))
    assert data2['items'][0]['rank'] == 3


def test_user_badges(client, make_user):
    from datetime import datetime, timedelta
    from extensions import db
    from models import UserBadge

    user = make_user(username='foto')
    db.session.add(UserBadge(user_id=user.id, type='fotografo', status='active'))
    # selo expirado não aparece
    db.session.add(UserBadge(user_id=user.id, type='atleta', status='active',
                             expires_at=datetime.utcnow() - timedelta(days=1)))
    db.session.commit()

    resp = client.get('/api/v1/users/foto/badges')
    assert resp.status_code == 200
    badges = _json(resp)['badges']
    types = [b['type'] for b in badges]
    assert 'fotografo' in types
    assert 'atleta' not in types
    assert badges[0]['label'] == 'Fotógrafo'


def test_user_badges_404(client):
    assert client.get('/api/v1/users/naoexiste/badges').status_code == 404
