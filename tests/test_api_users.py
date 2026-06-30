"""Testes de Usuários/Perfil/Follow (A2)."""


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    """Loga e devolve o header de Authorization."""
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    token = _json(resp)['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_get_profile_public(client, make_user):
    make_user(username='leo')
    resp = client.get('/api/v1/users/leo')
    assert resp.status_code == 200
    u = _json(resp)['user']
    assert u['username'] == 'leo'
    assert u['counts'] == {'posts': 0, 'followers': 0, 'following': 0}
    assert u['viewer_state'] == {'is_following': False, 'is_self': False}


def test_get_profile_case_insensitive_and_404(client, make_user):
    make_user(username='Leo')
    assert client.get('/api/v1/users/LEO').status_code == 200
    assert client.get('/api/v1/users/naoexiste').status_code == 404


def test_follow_unfollow_idempotent(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h = _auth(client, 'leo')

    # follow
    resp = client.post('/api/v1/users/ana/follow', headers=h)
    assert resp.status_code == 200
    assert _json(resp)['user']['viewer_state']['is_following'] is True
    assert _json(resp)['user']['counts']['followers'] == 1

    # follow de novo é idempotente (continua 1 seguidor)
    resp = client.post('/api/v1/users/ana/follow', headers=h)
    assert _json(resp)['user']['counts']['followers'] == 1

    # unfollow
    resp = client.delete('/api/v1/users/ana/follow', headers=h)
    assert resp.status_code == 200
    assert _json(resp)['user']['viewer_state']['is_following'] is False
    assert _json(resp)['user']['counts']['followers'] == 0

    # unfollow de novo é idempotente
    resp = client.delete('/api/v1/users/ana/follow', headers=h)
    assert resp.status_code == 200


def test_cannot_follow_self(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/users/leo/follow', headers=h)
    assert resp.status_code == 422
    assert _json(resp)['error']['code'] == 'cannot_follow_self'


def test_follow_requires_auth(client, make_user):
    make_user(username='ana')
    assert client.post('/api/v1/users/ana/follow').status_code == 401


def test_private_profile_posts_privacy(client, make_user, app):
    from extensions import db
    from models import Post, User

    owner = make_user(username='priv')
    owner.is_public = False
    db.session.add(Post(content='onda boa', user_id=owner.id))
    db.session.commit()

    make_user(username='stranger')
    make_user(username='fan')

    # estranho não vê os posts
    h_stranger = _auth(client, 'stranger')
    assert client.get('/api/v1/users/priv/posts', headers=h_stranger).status_code == 403

    # anônimo também não
    assert client.get('/api/v1/users/priv/posts').status_code == 403

    # o dono vê
    h_owner = _auth(client, 'priv')
    resp = client.get('/api/v1/users/priv/posts', headers=h_owner)
    assert resp.status_code == 200
    assert len(_json(resp)['items']) == 1

    # seguidor vê
    fan = User.query.filter_by(username='fan').first()
    fan.follow(owner)
    db.session.commit()
    h_fan = _auth(client, 'fan')
    assert client.get('/api/v1/users/priv/posts', headers=h_fan).status_code == 200


def test_followers_following_lists(client, make_user):
    from extensions import db

    leo = make_user(username='leo')
    ana = make_user(username='ana')
    leo.follow(ana)
    db.session.commit()

    resp = client.get('/api/v1/users/ana/followers')
    assert resp.status_code == 200
    names = [u['username'] for u in _json(resp)['items']]
    assert names == ['leo']

    resp = client.get('/api/v1/users/leo/following')
    names = [u['username'] for u in _json(resp)['items']]
    assert names == ['ana']


def test_search_users_excludes_admin(client, make_user):
    from extensions import db

    make_user(username='surfer_leo')
    admin = make_user(username='surfer_admin')
    admin.is_admin = True
    db.session.commit()

    resp = client.get('/api/v1/search/users?q=surfer')
    assert resp.status_code == 200
    names = [u['username'] for u in _json(resp)['items']]
    assert 'surfer_leo' in names
    assert 'surfer_admin' not in names

    # busca vazia devolve lista vazia
    assert _json(client.get('/api/v1/search/users?q='))['items'] == []


def test_patch_me(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.patch('/api/v1/me', json={'bio': 'surfista', 'location': 'Floripa', 'is_public': False}, headers=h)
    assert resp.status_code == 200
    u = _json(resp)['user']
    assert u['bio'] == 'surfista'
    assert u['location'] == 'Floripa'
    assert u['is_public'] is False


def test_patch_avatar(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    url = 'https://res.cloudinary.com/demo/image/upload/leo.jpg'
    resp = client.patch('/api/v1/me/avatar', json={'url': url}, headers=h)
    assert resp.status_code == 200
    assert _json(resp)['user']['avatar_url'] == url
