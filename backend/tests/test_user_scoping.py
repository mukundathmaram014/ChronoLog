import json
from conftest import auth_token


def test_habits_cross_user_isolation(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")

    # A creates a habit
    resp = client.post(
        "/api/habits/",
        data=json.dumps({"description": "A's habit", "date": "2026-01-15"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    habit_id = json.loads(resp.data)["id"]

    # B cannot GET A's habit by id
    resp = client.get(
        f"/api/habits/{habit_id}/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    # B cannot PUT A's habit
    resp = client.put(
        f"/api/habits/{habit_id}/",
        data=json.dumps({"done": True}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    # B cannot DELETE A's habit
    resp = client.delete(
        f"/api/habits/{habit_id}/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    # B's GET by date returns empty (A's habit is not visible)
    resp = client.get(
        "/api/habits/2026-01-15/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    body = json.loads(resp.data)
    assert body["habits"] == []


def test_completed_task_history_cross_user_isolation(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")

    # A creates and completes a task
    resp = client.post(
        "/api/tasks/",
        data=json.dumps({"description": "A's task", "date": "2026-01-15"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 201
    task_id = json.loads(resp.data)["id"]
    client.put(
        f"/api/tasks/{task_id}/",
        data=json.dumps({"done": True, "completed_date": "2026-01-15"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # B's history is empty; A's is not
    resp = client.get("/api/tasks/completed/", headers={"Authorization": f"Bearer {token_b}"})
    assert json.loads(resp.data)["completed"] == []
    resp = client.get("/api/tasks/completed/", headers={"Authorization": f"Bearer {token_a}"})
    assert [t["id"] for t in json.loads(resp.data)["completed"]] == [task_id]

    # and it is not reachable unauthenticated
    assert client.get("/api/tasks/completed/").status_code == 401


def test_stopwatch_cross_user_isolation(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")

    # A creates a stopwatch
    resp = client.post(
        "/api/stopwatches/",
        data=json.dumps({"title": "A's stopwatch", "date": "2026-01-15"}),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert resp.status_code == 200
    stopwatches = json.loads(resp.data)["stopwatches"]
    # stopwatches[0] = total, stopwatches[1] = the named stopwatch
    sw_id = stopwatches[1]["id"]

    # B cannot GET A's stopwatch
    resp = client.get(
        f"/api/stopwatches/{sw_id}/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404
