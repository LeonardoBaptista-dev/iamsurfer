"""Testes do upload assinado Cloudinary (A11)."""
import pytest


def _json(resp):
    return resp.get_json()


def _auth(client, username='leo', password='supersafe123'):
    resp = client.post('/api/v1/auth/login', json={'identifier': username, 'password': password})
    return {'Authorization': f'Bearer {_json(resp)["access_token"]}'}


def test_sign_requires_auth(client):
    assert client.post('/api/v1/media/sign', json={}).status_code == 401


def test_sign_without_cloudinary_returns_503(client, make_user, monkeypatch):
    make_user(username='leo')
    h = _auth(client)
    # Garante config Cloudinary vazia.
    try:
        import cloudinary
        monkeypatch.setattr(cloudinary, 'config', lambda **k: type('C', (), {
            'cloud_name': None, 'api_key': None, 'api_secret': None})())
    except ImportError:
        pass
    resp = client.post('/api/v1/media/sign', json={'resource_type': 'image'}, headers=h)
    assert resp.status_code == 503
    assert _json(resp)['error']['code'] == 'media_unavailable'


def test_sign_invalid_resource_type(client, make_user):
    make_user(username='leo')
    h = _auth(client)
    resp = client.post('/api/v1/media/sign', json={'resource_type': 'pdf'}, headers=h)
    assert resp.status_code == 422
    assert _json(resp)['error']['code'] == 'validation_error'


def test_sign_with_cloudinary(client, make_user, monkeypatch):
    cloudinary = pytest.importorskip('cloudinary')
    import cloudinary.utils

    make_user(username='leo')
    h = _auth(client)

    fake_cfg = type('C', (), {'cloud_name': 'demo', 'api_key': '123', 'api_secret': 'secret'})()
    monkeypatch.setattr(cloudinary, 'config', lambda **k: fake_cfg)

    resp = client.post('/api/v1/media/sign', json={'resource_type': 'image'}, headers=h)
    assert resp.status_code == 200, _json(resp)
    data = _json(resp)
    assert data['cloud_name'] == 'demo'
    assert data['api_key'] == '123'
    assert data['folder'].startswith('iamsurfer/')
    assert data['upload_url'] == 'https://api.cloudinary.com/v1_1/demo/image/upload'

    # A assinatura confere com o que o Cloudinary calcularia.
    expected = cloudinary.utils.api_sign_request(
        {'timestamp': data['timestamp'], 'folder': data['folder']}, 'secret')
    assert data['signature'] == expected


def test_sign_folder_confined_to_namespace(client, make_user, monkeypatch):
    cloudinary = pytest.importorskip('cloudinary')
    make_user(username='leo')
    h = _auth(client)
    fake_cfg = type('C', (), {'cloud_name': 'demo', 'api_key': '123', 'api_secret': 'secret'})()
    monkeypatch.setattr(cloudinary, 'config', lambda **k: fake_cfg)

    resp = client.post('/api/v1/media/sign',
                       json={'resource_type': 'image', 'folder': 'hack/../../etc'}, headers=h)
    assert _json(resp)['folder'].startswith('iamsurfer/')


def test_confirm_normalizes_media(client, make_user):
    make_user(username='leo')
    h = _auth(client)
    resp = client.post('/api/v1/media/confirm', json={
        'public_id': 'iamsurfer/uploads/abc',
        'secure_url': 'https://res.cloudinary.com/demo/image/upload/abc.jpg',
        'resource_type': 'image', 'width': 1080, 'height': 1080,
    }, headers=h)
    assert resp.status_code == 200
    media = _json(resp)['media']
    assert media['public_id'] == 'iamsurfer/uploads/abc'
    assert media['width'] == 1080
