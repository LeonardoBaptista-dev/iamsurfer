"""Testes de Mensagens/Notificações (A6) e push Expo (A12)."""


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


# ── Mensagens ─────────────────────────────────────────────────────────────────

def test_send_message(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')

    resp = client.post('/api/v1/conversations/ana/messages',
                       json={'content': 'bora surfar?'}, headers=h_leo)
    assert resp.status_code == 201, _json(resp)
    msg = _json(resp)['message']
    assert msg['content'] == 'bora surfar?'
    assert msg['from_me'] is True
    assert 'created_at' in msg


def test_send_message_empty_fails(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    resp = client.post('/api/v1/conversations/ana/messages',
                       json={'content': '   '}, headers=h_leo)
    assert resp.status_code == 422


def test_send_message_to_unknown_user_404(client, make_user):
    make_user(username='leo')
    h_leo = _auth(client, 'leo')
    resp = client.post('/api/v1/conversations/ghost/messages',
                       json={'content': 'oi'}, headers=h_leo)
    assert resp.status_code == 404


def test_send_message_requires_auth(client, make_user):
    make_user(username='ana')
    assert client.post('/api/v1/conversations/ana/messages',
                       json={'content': 'oi'}).status_code == 401


def test_conversation_history_from_me(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')

    client.post('/api/v1/conversations/ana/messages', json={'content': 'oi ana'}, headers=h_leo)
    client.post('/api/v1/conversations/leo/messages', json={'content': 'oi leo'}, headers=h_ana)

    # Do ponto de vista do leo
    resp = client.get('/api/v1/conversations/ana', headers=h_leo)
    assert resp.status_code == 200
    items = _json(resp)['items']
    by_content = {m['content']: m for m in items}
    assert by_content['oi ana']['from_me'] is True
    assert by_content['oi leo']['from_me'] is False


def test_conversation_marks_received_as_read(client, make_user):
    from models import Message

    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')

    client.post('/api/v1/conversations/ana/messages', json={'content': 'msg do leo'}, headers=h_leo)

    # A mensagem recebida pela ana começa não-lida.
    msg = Message.query.filter_by(content='msg do leo').first()
    assert msg.read is False

    # Ana abre a conversa -> marca como lida.
    client.get('/api/v1/conversations/leo', headers=h_ana)
    assert Message.query.filter_by(content='msg do leo').first().read is True


def test_inbox_conversations(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    make_user(username='bob')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')

    client.post('/api/v1/conversations/ana/messages', json={'content': 'oi ana'}, headers=h_leo)
    client.post('/api/v1/conversations/bob/messages', json={'content': 'oi bob'}, headers=h_leo)
    client.post('/api/v1/conversations/leo/messages', json={'content': 'oi de volta'}, headers=h_ana)

    resp = client.get('/api/v1/conversations', headers=h_leo)
    assert resp.status_code == 200
    items = _json(resp)['items']
    users = {c['user']['username'] for c in items}
    assert users == {'ana', 'bob'}  # uma entrada por interlocutor

    ana_convo = next(c for c in items if c['user']['username'] == 'ana')
    # Última mensagem com a ana é a recebida ('oi de volta'), não lida.
    assert ana_convo['last_message']['content'] == 'oi de volta'
    assert ana_convo['last_message']['from_me'] is False
    assert ana_convo['unread'] is True


# ── Notificações ──────────────────────────────────────────────────────────────

def test_notifications_list_and_count(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')

    client.post('/api/v1/conversations/ana/messages', json={'content': 'ola'}, headers=h_leo)

    # Ana recebe uma notificação de mensagem.
    resp = client.get('/api/v1/notifications', headers=h_ana)
    assert resp.status_code == 200
    items = _json(resp)['items']
    assert len(items) == 1
    assert items[0]['type'] == 'message'
    assert items[0]['read'] is False
    assert items[0]['actor']['username'] == 'leo'

    count = _json(client.get('/api/v1/notifications/count', headers=h_ana))
    assert count == {'unread': 1}


def test_notifications_mark_all_read(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')

    client.post('/api/v1/conversations/ana/messages', json={'content': 'm1'}, headers=h_leo)
    client.post('/api/v1/conversations/ana/messages', json={'content': 'm2'}, headers=h_leo)

    assert _json(client.get('/api/v1/notifications/count', headers=h_ana))['unread'] == 2

    resp = client.post('/api/v1/notifications/read', headers=h_ana)
    assert resp.status_code == 200
    assert _json(client.get('/api/v1/notifications/count', headers=h_ana))['unread'] == 0


def test_notifications_mark_specific_ids(client, make_user):
    make_user(username='leo')
    make_user(username='ana')
    h_leo = _auth(client, 'leo')
    h_ana = _auth(client, 'ana')

    client.post('/api/v1/conversations/ana/messages', json={'content': 'm1'}, headers=h_leo)
    client.post('/api/v1/conversations/ana/messages', json={'content': 'm2'}, headers=h_leo)

    items = _json(client.get('/api/v1/notifications', headers=h_ana))['items']
    one_id = items[0]['id']

    resp = client.post('/api/v1/notifications/read', json={'ids': [one_id]}, headers=h_ana)
    assert _json(resp)['updated'] == 1
    assert _json(client.get('/api/v1/notifications/count', headers=h_ana))['unread'] == 1


# ── Push Expo (A12) ───────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def test_send_push_uses_tokens(client, make_user, monkeypatch):
    from models import DeviceToken
    from extensions import db
    from routes.api import push

    ana = make_user(username='ana')
    db.session.add(DeviceToken(user_id=ana.id, token='ExpoTok[aaa]', platform='ios'))
    db.session.add(DeviceToken(user_id=ana.id, token='ExpoTok[bbb]', platform='android'))
    db.session.commit()

    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured['url'] = url
        captured['batch'] = json
        return _FakeResponse({'data': [{'status': 'ok'} for _ in json]})

    monkeypatch.setattr(push.requests, 'post', fake_post, raising=False)

    tickets = push.send_push([ana.id], 'Oi', 'corpo', data={'type': 'x'})

    assert captured['url'] == push.EXPO_PUSH_URL
    sent_tokens = {m['to'] for m in captured['batch']}
    assert sent_tokens == {'ExpoTok[aaa]', 'ExpoTok[bbb]'}
    assert captured['batch'][0]['title'] == 'Oi'
    assert captured['batch'][0]['data'] == {'type': 'x'}
    assert len(tickets) == 2


def test_send_push_removes_dead_token(client, make_user, monkeypatch):
    from models import DeviceToken
    from extensions import db
    from routes.api import push

    ana = make_user(username='ana')
    db.session.add(DeviceToken(user_id=ana.id, token='ExpoTok[dead]', platform='ios'))
    db.session.commit()

    def fake_post(url, json=None, headers=None, timeout=None):
        return _FakeResponse({'data': [
            {'status': 'error', 'message': 'not registered',
             'details': {'error': 'DeviceNotRegistered'}}
            for _ in json
        ]})

    monkeypatch.setattr(push.requests, 'post', fake_post, raising=False)

    push.send_push([ana.id], 'Oi', 'corpo')

    # Token morto foi apagado.
    assert DeviceToken.query.filter_by(token='ExpoTok[dead]').first() is None


def test_send_push_no_tokens_is_noop(client, make_user, monkeypatch):
    from routes.api import push

    ana = make_user(username='ana')

    called = {'n': 0}

    def fake_post(*a, **k):
        called['n'] += 1
        return _FakeResponse({'data': []})

    monkeypatch.setattr(push.requests, 'post', fake_post, raising=False)
    assert push.send_push([ana.id], 't', 'b') == []
    assert called['n'] == 0  # sem tokens, não bate na rede


def test_send_message_triggers_push(client, make_user, monkeypatch):
    from models import DeviceToken
    from extensions import db
    from routes.api import push

    make_user(username='leo')
    ana = make_user(username='ana')
    db.session.add(DeviceToken(user_id=ana.id, token='ExpoTok[ana]', platform='ios'))
    db.session.commit()

    sent = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        sent['batch'] = json
        return _FakeResponse({'data': [{'status': 'ok'} for _ in json]})

    monkeypatch.setattr(push.requests, 'post', fake_post, raising=False)

    h_leo = _auth(client, 'leo')
    resp = client.post('/api/v1/conversations/ana/messages',
                       json={'content': 'push!'}, headers=h_leo)
    assert resp.status_code == 201
    assert sent['batch'][0]['to'] == 'ExpoTok[ana]'
    assert 'leo' in sent['batch'][0]['title']
