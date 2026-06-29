import json
from conftest import auth_token


def register(client, username="user1", email="user1@example.com", password="pass"):
    return client.post(
        "/api/register",
        data=json.dumps({"username": username, "email": email, "password": password}),
        content_type="application/json",
    )


def login(client, username_or_email="user1", password="pass"):
    return client.post(
        "/api/login",
        data=json.dumps({"usernameOrEmail": username_or_email, "password": password}),
        content_type="application/json",
    )


def test_register_success(client):
    resp = register(client)
    assert resp.status_code == 201
    body = json.loads(resp.data)
    assert "password_hash" not in body
    assert body["username"] == "user1"


def test_register_duplicate_username(client):
    register(client)
    resp = register(client)
    assert resp.status_code == 409


def test_register_duplicate_email(client):
    register(client, username="user1")
    resp = register(client, username="user2")  # same email user1@example.com
    assert resp.status_code == 409


def test_login_success(client):
    register(client)
    resp = login(client)
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert "access_token" in body


def test_login_wrong_password(client):
    register(client)
    resp = login(client, password="wrong")
    assert resp.status_code == 401


def test_protected_route_no_token(client):
    resp = client.get("/api/habits/2026-01-15/")
    assert resp.status_code == 401


def test_protected_route_with_token(client):
    token = auth_token(client)
    resp = client.get(
        "/api/habits/2026-01-15/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code != 401
