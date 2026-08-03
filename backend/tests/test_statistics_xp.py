import json
from datetime import date, timedelta

from conftest import auth_token
from utils import ALL_HABITS_BONUS, GOAL_TIME_BONUS, GOAL_XP, HABIT_XP, INDIVIDUAL_GOAL_BONUS, XP_PER_HOUR, streak_multiplier

TODAY = "2026-01-15"


def create_habit(client, token, **fields):
    resp = client.post(
        "/api/habits/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return json.loads(resp.data)


def create_goal(client, token, **fields):
    resp = client.post(
        "/api/goals/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return json.loads(resp.data)


def update_goal(client, token, goal_id, **fields):
    resp = client.put(
        f"/api/goals/{goal_id}/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def post_stopwatch(client, token, title, goal_time, day=TODAY):
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": title, "date": day, "goal_time": goal_time}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)["stopwatches"][1]  # (total, new)


def put_stopwatch(client, token, sw_id, **fields):
    resp = client.put(
        f"/api/stopwatches/{sw_id}/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def get_xp_stats(client, token, date_string, time_period):
    resp = client.get(
        f"/api/stats/xp/{date_string}/{time_period}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def get_level(client, token, day):
    resp = client.get(
        f"/api/level/{day}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


# ---- route shape + breakdown reconciliation ----

def test_xp_stats_route_shape_and_breakdown_reconciles_to_total(client):
    token = auth_token(client)
    for i in range(2):
        create_habit(client, token, description=f"h{i}", date=TODAY, difficulty="medium", done=True)
    goal = create_goal(client, token, description="ship it", difficulty="easy")
    update_goal(client, token, goal["id"], done=True, date=TODAY)

    data = get_xp_stats(client, token, TODAY, "day")

    assert set(data.keys()) == {"total", "best_day", "streak", "breakdown", "days", "level"}

    expected_total = 2 * HABIT_XP["medium"] + ALL_HABITS_BONUS + GOAL_XP["easy"]
    assert data["total"] == {"xp": expected_total, "average_per_day": expected_total, "days_counted": 1}
    assert data["best_day"] == {"date": TODAY, "xp": expected_total}

    by_source = {item["source"]: item["xp"] for item in data["breakdown"]}
    assert by_source == {
        "Habits": 2 * HABIT_XP["medium"],
        "Work": 0,
        "Goals": GOAL_XP["easy"],
        "Bonuses": ALL_HABITS_BONUS,
    }
    assert sum(by_source.values()) == expected_total

    assert data["days"] == [{"date": TODAY, "xp": expected_total}]


def test_xp_stats_breakdown_includes_work_xp(client):
    token = auth_token(client)
    sw = post_stopwatch(client, token, "study", "02:00")
    put_stopwatch(client, token, sw["id"], curr_duration=2 * 3600000)

    data = get_xp_stats(client, token, TODAY, "day")

    # the "study" stopwatch has a 2h goal and 2h logged, so it hits BOTH the
    # total daily goal (+GOAL_TIME_BONUS) and its own individual goal
    # (+INDIVIDUAL_GOAL_BONUS, spec 0037) — the two bonuses stack.
    bonuses = GOAL_TIME_BONUS + INDIVIDUAL_GOAL_BONUS
    expected_total = 2 * XP_PER_HOUR + bonuses
    by_source = {item["source"]: item["xp"] for item in data["breakdown"]}
    assert by_source == {"Habits": 0, "Work": 2 * XP_PER_HOUR, "Goals": 0, "Bonuses": bonuses}
    assert data["total"]["xp"] == expected_total


# ---- period aggregation ----

def test_xp_stats_week_aggregates_across_days_with_streak_multiplier(client):
    token = auth_token(client)
    # 2026-01-12/13/14 are a Monday/Tuesday/Wednesday -- three consecutive,
    # fully-elapsed days in the same week as 2026-01-14
    days = ["2026-01-12", "2026-01-13", "2026-01-14"]
    for day in days:
        create_habit(client, token, description="deep work", date=day, difficulty="hard", done=True)

    data = get_xp_stats(client, token, "2026-01-14", "week")

    expected_daily = [round(HABIT_XP["hard"] * streak_multiplier(s)) + ALL_HABITS_BONUS for s in (1, 2, 3)]
    assert data["total"]["days_counted"] == 7
    assert data["total"]["xp"] == sum(expected_daily)
    assert data["total"]["average_per_day"] == sum(expected_daily) / 7
    assert data["best_day"]["xp"] == max(expected_daily)
    assert data["best_day"]["date"] == "2026-01-14"
    assert data["streak"]["qualified_days"] == 3
    assert data["streak"]["longest"] == 3
    assert data["streak"]["current"] == 3
    assert len(data["days"]) == 7


def test_xp_stats_week_average_covers_only_elapsed_days(client):
    token = auth_token(client)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    days_elapsed = today.weekday() + 1
    for i in range(days_elapsed):
        day = start_of_week + timedelta(days=i)
        create_habit(client, token, description="grind", date=day.isoformat(), difficulty="medium", done=True)

    data = get_xp_stats(client, token, today.isoformat(), "week")

    assert data["total"]["days_counted"] == days_elapsed
    assert len(data["days"]) == 7
    # the heatmap series still spans the full window; untouched future days are
    # real zeros, not missing entries
    future_days = data["days"][days_elapsed:]
    assert all(d["xp"] == 0 for d in future_days)
    assert data["total"]["average_per_day"] == data["total"]["xp"] / days_elapsed


def test_xp_stats_streak_longest_reflects_full_run_even_within_a_single_day_period(client):
    token = auth_token(client)
    days = [f"2026-01-{d:02d}" for d in range(10, 15)]  # 5-day qualifying run
    for day in days:
        create_habit(client, token, description="grind", date=day, difficulty="hard", done=True)

    data = get_xp_stats(client, token, days[-1], "day")

    # a "day" window only covers one ledger row, but its streak reflects the
    # full run that started before the window
    assert data["streak"]["longest"] == 5
    assert data["streak"]["qualified_days"] == 1
    assert data["streak"]["current"] == 5


# ---- empty period + invalid input ----

def test_xp_stats_empty_period(client):
    token = auth_token(client)
    data = get_xp_stats(client, token, TODAY, "day")

    assert data["total"] == {"xp": 0, "average_per_day": 0, "days_counted": 1}
    assert data["best_day"] is None
    assert data["streak"] == {"qualified_days": 0, "longest": 0, "current": 0}
    assert all(day["xp"] == 0 for day in data["days"])


def test_xp_stats_invalid_time_period(client):
    token = auth_token(client)
    resp = client.get(
        f"/api/stats/xp/{TODAY}/decade/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code != 200


# ---- level + user scoping ----

def test_xp_stats_level_matches_level_endpoint(client):
    token = auth_token(client)
    create_habit(client, token, description="grind", date=TODAY, difficulty="hard", done=True)

    stats = get_xp_stats(client, token, TODAY, "day")
    level = get_level(client, token, TODAY)

    # rank is gated behind the allowlist (spec 0035), so it's present in both
    # the level and stats payloads or in neither — never asserted unconditionally.
    expected = {
        "total_xp": level["total_xp"],
        "level": level["level"],
        "xp_into_level": level["xp_into_level"],
        "xp_to_next": level["xp_to_next"],
    }
    if "rank" in level:
        expected["rank"] = level["rank"]
    assert stats["level"] == expected


def test_xp_stats_scoped_by_user(client):
    token_a = auth_token(client, username="usera")
    token_b = auth_token(client, username="userb")
    create_habit(client, token_a, description="grind", date=TODAY, difficulty="hard", done=True)

    data_b = get_xp_stats(client, token_b, TODAY, "day")

    assert data_b["total"]["xp"] == 0
    assert data_b["best_day"] is None
    assert all(item["xp"] == 0 for item in data_b["breakdown"])
