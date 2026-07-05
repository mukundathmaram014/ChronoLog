import json
from conftest import auth_token


def create_stopwatch(client, token, title, date_string):
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": title, "date": date_string}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    stopwatches = json.loads(resp.data)["stopwatches"]
    return next(sw for sw in stopwatches if sw["title"] == title)


def set_duration(client, token, stopwatch_id, milliseconds):
    resp = client.put(
        f"/api/stopwatches/{stopwatch_id}/",
        data=json.dumps({"curr_duration": milliseconds}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def get_breakdown(client, token, date_string, time_period):
    resp = client.get(
        f"/api/stats/stopwatches/breakdown/{date_string}/{time_period}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)["breakdown"]


def test_day_breakdown_excludes_total(client):
    token = auth_token(client)
    sw_a = create_stopwatch(client, token, "Reading", "2026-01-15")
    sw_b = create_stopwatch(client, token, "Coding", "2026-01-15")
    set_duration(client, token, sw_a["id"], 60000)
    set_duration(client, token, sw_b["id"], 120000)

    breakdown = get_breakdown(client, token, "2026-01-15", "day")
    by_title = {item["title"]: item["duration"] for item in breakdown}

    assert by_title == {"Reading": 60000, "Coding": 120000}
    assert "Total Time" not in by_title


def test_week_breakdown_aggregates_by_title(client):
    token = auth_token(client)
    # 2026-01-12 is a Monday; both days fall in the same week
    sw_mon = create_stopwatch(client, token, "Reading", "2026-01-12")
    sw_tue = create_stopwatch(client, token, "Reading", "2026-01-13")
    set_duration(client, token, sw_mon["id"], 60000)
    set_duration(client, token, sw_tue["id"], 30000)

    breakdown = get_breakdown(client, token, "2026-01-14", "week")

    assert breakdown == [{"title": "Reading", "duration": 90000}]


def test_breakdown_empty_period(client):
    token = auth_token(client)
    assert get_breakdown(client, token, "2026-01-15", "day") == []


def test_breakdown_invalid_period(client):
    token = auth_token(client)
    resp = client.get(
        "/api/stats/stopwatches/breakdown/2026-01-15/decade/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code != 200


def test_breakdown_scoped_by_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")
    sw_a = create_stopwatch(client, token_a, "Reading", "2026-01-15")
    set_duration(client, token_a, sw_a["id"], 60000)

    assert get_breakdown(client, token_b, "2026-01-15", "day") == []
