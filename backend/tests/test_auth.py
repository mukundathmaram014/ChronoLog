import json
from http.cookies import SimpleCookie
from conftest import auth_token

THIRTY_DAYS_SECONDS = 30 * 24 * 60 * 60


def cookies_from(resp):
    """Parse a response's Set-Cookie headers into {name: Morsel}."""
    jar = {}
    for header in resp.headers.getlist("Set-Cookie"):
        parsed = SimpleCookie()
        parsed.load(header)
        for name, morsel in parsed.items():
            jar[name] = morsel
    return jar


def do_refresh(client, csrf):
    return client.post("/api/refresh", headers={"X-CSRF-TOKEN": csrf})


def send_refresh_cookies(client, refresh_cookie, csrf):
    """Replace the client's cookie jar with a specific refresh token pair."""
    client.cookie_jar.clear()
    client.set_cookie("localhost", "refresh_token_cookie", refresh_cookie)
    client.set_cookie("localhost", "csrf_refresh_token", csrf)


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


def test_login_refresh_cookies_outlive_browser_session(client):
    """
    Both refresh cookies must be persistent, not session cookies that die when
    the browser closes. Their Max-Age must also outlast the 30-day refresh
    token itself, so the token's own expiry is what ends the session.
    """
    register(client)
    jar = cookies_from(login(client))

    for name in ("refresh_token_cookie", "csrf_refresh_token"):
        assert name in jar, f"{name} not set on login"
        max_age = jar[name]["max-age"]
        assert max_age != "", f"{name} is a session cookie (no Max-Age)"
        assert int(max_age) >= THIRTY_DAYS_SECONDS


def test_refresh_succeeds_with_cookie_and_csrf(client):
    register(client)
    jar = cookies_from(login(client))

    resp = do_refresh(client, jar["csrf_refresh_token"].value)
    assert resp.status_code == 200
    body = json.loads(resp.data)
    assert body["access_token"]
    assert body["username"] == "user1"
    assert body["email"] == "user1@example.com"
    assert body["is_guest"] is False


def test_refresh_rotates_the_refresh_cookie(client):
    register(client)
    jar = cookies_from(login(client))
    old_refresh = jar["refresh_token_cookie"].value

    resp = do_refresh(client, jar["csrf_refresh_token"].value)
    assert resp.status_code == 200

    new_jar = cookies_from(resp)
    assert "refresh_token_cookie" in new_jar, "refresh did not re-issue the cookie"
    assert new_jar["refresh_token_cookie"].value != old_refresh
    assert int(new_jar["refresh_token_cookie"]["max-age"]) >= THIRTY_DAYS_SECONDS


def test_old_refresh_token_still_works_after_rotation(client):
    """Rotation must not revoke the old token — concurrent tabs would break."""
    register(client)
    jar = cookies_from(login(client))
    old_refresh = jar["refresh_token_cookie"].value
    old_csrf = jar["csrf_refresh_token"].value

    assert do_refresh(client, old_csrf).status_code == 200  # rotates

    send_refresh_cookies(client, old_refresh, old_csrf)
    assert do_refresh(client, old_csrf).status_code == 200


def test_logout_after_refresh_revokes_the_rotated_token(client):
    register(client)
    jar = cookies_from(login(client))

    refreshed = do_refresh(client, jar["csrf_refresh_token"].value)
    access_token = json.loads(refreshed.data)["access_token"]
    new_jar = cookies_from(refreshed)
    new_refresh = new_jar["refresh_token_cookie"].value
    new_csrf = new_jar["csrf_refresh_token"].value

    logout = client.post(
        "/api/logout", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert logout.status_code == 200

    send_refresh_cookies(client, new_refresh, new_csrf)
    assert do_refresh(client, new_csrf).status_code == 401
