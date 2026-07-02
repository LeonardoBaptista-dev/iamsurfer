"""Testes de Stories (A4)."""


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def test_create_story_requires_media(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    assert client.post('/api/v1/stories', json={}, headers=h).status_code == 422


def test_create_and_list_story_bar(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/stories', json={
        'media_url': 'https://res.cloudinary.com/demo/s.jpg', 'media_type': 'image',
    }, headers=h)
    assert resp.status_code == 201, _json(resp)

    resp = client.get('/api/v1/stories', headers=h)
    assert resp.status_code == 200
    items = _json(resp)['items']
    assert len(items) == 1
    group = items[0]
    assert group['username'] == 'leo'
    assert group['is_self'] is True
    assert group['has_unseen'] is True  # próprio story ainda não visto
    assert len(group['stories']) == 1
    assert group['stories'][0]['can_delete'] is True


def test_story_bar_shows_followed(client, make_user):
    from extensions import db

    leo = make_user(username='leo')
    ana = make_user(username='ana')
    bob = make_user(username='bob')
    leo.follow(ana)
    db.session.commit()

    h_ana = _auth(client, 'ana')
    h_bob = _auth(client, 'bob')
    client.post('/api/v1/stories', json={'media_url': 'https://x/a.jpg'}, headers=h_ana)
    client.post('/api/v1/stories', json={'media_url': 'https://x/b.jpg'}, headers=h_bob)

    h_leo = _auth(client, 'leo')
    items = _json(client.get('/api/v1/stories', headers=h_leo))['items']
    usernames = [g['username'] for g in items]
    assert 'ana' in usernames    # segue
    assert 'bob' not in usernames  # não segue


def test_mark_seen(client, make_user):
    from extensions import db

    leo = make_user(username='leo')
    ana = make_user(username='ana')
    leo.follow(ana)
    db.session.commit()

    h_ana = _auth(client, 'ana')
    sid = _json(client.post('/api/v1/stories', json={'media_url': 'https://x/a.jpg'}, headers=h_ana))['story']['id']

    h_leo = _auth(client, 'leo')
    # antes: não visto
    items = _json(client.get('/api/v1/stories', headers=h_leo))['items']
    ana_group = next(g for g in items if g['username'] == 'ana')
    assert ana_group['has_unseen'] is True

    # marca visto (idempotente)
    assert client.post(f'/api/v1/stories/{sid}/seen', headers=h_leo).status_code == 200
    assert client.post(f'/api/v1/stories/{sid}/seen', headers=h_leo).status_code == 200

    items = _json(client.get('/api/v1/stories', headers=h_leo))['items']
    ana_group = next(g for g in items if g['username'] == 'ana')
    assert ana_group['has_unseen'] is False


def test_delete_story_only_owner(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')
    sid = _json(client.post('/api/v1/stories', json={'media_url': 'https://x/a.jpg'}, headers=h_leo))['story']['id']

    assert client.delete(f'/api/v1/stories/{sid}', headers=h_ana).status_code == 403
    assert client.delete(f'/api/v1/stories/{sid}', headers=h_leo).status_code == 200
