import json
from datetime import date, datetime, timedelta, timezone

from conftest import auth_token

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def create_stopwatch(client, token, **fields):
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)["stopwatches"][1]["id"]


def start_stopwatch(client, token, stopwatch_id):
    return client.patch(
        f"/api/stopwatches/start/{stopwatch_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )


def stop_stopwatch(client, token, stopwatch_id):
    return client.patch(
        f"/api/stopwatches/stop/{stopwatch_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )


def reset_stopwatch(client, token, stopwatch_id, state=None):
    return client.patch(
        f"/api/stopwatches/reset/{stopwatch_id}/",
        data=json.dumps({"state": state}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_intervals(client, token, day):
    resp = client.get(
        f"/api/stopwatches/intervals/{day}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)["intervals"]


def total_id(client, token, day):
    resp = client.get(
        f"/api/stopwatches/{day}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    stopwatches = json.loads(resp.data)["stopwatches"]
    return next(sw["id"] for sw in stopwatches if sw["isTotal"])


def test_stop_records_one_interval(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="deep work", date=TODAY)

    assert start_stopwatch(client, token, sw_id).status_code == 200
    stopped = json.loads(stop_stopwatch(client, token, sw_id).data)["stopwatches"][1]

    intervals = get_intervals(client, token, TODAY)
    assert len(intervals) == 1
    assert intervals[0]["stopwatch_id"] == sw_id
    assert intervals[0]["title"] == "deep work"
    # the recorded bounds are the same pair the endpoint used for the increment
    assert intervals[0]["end_time"] == stopped["end_time"]
    assert intervals[0]["start_time"] == stopped["interval_start"]


def test_two_cycles_record_two_ordered_intervals(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="reading", date=TODAY)

    for _ in range(2):
        assert start_stopwatch(client, token, sw_id).status_code == 200
        assert stop_stopwatch(client, token, sw_id).status_code == 200

    intervals = get_intervals(client, token, TODAY)
    assert len(intervals) == 2
    assert intervals[0]["start_time"] <= intervals[1]["start_time"]
    assert intervals[0]["end_time"] <= intervals[1]["start_time"]


def test_total_row_records_no_interval(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="writing", date=TODAY)
    total = total_id(client, token, TODAY)

    # the frontend never stops the Total directly, but the endpoint allows it
    assert start_stopwatch(client, token, sw_id).status_code == 200
    assert stop_stopwatch(client, token, total).status_code == 200

    assert get_intervals(client, token, TODAY) == []


def test_stale_finalize_records_nothing(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="stranded", date=YESTERDAY)
    assert start_stopwatch(client, token, sw_id).status_code == 200

    # fetching the day sweeps the stranded stopwatch (end_time = interval_start)
    client.get(f"/api/stopwatches/{TODAY}/", headers={"Authorization": f"Bearer {token}"})

    assert get_intervals(client, token, YESTERDAY) == []


def test_non_positive_segment_is_skipped(client, app):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="misfire", date=TODAY)
    assert start_stopwatch(client, token, sw_id).status_code == 200

    # an interval_start at/after the stop credits no time (the shape a stale
    # finalize leaves behind, or a clock-skewed start) — it must record nothing
    with app.app_context():
        from db import db, Stopwatch
        stopwatch = db.session.get(Stopwatch, sw_id)
        stopwatch.interval_start = datetime.now(timezone.utc) + timedelta(minutes=5)
        db.session.commit()

    assert stop_stopwatch(client, token, sw_id).status_code == 200
    assert get_intervals(client, token, TODAY) == []


def test_reset_deletes_only_that_stopwatch_and_day(client):
    token = auth_token(client)
    kept_other = create_stopwatch(client, token, title="kept", date=TODAY)
    target_today = create_stopwatch(client, token, title="target", date=TODAY)
    target_yesterday = create_stopwatch(client, token, title="target", date=YESTERDAY)

    for sw_id in (kept_other, target_today, target_yesterday):
        assert start_stopwatch(client, token, sw_id).status_code == 200
        assert stop_stopwatch(client, token, sw_id).status_code == 200

    assert len(get_intervals(client, token, TODAY)) == 2
    assert len(get_intervals(client, token, YESTERDAY)) == 1

    assert reset_stopwatch(client, token, target_today).status_code == 200

    today_intervals = get_intervals(client, token, TODAY)
    assert [i["stopwatch_id"] for i in today_intervals] == [kept_other]
    # the other day's rows for the same title are untouched
    assert len(get_intervals(client, token, YESTERDAY)) == 1


def test_deleting_stopwatch_removes_its_intervals(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="doomed", date=TODAY)
    assert start_stopwatch(client, token, sw_id).status_code == 200
    assert stop_stopwatch(client, token, sw_id).status_code == 200
    assert len(get_intervals(client, token, TODAY)) == 1

    resp = client.delete(
        f"/api/stopwatches/{sw_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    assert get_intervals(client, token, TODAY) == []


def test_manual_duration_edit_creates_no_interval(client):
    token = auth_token(client)
    sw_id = create_stopwatch(client, token, title="edited", date=TODAY)

    resp = client.put(
        f"/api/stopwatches/{sw_id}/",
        data=json.dumps({"curr_duration": 1800000}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # accepted mismatch: edited totals produce no session-log rows (spec 0030)
    assert get_intervals(client, token, TODAY) == []


def test_intervals_are_scoped_to_the_requesting_user(client):
    owner = auth_token(client, username="owner")
    sw_id = create_stopwatch(client, owner, title="owner work", date=TODAY)
    assert start_stopwatch(client, owner, sw_id).status_code == 200
    assert stop_stopwatch(client, owner, sw_id).status_code == 200

    intruder = auth_token(client, username="intruder")
    assert get_intervals(client, intruder, TODAY) == []
    assert len(get_intervals(client, owner, TODAY)) == 1
