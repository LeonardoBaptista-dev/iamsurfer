"""Testes de Reels (A5)."""


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def test_create_reel_requires_video(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    # sem vídeo → 422
    resp = client.post('/api/v1/reels', json={'content': 'sem video'}, headers=h)
    assert resp.status_code == 422
    assert _json(resp)['error']['code'] == 'validation_error'


def test_create_and_list_reel(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/reels', json={
        'content': 'dropei essa',
        'media': [{'type': 'video', 'url': 'https://res.cloudinary.com/demo/v.mp4'}],
    }, headers=h)
    assert resp.status_code == 201, _json(resp)
    reel = _json(resp)['reel']
    assert reel['is_reel'] is True
    assert any(m['type'] == 'video' for m in reel['media'])

    resp = client.get('/api/v1/reels')
    assert resp.status_code == 200
    items = _json(resp)['items']
    assert len(items) == 1
    assert items[0]['content'] == 'dropei essa'


def test_reel_excludes_private_and_regular_posts(client, make_user):
    from extensions import db

    priv = make_user(username='priv')
    priv.is_public = False
    db.session.commit()
    h_priv = _auth(client, 'priv')
    client.post('/api/v1/reels', json={
        'media': [{'type': 'video', 'url': 'https://res.cloudinary.com/demo/p.mp4'}],
    }, headers=h_priv)

    pub = make_user(username='pub')
    h_pub = _auth(client, 'pub')
    # post normal (não reel) não deve aparecer no feed de reels
    client.post('/api/v1/posts', json={'content': 'post normal'}, headers=h_pub)

    items = _json(client.get('/api/v1/reels'))['items']
    assert items == []  # reel privado fora + post normal não conta


def test_reel_like_via_posts_endpoint(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')
    rid = _json(client.post('/api/v1/reels', json={
        'media': [{'type': 'video', 'url': 'https://res.cloudinary.com/demo/r.mp4'}],
    }, headers=h_leo))['reel']['id']

    # like reusa o endpoint de posts
    resp = client.post(f'/api/v1/posts/{rid}/like', headers=h_ana)
    assert resp.status_code == 200
    assert _json(resp) == {'liked': True, 'likes': 1}
