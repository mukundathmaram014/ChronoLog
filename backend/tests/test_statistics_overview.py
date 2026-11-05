import json
from datetime import date, timedelta

from conftest import auth_token

HOUR = 3600000


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def this_monday():
    today = date.today()
    return today - timedelta(days=today.weekday())


def week_year(monday):
    return (monday + timedelta(days=3)).year


def create_habit(client, token, description, day, done=False):
    resp = client.post(
        "/api/habits/",
        data=json.dumps({"description": description, "date": day.isoformat(), "done": done}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 201


def create_stopwatch(client, token, title, day, milliseconds=0):
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": title, "date": day.isoformat()}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 200
    stopwatch = next(sw for sw in json.loads(resp.data)["stopwatches"] if sw["title"] == title)
    if milliseconds:
        put = client.put(
            f"/api/stopwatches/{stopwatch['id']}/",
            data=json.dumps({"curr_duration": milliseconds}),
            content_type="application/json",
            headers=headers(token),
        )
        assert put.status_code == 200


def get_overview(client, token, year):
    resp = client.get(f"/api/stats/overview/{year}/", headers=headers(token))
    assert resp.status_code == 200
    return json.loads(resp.data)


def put_note(client, token, week_start, note):
    return client.put(
        f"/api/stats/overview/notes/{week_start}/",
        data=json.dumps({"note": note}),
        content_type="application/json",
        headers=headers(token),
    )


def import_notes(client, token, notes):
    resp = client.post(
        "/api/stats/overview/notes/import/",
        data=json.dumps({"notes": notes}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def test_empty_account_has_no_weeks(client):
    token = auth_token(client)
    data = get_overview(client, token, date.today().year)
    assert data["weeks"] == []
    assert data["xp_days"] == []


def test_invalid_year_is_rejected(client):
    token = auth_token(client)
    assert client.get("/api/stats/overview/0/", headers=headers(token)).status_code == 400


def test_week_matches_the_week_stats_endpoints(client):
    token = auth_token(client)
    monday = this_monday() - timedelta(days=14)
    create_habit(client, token, "Habit A", monday, done=True)
    create_habit(client, token, "Habit B", monday)
    create_habit(client, token, "Habit A", monday + timedelta(days=1), done=True)
    create_stopwatch(client, token, "item a", monday, 7 * HOUR)

    week = next(w for w in get_overview(client, token, week_year(monday))["weeks"] if w["week_start"] == monday.isoformat())

    habits = json.loads(client.get(f"/api/stats/habits/{monday.isoformat()}/week/", headers=headers(token)).data)
    time = json.loads(client.get(f"/api/stats/stopwatches/{monday.isoformat()}/week/", headers=headers(token)).data)
    assert week["total_habits"] == habits["total_habits"] == 3
    assert week["completed_habits"] == habits["completed_habits"] == 2
    assert week["total_time_worked"] == time["total_time_worked"]
    assert week["average_time_worked_per_day"] == time["average_time_worked_per_day"] == HOUR
    assert week["in_progress"] is False


def test_weeks_start_at_the_first_tracked_week_and_stop_at_today(client):
    token = auth_token(client)
    monday = this_monday()
    start = monday - timedelta(days=14)
    create_habit(client, token, "Habit A", start + timedelta(days=2))

    data = get_overview(client, token, week_year(monday))
    weeks = [w["week_start"] for w in data["weeks"]]

    assert weeks[-1] == monday.isoformat()
    assert data["weeks"][-1]["in_progress"] is True
    if week_year(start) == week_year(monday):
        assert weeks == [start.isoformat(), (start + timedelta(days=7)).isoformat(), monday.isoformat()]


def test_week_straddling_new_year_counts_towards_the_year_of_its_thursday(client):
    token = auth_token(client)
    # 2025-12-29 is a Monday whose Thursday is 2026-01-01
    create_habit(client, token, "Habit A", date(2025, 12, 29))

    assert get_overview(client, token, 2025)["weeks"] == []
    data_2026 = get_overview(client, token, 2026)
    assert data_2026["weeks"][0]["week_start"] == "2025-12-29"
    assert data_2026["axis_start"] == "2025-12-29"
    assert 2026 in data_2026["years"]


def test_xp_curve_accumulates_and_ends_at_the_current_total(client):
    token = auth_token(client)
    monday = this_monday() - timedelta(days=14)
    create_habit(client, token, "Habit A", monday, done=True)
    create_habit(client, token, "Habit A", monday + timedelta(days=2), done=True)

    data = get_overview(client, token, week_year(monday))
    totals = [day["total_xp"] for day in data["xp_days"]]
    level = json.loads(client.get(f"/api/level/{date.today().isoformat()}/", headers=headers(token)).data)

    assert totals == sorted(totals)
    assert totals[-1] == level["total_xp"] > 0
    week = next(w for w in data["weeks"] if w["week_start"] == monday.isoformat())
    assert week["xp"] == totals[-1]


def test_note_set_edit_and_clear(client):
    token = auth_token(client)
    monday = this_monday() - timedelta(days=7)
    create_habit(client, token, "Habit A", monday)
    year = week_year(monday)
    week = lambda: next(w for w in get_overview(client, token, year)["weeks"] if w["week_start"] == monday.isoformat())

    assert json.loads(put_note(client, token, monday.isoformat(), "  note a  ").data)["note"] == "note a"
    assert week()["note"] == "note a"

    put_note(client, token, monday.isoformat(), "note b")
    assert week()["note"] == "note b"

    assert json.loads(put_note(client, token, monday.isoformat(), "   ").data)["note"] is None
    assert week()["note"] is None


def test_note_rejects_bad_weeks_and_long_text(client):
    token = auth_token(client)
    monday = this_monday()
    assert put_note(client, token, (monday + timedelta(days=1)).isoformat(), "note a").status_code == 400
    assert put_note(client, token, "not-a-date", "note a").status_code == 400
    assert put_note(client, token, monday.isoformat(), "x" * 501).status_code == 400
    assert put_note(client, token, monday.isoformat(), 5).status_code == 400


def test_notes_are_scoped_by_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")
    monday = this_monday() - timedelta(days=7)
    create_habit(client, token_a, "Habit A", monday)
    create_habit(client, token_b, "Habit A", monday)

    put_note(client, token_a, monday.isoformat(), "note a")

    year = week_year(monday)
    assert get_overview(client, token_a, year)["weeks"][0]["note"] == "note a"
    assert get_overview(client, token_b, year)["weeks"][0]["note"] is None


def test_import_adds_new_notes_and_keeps_existing_ones(client):
    token = auth_token(client)
    monday = this_monday() - timedelta(days=7)
    earlier = monday - timedelta(days=7)
    create_habit(client, token, "Habit A", earlier)
    put_note(client, token, monday.isoformat(), "kept")

    result = import_notes(client, token, [
        {"week_start": earlier.isoformat(), "note": "note a"},
        {"week_start": monday.isoformat(), "note": "replacement"},
        {"week_start": (monday + timedelta(days=1)).isoformat(), "note": "not a monday"},
        {"week_start": "nonsense", "note": "note b"},
    ])

    assert result["imported"] == 1
    assert result["skipped"] == 1
    assert len(result["errors"]) == 2

    # running it again changes nothing
    again = import_notes(client, token, [{"week_start": earlier.isoformat(), "note": "note a"}])
    assert again["imported"] == 0 and again["skipped"] == 1

    notes = {}
    for year in {week_year(earlier), week_year(monday)}:
        notes.update({w["week_start"]: w["note"] for w in get_overview(client, token, year)["weeks"]})
    assert notes[earlier.isoformat()] == "note a"
    assert notes[monday.isoformat()] == "kept"


def test_import_requires_a_list(client):
    token = auth_token(client)
    resp = client.post(
        "/api/stats/overview/notes/import/",
        data=json.dumps({"notes": "nope"}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 400


def create_goal(client, token, description, difficulty, day):
    resp = client.post(
        "/api/goals/",
        data=json.dumps({"description": description, "difficulty": difficulty}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 201
    goal_id = json.loads(resp.data)["id"]
    resp = client.put(
        f"/api/goals/{goal_id}/",
        data=json.dumps({"done": True, "date": day.isoformat()}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 200


def get_all_time(client, token):
    resp = client.get("/api/stats/overview/all/", headers=headers(token))
    assert resp.status_code == 200
    return json.loads(resp.data)


def test_all_time_spans_every_year_with_data(client):
    token = auth_token(client)
    create_habit(client, token, "Habit A", date(2025, 3, 3))

    data = get_all_time(client, token)

    assert data["year"] is None
    assert data["axis_start"] == "2025-03-03"
    assert data["axis_end"] == date.today().isoformat()
    assert data["weeks"][0]["week_start"] == "2025-03-03"
    assert data["weeks"][-1]["week_start"] == this_monday().isoformat()
    assert data["years"][0] == 2025


def test_all_time_with_no_data_is_empty(client):
    token = auth_token(client)
    data = get_all_time(client, token)
    assert data["weeks"] == []
    assert data["projection"] is None


def test_goals_appear_on_their_completion_day(client):
    token = auth_token(client)
    day = date.today() - timedelta(days=3)
    create_habit(client, token, "Habit A", day)
    create_goal(client, token, "goal a", "easy", day)

    days = {d["date"]: d for d in get_all_time(client, token)["xp_days"]}

    assert days[day.isoformat()]["goals"] == ["goal a"]
    assert days[day.isoformat()]["goal_xp"] == 500
    assert days[(day + timedelta(days=1)).isoformat()]["goals"] == []


def test_goals_are_scoped_by_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")
    day = date.today() - timedelta(days=3)
    create_habit(client, token_a, "Habit A", day)
    create_habit(client, token_b, "Habit A", day)
    create_goal(client, token_a, "goal a", "easy", day)

    assert all(d["goals"] == [] for d in get_all_time(client, token_b)["xp_days"])


def test_projection_rate_leaves_out_goals_and_today(client):
    token = auth_token(client)
    today = date.today()
    start = today - timedelta(days=4)
    for offset in range(4):
        create_habit(client, token, "Habit A", start + timedelta(days=offset), done=True)
    create_habit(client, token, "Habit A", today, done=True)
    before = get_all_time(client, token)["projection"]
    assert before["window_days"] == 4
    assert before["rate_per_day"] > 0

    create_goal(client, token, "goal a", "extreme", today - timedelta(days=1))
    after = get_all_time(client, token)["projection"]

    # a 20,000 XP goal doesn't predict 5,000 XP more every day
    assert after["rate_per_day"] < 1000


def test_projection_extends_from_the_current_total(client):
    token = auth_token(client)
    today = date.today()
    create_habit(client, token, "Habit A", today - timedelta(days=2), done=True)
    create_habit(client, token, "Habit A", today - timedelta(days=1), done=True)

    data = get_all_time(client, token)
    projection = data["projection"]
    current = data["xp_days"][-1]["total_xp"]
    points = projection["points"]

    assert points[0]["date"] == (today + timedelta(days=7)).isoformat()
    assert points[-1]["date"] == (today + timedelta(days=182)).isoformat()
    assert [p["total_xp"] for p in points] == sorted(p["total_xp"] for p in points)
    assert points[0]["total_xp"] == round(current + projection["rate_per_day"] * 7)
    assert projection["next_level"]["level"] == data["xp_days"][-1]["level"] + 1
    assert projection["next_level"]["date"] > today.isoformat()
    assert projection["in_one_year"]["date"] == (today + timedelta(days=365)).isoformat()


def test_no_projection_without_recent_xp_or_for_a_finished_year(client):
    token = auth_token(client)
    create_habit(client, token, "Habit A", date(2025, 3, 3), done=True)
    # nothing earned in the last 28 days
    assert get_all_time(client, token)["projection"] is None
    assert get_overview(client, token, 2025)["projection"] is None
