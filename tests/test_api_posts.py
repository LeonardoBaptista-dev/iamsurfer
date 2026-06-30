"""Testes de Feed/Posts/Comentários/Likes (A3)."""


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def test_create_post_text(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/posts', json={'content': 'primeira onda do dia'}, headers=h)
    assert resp.status_code == 201, _json(resp)
    post = _json(resp)['post']
    assert post['content'] == 'primeira onda do dia'
    assert post['author']['username'] == 'leo'
    assert post['counts'] == {'likes': 0, 'comments': 0}
    assert post['viewer_state']['liked'] is False


def test_create_post_with_media(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/posts', json={
        'content': 'foto',
        'media': [{'type': 'image', 'url': 'https://res.cloudinary.com/demo/img.jpg'}],
    }, headers=h)
    assert resp.status_code == 201
    media = _json(resp)['post']['media']
    assert len(media) == 1
    assert media[0]['type'] == 'image'
    assert media[0]['url'] == 'https://res.cloudinary.com/demo/img.jpg'


def test_create_post_empty_fails(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    resp = client.post('/api/v1/posts', json={'content': '   '}, headers=h)
    assert resp.status_code == 422


def test_create_post_requires_auth(client):
    assert client.post('/api/v1/posts', json={'content': 'x'}).status_code == 401


def test_feed_shows_followed_and_own(client, make_user):
    from extensions import db

    leo = make_user(username='leo')
    ana = make_user(username='ana')
    bob = make_user(username='bob')
    leo.follow(ana)
    db.session.commit()

    h_ana = _auth(client, 'ana')
    h_bob = _auth(client, 'bob')
    h_leo = _auth(client, 'leo')
    client.post('/api/v1/posts', json={'content': 'post da ana'}, headers=h_ana)
    client.post('/api/v1/posts', json={'content': 'post do bob'}, headers=h_bob)
    client.post('/api/v1/posts', json={'content': 'post do leo'}, headers=h_leo)

    resp = client.get('/api/v1/feed', headers=h_leo)
    assert resp.status_code == 200
    contents = [p['content'] for p in _json(resp)['items']]
    assert 'post da ana' in contents   # segue
    assert 'post do leo' in contents   # próprio
    assert 'post do bob' not in contents  # não segue


def test_feed_pagination_cursor(client, make_user):
    make_user(username='leo')
    h = _auth(client, 'leo')
    for i in range(5):
        client.post('/api/v1/posts', json={'content': f'post {i}'}, headers=h)

    resp = client.get('/api/v1/feed?limit=2', headers=h)
    data = _json(resp)
    assert len(data['items']) == 2
    assert data['next_cursor'] is not None

    resp2 = client.get(f'/api/v1/feed?limit=2&cursor={data["next_cursor"]}', headers=h)
    data2 = _json(resp2)
    # Páginas não se sobrepõem.
    ids1 = {p['id'] for p in data['items']}
    ids2 = {p['id'] for p in data2['items']}
    assert ids1.isdisjoint(ids2)


def test_like_unlike_idempotent(client, make_user):
    from extensions import db

    make_user(username='leo')
    make_user(username='ana')
    h_ana = _auth(client, 'ana')
    h_leo = _auth(client, 'leo')
    pid = _json(client.post('/api/v1/posts', json={'content': 'curta!'}, headers=h_ana))['post']['id']

    resp = client.post(f'/api/v1/posts/{pid}/like', headers=h_leo)
    assert resp.status_code == 200
    assert _json(resp) == {'liked': True, 'likes': 1}

    # like de novo é idempotente
    assert _json(client.post(f'/api/v1/posts/{pid}/like', headers=h_leo))['likes'] == 1

    # viewer_state reflete o like
    detail = client.get(f'/api/v1/posts/{pid}', headers=h_leo)
    assert _json(detail)['post']['viewer_state']['liked'] is True

    resp = client.delete(f'/api/v1/posts/{pid}/like', headers=h_leo)
    assert _json(resp) == {'liked': False, 'likes': 0}
    # unlike de novo idempotente
    assert client.delete(f'/api/v1/posts/{pid}/like', headers=h_leo).status_code == 200


def test_comments_flow(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_ana = _auth(client, 'ana')
    h_leo = _auth(client, 'leo')
    pid = _json(client.post('/api/v1/posts', json={'content': 'comente'}, headers=h_ana))['post']['id']

    resp = client.post(f'/api/v1/posts/{pid}/comments', json={'content': 'top demais'}, headers=h_leo)
    assert resp.status_code == 201
    cid = _json(resp)['comment']['id']
    assert _json(resp)['comment']['author']['username'] == 'leo'

    resp = client.get(f'/api/v1/posts/{pid}/comments')
    assert resp.status_code == 200
    assert len(_json(resp)['items']) == 1

    # autor do comentário pode remover
    assert client.delete(f'/api/v1/comments/{cid}', headers=h_leo).status_code == 200
    assert len(_json(client.get(f'/api/v1/posts/{pid}/comments'))['items']) == 0


def test_delete_post_only_author(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_ana = _auth(client, 'ana')
    h_leo = _auth(client, 'leo')
    pid = _json(client.post('/api/v1/posts', json={'content': 'meu post'}, headers=h_ana))['post']['id']

    # outro usuário não pode
    assert client.delete(f'/api/v1/posts/{pid}', headers=h_leo).status_code == 403
    # autor pode
    assert client.delete(f'/api/v1/posts/{pid}', headers=h_ana).status_code == 200
    assert client.get(f'/api/v1/posts/{pid}').status_code == 404


def test_post_detail_privacy(client, make_user):
    from extensions import db

    owner = make_user(username='priv')
    owner.is_public = False
    db.session.commit()
    h_owner = _auth(client, 'priv')
    pid = _json(client.post('/api/v1/posts', json={'content': 'segredo'}, headers=h_owner))['post']['id']

    make_user(username='stranger')
    h_stranger = _auth(client, 'stranger')
    assert client.get(f'/api/v1/posts/{pid}', headers=h_stranger).status_code == 403
    assert client.get(f'/api/v1/posts/{pid}', headers=h_owner).status_code == 200
