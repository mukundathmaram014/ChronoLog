import json
from datetime import date, timedelta
from conftest import auth_token


def create_habit(client, token, description, date_str):
    return client.post(
        "/api/habits/",
        data=json.dumps({"description": description, "date": date_str}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_habits(client, token, date_str):
    return client.get(
        f"/api/habits/{date_str}/",
        headers={"Authorization": f"Bearer {token}"},
    )


def delete_habit(client, token, habit_id):
    return client.delete(
        f"/api/habits/{habit_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )


def test_carry_forward_next_day(client):
    token = auth_token(client)
    d = date(2026, 1, 15)
    create_habit(client, token, "Morning run", d.isoformat())
    create_habit(client, token, "Read book", d.isoformat())

    resp = get_habits(client, token, (d + timedelta(days=1)).isoformat())
    body = json.loads(resp.data)
    habits = body["habits"]
    descriptions = {h["description"] for h in habits}
    assert descriptions == {"Morning run", "Read book"}
    assert all(h["done"] is False for h in habits)
    assert all(h["date"] == (d + timedelta(days=1)).isoformat() for h in habits)


def test_carry_forward_gap_fill(client):
    token = auth_token(client)
    d = date(2026, 1, 15)
    create_habit(client, token, "Morning run", d.isoformat())

    # GET D+3 should fill D+1, D+2, and D+3
    resp = get_habits(client, token, (d + timedelta(days=3)).isoformat())
    body = json.loads(resp.data)
    habits = body["habits"]
    assert len(habits) == 1
    assert habits[0]["description"] == "Morning run"
    assert habits[0]["date"] == (d + timedelta(days=3)).isoformat()

    # Intermediate day D+1 was created in the DB during the D+3 request
    resp = get_habits(client, token, (d + timedelta(days=1)).isoformat())
    body = json.loads(resp.data)
    assert len(body["habits"]) == 1
    assert body["habits"][0]["date"] == (d + timedelta(days=1)).isoformat()


def test_deleted_day_no_repopulate(client):
    token = auth_token(client)
    d = date(2026, 1, 15)
    resp = create_habit(client, token, "Morning run", d.isoformat())
    habit_id = json.loads(resp.data)["id"]

    # Delete the only habit — creates DeletedDay marker
    delete_habit(client, token, habit_id)

    # Re-GET should not repopulate
    resp = get_habits(client, token, d.isoformat())
    body = json.loads(resp.data)
    assert body["habits"] == []


def test_carry_forward_stops_at_deleted_day(client):
    token = auth_token(client)
    d = date(2026, 1, 15)

    # Create a habit on d-1
    create_habit(client, token, "Morning run", (d - timedelta(days=1)).isoformat())

    # Create and immediately delete a habit on d → creates DeletedDay marker for d
    resp = create_habit(client, token, "Temp habit", d.isoformat())
    habit_id = json.loads(resp.data)["id"]
    delete_habit(client, token, habit_id)

    # GET d+1: carry-forward backwalks to d, hits DeletedDay, stops → empty
    resp = get_habits(client, token, (d + timedelta(days=1)).isoformat())
    body = json.loads(resp.data)
    assert body["habits"] == []
