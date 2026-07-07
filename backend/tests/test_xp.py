import json

from conftest import auth_token
from utils import (
    GOAL_XP,
    HABIT_XP,
    LEVEL_B,
    LEVEL_P,
    XP_PER_HOUR,
    XP_PER_HOUR_OVERTIME,
    compute_day_xp,
    level_cost,
    level_from_xp,
    rank_from_level,
    streak_multiplier,
)

TODAY = "2026-01-15"


def create_habit(client, token, **fields):
    return client.post(
        "/api/habits/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def update_habit(client, token, habit_id, **fields):
    return client.put(
        f"/api/habits/{habit_id}/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def create_goal(client, token, **fields):
    return client.post(
        "/api/goals/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def update_goal(client, token, goal_id, **fields):
    return client.put(
        f"/api/goals/{goal_id}/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )


def get_level(client, token, day=TODAY):
    resp = client.get(
        f"/api/level/{day}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


# ---- pure helpers ----

def test_level_curve_first_levels():
    assert level_from_xp(0) == {"level": 1, "xp_into_level": 0, "xp_to_next": level_cost(1)}
    # verify the first few thresholds against round(B * L^p)
    cost1 = round(LEVEL_B * 1 ** LEVEL_P)
    cost2 = round(LEVEL_B * 2 ** LEVEL_P)
    cost3 = round(LEVEL_B * 3 ** LEVEL_P)
    assert (level_cost(1), level_cost(2), level_cost(3)) == (cost1, cost2, cost3)
    assert level_from_xp(cost1 - 1)["level"] == 1
    assert level_from_xp(cost1) == {"level": 2, "xp_into_level": 0, "xp_to_next": cost2}
    assert level_from_xp(cost1 + cost2) == {"level": 3, "xp_into_level": 0, "xp_to_next": cost3}
    assert level_from_xp(cost1 + cost2 + cost3 - 1) == {"level": 3, "xp_into_level": cost3 - 1, "xp_to_next": cost3}


def test_day_xp_helper_sums_sources_and_ramps_multiplier():
    # a qualifying day needs habit + work XP >= STREAK_THRESHOLD (250);
    # 5 hard habits = 250 base clears it on its own. Fresh streak: no boost yet
    result = compute_day_xp(["hard"] * 5, 0, [], 0)
    assert result == {"xp_earned": 250, "streak": 1, "multiplier": 1.0}

    # multiplier ramps with the running streak (habit XP only)
    result = compute_day_xp(["hard"] * 5, 0, [], 5)
    assert result["streak"] == 6
    assert result["multiplier"] == 1.5
    assert result["xp_earned"] == 375

    # and caps at 2.0
    result = compute_day_xp(["hard"] * 5, 0, [], 30)
    assert result["multiplier"] == 2.0
    assert result["xp_earned"] == 500

    # work and goal XP are flat (not streak-multiplied)
    result = compute_day_xp(["hard"] * 5, 1.0, ["easy"], 30)
    assert result["xp_earned"] == HABIT_XP["hard"] * 5 * 2 + XP_PER_HOUR + GOAL_XP["easy"]


def test_day_xp_helper_non_qualifying_day_resets_streak():
    # a light day (one easy habit + 2h work = 50 grind XP) is below the
    # threshold: streak resets, but the day's flat XP still counts
    result = compute_day_xp(["easy"], 2.0, ["medium"], 7)
    assert result["streak"] == 0
    assert result["multiplier"] == 1.0
    assert result["xp_earned"] == HABIT_XP["easy"] + 2 * XP_PER_HOUR + GOAL_XP["medium"]


def test_work_counts_toward_streak_qualification():
    # habits alone below threshold (4 hard = 200), but habits + work clear it
    assert compute_day_xp(["hard"] * 4, 0, [], 0)["streak"] == 0
    assert compute_day_xp(["hard"] * 4, 2.5, [], 0)["streak"] == 1  # 200 + 50 = 250
    # goals never count toward qualification, however large
    assert compute_day_xp([], 0, ["extreme"], 0)["streak"] == 0


# ---- accrual sync ----

def test_habit_toggle_updates_total_and_streak(client):
    token = auth_token(client)
    # a qualifying day needs >= 250 grind XP; 5 hard habits = 250 base
    habit_ids = []
    for i in range(5):
        resp = create_habit(client, token, description=f"deep work {i}", date=TODAY, difficulty="hard")
        habit_ids.append(json.loads(resp.data)["id"])
    assert json.loads(resp.data)["difficulty"] == "hard"
    assert get_level(client, token)["total_xp"] == 0

    for habit_id in habit_ids:
        update_habit(client, token, habit_id, done=True)
    level = get_level(client, token)
    assert level["total_xp"] == 5 * HABIT_XP["hard"]
    assert level["streak"] == 1
    assert level["multiplier"] == 1.0

    # dropping one hard habit falls to 200 base, below the qualifying threshold
    update_habit(client, token, habit_ids[0], done=False)
    level = get_level(client, token)
    assert level["total_xp"] == 4 * HABIT_XP["hard"]
    assert level["streak"] == 0


def test_habit_difficulty_change_while_done_adjusts_total(client):
    token = auth_token(client)
    resp = create_habit(client, token, description="reading", date=TODAY, difficulty="hard", done=True)
    habit_id = json.loads(resp.data)["id"]
    assert get_level(client, token)["total_xp"] == HABIT_XP["hard"]

    update_habit(client, token, habit_id, difficulty="medium")
    assert get_level(client, token)["total_xp"] == HABIT_XP["medium"]


def test_habit_difficulty_validation(client):
    token = auth_token(client)
    assert create_habit(client, token, description="x", date=TODAY, difficulty="brutal").status_code == 400
    resp = create_habit(client, token, description="x", date=TODAY)
    habit_id = json.loads(resp.data)["id"]
    assert json.loads(resp.data)["difficulty"] == "medium"
    assert update_habit(client, token, habit_id, difficulty="brutal").status_code == 400


def test_past_day_edit_recomputes_streak_forward(client):
    token = auth_token(client)
    days = ["2026-01-13", "2026-01-14", "2026-01-15"]
    habit_ids = {}
    for day in days:
        for i in range(5):  # 5 hard habits = 250 base, a qualifying day
            resp = create_habit(client, token, description=f"work {i}", date=day, difficulty="hard", done=True)
            habit_ids[(day, i)] = json.loads(resp.data)["id"]

    # base 250/day, streaks 1/2/3 -> 250 + 275 + 300
    level = get_level(client, token)
    assert level["total_xp"] == 250 + 275 + 300
    assert level["streak"] == 3
    assert level["multiplier"] == streak_multiplier(3)

    # unchecking one of the middle day's hard habits drops it to 200 base,
    # below the qualifying threshold: its streak resets and the last day restarts at 1
    update_habit(client, token, habit_ids[("2026-01-14", 0)], done=False)
    level = get_level(client, token)
    assert level["total_xp"] == 250 + 200 + 250
    assert level["streak"] == 1


def test_deleting_done_habit_removes_its_xp(client):
    token = auth_token(client)
    resp = create_habit(client, token, description="workout", date=TODAY, difficulty="hard", done=True)
    habit_id = json.loads(resp.data)["id"]
    assert get_level(client, token)["total_xp"] == HABIT_XP["hard"]

    resp = client.delete(
        f"/api/habits/{habit_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert get_level(client, token)["total_xp"] == 0


def test_worked_time_grants_flat_xp(client):
    token = auth_token(client)
    # a 2h goal so working exactly 2h is at-goal (no overtime), i.e. flat XP
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": "study", "date": TODAY, "goal_time": "02:00"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    stopwatch = json.loads(resp.data)["stopwatches"][1]

    # set 2 hours worked (7,200,000 ms) via the update route
    resp = client.put(
        f"/api/stopwatches/{stopwatch['id']}/",
        data=json.dumps({"curr_duration": 7200000}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    level = get_level(client, token)
    assert level["total_xp"] == 2 * XP_PER_HOUR
    # 2h of work (40 XP) is well below the 250 streak threshold
    assert level["streak"] == 0

    # resetting the stopwatch takes the day's work XP back out
    resp = client.patch(
        f"/api/stopwatches/reset/{stopwatch['id']}/",
        data=json.dumps({"state": "paused"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert get_level(client, token)["total_xp"] == 0


def test_overtime_work_xp_helper():
    # goal 6h, worked 5h: all standard, no overtime
    assert compute_day_xp([], 5.0, [], 0, goal_hours=6.0)["xp_earned"] == round(5 * XP_PER_HOUR)
    # goal 6h, worked 8h: 6h standard + 2h overtime
    assert compute_day_xp([], 8.0, [], 0, goal_hours=6.0)["xp_earned"] == round(
        6 * XP_PER_HOUR + 2 * XP_PER_HOUR_OVERTIME
    )
    # no goal set (0h): flat standard rate even on a long day
    assert compute_day_xp([], 8.0, [], 0, goal_hours=0)["xp_earned"] == round(8 * XP_PER_HOUR)


def test_overtime_work_xp_over_the_stopwatch_api(client):
    token = auth_token(client)
    # day's total goal = 2h
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": "study", "date": TODAY, "goal_time": "02:00"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    stopwatch = json.loads(resp.data)["stopwatches"][1]
    # log 3h of work -> 2h standard + 1h overtime
    client.put(
        f"/api/stopwatches/{stopwatch['id']}/",
        data=json.dumps({"curr_duration": 3 * 3600000}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_level(client, token)["total_xp"] == 2 * XP_PER_HOUR + 1 * XP_PER_HOUR_OVERTIME


def test_no_goal_stopwatch_stores_zero_and_skips_overtime(client):
    token = auth_token(client)
    # a "no goal" stopwatch is stored as goal_time 0
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": "reading", "date": TODAY, "goal_time": None}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    stopwatch = json.loads(resp.data)["stopwatches"][1]
    assert stopwatch["goal_time"] == 0
    # with no goal set, the day's goal is 0h -> no overtime, flat standard rate
    client.put(
        f"/api/stopwatches/{stopwatch['id']}/",
        data=json.dumps({"curr_duration": 3 * 3600000}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_level(client, token)["total_xp"] == 3 * XP_PER_HOUR


def test_goal_complete_uncomplete_and_delete(client):
    token = auth_token(client)
    resp = create_goal(client, token, description="run a marathon", difficulty="medium")
    assert resp.status_code == 201
    goal_id = json.loads(resp.data)["id"]
    assert get_level(client, token)["total_xp"] == 0

    resp = update_goal(client, token, goal_id, done=True, date=TODAY)
    assert json.loads(resp.data)["completed_date"] == TODAY
    assert get_level(client, token)["total_xp"] == GOAL_XP["medium"]

    # re-tiering a completed goal adjusts its granted XP
    update_goal(client, token, goal_id, difficulty="hard")
    assert get_level(client, token)["total_xp"] == GOAL_XP["hard"]

    # un-completing removes it
    resp = update_goal(client, token, goal_id, done=False)
    assert json.loads(resp.data)["completed_date"] is None
    assert get_level(client, token)["total_xp"] == 0

    # deleting a completed goal removes its XP too
    update_goal(client, token, goal_id, done=True, date=TODAY)
    assert get_level(client, token)["total_xp"] == GOAL_XP["hard"]
    client.delete(f"/api/goals/{goal_id}/", headers={"Authorization": f"Bearer {token}"})
    assert get_level(client, token)["total_xp"] == 0


def test_goal_validation(client):
    token = auth_token(client)
    assert create_goal(client, token, description="   ").status_code == 400
    assert create_goal(client, token, description="x", difficulty="brutal").status_code == 400
    # "extreme" is a goal-only tier and must be accepted
    assert create_goal(client, token, description="frontier lab", difficulty="extreme").status_code == 201
    resp = create_goal(client, token, description="x")
    goal_id = json.loads(resp.data)["id"]
    assert update_goal(client, token, goal_id, difficulty="brutal").status_code == 400


def test_extreme_goal_grants_its_xp(client):
    token = auth_token(client)
    resp = create_goal(client, token, description="join a league", difficulty="extreme")
    goal_id = json.loads(resp.data)["id"]
    update_goal(client, token, goal_id, done=True, date=TODAY)
    assert get_level(client, token)["total_xp"] == GOAL_XP["extreme"]


def test_rank_from_level():
    assert rank_from_level(1) == "E"
    assert rank_from_level(9) == "E"
    assert rank_from_level(10) == "D"
    assert rank_from_level(24) == "D"
    assert rank_from_level(25) == "C"
    assert rank_from_level(49) == "C"
    assert rank_from_level(50) == "B"
    assert rank_from_level(74) == "B"
    assert rank_from_level(75) == "A"
    assert rank_from_level(99) == "A"
    assert rank_from_level(100) == "S"
    assert rank_from_level(500) == "S"


def test_level_readout_includes_rank(client):
    token = auth_token(client)
    assert get_level(client, token)["rank"] == "E"


def test_level_readout_includes_day_xp(client):
    token = auth_token(client)
    assert get_level(client, token)["day_xp"] == 0
    # XP earned today shows up on today's readout
    resp = create_goal(client, token, description="ship it", difficulty="easy")
    goal_id = json.loads(resp.data)["id"]
    update_goal(client, token, goal_id, done=True, date=TODAY)
    assert get_level(client, token)["day_xp"] == GOAL_XP["easy"]


def test_xp_and_goals_are_user_scoped(client):
    token_a = auth_token(client, username="usera")
    token_b = auth_token(client, username="userb")

    create_habit(client, token_a, description="workout", date=TODAY, difficulty="hard", done=True)
    resp = create_goal(client, token_a, description="secret goal")
    goal_id = json.loads(resp.data)["id"]

    assert get_level(client, token_a)["total_xp"] == HABIT_XP["hard"]
    level_b = get_level(client, token_b)
    assert level_b["total_xp"] == 0
    assert level_b["streak"] == 0

    resp = client.get("/api/goals/", headers={"Authorization": f"Bearer {token_b}"})
    assert json.loads(resp.data)["goals"] == []
    resp = client.get(f"/api/goals/{goal_id}/", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


# ---- calibration ----

def test_calibration_dedicated_user_reaches_level_100_in_4_to_5_years():
    """
    The dedicated-user grind: 3 easy + 3 medium + 3 hard habits done daily,
    5.5 h/day of tracked work, and a sustained streak. Goals are excluded here:
    on the goal-XP scale they are large, occasional bonuses (a medium goal is
    ~1-2 weeks of effort), so the habit + time grind *alone* must land level 100
    in ~4-5 years, with any goals only accelerating past that floor.
    """
    habits = ["easy"] * 3 + ["medium"] * 3 + ["hard"] * 3
    total_xp = 0
    streak = 0
    level_100_day = None
    level_after_30_days = None

    for day in range(1, 365 * 6 + 1):
        result = compute_day_xp(habits, 5.5, [], streak)
        streak = result["streak"]
        total_xp += result["xp_earned"]
        if day == 30:
            level_after_30_days = level_from_xp(total_xp)["level"]
        if level_from_xp(total_xp)["level"] >= 100:
            level_100_day = day
            break

    assert level_100_day is not None, "never reached level 100 within 6 years"
    assert 4 * 365 <= level_100_day <= 5 * 365, f"level 100 at day {level_100_day}, outside the 4-5 year window"
    # early levels come quickly...
    assert level_after_30_days >= 15
    # ...and late levels slowly: the last step alone takes over a month
    assert level_cost(99) > 30 * 700
