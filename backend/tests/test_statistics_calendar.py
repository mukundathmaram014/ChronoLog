import json
from conftest import auth_token

ALL_DAYS = 127  # repeat_days bitmask: every weekday scheduled


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


def total_stopwatch(client, token, date_string):
    resp = client.get(
        f"/api/stopwatches/{date_string}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    stopwatches = json.loads(resp.data)["stopwatches"]
    return next(sw for sw in stopwatches if sw["isTotal"])


def set_duration(client, token, stopwatch_id, milliseconds):
    resp = client.put(
        f"/api/stopwatches/{stopwatch_id}/",
        data=json.dumps({"curr_duration": milliseconds}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def create_habit(client, token, description, date_string, repeat_days=ALL_DAYS):
    resp = client.post(
        "/api/habits/",
        data=json.dumps({
            "description": description,
            "date": date_string,
            "repeat_days": repeat_days,
        }),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return json.loads(resp.data)


def set_done(client, token, habit_id, done):
    resp = client.put(
        f"/api/habits/{habit_id}/",
        data=json.dumps({"done": done}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def get_time_calendar(client, token, date_string, time_period):
    resp = client.get(
        f"/api/stats/stopwatches/calendar/{date_string}/{time_period}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def get_batch_calendar(client, token, date_string, time_period):
    resp = client.get(
        f"/api/stats/habits/calendar/all/{date_string}/{time_period}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def get_single_calendar(client, token, date_string, time_period, description):
    resp = client.get(
        f"/api/stats/habits/calendar/{date_string}/{time_period}/?description={description}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


# --- stopwatch time calendar -------------------------------------------------

def test_time_calendar_day_reports_total_row(client):
    token = auth_token(client)
    sw = create_stopwatch(client, token, "Reading", "2026-01-15")
    set_duration(client, token, sw["id"], 90000)

    data = get_time_calendar(client, token, "2026-01-15", "day")

    assert data["mode"] == "time"
    assert data["start"] == "2026-01-15"
    assert len(data["days"]) == 1
    assert data["days"][0]["date"] == "2026-01-15"
    # the Total row mirrors the day's stopwatch time
    assert data["days"][0]["duration"] == total_stopwatch(client, token, "2026-01-15")["curr_duration"]


def test_time_calendar_week_covers_every_day(client):
    token = auth_token(client)
    # 2026-01-12 is a Monday
    sw = create_stopwatch(client, token, "Reading", "2026-01-14")
    set_duration(client, token, sw["id"], 60000)

    data = get_time_calendar(client, token, "2026-01-14", "week")
    days = data["days"]

    assert data["start"] == "2026-01-12"
    assert len(days) == 7
    assert [d["date"] for d in days][0] == "2026-01-12"
    by_date = {d["date"]: d["duration"] for d in days}
    assert by_date["2026-01-14"] > 0


def test_time_calendar_month_length_and_missing_days_are_zero(client):
    token = auth_token(client)

    data = get_time_calendar(client, token, "2026-01-15", "month")
    days = data["days"]

    assert data["start"] == "2026-01-01"
    assert len(days) == 31
    # no stopwatches at all -> every day reports zeroes, never a missing key
    assert all(d["duration"] == 0 and d["goal"] == 0 for d in days)


def test_time_calendar_invalid_period(client):
    token = auth_token(client)
    resp = client.get(
        "/api/stats/stopwatches/calendar/2026-01-15/decade/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code != 200


def test_time_calendar_scoped_by_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")
    sw_a = create_stopwatch(client, token_a, "Reading", "2026-01-15")
    set_duration(client, token_a, sw_a["id"], 60000)

    data = get_time_calendar(client, token_b, "2026-01-15", "day")

    assert data["days"][0]["duration"] == 0


# --- batch per-habit calendar ------------------------------------------------

def test_batch_calendar_matches_single_habit_endpoint(client):
    token = auth_token(client)
    habit = create_habit(client, token, "Read", "2026-01-15")
    set_done(client, token, habit["id"], True)
    create_habit(client, token, "Run", "2026-01-15")

    batch = get_batch_calendar(client, token, "2026-01-15", "month")
    by_description = {h["description"]: h["days"] for h in batch["habits"]}

    assert sorted(by_description) == ["Read", "Run"]
    for description in ("Read", "Run"):
        single = get_single_calendar(client, token, "2026-01-15", "month", description)
        assert by_description[description] == single["days"]


def test_batch_calendar_marks_absent_days_no_data(client):
    token = auth_token(client)
    # only exists on the 15th; the rest of the month has no row for it
    create_habit(client, token, "Read", "2026-01-15")

    batch = get_batch_calendar(client, token, "2026-01-15", "month")
    days = batch["habits"][0]["days"]
    by_date = {d["date"]: d["status"] for d in days}

    assert len(days) == 31
    assert by_date["2026-01-15"] == "missed"
    assert by_date["2026-01-14"] == "no-data"
    assert by_date["2026-01-16"] == "no-data"


def test_batch_calendar_respects_repeat_days(client):
    token = auth_token(client)
    # 2026-01-15 is a Thursday (weekday 3); schedule Monday only
    create_habit(client, token, "Read", "2026-01-15", repeat_days=1)

    batch = get_batch_calendar(client, token, "2026-01-15", "day")

    assert batch["habits"][0]["days"][0]["status"] == "not-scheduled"


def test_batch_calendar_empty_period(client):
    token = auth_token(client)
    assert get_batch_calendar(client, token, "2026-01-15", "day")["habits"] == []


def test_batch_calendar_invalid_period(client):
    token = auth_token(client)
    resp = client.get(
        "/api/stats/habits/calendar/all/2026-01-15/decade/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code != 200


def test_batch_calendar_scoped_by_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")
    create_habit(client, token_a, "Read", "2026-01-15")

    assert get_batch_calendar(client, token_b, "2026-01-15", "day")["habits"] == []
