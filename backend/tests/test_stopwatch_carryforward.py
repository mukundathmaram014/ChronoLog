import json
from datetime import date, timedelta
from conftest import auth_token
from db import db, Stopwatch, User

D = date(2026, 1, 15)
ONE_HOUR_MS = 3600000
HALF_HOUR_MS = 1800000


def create_stopwatch(client, token, title, date_str, goal_time="01:00", is_recurring=None, repeat_days=None, weekday_goal_times=None):
    body = {"title": title, "date": date_str, "goal_time": goal_time}
    if is_recurring is not None:
        body["is_recurring"] = is_recurring
    if repeat_days is not None:
        body["repeat_days"] = repeat_days
    if weekday_goal_times is not None:
        body["weekday_goal_times"] = weekday_goal_times
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


# ---- per-weekday repeat days (spec 0027) ----
# bit i = date.weekday() i (0 = Mon ... 6 = Sun); 2026-01-05 is a Monday
MONDAY = date(2026, 1, 5)
MON, TUE, WED, THU, FRI, SAT, SUN = (1 << i for i in range(7))
MWF = MON | WED | FRI


def day(offset):
    """Date `offset` days after the anchor Monday, as an ISO string."""
    return (MONDAY + timedelta(days=offset)).isoformat()


def titles_on(client, token, offset):
    return [s["title"] for s in regulars_of(get_stopwatches(client, token, day(offset)))]


def test_new_stopwatch_defaults_to_every_day(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "study", day(0))
    assert json.loads(resp.data)["stopwatches"][1]["repeat_days"] == 127


def test_repeat_days_persists_on_create(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "gym", day(0), repeat_days=MWF)
    assert json.loads(resp.data)["stopwatches"][1]["repeat_days"] == MWF


def test_carry_forward_skips_unscheduled_weekday(client):
    token = auth_token(client)
    create_stopwatch(client, token, "gym", day(0), repeat_days=MWF)

    # Tuesday isn't in the repeat set, so nothing carries there
    assert titles_on(client, token, 1) == []
    # Wednesday is, so it comes back
    assert titles_on(client, token, 2) == ["gym"]


def test_gap_fill_only_creates_scheduled_weekdays(client):
    token = auth_token(client)
    create_stopwatch(client, token, "gym", day(0), repeat_days=MWF)

    # opening Friday backfills the intermediate days, but only Wednesday qualifies
    assert titles_on(client, token, 4) == ["gym"]
    assert titles_on(client, token, 2) == ["gym"]
    assert titles_on(client, token, 1) == []
    assert titles_on(client, token, 3) == []


def test_off_day_stopwatch_survives_extended_lookback(client):
    token = auth_token(client)
    create_stopwatch(client, token, "daily", day(0))
    create_stopwatch(client, token, "mondays", day(0), repeat_days=MON)

    # Tue..Sun are filled by "daily" only; a naive scan that stopped at the most
    # recent filled day would lose "mondays" forever
    for offset in range(1, 7):
        assert titles_on(client, token, offset) == ["daily"]

    # the extended 7-day scan finds it again on the next Monday
    assert set(titles_on(client, token, 7)) == {"daily", "mondays"}


def test_deletion_on_a_scheduled_day_stops_carry_forward(client):
    token = auth_token(client)
    create_stopwatch(client, token, "daily", day(0))
    create_stopwatch(client, token, "gym", day(0), repeat_days=MWF)

    # delete "gym" on Wednesday, one of its scheduled days ("daily" keeps the day
    # non-empty, so no DeletedDay marker is written)
    wednesday = get_stopwatches(client, token, day(2))
    gym = next(s for s in wednesday if s["title"] == "gym")
    delete_stopwatch(client, token, gym["id"])

    # Friday is scheduled, but the Wednesday deletion means it shouldn't return
    assert titles_on(client, token, 4) == ["daily"]


