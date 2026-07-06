import calendar
import json
from datetime import date, timedelta

from conftest import auth_token


def create_habit(client, token, description, habit_date, done=False):
    resp = client.post(
        "/api/habits/",
        data=json.dumps({"description": description, "date": habit_date.isoformat(), "done": done}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


def get_habit_stats(client, token, date_string, time_period):
    resp = client.get(
        f"/api/stats/habits/{date_string}/{time_period}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def test_week_stats_exclude_future_days(client):
    token = auth_token(client)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    for i in range(7):
        create_habit(client, token, "Reading", start_of_week + timedelta(days=i), done=True)

    stats = get_habit_stats(client, token, today.isoformat(), "week")

    days_elapsed = today.weekday() + 1
    assert stats["total_habits"] == days_elapsed
    assert stats["completed_habits"] == days_elapsed
    assert stats["percentage"] == 100


def test_month_stats_exclude_future_days(client):
    token = auth_token(client)
    today = date.today()
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    marker_days = sorted({first_day, today, last_day})
    for i, habit_date in enumerate(marker_days):
        create_habit(client, token, f"Habit {i}", habit_date, done=True)

    stats = get_habit_stats(client, token, today.isoformat(), "month")

    expected = sum(1 for habit_date in marker_days if habit_date <= today)
    assert stats["total_habits"] == expected
    assert stats["completed_habits"] == expected


def test_year_stats_exclude_future_days(client):
    token = auth_token(client)
    today = date.today()
    first_day = today.replace(month=1, day=1)
    last_day = today.replace(month=12, day=31)
    marker_days = sorted({first_day, today, last_day})
    for i, habit_date in enumerate(marker_days):
        create_habit(client, token, f"Habit {i}", habit_date, done=True)

    stats = get_habit_stats(client, token, today.isoformat(), "year")

    expected = sum(1 for habit_date in marker_days if habit_date <= today)
    assert stats["total_habits"] == expected
    assert stats["completed_habits"] == expected


def test_past_week_stats_unchanged(client):
    token = auth_token(client)
    # 2026-01-12 is a Monday; the whole week is in the past
    start_of_week = date(2026, 1, 12)
    for i in range(7):
        create_habit(client, token, "Reading", start_of_week + timedelta(days=i), done=(i % 2 == 0))

    stats = get_habit_stats(client, token, "2026-01-14", "week")

    assert stats["total_habits"] == 7
    assert stats["completed_habits"] == 4


def test_habits_all_excludes_future_days(client):
    token = auth_token(client)
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    for i in range(7):
        create_habit(client, token, "Reading", start_of_week + timedelta(days=i), done=True)

    resp = client.get(
        f"/api/stats/habits/all/{today.isoformat()}/week/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = json.loads(resp.data)

    days_elapsed = today.weekday() + 1
    assert body["total"]["total_habits"] == days_elapsed
    assert body["items"] == [{
        "description": "Reading",
        "total_habits": days_elapsed,
        "completed_habits": days_elapsed,
        "percentage": 100,
    }]
