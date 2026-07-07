import json
from datetime import date, timedelta

from conftest import auth_token
from db import db, Stopwatch, User


D = date(2026, 1, 15)
ONE_HOUR_MS = 3600000
HALF_HOUR_MS = 1800000


def create_stopwatch(client, token, title, date_str, goal_time="01:00"):
    return client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": title, "date": date_str, "goal_time": goal_time}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_stopwatches(client, token, date_str):
    resp = client.get(
        f"/api/stopwatches/{date_str}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)["stopwatches"]


def delete_stopwatch(client, token, stopwatch_id):
    return client.delete(
        f"/api/stopwatches/{stopwatch_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )


def seed_total_only_day(app, day, goal_time=0.0, goal_overridden=False, username="testuser"):
    """
    Insert a bare Total row with no regular stopwatches and no DeletedDay
    marker — the state legacy data (from before the DeletedDay marker system)
    left behind; current API paths always pair a marker with a Total-only day.
    """
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        total = Stopwatch(
            title="Total Time",
            date=day,
            isTotal=True,
            goal_time=goal_time,
            goal_overridden=goal_overridden,
            user_id=user.id,
        )
        db.session.add(total)
        db.session.commit()


def totals_of(stopwatches):
    return [s for s in stopwatches if s["isTotal"]]


def regulars_of(stopwatches):
    return [s for s in stopwatches if not s["isTotal"]]


def test_carry_forward_next_day(client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", D.isoformat())
    create_stopwatch(client, token, "Reading", D.isoformat(), goal_time="00:30")

    next_day = (D + timedelta(days=1)).isoformat()
    stopwatches = get_stopwatches(client, token, next_day)

    assert {s["title"] for s in regulars_of(stopwatches)} == {"Coding", "Reading"}
    totals = totals_of(stopwatches)
    assert len(totals) == 1
    # the returned Total reflects every carried goal, not just the first
    assert totals[0]["goal_time"] == ONE_HOUR_MS + HALF_HOUR_MS
    assert all(s["curr_duration"] == 0 for s in stopwatches)
    assert all(s["date"] == next_day for s in stopwatches)


def test_total_only_day_repopulates(app, client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", D.isoformat())
    # a leftover goal on the Total must not survive into the repopulated sum
    seed_total_only_day(app, D + timedelta(days=1), goal_time=12345.0)

    next_day = (D + timedelta(days=1)).isoformat()
    stopwatches = get_stopwatches(client, token, next_day)

    assert [s["title"] for s in regulars_of(stopwatches)] == ["Coding"]
    totals = totals_of(stopwatches)
    assert len(totals) == 1
    assert totals[0]["goal_time"] == ONE_HOUR_MS

    # a second visit creates no duplicates
    stopwatches = get_stopwatches(client, token, next_day)
    assert len(stopwatches) == 2
    assert len(totals_of(stopwatches)) == 1


def test_total_only_day_keeps_overridden_goal(app, client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", D.isoformat())
    seed_total_only_day(app, D + timedelta(days=1), goal_time=2 * ONE_HOUR_MS, goal_overridden=True)

    stopwatches = get_stopwatches(client, token, (D + timedelta(days=1)).isoformat())

    assert [s["title"] for s in regulars_of(stopwatches)] == ["Coding"]
    totals = totals_of(stopwatches)
    assert len(totals) == 1
    assert totals[0]["goal_time"] == 2 * ONE_HOUR_MS
    assert totals[0]["goal_overridden"] is True


def test_deleted_day_not_repopulated(client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", (D - timedelta(days=1)).isoformat())
    resp = create_stopwatch(client, token, "Temp", D.isoformat())
    temp_id = json.loads(resp.data)["stopwatches"][1]["id"]

    # deleting the day's only stopwatch marks it intentionally emptied
    delete_stopwatch(client, token, temp_id)

    stopwatches = get_stopwatches(client, token, D.isoformat())
    assert regulars_of(stopwatches) == []
    assert len(totals_of(stopwatches)) == 1


def test_carry_forward_stops_at_deleted_day(client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", (D - timedelta(days=1)).isoformat())
    resp = create_stopwatch(client, token, "Temp", D.isoformat())
    temp_id = json.loads(resp.data)["stopwatches"][1]["id"]
    delete_stopwatch(client, token, temp_id)

    # the backwalk from D+1 hits D's DeletedDay marker and carries nothing
    stopwatches = get_stopwatches(client, token, (D + timedelta(days=1)).isoformat())
    assert stopwatches == []


def test_multi_day_gap_fills_intermediates(client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", D.isoformat())

    stopwatches = get_stopwatches(client, token, (D + timedelta(days=3)).isoformat())
    assert [s["title"] for s in regulars_of(stopwatches)] == ["Coding"]
    assert all(s["date"] == (D + timedelta(days=3)).isoformat() for s in stopwatches)

    # intermediate days were created in the DB during the D+3 request
    for offset in (1, 2):
        day_stopwatches = get_stopwatches(client, token, (D + timedelta(days=offset)).isoformat())
        assert [s["title"] for s in regulars_of(day_stopwatches)] == ["Coding"]
        assert len(totals_of(day_stopwatches)) == 1


def test_gap_backfill_through_total_only_day(app, client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", D.isoformat())
    seed_total_only_day(app, D + timedelta(days=1))

    # the backwalk from D+3 skips the Total-only D+1 and carries from D;
    # the in-between backfill must reuse D+1's Total, not duplicate it
    stopwatches = get_stopwatches(client, token, (D + timedelta(days=3)).isoformat())
    assert [s["title"] for s in regulars_of(stopwatches)] == ["Coding"]

    for offset in (1, 2):
        day_stopwatches = get_stopwatches(client, token, (D + timedelta(days=offset)).isoformat())
        assert [s["title"] for s in regulars_of(day_stopwatches)] == ["Coding"]
        assert len(totals_of(day_stopwatches)) == 1


def test_carry_forward_leaves_day_xp_unchanged(client):
    token = auth_token(client)
    create_stopwatch(client, token, "Coding", D.isoformat())

    day = (D + timedelta(days=1)).isoformat()
    headers = {"Authorization": f"Bearer {token}"}
    before = json.loads(client.get(f"/api/level/{day}/", headers=headers).data)
    get_stopwatches(client, token, day)  # triggers carry-forward
    after = json.loads(client.get(f"/api/level/{day}/", headers=headers).data)
    assert before == after