def test_total_goal_counts_only_stopwatches_landing_that_day(client):
    token = auth_token(client)
    create_stopwatch(client, token, "daily", day(0), goal_time="01:00")
    create_stopwatch(client, token, "mondays", day(0), goal_time="02:00", repeat_days=MON)

    tuesday = get_stopwatches(client, token, day(1))
    assert [s["title"] for s in regulars_of(tuesday)] == ["daily"]
    totals = totals_of(tuesday)
    assert len(totals) == 1
    # only the carried "daily" goal, not the off-day "mondays" one
    assert totals[0]["goal_time"] == ONE_HOUR_MS


def test_non_recurring_ignores_repeat_days(client):
    token = auth_token(client)
    # scheduled for Tuesday, but non-recurring wins: it never carries
    create_stopwatch(client, token, "errand", day(0), is_recurring=False, repeat_days=TUE)

    assert titles_on(client, token, 1) == []


def test_repeat_days_is_editable_and_applies_forward(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "gym", day(0))
    stopwatch = json.loads(resp.data)["stopwatches"][1]

    resp = update_stopwatch(client, token, stopwatch["id"], {"repeat_days": MON})
    assert json.loads(resp.data)["stopwatches"][1]["repeat_days"] == MON

    # now a Monday-only stopwatch: Tuesday is skipped
    assert titles_on(client, token, 1) == []


def test_invalid_repeat_days_rejected_on_create_and_edit(client):
    token = auth_token(client)
    for bad in (0, 128, -1, "127", True):
        resp = create_stopwatch(client, token, f"bad{bad}", day(0), repeat_days=bad)
        assert resp.status_code == 400, f"repeat_days={bad!r} should be rejected"

    resp = create_stopwatch(client, token, "gym", day(0))
    stopwatch = json.loads(resp.data)["stopwatches"][1]
    for bad in (0, 128, -1, "127", True):
        resp = update_stopwatch(client, token, stopwatch["id"], {"repeat_days": bad})
        assert resp.status_code == 400, f"repeat_days={bad!r} should be rejected"


def test_editing_total_ignores_repeat_days(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "gym", day(0))
    total = json.loads(resp.data)["stopwatches"][0]

    # the Total has no meaningful mask; the edit still succeeds
    resp = update_stopwatch(client, token, total["id"], {"goal_time": "03:00"})
    assert resp.status_code == 200
    assert json.loads(resp.data)["stopwatches"][0]["goal_time"] == 3 * ONE_HOUR_MS


def test_titles_endpoint_returns_repeat_days(client):
    token = auth_token(client)
    create_stopwatch(client, token, "gym", day(0), repeat_days=MWF)
    create_stopwatch(client, token, "study", day(0))

    titles = {t["title"]: t["repeat_days"] for t in get_titles(client, token)}
    assert titles == {"gym": MWF, "study": 127}


def test_weekday_gated_carry_forward_leaves_day_xp_unchanged(client):
    token = auth_token(client)
    create_stopwatch(client, token, "gym", day(0), repeat_days=MWF)

    headers = {"Authorization": f"Bearer {token}"}
    before = json.loads(client.get(f"/api/level/{day(2)}/", headers=headers).data)
    get_stopwatches(client, token, day(2))  # triggers weekday-gated carry-forward
    after = json.loads(client.get(f"/api/level/{day(2)}/", headers=headers).data)
    for field in ("total_xp", "day_xp", "level", "xp_into_level", "xp_to_next", "streak", "multiplier"):
        assert before[field] == after[field]


# ---- per-weekday goal times (spec 0036) ----
# index i = date.weekday() i (0 = Mon ... 6 = Sun), the same convention as repeat_days

def schedule(**by_label):
    """
    A dense 7-slot "HH:MM" schedule; unnamed weekdays default to "00:30".
    e.g. schedule(Mo="02:00", Sa="00:00")
    """
    labels = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    return [by_label.get(label, "00:30") for label in labels]


def regular_on(client, token, offset, title):
    return next(s for s in regulars_of(get_stopwatches(client, token, day(offset))) if s["title"] == title)


def total_on(client, token, offset):
    return totals_of(get_stopwatches(client, token, day(offset)))[0]


