import json
from datetime import date, timedelta
from conftest import auth_token


def create_habit(client, token, description, date_str, repeat_days=None):
    body = {"description": description, "date": date_str}
    if repeat_days is not None:
        body["repeat_days"] = repeat_days
    return client.post(
        "/api/habits/",
        data=json.dumps(body),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def update_habit(client, token, habit_id, body):
    return client.put(
        f"/api/habits/{habit_id}/",
        data=json.dumps(body),
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


# --- repeat_days (spec 0014) ---
# bit i = date.weekday() i (0 = Mon ... 6 = Sun); Mon/Wed/Fri = 0b0010101 = 21
MWF = 0b0010101
MONDAY = date(2026, 1, 12)  # a Monday


def test_repeat_days_default_and_persistence(client):
    token = auth_token(client)
    resp = create_habit(client, token, "Everyday habit", MONDAY.isoformat())
    assert json.loads(resp.data)["repeat_days"] == 127

    resp = create_habit(client, token, "MWF habit", MONDAY.isoformat(), repeat_days=MWF)
    habit = json.loads(resp.data)
    assert habit["repeat_days"] == MWF

    resp = client.get(
        f"/api/habits/{habit['id']}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert json.loads(resp.data)["repeat_days"] == MWF


def test_edit_repeat_days_persists_for_same_habit(client):
    token = auth_token(client)
    resp = create_habit(client, token, "Editable habit", MONDAY.isoformat())
    habit_id = json.loads(resp.data)["id"]

    resp = update_habit(client, token, habit_id, {"description": "Editable habit", "repeat_days": MWF})
    assert resp.status_code == 200
    assert json.loads(resp.data)["repeat_days"] == MWF

    resp = client.get(
        f"/api/habits/{habit_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert json.loads(resp.data)["repeat_days"] == MWF

    resp = get_habits(client, token, MONDAY.isoformat())
    habits = json.loads(resp.data)["habits"]
    assert len(habits) == 1
    assert habits[0]["repeat_days"] == MWF


def test_repeat_days_rejects_invalid(client):
    token = auth_token(client)
    for bad in (0, 128, -1, "21", True):
        resp = create_habit(client, token, "Bad habit", MONDAY.isoformat(), repeat_days=bad)
        assert resp.status_code == 400


def test_carry_forward_skips_unselected_weekday(client):
    token = auth_token(client)
    create_habit(client, token, "MWF habit", MONDAY.isoformat(), repeat_days=MWF)

    # Tuesday: weekday bit not set → habit absent
    resp = get_habits(client, token, (MONDAY + timedelta(days=1)).isoformat())
    assert json.loads(resp.data)["habits"] == []

    # Wednesday: bit set → carried forward with the same repeat_days
    resp = get_habits(client, token, (MONDAY + timedelta(days=2)).isoformat())
    habits = json.loads(resp.data)["habits"]
    assert len(habits) == 1
    assert habits[0]["description"] == "MWF habit"
    assert habits[0]["repeat_days"] == MWF

    # Tuesday is still empty after the Wednesday gap-fill
    resp = get_habits(client, token, (MONDAY + timedelta(days=1)).isoformat())
    assert json.loads(resp.data)["habits"] == []


def test_carry_forward_multi_day_gap_respects_repeat_days(client):
    token = auth_token(client)
    create_habit(client, token, "MWF habit", MONDAY.isoformat(), repeat_days=MWF)

    # Jump straight to the next Monday: intermediates fill only on Wed/Fri
    resp = get_habits(client, token, (MONDAY + timedelta(days=7)).isoformat())
    habits = json.loads(resp.data)["habits"]
    assert len(habits) == 1
    assert habits[0]["date"] == (MONDAY + timedelta(days=7)).isoformat()

    expected_present = {2, 4}  # Wed, Fri offsets
    for offset in range(1, 7):
        resp = get_habits(client, token, (MONDAY + timedelta(days=offset)).isoformat())
        habits = json.loads(resp.data)["habits"]
        if offset in expected_present:
            assert len(habits) == 1, f"expected habit on day +{offset}"
        else:
            assert habits == [], f"expected no habit on day +{offset}"


def test_carry_forward_mixed_habits(client):
    token = auth_token(client)
    create_habit(client, token, "Everyday habit", MONDAY.isoformat())
    create_habit(client, token, "MWF habit", MONDAY.isoformat(), repeat_days=MWF)

    # Tuesday: only the everyday habit carries forward
    resp = get_habits(client, token, (MONDAY + timedelta(days=1)).isoformat())
    habits = json.loads(resp.data)["habits"]
    assert {h["description"] for h in habits} == {"Everyday habit"}

    # Wednesday: both
    resp = get_habits(client, token, (MONDAY + timedelta(days=2)).isoformat())
    habits = json.loads(resp.data)["habits"]
    assert {h["description"] for h in habits} == {"Everyday habit", "MWF habit"}


def test_edit_repeat_days_applies_forward_only(client):
    token = auth_token(client)
    resp = create_habit(client, token, "Morning run", MONDAY.isoformat())
    monday_id = json.loads(resp.data)["id"]

    # Carry forward to Tuesday, then restrict Tuesday's row to MWF
    resp = get_habits(client, token, (MONDAY + timedelta(days=1)).isoformat())
    tuesday_id = json.loads(resp.data)["habits"][0]["id"]
    resp = update_habit(client, token, tuesday_id, {"repeat_days": MWF})
    assert json.loads(resp.data)["repeat_days"] == MWF

    # Wednesday: bit set → present with the new mask
    resp = get_habits(client, token, (MONDAY + timedelta(days=2)).isoformat())
    habits = json.loads(resp.data)["habits"]
    assert len(habits) == 1
    assert habits[0]["repeat_days"] == MWF

    # Thursday: bit not set → absent
    resp = get_habits(client, token, (MONDAY + timedelta(days=3)).isoformat())
    assert json.loads(resp.data)["habits"] == []

    # Past row (Monday) untouched
    resp = client.get(
        f"/api/habits/{monday_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert json.loads(resp.data)["repeat_days"] == 127
