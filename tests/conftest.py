"""Fixtures de teste para a API REST (/api/v1).

Usa um SQLite temporário e isola cada teste (create_all/drop_all). O rate limit
é desligado para os testes não esbarrarem nos limites de login.
"""
import os
import tempfile

# Configura o ambiente ANTES de importar a app (a app lê isto no import).
_db_fd, _db_path = tempfile.mkstemp(suffix='.db')
os.environ['DATABASE_URL'] = 'sqlite:///' + _db_path.replace('\\', '/')
os.environ['SECRET_KEY'] = 'test-secret'
os.environ['JWT_SECRET_KEY'] = 'test-secret'
os.environ.pop('FLASK_ENV', None)  # garante modo não-produção

import pytest  # noqa: E402

from app import app as flask_app  # noqa: E402
from extensions import db  # noqa: E402

# Desliga o rate limit nos testes.
try:
    from routes.api import limiter
    if limiter is not None:
        limiter.enabled = False
except Exception:
    pass

# Os blueprints de messages/trips/photos agora são registrados oficialmente em
# routes/api/register_api() (chamado no import de app), então não há registro
# aditivo aqui.


@pytest.fixture()
def app():
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        db.create_all()
        try:
            yield flask_app
        finally:
            db.session.remove()
            db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_user(app):
    """Cria e persiste um usuário de teste."""
    from models import User

    def _make(username='leo', email=None, password='supersafe123'):
        user = User(username=username, email=email or f'{username}@test.com')
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make
