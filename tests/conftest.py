import os
import pytest
from app import create_app
from models import db

# Creates a Flask app with a temporary SQLite database for tests.
@pytest.fixture()
def app(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    app.config.update(TESTING=True)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()

@pytest.fixture()
def client(app):
    return app.test_client()
