import json
from datetime import date, timedelta

from conftest import auth_token

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def create_stopwatch(client, token, **fields):
    return client.post(
        "/api/stopwatches/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def start_stopwatch(client, token, stopwatch_id):
    return client.patch(
        f"/api/stopwatches/start/{stopwatch_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_stopwatches(client, token, day):
    resp = client.get(
        f"/api/stopwatches/{day}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)["stopwatches"]


def get_level(client, token, day):
    resp = client.get(
        f"/api/level/{day}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def test_stale_running_stopwatch_is_frozen_on_fetch(client):
    token = auth_token(client)

    # a stopwatch left running on a past day (tab closed before the stop landed)
    resp = create_stopwatch(client, token, title="stranded", date=YESTERDAY)
    assert resp.status_code == 200
    sw_id = json.loads(resp.data)["stopwatches"][1]["id"]
    assert start_stopwatch(client, token, sw_id).status_code == 200

    xp_before = get_level(client, token, YESTERDAY)

    # fetching the day sweeps it: frozen at end_time = interval_start,
    # curr_duration untouched — the Total was running in lockstep and freezes too
    stopwatches = get_stopwatches(client, token, YESTERDAY)
    assert len(stopwatches) == 2
    for sw in stopwatches:
        assert sw["end_time"] is not None
        assert sw["end_time"] == sw["interval_start"]
        assert sw["curr_duration"] == 0.0

    # the sweep must not touch the XP ledger
    assert get_level(client, token, YESTERDAY) == xp_before


def test_todays_running_stopwatch_is_not_frozen(client):
    token = auth_token(client)

    resp = create_stopwatch(client, token, title="active", date=TODAY)
    assert resp.status_code == 200
    sw_id = json.loads(resp.data)["stopwatches"][1]["id"]
    assert start_stopwatch(client, token, sw_id).status_code == 200

    stopwatches = get_stopwatches(client, token, TODAY)
    running = [sw for sw in stopwatches if sw["id"] == sw_id]
    assert len(running) == 1
    assert running[0]["end_time"] is None
