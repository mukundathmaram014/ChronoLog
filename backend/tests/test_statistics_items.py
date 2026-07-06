import json
from conftest import auth_token


def create_habit(client, token, description, date_string):
    resp = client.post(
        "/api/habits/",
        data=json.dumps({"description": description, "date": date_string}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


def create_stopwatch(client, token, title, date_string):
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": title, "date": date_string}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def get_items(client, token, date_string, time_period):
    resp = client.get(
        f"/api/stats/items/{date_string}/{time_period}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def test_month_includes_items_from_other_days(client):
    token = auth_token(client)
    create_habit(client, token, "Meditate", "2026-01-05")
    create_habit(client, token, "Journal", "2026-01-20")
    create_stopwatch(client, token, "Reading", "2026-01-05")
    create_stopwatch(client, token, "Coding", "2026-01-20")

    items = get_items(client, token, "2026-01-20", "month")

    assert items["habits"] == ["Journal", "Meditate"]
    assert items["stopwatches"] == ["Total Time", "Coding", "Reading"]


def test_period_excludes_items_outside_it(client):
    token = auth_token(client)
    # 2026-01-12 is a Monday; 2026-01-10 falls in the previous week
    create_habit(client, token, "Meditate", "2026-01-10")
    create_habit(client, token, "Journal", "2026-01-13")

    items = get_items(client, token, "2026-01-14", "week")

    assert items["habits"] == ["Journal"]


def test_duplicate_names_collapse(client):
    token = auth_token(client)
    create_habit(client, token, "Meditate", "2026-01-12")
    create_habit(client, token, "Meditate", "2026-01-13")
    create_stopwatch(client, token, "Reading", "2026-01-12")
    create_stopwatch(client, token, "Reading", "2026-01-13")

    items = get_items(client, token, "2026-01-14", "week")

    assert items["habits"] == ["Meditate"]
    assert items["stopwatches"] == ["Total Time", "Reading"]


def test_day_only_lists_that_day(client):
    token = auth_token(client)
    create_habit(client, token, "Meditate", "2026-01-05")
    create_habit(client, token, "Journal", "2026-01-20")

    items = get_items(client, token, "2026-01-20", "day")

    assert items["habits"] == ["Journal"]


def test_items_scoped_by_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")
    create_habit(client, token_a, "Meditate", "2026-01-15")
    create_stopwatch(client, token_a, "Reading", "2026-01-15")

    items = get_items(client, token_b, "2026-01-15", "month")

    assert items["habits"] == []
    assert items["stopwatches"] == ["Total Time"]


def test_items_invalid_period(client):
    token = auth_token(client)
    resp = client.get(
        "/api/stats/items/2026-01-15/decade/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code != 200
