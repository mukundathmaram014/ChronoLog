import os
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")  # must precede `from app import …`

import json
import pytest
from sqlalchemy.pool import StaticPool
from app import create_app


@pytest.fixture()
def app():
    yield create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        },
        "JWT_SECRET_KEY": "test-secret-key",
        "JWT_COOKIE_SECURE": False,
    })


@pytest.fixture()
def client(app):
    return app.test_client()


def auth_token(client, username="testuser", email=None, password="testpass"):
    """Register + login, return Bearer token string."""
    if email is None:
        email = f"{username}@example.com"
    client.post(
        "/api/register",
        data=json.dumps({"username": username, "email": email, "password": password}),
        content_type="application/json",
    )
    resp = client.post(
        "/api/login",
        data=json.dumps({"usernameOrEmail": username, "password": password}),
        content_type="application/json",
    )
    return json.loads(resp.data)["access_token"]
