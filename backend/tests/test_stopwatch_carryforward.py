import json
from datetime import date, timedelta
from conftest import auth_token
from db import db, Stopwatch, User

D = date(2026, 1, 15)
ONE_HOUR_MS = 3600000
HALF_HOUR_MS = 1800000


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


def seed_total_only_day(app, day, goal_time=0.0, goal_overridden=False, username="testuser"):
    """
    Insert a bare Total row with no regular stopwatches and no DeletedDay
    marker â€” the state legacy data (from before the DeletedDay marker system)
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
    # carry-forward grants no XP: the XP/level/streak-count fields are unchanged.
    # (The streak-requirement fields do change -- carry-forward adds a goal to hit.)
    for field in ("total_xp", "day_xp", "level", "rank", "xp_into_level", "xp_to_next", "streak", "multiplier"):
        assert before[field] == after[field]