def test_weekday_schedule_persists_and_sets_the_creation_days_goal(client):
    token = auth_token(client)
    # created on the anchor Monday: it lands with Monday's slot, not the goal_time field
    resp = create_stopwatch(client, token, "study", day(0), goal_time="09:00",
                            weekday_goal_times=schedule(Mo="02:00"))
    created = json.loads(resp.data)["stopwatches"][1]
    assert created["goal_time"] == 2 * ONE_HOUR_MS
    assert created["weekday_goal_times"] == [2 * ONE_HOUR_MS] + [HALF_HOUR_MS] * 6
    # and the Total is that landed goal, not the ignored 9h
    assert json.loads(resp.data)["stopwatches"][0]["goal_time"] == 2 * ONE_HOUR_MS


def test_carry_forward_lands_the_new_days_weekday_goal(client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="02:00", Tu="00:45"))

    tuesday = regular_on(client, token, 1, "study")
    assert tuesday["goal_time"] == 45 * 60000
    # the schedule itself carries forward unchanged
    assert tuesday["weekday_goal_times"] == json.loads(
        client.get(f"/api/stopwatches/{day(0)}/", headers={"Authorization": f"Bearer {token}"}).data
    )["stopwatches"][1]["weekday_goal_times"]
    # the day's Total is the sum of the goals that actually landed there
    assert total_on(client, token, 1)["goal_time"] == 45 * 60000


def test_gap_backfill_gives_each_day_its_own_weekday_goal(client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0),
                     weekday_goal_times=schedule(Mo="01:00", Tu="02:00", We="03:00", Th="04:00"))

    # opening Thursday backfills Tue and Wed; each gets its own weekday's goal
    assert regular_on(client, token, 3, "study")["goal_time"] == 4 * ONE_HOUR_MS
    assert regular_on(client, token, 1, "study")["goal_time"] == 2 * ONE_HOUR_MS
    assert regular_on(client, token, 2, "study")["goal_time"] == 3 * ONE_HOUR_MS
    for offset in (1, 2, 3):
        assert total_on(client, token, offset)["goal_time"] == regular_on(client, token, offset, "study")["goal_time"]


def test_zero_slot_carries_a_row_with_no_goal(client):
    token = auth_token(client)
    # Saturday set to 0: the stopwatch still lands there, just without a target
    create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Sa="00:00"))

    saturday = regular_on(client, token, 5, "study")
    assert saturday["goal_time"] == 0
    assert total_on(client, token, 5)["goal_time"] == 0
    # ...unlike unchecking Saturday in the picker, which creates no row at all
    assert "study" in [s["title"] for s in regulars_of(get_stopwatches(client, token, day(5)))]


def test_no_schedule_carries_the_uniform_goal_exactly_as_before(client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0), goal_time="02:00")

    carried = regular_on(client, token, 1, "study")
    assert carried["weekday_goal_times"] is None
    assert carried["goal_time"] == 2 * ONE_HOUR_MS


def test_schedule_survives_a_chain_of_carried_days(client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="01:00", Su="05:00"))

    # walk day by day rather than backfilling in one request
    for offset in range(1, 8):
        get_stopwatches(client, token, day(offset))
    assert regular_on(client, token, 6, "study")["goal_time"] == 5 * ONE_HOUR_MS   # Sunday
    next_monday = regular_on(client, token, 7, "study")
    assert next_monday["goal_time"] == ONE_HOUR_MS
    assert next_monday["weekday_goal_times"] is not None


def test_row_outside_its_repeat_days_still_reads_that_weekdays_slot(client):
    token = auth_token(client)
    # a Monday-only stopwatch created by hand on a Tuesday still gets Tuesday's slot
    resp = create_stopwatch(client, token, "gym", day(1), repeat_days=MON,
                            weekday_goal_times=schedule(Mo="01:00", Tu="03:00"))
    assert json.loads(resp.data)["stopwatches"][1]["goal_time"] == 3 * ONE_HOUR_MS


def test_total_goal_sums_each_days_landed_goals(client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="02:00", Tu="01:00"))
    create_stopwatch(client, token, "gym", day(0), weekday_goal_times=schedule(Mo="00:30", Tu="02:00"))

    assert total_on(client, token, 0)["goal_time"] == 2 * ONE_HOUR_MS + HALF_HOUR_MS
    assert total_on(client, token, 1)["goal_time"] == 3 * ONE_HOUR_MS


