import json
from conftest import auth_token

TODAY = "2026-01-15"


def create_task(client, token, **fields):
    resp = client.post(
        "/api/tasks/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


def update_task(client, token, task_id, **fields):
    resp = client.put(
        f"/api/tasks/{task_id}/",
        data=json.dumps(fields),
        content_type="application/json",
        headers={"Authorization": f"Bearer {token}"},
    )
    return resp


def get_grouped(client, token, today=TODAY):
    resp = client.get(
        f"/api/tasks/{today}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def test_create_and_group_overdue_today_upcoming(client):
    token = auth_token(client)

    assert create_task(client, token, description="past undone", date="2026-01-10").status_code == 201
    resp = create_task(client, token, description="past done", date="2026-01-10")
    past_done_id = json.loads(resp.data)["id"]
    update_task(client, token, past_done_id, done=True)
    assert create_task(client, token, description="due today", date=TODAY).status_code == 201
    assert create_task(client, token, description="future", date="2026-01-20").status_code == 201

    groups = get_grouped(client, token)
    assert [t["description"] for t in groups["overdue"]] == ["past undone"]
    assert [t["description"] for t in groups["today"]] == ["due today"]
    assert [t["description"] for t in groups["upcoming"]] == ["future"]


def test_overdue_rolls_forward_until_done(client):
    token = auth_token(client)
    resp = create_task(client, token, description="lingering", date="2026-01-10")
    task_id = json.loads(resp.data)["id"]

    # still overdue days later
    groups = get_grouped(client, token, today="2026-01-30")
    assert [t["id"] for t in groups["overdue"]] == [task_id]

    # completing it removes it from every group
    update_task(client, token, task_id, done=True)
    groups = get_grouped(client, token, today="2026-01-30")
    assert groups["overdue"] == [] and groups["today"] == [] and groups["upcoming"] == []


def test_create_requires_description_and_valid_recurrence(client):
    token = auth_token(client)
    assert create_task(client, token, description="  ", date=TODAY).status_code == 400
    assert create_task(client, token, description="x", date=TODAY, recurrence="yearly").status_code == 400


def test_subtasks_nest_inherit_date_and_cascade_delete(client):
    token = auth_token(client)
    resp = create_task(client, token, description="parent", date=TODAY)
    parent_id = json.loads(resp.data)["id"]

    resp = create_task(client, token, description="child", parent_id=parent_id)
    assert resp.status_code == 201
    child = json.loads(resp.data)
    assert child["parent_id"] == parent_id
    assert child["date"] == TODAY  # inherited from parent

    # only one level of nesting
    assert create_task(client, token, description="grandchild", parent_id=child["id"]).status_code == 400

    # nested in the list response, not top-level
    groups = get_grouped(client, token)
    assert len(groups["today"]) == 1
    assert [s["description"] for s in groups["today"][0]["subtasks"]] == ["child"]

    # deleting the parent cascades to the sub-task
    resp = client.delete(
        f"/api/tasks/{parent_id}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    resp = client.get(
        f"/api/tasks/{child['id']}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


def test_completing_all_subtasks_autocompletes_parent(client):
    token = auth_token(client)
    parent_id = json.loads(create_task(client, token, description="parent", date=TODAY).data)["id"]
    sub_a = json.loads(create_task(client, token, description="a", parent_id=parent_id).data)["id"]
    sub_b = json.loads(create_task(client, token, description="b", parent_id=parent_id).data)["id"]

    update_task(client, token, sub_a, done=True)
    groups = get_grouped(client, token)
    assert groups["today"][0]["done"] is False

    update_task(client, token, sub_b, done=True)
    groups = get_grouped(client, token)
    assert groups["today"][0]["done"] is True


def test_periodic_task_spawns_next_occurrence_on_complete(client):
    token = auth_token(client)
    resp = create_task(client, token, description="report", date=TODAY, recurrence="weekly")
    task_id = json.loads(resp.data)["id"]
    sub_id = json.loads(create_task(client, token, description="step", parent_id=task_id).data)["id"]

    update_task(client, token, sub_id, done=True)  # auto-completes parent -> spawns

    groups = get_grouped(client, token)
    assert len(groups["upcoming"]) == 1
    spawned = groups["upcoming"][0]
    assert spawned["description"] == "report"
    assert spawned["date"] == "2026-01-22"
    assert spawned["done"] is False
    assert spawned["recurrence"] == "weekly"
    # fresh, undone copy of the sub-task
    assert [(s["description"], s["done"]) for s in spawned["subtasks"]] == [("step", False)]

    # unchecking and re-completing does not double-spawn
    update_task(client, token, task_id, done=False)
    update_task(client, token, task_id, done=True)
    groups = get_grouped(client, token)
    assert len(groups["upcoming"]) == 1


def test_missed_periodic_task_stays_overdue_then_spawns(client):
    token = auth_token(client)
    resp = create_task(client, token, description="daily thing", date="2026-01-10", recurrence="daily")
    task_id = json.loads(resp.data)["id"]

    groups = get_grouped(client, token)
    assert [t["id"] for t in groups["overdue"]] == [task_id]

    update_task(client, token, task_id, done=True)
    groups = get_grouped(client, token)
    # next occurrence keeps the recurrence cadence from the original date
    assert [t["date"] for t in groups["overdue"]] == ["2026-01-11"]
    assert groups["overdue"][0]["done"] is False


def test_monthly_recurrence_clamps_day(client):
    token = auth_token(client)
    resp = create_task(client, token, description="rent", date="2026-01-31", recurrence="monthly")
    task_id = json.loads(resp.data)["id"]

    update_task(client, token, task_id, done=True)
    groups = get_grouped(client, token, today="2026-01-31")
    assert [t["date"] for t in groups["upcoming"]] == ["2026-02-28"]


def test_rescheduling_parent_moves_subtasks(client):
    token = auth_token(client)
    parent_id = json.loads(create_task(client, token, description="parent", date=TODAY).data)["id"]
    create_task(client, token, description="child", parent_id=parent_id)

    resp = update_task(client, token, parent_id, date="2026-01-20")
    body = json.loads(resp.data)
    assert body["date"] == "2026-01-20"
    assert [s["date"] for s in body["subtasks"]] == ["2026-01-20"]


def test_tasks_cross_user_isolation(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")

    resp = create_task(client, token_a, description="A's task", date=TODAY)
    task_id = json.loads(resp.data)["id"]

    resp = client.get(
        f"/api/tasks/{task_id}/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    assert update_task(client, token_b, task_id, done=True).status_code == 404

    resp = client.delete(
        f"/api/tasks/{task_id}/",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert resp.status_code == 404

    # B cannot attach a sub-task to A's task
    assert create_task(client, token_b, description="sneaky", parent_id=task_id).status_code == 404

    groups = get_grouped(client, token_b)
    assert groups["overdue"] == [] and groups["today"] == [] and groups["upcoming"] == []
