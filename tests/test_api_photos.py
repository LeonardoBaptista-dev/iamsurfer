"""Testes de Fotos à venda + Pagamento (A9), em MODO TESTE (sem rede).

Não há credenciais do Mercado Pago no ambiente, então o provedor opera em modo
teste (payments.create_payment gera um id fake e a confirmação vem por um
webhook simulado {purchase_id, status:'paid'}). Nenhum teste toca a rede.
"""
from datetime import date

from extensions import db


def _json(resp):
    return resp.get_json()


def _auth(client, username, password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def _make_session(photographer, price=50.0, n_photos=2):
    """Cria um Spot + PhotoSession + N SessionPhoto e devolve (session, photos)."""
    from models import Spot, PhotoSession, SessionPhoto

    spot = Spot(name='Pico Teste', latitude=-25.0, longitude=-48.0,
                created_by=photographer.id, status='approved')
    db.session.add(spot)
    db.session.flush()

    session = PhotoSession(spot_id=spot.id, title='Sessão Sábado',
                           description='Ondas boas', session_date=date.today(),
                           photographer_id=photographer.id, price_per_photo=price)
    db.session.add(session)
    db.session.flush()

    photos = []
    for i in range(n_photos):
        ph = SessionPhoto(session_id=session.id, filename=f'sess_{session.id}_{i}.jpg',
                          title=f'Foto {i}', price=price, is_available=True)
        db.session.add(ph)
        photos.append(ph)
    db.session.commit()
    return session, photos


def test_list_photo_sessions(client, make_user):
    photog = make_user(username='foto')
    _make_session(photog)
    h = _auth(client, 'foto')

    resp = client.get('/api/v1/photo-sessions', headers=h)
    assert resp.status_code == 200, _json(resp)
    items = _json(resp)['items']
    assert len(items) == 1
    assert items[0]['title'] == 'Sessão Sábado'
    assert items[0]['photos_count'] == 2
    assert items[0]['price_per_photo_cents'] == 5000


def test_session_detail_preview_only_before_purchase(client, make_user):
    photog = make_user(username='foto')
    make_user(username='buyer')
    session, photos = _make_session(photog)
    h = _auth(client, 'buyer')

    resp = client.get(f'/api/v1/photo-sessions/{session.id}', headers=h)
    assert resp.status_code == 200
    data = _json(resp)['session']
    assert len(data['photos']) == 2
    ph = data['photos'][0]
    assert ph['preview_url'] is not None       # preview sempre disponível
    assert ph['download_url'] is None          # alta só após comprar
    assert ph['is_purchased'] is False
    assert ph['price_cents'] == 5000


def test_purchase_creates_pending_and_ignores_client_price(client, make_user):
    photog = make_user(username='foto')
    make_user(username='buyer')
    session, photos = _make_session(photog, price=50.0)
    h = _auth(client, 'buyer')

    # O cliente tenta forçar preço/valor — deve ser ignorado (preço do servidor).
    resp = client.post(f'/api/v1/photos/{photos[0].id}/purchase',
                       json={'price': 1, 'amount_cents': 1, 'amount': 0.01}, headers=h)
    assert resp.status_code == 201, _json(resp)
    data = _json(resp)
    assert data['already_purchased'] is False
    assert data['purchase']['status'] == 'pending'
    assert data['purchase']['amount_cents'] == 5000   # preço do servidor, não do cliente
    assert data['payment']['test_mode'] is True
    assert data['payment']['provider'] == 'test'
    assert data['payment']['amount_cents'] == 5000

    # Enquanto pending, o download NÃO é liberado.
    assert data['purchase']['download_url'] is None


def test_photo_released_only_after_paid_via_webhook(client, make_user):
    photog = make_user(username='foto')
    make_user(username='buyer')
    session, photos = _make_session(photog)
    h = _auth(client, 'buyer')

    pid = _json(client.post(f'/api/v1/photos/{photos[0].id}/purchase', headers=h))['purchase_id']

    # Antes do webhook: em me/purchases continua pending e sem download.
    mine = _json(client.get('/api/v1/me/purchases', headers=h))['items']
    assert mine[0]['status'] == 'pending'
    assert mine[0]['download_url'] is None

    # Webhook (modo teste) confirma o pagamento.
    wh = client.post('/api/v1/webhooks/payments', json={'purchase_id': pid, 'status': 'paid'})
    assert wh.status_code == 200
    assert _json(wh)['status'] == 'paid'

    # Agora o download é liberado.
    mine = _json(client.get('/api/v1/me/purchases', headers=h))['items']
    assert mine[0]['status'] == 'paid'
    assert mine[0]['download_url'] is not None
    assert mine[0]['photo']['download_url'] is not None

    # E no detalhe da sessão a foto aparece como comprada.
    detail = _json(client.get(f'/api/v1/photo-sessions/{session.id}', headers=h))['session']
    bought = next(p for p in detail['photos'] if p['id'] == photos[0].id)
    assert bought['is_purchased'] is True
    assert bought['download_url'] is not None


def test_webhook_is_idempotent(client, make_user):
    from models import PhotoPurchase

    photog = make_user(username='foto')
    make_user(username='buyer')
    session, photos = _make_session(photog)
    h = _auth(client, 'buyer')
    pid = _json(client.post(f'/api/v1/photos/{photos[0].id}/purchase', headers=h))['purchase_id']

    first = client.post('/api/v1/webhooks/payments', json={'purchase_id': pid, 'status': 'paid'})
    assert first.status_code == 200
    assert _json(first).get('already') in (None, False)

    # Segunda chamada: idempotente, não duplica nem re-libera.
    second = client.post('/api/v1/webhooks/payments', json={'purchase_id': pid, 'status': 'paid'})
    assert second.status_code == 200
    assert _json(second)['already'] is True

    # Continua existindo exatamente 1 compra paga para o par (foto, usuário).
    count = PhotoPurchase.query.filter_by(photo_id=photos[0].id, status='paid').count()
    assert count == 1


def test_purchase_paid_photo_does_not_recharge(client, make_user):
    photog = make_user(username='foto')
    make_user(username='buyer')
    session, photos = _make_session(photog)
    h = _auth(client, 'buyer')

    pid = _json(client.post(f'/api/v1/photos/{photos[0].id}/purchase', headers=h))['purchase_id']
    client.post('/api/v1/webhooks/payments', json={'purchase_id': pid, 'status': 'paid'})

    # Nova tentativa de compra da mesma foto já paga → não cobra de novo.
    resp = client.post(f'/api/v1/photos/{photos[0].id}/purchase', headers=h)
    assert resp.status_code == 200
    data = _json(resp)
    assert data['already_purchased'] is True
    assert data['purchase_id'] == pid


def test_coupon_applies_discount(client, make_user):
    from models import Business, Coupon

    photog = make_user(username='foto')
    make_user(username='buyer')
    session, photos = _make_session(photog, price=100.0)

    # Cria um negócio + cupom de 10%.
    biz = Business(owner_id=photog.id, spot_id=session.spot_id, name='Escola Surf')
    db.session.add(biz)
    db.session.flush()
    db.session.add(Coupon(business_id=biz.id, code='SURF10', discount='10%'))
    db.session.commit()

    h = _auth(client, 'buyer')
    resp = client.post(f'/api/v1/photos/{photos[0].id}/purchase',
                       json={'coupon_code': 'SURF10'}, headers=h)
    assert resp.status_code == 201
    data = _json(resp)
    assert data['purchase']['amount_cents'] == 9000    # 100.00 - 10%
    assert data['purchase']['coupon_code'] == 'SURF10'


def test_purchase_requires_auth(client, make_user):
    photog = make_user(username='foto')
    _, photos = _make_session(photog)
    assert client.post(f'/api/v1/photos/{photos[0].id}/purchase').status_code == 401


def test_webhook_unknown_purchase_is_ignored(client):
    resp = client.post('/api/v1/webhooks/payments', json={'purchase_id': 99999, 'status': 'paid'})
    assert resp.status_code == 200
    assert _json(resp)['ignored'] is True
