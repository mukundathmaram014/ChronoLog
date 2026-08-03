import json
from datetime import date

from conftest import auth_token
from db import DailyXP, User
from utils import (
    ALL_HABITS_BONUS,
    GOAL_TIME_BONUS,
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
    rank_visible,
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
    # a day qualifies at >= 85% of its max; 5 hard habits all done (max 250) is
    # 100%. Fresh streak: no boost yet
    result = compute_day_xp(["hard"] * 5, 0, [], 0, max_habit_xp=250)
    assert result == {
        "xp_earned": 250, "streak": 1, "multiplier": 1.0,
        "habit_xp": 250, "work_xp": 0, "goal_xp": 0, "bonus_xp": 0,
    }

    # multiplier ramps with the running streak (habit XP only)
    result = compute_day_xp(["hard"] * 5, 0, [], 5, max_habit_xp=250)
    assert result["streak"] == 6
    assert result["multiplier"] == 1.5
    assert result["xp_earned"] == 375

    # and caps at 2.0
    result = compute_day_xp(["hard"] * 5, 0, [], 30, max_habit_xp=250)
    assert result["multiplier"] == 2.0
    assert result["xp_earned"] == 500

    # work and goal XP are flat (not streak-multiplied)
    result = compute_day_xp(["hard"] * 5, 1.0, ["easy"], 30, max_habit_xp=250)
    assert result["xp_earned"] == HABIT_XP["hard"] * 5 * 2 + XP_PER_HOUR + GOAL_XP["easy"]


def test_day_xp_helper_non_qualifying_day_resets_streak():
    # only 1 of a possible 8h goal's worth done + one easy habit of many: well
    # under 85%, streak resets, but the day's flat XP still counts
    result = compute_day_xp(["easy"], 2.0, ["medium"], 7, goal_hours=8.0, max_habit_xp=200)
    assert result["streak"] == 0
    assert result["multiplier"] == 1.0
    assert result["xp_earned"] == HABIT_XP["easy"] + 2 * XP_PER_HOUR + GOAL_XP["medium"]


def test_day_xp_components_sum_to_xp_earned():
    # habits + work + two goals + both flat bonuses, all in one day
    result = compute_day_xp(
        ["hard"] * 5, 2.0, ["easy", "medium"], 5,
        goal_hours=1.0, all_habits_done=True, max_habit_xp=250,
    )
    assert result["habit_xp"] + result["work_xp"] + result["goal_xp"] + result["bonus_xp"] == result["xp_earned"]
    assert result["goal_xp"] == GOAL_XP["easy"] + GOAL_XP["medium"]
    assert result["bonus_xp"] == ALL_HABITS_BONUS + GOAL_TIME_BONUS
    assert result["habit_xp"] == round(5 * HABIT_XP["hard"] * streak_multiplier(6))
    # 2h worked against a 1h goal: 1h standard + 1h overtime
    assert result["work_xp"] == round(1.0 * XP_PER_HOUR + 1.0 * XP_PER_HOUR_OVERTIME)


def test_streak_threshold_is_percentage_of_max():
    # all habits done + full goal time = 100% -> qualifies
    assert compute_day_xp(["hard"] * 3, 6.0, [], 0, goal_hours=6.0, max_habit_xp=150)["streak"] == 1
    # a small miss still clears 85% (all habits, ~1h short of a 6h goal)
    assert compute_day_xp(["hard"] * 3, 5.0, [], 0, goal_hours=6.0, max_habit_xp=150)["streak"] == 1
    # a big miss breaks it (only 1 of 3 hard habits, even with full work)
    assert compute_day_xp(["hard"] * 1, 6.0, [], 0, goal_hours=6.0, max_habit_xp=150)["streak"] == 0
    # overtime can't cover skipped habits (work is capped at the goal for the streak)
    assert compute_day_xp(["hard"] * 1, 20.0, [], 0, goal_hours=6.0, max_habit_xp=150)["streak"] == 0
    # a day with nothing to do (max 0) can't be completed -> no streak
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
    # all 5 habits done -> base + all-habits bonus
    assert level["total_xp"] == 5 * HABIT_XP["hard"] + ALL_HABITS_BONUS
    assert level["streak"] == 1
    assert level["multiplier"] == 1.0

    # dropping one hard habit falls to 200 base (below threshold) and forfeits
    # the all-habits bonus (no longer all done)
    update_habit(client, token, habit_ids[0], done=False)
    level = get_level(client, token)
    assert level["total_xp"] == 4 * HABIT_XP["hard"]
    assert level["streak"] == 0


def test_habit_difficulty_change_while_done_adjusts_total(client):
    token = auth_token(client)
    resp = create_habit(client, token, description="reading", date=TODAY, difficulty="hard", done=True)
    habit_id = json.loads(resp.data)["id"]
    # the day's only habit is done -> base + all-habits bonus
    assert get_level(client, token)["total_xp"] == HABIT_XP["hard"] + ALL_HABITS_BONUS

    update_habit(client, token, habit_id, difficulty="medium")
    assert get_level(client, token)["total_xp"] == HABIT_XP["medium"] + ALL_HABITS_BONUS


def test_habit_difficulty_validation(client):
    token = auth_token(client)
    assert create_habit(client, token, description="x", date=TODAY, difficulty="brutal").status_code == 400
    resp = create_habit(client, token, description="x", date=TODAY)
    habit_id = json.loads(resp.data)["id"]
    assert json.loads(resp.data)["difficulty"] == "medium"
    assert update_habit(client, token, habit_id, difficulty="brutal").status_code == 400


def test_all_habits_bonus_helper():
    # completing every habit adds the flat bonus on top of the day's XP
    base = compute_day_xp(["medium"], 0, [], 0)["xp_earned"]
    assert compute_day_xp(["medium"], 0, [], 0, all_habits_done=True)["xp_earned"] == base + ALL_HABITS_BONUS
    # the bonus is flat (not streak-multiplied): 5 hard at a capped 2.0x + flat bonus
    assert compute_day_xp(["hard"] * 5, 0, [], 30, all_habits_done=True, max_habit_xp=250)["xp_earned"] == (
        round(5 * HABIT_XP["hard"] * streak_multiplier(31)) + ALL_HABITS_BONUS
    )


def test_all_habits_bonus_over_the_api(client):
    token = auth_token(client)
    ids = []
    for i in range(2):
        resp = create_habit(client, token, description=f"h{i}", date=TODAY, difficulty="medium", done=True)
        ids.append(json.loads(resp.data)["id"])
    # both habits done -> 2 * medium + all-habits bonus
    assert get_level(client, token)["total_xp"] == 2 * HABIT_XP["medium"] + ALL_HABITS_BONUS
    # undo one -> no longer all done, bonus removed
    update_habit(client, token, ids[0], done=False)
    assert get_level(client, token)["total_xp"] == HABIT_XP["medium"]


def test_past_day_edit_recomputes_streak_forward(client):
    token = auth_token(client)
    days = ["2026-01-13", "2026-01-14", "2026-01-15"]
    habit_ids = {}
    for day in days:
        for i in range(5):  # 5 hard habits = 250 base, a qualifying day
            resp = create_habit(client, token, description=f"work {i}", date=day, difficulty="hard", done=True)
            habit_ids[(day, i)] = json.loads(resp.data)["id"]

    # base 250/day, streaks 1/2/3 -> 250 + 275 + 300; each day is all-done (+bonus)
    level = get_level(client, token)
    assert level["total_xp"] == (250 + 275 + 300) + 3 * ALL_HABITS_BONUS
    assert level["streak"] == 3
    assert level["multiplier"] == streak_multiplier(3)

    # unchecking one of the middle day's hard habits drops it to 200 base (below
    # the threshold) and forfeits that day's bonus: streak resets and the last day
    # restarts at 1; days 1 and 3 keep their all-habits bonus
    update_habit(client, token, habit_ids[("2026-01-14", 0)], done=False)
    level = get_level(client, token)
    assert level["total_xp"] == (250 + 200 + 250) + 2 * ALL_HABITS_BONUS
    assert level["streak"] == 1


def test_recompute_from_persists_xp_components_on_the_ledger_row(app, client):
    token = auth_token(client)
    create_habit(client, token, description="deep work", date=TODAY, difficulty="hard", done=True)

    with app.app_context():
        row = DailyXP.query.filter_by(user_id=User.query.first().id, date=date.fromisoformat(TODAY)).first()
        assert row.habit_xp == HABIT_XP["hard"]
        assert row.bonus_xp == ALL_HABITS_BONUS  # the day's only habit is done
        assert row.work_xp == 0
        assert row.goal_xp == 0
        assert row.habit_xp + row.work_xp + row.goal_xp + row.bonus_xp == row.xp_earned


def test_deleting_done_habit_removes_its_xp(client):
    token = auth_token(client)
    resp = create_habit(client, token, description="workout", date=TODAY, difficulty="hard", done=True)
    habit_id = json.loads(resp.data)["id"]
    # the day's only habit is done -> base + all-habits bonus
    assert get_level(client, token)["total_xp"] == HABIT_XP["hard"] + ALL_HABITS_BONUS

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
    # worked exactly the 2h goal -> flat work XP + goal-time bonus
    assert level["total_xp"] == 2 * XP_PER_HOUR + GOAL_TIME_BONUS
    # no habits and the goal fully met = 100% of the day's possible XP -> streak qualifies
    assert level["streak"] == 1

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
    # goal 6h, worked 8h: 6h standard + 2h overtime + goal-time bonus (goal met)
    assert compute_day_xp([], 8.0, [], 0, goal_hours=6.0)["xp_earned"] == round(
        6 * XP_PER_HOUR + 2 * XP_PER_HOUR_OVERTIME + GOAL_TIME_BONUS
    )
    # no goal set (0h): flat standard rate even on a long day
    assert compute_day_xp([], 8.0, [], 0, goal_hours=0)["xp_earned"] == round(8 * XP_PER_HOUR)


def test_goal_time_bonus_helper():
    # reaching the day's goal time adds the flat bonus (no overtime at exactly goal)
    assert compute_day_xp([], 2.0, [], 0, goal_hours=2.0)["xp_earned"] == round(2 * XP_PER_HOUR) + GOAL_TIME_BONUS
    # under the goal -> no bonus
    assert compute_day_xp([], 1.5, [], 0, goal_hours=2.0)["xp_earned"] == round(1.5 * XP_PER_HOUR)
    # no goal set -> no bonus
    assert compute_day_xp([], 5.0, [], 0, goal_hours=0)["xp_earned"] == round(5 * XP_PER_HOUR)


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
    # 2h standard + 1h overtime + goal-time bonus (worked past the 2h goal)
    assert get_level(client, token)["total_xp"] == 2 * XP_PER_HOUR + 1 * XP_PER_HOUR_OVERTIME + GOAL_TIME_BONUS


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


def _post_stopwatch(client, token, title, goal_time="01:00", weekday_goal_times=None, day=TODAY):
    body = {"title": title, "date": day, "goal_time": goal_time}
    if weekday_goal_times is not None:
        body["weekday_goal_times"] = weekday_goal_times
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps(body),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    data = json.loads(resp.data)["stopwatches"]
    return data[0], data[1]  # (total, new)


def _put_stopwatch(client, token, sw_id, **fields):
    resp = client.put(
        f"/api/stopwatches/{sw_id}/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    return json.loads(resp.data)["stopwatches"][0]  # total


def test_total_goal_defaults_to_sum_then_holds_an_override(client):
    token = auth_token(client)
    total, _ = _post_stopwatch(client, token, "study", "02:00")
    # default: Total goal = sum of individual goals (2h), not overridden
    assert total["goal_time"] == 2 * 3600000
    assert total["goal_overridden"] is False

    # override the Total goal to 5h
    total = _put_stopwatch(client, token, total["id"], goal_time="05:00")
    assert total["goal_time"] == 5 * 3600000
    assert total["goal_overridden"] is True

    # adding another stopwatch must NOT change the overridden Total
    total2, _ = _post_stopwatch(client, token, "reading", "01:00")
    assert total2["goal_time"] == 5 * 3600000

    # match_sum clears the override -> back to the live sum (2h + 1h = 3h)
    total = _put_stopwatch(client, token, total["id"], match_sum=True)
    assert total["goal_time"] == 3 * 3600000
    assert total["goal_overridden"] is False


def test_total_goal_override_drives_xp(client):
    token = auth_token(client)
    total, study = _post_stopwatch(client, token, "study", "02:00")
    # override the daily total to 3h (vs the 2h sum)
    _put_stopwatch(client, token, total["id"], goal_time="03:00")
    # log exactly 3h -> hits the 3h override: flat 3h work + goal bonus, no overtime
    _put_stopwatch(client, token, study["id"], curr_duration=3 * 3600000)
    assert get_level(client, token)["total_xp"] == 3 * XP_PER_HOUR + GOAL_TIME_BONUS


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


def test_level_readout_omits_rank_by_default(client):
    token = auth_token(client)
    assert "rank" not in get_level(client, token)


def test_level_readout_includes_rank_when_allowlisted(client, monkeypatch):
    monkeypatch.setenv("RANK_USERNAMES", "testuser")
    token = auth_token(client)
    assert get_level(client, token)["rank"] == "E"


def test_rank_visible(monkeypatch):
    owner = User(username="Owner", is_guest=False)
    other = User(username="someoneelse", is_guest=False)
    guest_owner = User(username="owner", is_guest=True)

    monkeypatch.delenv("RANK_USERNAMES", raising=False)
    assert rank_visible(owner) is False  # unset allowlist -> nobody
    assert rank_visible(None) is False

    monkeypatch.setenv("RANK_USERNAMES", " owner , other-name")
    assert rank_visible(owner) is True  # case-insensitive, whitespace-trimmed match
    assert rank_visible(other) is False
    assert rank_visible(guest_owner) is False  # guest check wins even when allowlisted


def test_level_readout_includes_day_xp(client):
    token = auth_token(client)
    assert get_level(client, token)["day_xp"] == 0
    # XP earned today shows up on today's readout
    resp = create_goal(client, token, description="ship it", difficulty="easy")
    goal_id = json.loads(resp.data)["id"]
    update_goal(client, token, goal_id, done=True, date=TODAY)
    assert get_level(client, token)["day_xp"] == GOAL_XP["easy"]


def test_streak_progress_helper():
    from utils import streak_progress
    # 150 max habit + 6h*20 goal = 270 max; target 85% = 229.5
    sp = streak_progress(0, 0, 6.0, 150)  # nothing done yet
    assert sp["possible"] is True and sp["qualified"] is False
    assert sp["remaining"] == 230  # ceil(229.5)
    sp = streak_progress(150, 6.0, 6.0, 150)  # all habits + full goal
    assert sp["qualified"] is True and sp["remaining"] == 0
    sp = streak_progress(0, 0, 0, 0)  # nothing to do
    assert sp["possible"] is False and sp["remaining"] == 0


def test_level_readout_includes_streak_progress(client):
    token = auth_token(client)
    # nothing scheduled and no goal -> streak not possible today
    lvl = get_level(client, token)
    assert lvl["streak_possible"] is False
    assert lvl["streak_remaining"] == 0

    # a hard habit (not yet done) -> possible, needs XP
    resp = create_habit(client, token, description="workout", date=TODAY, difficulty="hard")
    habit_id = json.loads(resp.data)["id"]
    lvl = get_level(client, token)
    assert lvl["streak_possible"] is True
    assert lvl["streak_qualified"] is False
    assert lvl["streak_remaining"] > 0

    # completing it = 100% of a habit-only day -> qualified, nothing remaining
    update_habit(client, token, habit_id, done=True)
    lvl = get_level(client, token)
    assert lvl["streak_qualified"] is True
    assert lvl["streak_remaining"] == 0


def test_xp_and_goals_are_user_scoped(client):
    token_a = auth_token(client, username="usera")
    token_b = auth_token(client, username="userb")

    create_habit(client, token_a, description="workout", date=TODAY, difficulty="hard", done=True)
    resp = create_goal(client, token_a, description="secret goal")
    goal_id = json.loads(resp.data)["id"]

    # user A's only habit is done -> base + all-habits bonus
    assert get_level(client, token_a)["total_xp"] == HABIT_XP["hard"] + ALL_HABITS_BONUS
    level_b = get_level(client, token_b)
    assert level_b["total_xp"] == 0
    assert level_b["streak"] == 0

    resp = client.get("/api/goals/", headers={"Authorization": f"Bearer {token_b}"})
    assert json.loads(resp.data)["goals"] == []
    resp = client.get(f"/api/goals/{goal_id}/", headers={"Authorization": f"Bearer {token_b}"})
    assert resp.status_code == 404


# ---- per-weekday goals + XP recompute on goal change (spec 0036) ----
# TODAY (2026-01-15) is a Thursday, i.e. date.weekday() index 3

def _thursday_schedule(thursday, other="02:00"):
    return [other] * 3 + [thursday] + [other] * 3


def test_lighter_weekday_goal_reaches_the_bonus_and_overtime_sooner(client):
    token = auth_token(client)
    _, study = _post_stopwatch(client, token, "study", "02:00",
                               weekday_goal_times=_thursday_schedule("01:00"))
    # the row landed on its 1h Thursday slot, not the 2h field
    assert study["goal_time"] == 3600000

    _put_stopwatch(client, token, study["id"], curr_duration=2 * 3600000)
    # against a 2h goal this would be 2h flat and no bonus; against 1h it's
    # 1h standard + 1h overtime + the goal-time bonus
    assert get_level(client, token)["total_xp"] == XP_PER_HOUR + XP_PER_HOUR_OVERTIME + GOAL_TIME_BONUS


def test_heavier_weekday_goal_pushes_the_bonus_and_overtime_out(client):
    token = auth_token(client)
    _, study = _post_stopwatch(client, token, "study", "02:00",
                               weekday_goal_times=_thursday_schedule("04:00"))
    assert study["goal_time"] == 4 * 3600000

    _put_stopwatch(client, token, study["id"], curr_duration=2 * 3600000)
    # short of the 4h Thursday goal: flat rate, no overtime, no bonus
    assert get_level(client, token)["total_xp"] == 2 * XP_PER_HOUR


def test_goal_only_edit_rescores_the_day(client):
    token = auth_token(client)
    _, study = _post_stopwatch(client, token, "study", "02:00")
    _put_stopwatch(client, token, study["id"], curr_duration=3 * 3600000)
    assert get_level(client, token)["total_xp"] == 2 * XP_PER_HOUR + XP_PER_HOUR_OVERTIME + GOAL_TIME_BONUS

    # raising the goal with no duration change still moves the day's XP: the
    # overtime hour becomes a standard one
    _put_stopwatch(client, token, study["id"], goal_time="03:00")
    assert get_level(client, token)["total_xp"] == 3 * XP_PER_HOUR + GOAL_TIME_BONUS


def test_weekday_schedule_edit_rescores_the_day(client):
    token = auth_token(client)
    _, study = _post_stopwatch(client, token, "study", "02:00")
    _put_stopwatch(client, token, study["id"], curr_duration=2 * 3600000)
    assert get_level(client, token)["total_xp"] == 2 * XP_PER_HOUR + GOAL_TIME_BONUS

    # switching to a schedule whose Thursday is 1h re-splits the same 2h worked
    _put_stopwatch(client, token, study["id"], weekday_goal_times=_thursday_schedule("01:00"))
    assert get_level(client, token)["total_xp"] == XP_PER_HOUR + XP_PER_HOUR_OVERTIME + GOAL_TIME_BONUS


def test_create_and_delete_that_move_the_days_goal_rescore_it(client):
    token = auth_token(client)
    _, study = _post_stopwatch(client, token, "study", "02:00")
    _put_stopwatch(client, token, study["id"], curr_duration=3 * 3600000)
    assert get_level(client, token)["total_xp"] == 2 * XP_PER_HOUR + XP_PER_HOUR_OVERTIME + GOAL_TIME_BONUS

    # a second stopwatch adds its goal to the day even though it logs no time
    _, reading = _post_stopwatch(client, token, "reading", "01:00")
    assert get_level(client, token)["total_xp"] == 3 * XP_PER_HOUR + GOAL_TIME_BONUS

    # ...and deleting that zero-duration stopwatch takes the goal back out
    resp = client.delete(f"/api/stopwatches/{reading['id']}/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert get_level(client, token)["total_xp"] == 2 * XP_PER_HOUR + XP_PER_HOUR_OVERTIME + GOAL_TIME_BONUS


def test_overridden_total_ignores_a_child_goal_edit_for_xp(client):
    token = auth_token(client)
    total, study = _post_stopwatch(client, token, "study", "02:00")
    _put_stopwatch(client, token, total["id"], goal_time="03:00")
    _put_stopwatch(client, token, study["id"], curr_duration=3 * 3600000)
    assert get_level(client, token)["total_xp"] == 3 * XP_PER_HOUR + GOAL_TIME_BONUS

    # the child's goal no longer feeds the overridden Total, so the day's XP holds
    _put_stopwatch(client, token, study["id"], goal_time="00:30")
    assert get_level(client, token)["total_xp"] == 3 * XP_PER_HOUR + GOAL_TIME_BONUS


def test_carry_forward_rescores_a_day_that_already_had_a_ledger_row(app, client):
    token = auth_token(client)
    monday, tuesday = "2026-01-05", "2026-01-06"
    _post_stopwatch(client, token, "study", "01:00",
                    weekday_goal_times=["01:00", "04:00"] + ["01:00"] * 5, day=monday)
    # Tuesday's only habit is done, so before any goal lands there the day is 100%
    # complete and its ledger row qualifies for the streak
    create_habit(client, token, description="reading", date=tuesday, difficulty="medium", done=True)
    with app.app_context():
        row = DailyXP.query.filter_by(user_id=User.query.first().id, date=date(2026, 1, 6)).first()
        assert row.streak == 1

    # opening Tuesday carries the stopwatch in with a 4h goal, which the day has
    # not worked -- the ledger row must be rewritten, not left stale
    client.get(f"/api/stopwatches/{tuesday}/", headers={"Authorization": f"Bearer {token}"})
    with app.app_context():
        row = DailyXP.query.filter_by(user_id=User.query.first().id, date=date(2026, 1, 6)).first()
        assert row.streak == 0
        assert row.xp_earned == HABIT_XP["medium"] + ALL_HABITS_BONUS


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
    max_habit_xp = sum(HABIT_XP[d] for d in habits)  # all habits done each day
    total_xp = 0
    streak = 0
    level_100_day = None
    level_after_30_days = None

    for day in range(1, 365 * 6 + 1):
        result = compute_day_xp(habits, 5.5, [], streak, max_habit_xp=max_habit_xp)
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
