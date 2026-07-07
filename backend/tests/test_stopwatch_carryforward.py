import json
from datetime import date, timedelta
from conftest import auth_token


def create_stopwatch(client, token, title, date_str, goal_time="01:00", is_recurring=None):
    body = {"title": title, "date": date_str, "goal_time": goal_time}
    if is_recurring is not None:
        body["is_recurring"] = is_recurring
    return client.post(
        "/api/stopwatches/",
        data=json.dumps(body),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def update_stopwatch(client, token, stopwatch_id, body):
    return client.put(
        f"/api/stopwatches/{stopwatch_id}/",
        data=json.dumps(body),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_stopwatches(client, token, date_str):
    resp = client.get(
        f"/api/stopwatches/{date_str}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    return json.loads(resp.data)["stopwatches"]


def delete_stopwatch(client, token, stopwatch_id):
    return client.delete(
        f"/api/stopwatches/{stopwatch_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_titles(client, token):
    resp = client.get(
        "/api/stopwatches/titles/",
        headers={"Authorization": f"Bearer {token}"},
    )
    return json.loads(resp.data)["titles"]


def test_new_stopwatch_defaults_to_recurring(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "study", "2026-01-15")
    stopwatch = json.loads(resp.data)["stopwatches"][1]
    assert stopwatch["is_recurring"] is True


def test_non_recurring_flag_persists_and_is_editable(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "errand", "2026-01-15", is_recurring=False)
    stopwatch = json.loads(resp.data)["stopwatches"][1]
    assert stopwatch["is_recurring"] is False

    # flip it back to recurring via edit
    resp = update_stopwatch(client, token, stopwatch["id"], {"is_recurring": True})
    edited = json.loads(resp.data)["stopwatches"][1]
    assert edited["is_recurring"] is True


def test_only_recurring_stopwatches_carry_forward(client):
    token = auth_token(client)
    d = date(2026, 1, 15)
    create_stopwatch(client, token, "study", d.isoformat(), goal_time="02:00")
    create_stopwatch(client, token, "errand", d.isoformat(), goal_time="01:00", is_recurring=False)

    stopwatches = get_stopwatches(client, token, (d + timedelta(days=1)).isoformat())
    titles = [s["title"] for s in stopwatches]
    assert titles == ["Total Time", "study"]
    carried = next(s for s in stopwatches if s["title"] == "study")
    assert carried["is_recurring"] is True
    assert carried["curr_duration"] == 0.0
    # the new day's Total goal reflects only the carried (recurring) goals
    total = next(s for s in stopwatches if s["isTotal"])
    assert total["goal_time"] == 2 * 3600000


def test_day_with_only_non_recurring_leaves_next_day_empty(client):
    token = auth_token(client)
    d = date(2026, 1, 15)
    create_stopwatch(client, token, "errand", d.isoformat(), is_recurring=False)

    assert get_stopwatches(client, token, (d + timedelta(days=1)).isoformat()) == []


def test_gap_fill_only_propagates_recurring(client):
    token = auth_token(client)
    d = date(2026, 1, 15)
    create_stopwatch(client, token, "study", d.isoformat())
    create_stopwatch(client, token, "errand", d.isoformat(), is_recurring=False)

    # opening d+3 backfills d+1 and d+2 with the recurring stopwatch only
    stopwatches = get_stopwatches(client, token, (d + timedelta(days=3)).isoformat())
    assert [s["title"] for s in stopwatches] == ["Total Time", "study"]
    for offset in (1, 2):
        day = get_stopwatches(client, token, (d + timedelta(days=offset)).isoformat())
        assert [s["title"] for s in day] == ["Total Time", "study"]


def test_intentionally_emptied_day_stays_empty(client):
    token = auth_token(client)
    d = date(2026, 1, 15)
    resp = create_stopwatch(client, token, "study", d.isoformat())
    stopwatch = json.loads(resp.data)["stopwatches"][1]
    # deleting the only stopwatch marks the day as intentionally emptied
    delete_stopwatch(client, token, stopwatch["id"])

    assert get_stopwatches(client, token, (d + timedelta(days=1)).isoformat()) == []


def test_titles_endpoint_returns_distinct_most_recent_first(client):
    token = auth_token(client)
    create_stopwatch(client, token, "alpha", "2026-01-10", goal_time="01:00")
    create_stopwatch(client, token, "beta", "2026-01-12", goal_time="02:00", is_recurring=False)
    # same title again later, with a different goal: deduped, most recent goal wins
    create_stopwatch(client, token, "alpha", "2026-01-14", goal_time="03:00")

    titles = get_titles(client, token)
    assert [t["title"] for t in titles] == ["alpha", "beta"]  # no "Total Time"
    assert titles[0]["goal_time"] == 3 * 3600000
    assert titles[1]["goal_time"] == 2 * 3600000


def test_titles_endpoint_is_user_scoped(client):
    token_a = auth_token(client, username="usera")
    token_b = auth_token(client, username="userb")
    create_stopwatch(client, token_a, "private", "2026-01-15")

    assert get_titles(client, token_b) == []