def test_carry_forward_leaves_an_overridden_total_untouched(app, client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="02:00", Tu="01:00"))
    seed_total_only_day(app, MONDAY + timedelta(days=1), goal_time=8 * ONE_HOUR_MS, goal_overridden=True)

    tuesday = get_stopwatches(client, token, day(1))
    assert regulars_of(tuesday)[0]["goal_time"] == ONE_HOUR_MS
    assert totals_of(tuesday)[0]["goal_time"] == 8 * ONE_HOUR_MS


def test_editing_a_schedule_rewrites_the_open_days_goal_and_the_total(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="02:00"))
    stopwatch = json.loads(resp.data)["stopwatches"][1]

    # editing Monday's slot moves this (Monday) row's goal and the Total with it
    resp = update_stopwatch(client, token, stopwatch["id"],
                            {"weekday_goal_times": schedule(Mo="03:00", Tu="00:15")})
    total, edited = json.loads(resp.data)["stopwatches"]
    assert edited["goal_time"] == 3 * ONE_HOUR_MS
    assert total["goal_time"] == 3 * ONE_HOUR_MS
    # editing a *different* weekday's slot changes nothing until that day comes round
    assert regular_on(client, token, 1, "study")["goal_time"] == 15 * 60000


def test_clearing_the_schedule_returns_the_stopwatch_to_a_uniform_goal(client):
    token = auth_token(client)
    resp = create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="02:00"))
    stopwatch = json.loads(resp.data)["stopwatches"][1]

    resp = update_stopwatch(client, token, stopwatch["id"],
                            {"weekday_goal_times": None, "goal_time": "04:00"})
    total, edited = json.loads(resp.data)["stopwatches"]
    assert edited["weekday_goal_times"] is None
    assert edited["goal_time"] == 4 * ONE_HOUR_MS
    assert total["goal_time"] == 4 * ONE_HOUR_MS
    # and every carried day now uses that one goal again
    assert regular_on(client, token, 1, "study")["goal_time"] == 4 * ONE_HOUR_MS


def test_deleting_a_scheduled_stopwatch_removes_its_landed_goal(client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="02:00"))
    resp = create_stopwatch(client, token, "gym", day(0), weekday_goal_times=schedule(Mo="00:30"))
    gym_id = json.loads(resp.data)["stopwatches"][1]["id"]

    resp = delete_stopwatch(client, token, gym_id)
    assert json.loads(resp.data)["stopwatches"][0]["goal_time"] == 2 * ONE_HOUR_MS


def test_invalid_weekday_goal_times_rejected_on_create_and_edit(client):
    token = auth_token(client)
    bad_schedules = (["01:00"] * 6, ["01:00"] * 8, "01:00", [3600000] * 7, ["24:00"] * 7, ["01:60"] * 7)
    for index, bad in enumerate(bad_schedules):
        resp = create_stopwatch(client, token, f"bad{index}", day(0), weekday_goal_times=bad)
        assert resp.status_code == 400, f"weekday_goal_times={bad!r} should be rejected"

    resp = create_stopwatch(client, token, "study", day(0))
    stopwatch = json.loads(resp.data)["stopwatches"][1]
    for bad in bad_schedules:
        resp = update_stopwatch(client, token, stopwatch["id"], {"weekday_goal_times": bad})
        assert resp.status_code == 400, f"weekday_goal_times={bad!r} should be rejected"
    # the rejected edits changed nothing
    assert regular_on(client, token, 0, "study")["goal_time"] == ONE_HOUR_MS


def test_titles_endpoint_returns_the_weekday_schedule(client):
    token = auth_token(client)
    create_stopwatch(client, token, "study", day(0), weekday_goal_times=schedule(Mo="02:00"))
    create_stopwatch(client, token, "gym", day(0))

    titles = {t["title"]: t["weekday_goal_times"] for t in get_titles(client, token)}
    assert titles["gym"] is None
    assert titles["study"] == [2 * ONE_HOUR_MS] + [HALF_HOUR_MS] * 6


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
    for field in ("total_xp", "day_xp", "level", "xp_into_level", "xp_to_next", "streak", "multiplier"):
        assert before[field] == after[field]
