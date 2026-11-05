import json
from datetime import date, timedelta

from conftest import auth_token

HOUR = 3600000


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def monday_weeks_ago(weeks):
    today = date.today()
    return today - timedelta(days=today.weekday() + 7 * weeks)


def create_stopwatch(client, token, title, day, repeat_days=127):
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": title, "date": day.isoformat(), "repeat_days": repeat_days}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 200
    stopwatches = json.loads(resp.data)["stopwatches"]
    return next(sw for sw in stopwatches if sw["title"] == title)["id"]


def set_duration(client, token, stopwatch_id, milliseconds):
    resp = client.put(
        f"/api/stopwatches/{stopwatch_id}/",
        data=json.dumps({"curr_duration": milliseconds}),
        content_type="application/json",
        headers=headers(token),
    )
    assert resp.status_code == 200


def week_average(client, token, day, query=""):
    resp = client.get(f"/api/stats/stopwatches/{day.isoformat()}/week/{query}", headers=headers(token))
    assert resp.status_code == 200
    return json.loads(resp.data)["average_time_worked_per_day"]


def combined_average(client, token, day, query=""):
    resp = client.get(f"/api/stats/stopwatches/all/{day.isoformat()}/week/{query}", headers=headers(token))
    assert resp.status_code == 200
    return json.loads(resp.data)["total"]["average_time_worked_per_day"]


def test_average_counts_days_with_nothing_scheduled(client):
    token = auth_token(client)
    monday = monday_weeks_ago(2)
    # scheduled on Mondays only, so that's the only day of the week with a row
    sw_id = create_stopwatch(client, token, "item a", monday, repeat_days=1)
    set_duration(client, token, sw_id, 7 * HOUR)

    assert week_average(client, token, monday) == HOUR
    assert combined_average(client, token, monday) == HOUR


def test_average_starts_at_the_first_tracked_day(client):
    token = auth_token(client)
    thursday = monday_weeks_ago(2) + timedelta(days=3)
    sw_id = create_stopwatch(client, token, "item a", thursday)
    set_duration(client, token, sw_id, 4 * HOUR)

    # Thursday through Sunday, not the days before this user had any data
    assert week_average(client, token, thursday) == HOUR


def test_average_stops_at_the_users_today(client):
    token = auth_token(client)
    yesterday = date.today() - timedelta(days=1)
    sw_id = create_stopwatch(client, token, "item a", yesterday)
    set_duration(client, token, sw_id, 3 * HOUR)

    # the user's clock still says it's that first day, so today isn't an elapsed day yet
    assert week_average(client, token, yesterday, f"?today={yesterday.isoformat()}") == 3 * HOUR


def test_implausible_today_param_is_ignored(client):
    token = auth_token(client)
    monday = monday_weeks_ago(0)
    sw_id = create_stopwatch(client, token, "item a", monday)
    set_duration(client, token, sw_id, 2 * HOUR)

    expected = week_average(client, token, monday)
    assert week_average(client, token, monday, "?today=2000-01-01") == expected
    assert week_average(client, token, monday, "?today=not-a-date") == expected


def test_single_stopwatch_averages_over_its_own_days(client):
    token = auth_token(client)
    monday = monday_weeks_ago(2)
    first = create_stopwatch(client, token, "item a", monday)
    second = create_stopwatch(client, token, "item a", monday + timedelta(days=2))
    set_duration(client, token, first, 3 * HOUR)
    set_duration(client, token, second, HOUR)

    assert week_average(client, token, monday, "?title=item%20a") == 2 * HOUR


def test_empty_period_averages_to_zero(client):
    token = auth_token(client)
    assert week_average(client, token, monday_weeks_ago(2)) == 0

    # a week before the first tracked day
    create_stopwatch(client, token, "item a", monday_weeks_ago(1))
    assert week_average(client, token, monday_weeks_ago(2)) == 0
