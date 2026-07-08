import json
from datetime import datetime, timedelta, timezone

from conftest import auth_token
from db import db, User, Habit, TokenBlocklist


def guest(client):
    return client.post("/api/guest")


def test_guest_entry(client):
    resp = guest(client)
    assert resp.status_code == 201
    body = json.loads(resp.data)
    assert "access_token" in body
    assert body["user"]["is_guest"] is True
    assert "password_hash" not in body["user"]
    # logged in like a normal user: refresh cookie set
    assert "refresh_token_cookie" in resp.headers.get("Set-Cookie", "")


def test_guest_usernames_unique(client):
    body_a = json.loads(guest(client).data)
    body_b = json.loads(guest(client).data)
    assert body_a["user"]["username"] != body_b["user"]["username"]


def test_guest_can_use_habits(client):
    token = json.loads(guest(client).data)["access_token"]
    resp = client.post(
        "/api/habits/",
        data=json.dumps({"description": "guest habit", "date": "2026-01-15"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201

    resp = client.get(
        "/api/habits/2026-01-15/",
        headers={"Authorization": f"Bearer {token}"},
    )
    habits = json.loads(resp.data)["habits"]
    assert [h["description"] for h in habits] == ["guest habit"]


def test_guest_isolation(client):
    token_guest = json.loads(guest(client).data)["access_token"]
    token_user = auth_token(client)

    resp = client.post(
        "/api/habits/",
        data=json.dumps({"description": "user habit", "date": "2026-01-15"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token_user}"},
    )
    habit_id = json.loads(resp.data)["id"]

    # the guest cannot see or touch the registered user's habit
    resp = client.get(
        f"/api/habits/{habit_id}/",
        headers={"Authorization": f"Bearer {token_guest}"},
    )
    assert resp.status_code == 404
    resp = client.get(
        "/api/habits/2026-01-15/",
        headers={"Authorization": f"Bearer {token_guest}"},
    )
    assert json.loads(resp.data)["habits"] == []


def test_guest_homepage_note(client):
    token = json.loads(guest(client).data)["access_token"]
    resp = client.put(
        "/api/note",
        data=json.dumps({"homepage_note": "guest note"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    resp = client.get("/api/note", headers={"Authorization": f"Bearer {token}"})
    assert json.loads(resp.data)["homepage_note"] == "guest note"


def _backdate(app, user_id, days):
    with app.app_context():
        user = db.session.get(User, user_id)
        user.created_at = datetime.now(timezone.utc) - timedelta(days=days)
        db.session.commit()


def test_purge_removes_expired_guest_and_data(app, client):
    body = json.loads(guest(client).data)
    guest_id = body["user"]["id"]
    guest_username = body["user"]["username"]
    token = body["access_token"]
    client.post(
        "/api/habits/",
        data=json.dumps({"description": "guest habit", "date": "2026-01-15"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    _backdate(app, guest_id, days=8)

    # provisioning a new guest triggers the purge (compare by username: SQLite
    # reuses the purged row's id for the new guest)
    guest(client)

    with app.app_context():
        assert User.query.filter_by(username=guest_username).first() is None
        assert Habit.query.filter_by(user_id=guest_id).count() == 0
        assert TokenBlocklist.query.filter_by(user_id=guest_id).count() == 0


def test_purge_spares_regular_users_and_fresh_guests(app, client):
    auth_token(client)  # registered user
    fresh_guest_username = json.loads(guest(client).data)["user"]["username"]
    with app.app_context():
        regular = User.query.filter_by(is_guest=False).one()
        regular_id = regular.id
    # an old registered account must never be purged
    _backdate(app, regular_id, days=100)

    guest(client)

    with app.app_context():
        assert db.session.get(User, regular_id) is not None
        assert User.query.filter_by(username=fresh_guest_username).first() is not None
