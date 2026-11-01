import json
from datetime import date, datetime, timedelta, timezone

from conftest import auth_token

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def create_stopwatch(client, token, **fields):
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps(fields),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 200
    return json.loads(resp.data)["stopwatches"][1]["id"]


def start(client, token, stopwatch_id, interval_start=None):
    body = {} if interval_start is None else {"interval_start": interval_start}
    return client.patch(
        f"/api/stopwatches/start/{stopwatch_id}/",
        data=json.dumps(body),
        content_type="application/json",
        headers=headers(token),
    )


def stop(client, token, stopwatch_id, end_time=None):
    body = {} if end_time is None else {"end_time": end_time}
    return client.patch(
        f"/api/stopwatches/stop/{stopwatch_id}/",
        data=json.dumps(body),
        content_type="application/json",
        headers=headers(token),
    )


def get_day(client, token, day):
    resp = client.get(f"/api/stopwatches/{day}/", headers=headers(token))
    assert resp.status_code == 200
    return json.loads(resp.data)["stopwatches"]


def get_running(client, token):
    resp = client.get("/api/stopwatches/running/", headers=headers(token))
    assert resp.status_code == 200
    return json.loads(resp.data)["stopwatches"]


def iso_z(dt):
    # what the browser sends: toISOString() ends in "Z"
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def test_stop_at_explicit_time_credits_up_to_it(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="late night", date=TODAY)
    now = datetime.now(timezone.utc)

    assert start(client, token, sw_id, iso_z(now - timedelta(hours=2))).status_code == 200
    resp = stop(client, token, sw_id, iso_z(now - timedelta(hours=1)))
    assert resp.status_code == 200
    total, stopped = json.loads(resp.data)["stopwatches"]

    # exactly the hour between the two explicit instants, on the row and the Total
    assert stopped["curr_duration"] == 3600000
    assert total["curr_duration"] == 3600000

    intervals = json.loads(client.get(f"/api/stopwatches/intervals/{TODAY}/", headers=headers(token)).data)["intervals"]
    assert len(intervals) == 1
    assert intervals[0]["end_time"] == stopped["end_time"]


def test_stop_without_body_still_stops_now(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="plain", date=TODAY)
    assert start(client, token, sw_id).status_code == 200

    # the frontend's plain stop sends no body at all
    resp = client.patch(f"/api/stopwatches/stop/{sw_id}/", headers=headers(token))
    assert resp.status_code == 200
    assert json.loads(resp.data)["stopwatches"][1]["end_time"] is not None


def test_stop_time_in_the_future_is_clamped_to_now(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="future", date=TODAY)
    assert start(client, token, sw_id).status_code == 200

    resp = stop(client, token, sw_id, iso_z(datetime.now(timezone.utc) + timedelta(hours=5)))
    assert resp.status_code == 200
    # credited at most the real elapsed time, not five extra hours
    assert json.loads(resp.data)["stopwatches"][1]["curr_duration"] < 60000


def test_stop_time_before_start_is_rejected(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="backwards", date=TODAY)
    now = datetime.now(timezone.utc)
    assert start(client, token, sw_id, iso_z(now - timedelta(minutes=10))).status_code == 200

    assert stop(client, token, sw_id, iso_z(now - timedelta(hours=1))).status_code == 400
    # nothing was stopped by the rejected request
    assert get_running(client, token)[0]["id"] == sw_id


def test_bad_or_naive_times_are_rejected(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="bad input", date=TODAY)

    assert start(client, token, sw_id, "not a date").status_code == 400
    # no UTC offset: ambiguous, since the server doesn't know the user's timezone
    assert start(client, token, sw_id, "2026-10-31T00:00:00").status_code == 400
    assert start(client, token, sw_id, iso_z(datetime.now(timezone.utc) - timedelta(days=3))).status_code == 400

    assert start(client, token, sw_id).status_code == 200
    assert stop(client, token, sw_id, "not a date").status_code == 400


def test_running_lists_only_running_children_for_this_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")
    running_id = create_stopwatch(client, token_a, title="running", date=YESTERDAY)
    create_stopwatch(client, token_a, title="idle", date=YESTERDAY)
    other_id = create_stopwatch(client, token_b, title="someone else", date=TODAY)

    assert start(client, token_a, running_id).status_code == 200
    assert start(client, token_b, other_id).status_code == 200

    running = get_running(client, token_a)
    # the Total runs in lockstep but isn't listed; the idle row and user B's row aren't either
    assert [sw["id"] for sw in running] == [running_id]
    assert running[0]["date"] == YESTERDAY


def test_midnight_split_credits_each_day_its_own_time(client):
    token = auth_token(client)
    yesterday_id = create_stopwatch(client, token, title="deep work", date=YESTERDAY)
    now = datetime.now(timezone.utc)
    # stand-ins for 23:00 and 00:00: an hour on the old day, then the app wakes later
    started = now - timedelta(hours=2)
    midnight = now - timedelta(hours=1)
    assert start(client, token, yesterday_id, iso_z(started)).status_code == 200

    # the client splits at midnight: stop the old day there...
    assert stop(client, token, yesterday_id, iso_z(midnight)).status_code == 200
    # ...then the new day's carried-forward copy restarts from that same instant
    today_row = next(sw for sw in get_day(client, token, TODAY) if sw["title"] == "deep work")
    assert start(client, token, today_row["id"], iso_z(midnight)).status_code == 200
    total_today, stopped_today = json.loads(stop(client, token, today_row["id"]).data)["stopwatches"]

    yesterday = get_day(client, token, YESTERDAY)
    assert all(sw["curr_duration"] == 3600000 for sw in yesterday)  # row and Total
    # today has the hour since midnight (plus the few ms the test took)
    assert 3600000 <= stopped_today["curr_duration"] < 3600000 + 60000
    assert total_today["curr_duration"] == stopped_today["curr_duration"]
    assert get_running(client, token) == []
