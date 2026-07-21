"""
Covers GET /api/tasks/completed/ — the opt-in look back at finished tasks
(spec 0031). Completed tasks are dropped from every bucket get_tasks returns,
so this endpoint is the only way they are ever visible again.
"""
import json

from conftest import auth_token
from test_tasks import TODAY, create_task, get_grouped, update_task

from db import db, Task


def get_history(client, token, **params):
    query = "&".join(f"{key}={value}" for key, value in params.items())
    resp = client.get(
        f"/api/tasks/completed/{'?' + query if query else ''}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    return json.loads(resp.data)


def test_completed_past_task_leaves_the_buckets_but_enters_history(client):
    token = auth_token(client)
    task_id = json.loads(create_task(client, token, description="shipped", date="2026-01-10").data)["id"]
    update_task(client, token, task_id, done=True, completed_date=TODAY)

    groups = get_grouped(client, token)
    assert groups["overdue"] == [] and groups["today"] == [] and groups["upcoming"] == []

    body = get_history(client, token)
    assert [t["description"] for t in body["completed"]] == ["shipped"]
    # filed under the day it was finished, not the due date it blew through
    assert body["completed"][0]["completed_date"] == TODAY
    assert body["has_more"] is False


def test_undone_past_task_is_overdue_and_absent_from_history(client):
    token = auth_token(client)
    create_task(client, token, description="still pending", date="2026-01-10")

    assert [t["description"] for t in get_grouped(client, token)["overdue"]] == ["still pending"]
    assert get_history(client, token)["completed"] == []


def test_periodic_task_records_one_entry_and_its_successor_stays_out(client):
    token = auth_token(client)
    task_id = json.loads(create_task(client, token, description="report", date=TODAY, recurrence="weekly").data)["id"]
    update_task(client, token, task_id, done=True, completed_date=TODAY)

    # the spawned occurrence is undone, so only the finished one is history
    assert [t["date"] for t in get_grouped(client, token)["upcoming"]] == ["2026-01-22"]
    completed = get_history(client, token)["completed"]
    assert [(t["id"], t["date"]) for t in completed] == [(task_id, TODAY)]


def test_uncompleting_removes_the_task_from_history(client):
    token = auth_token(client)
    task_id = json.loads(create_task(client, token, description="premature", date=TODAY).data)["id"]

    update_task(client, token, task_id, done=True, completed_date=TODAY)
    assert len(get_history(client, token)["completed"]) == 1

    update_task(client, token, task_id, done=False)
    assert get_history(client, token)["completed"] == []


def test_legacy_row_without_completed_date_falls_back_to_its_due_date(client, app):
    token = auth_token(client)
    task_id = json.loads(create_task(client, token, description="from before the column", date="2026-01-05").data)["id"]
    update_task(client, token, task_id, done=True, completed_date=TODAY)

    # mimic a row completed before completed_date existed
    with app.app_context():
        Task.query.filter_by(id=task_id).first().completed_date = None
        db.session.commit()

    entry = get_history(client, token)["completed"][0]
    assert entry["completed_date"] is None
    assert entry["date"] == "2026-01-05"  # the client keys off `date` in this case


def test_subtasks_nest_under_the_parent_entry(client):
    token = auth_token(client)
    parent_id = json.loads(create_task(client, token, description="parent", date=TODAY).data)["id"]
    create_task(client, token, description="child", parent_id=parent_id)
    update_task(client, token, parent_id, done=True, completed_date=TODAY)

    completed = get_history(client, token)["completed"]
    assert [t["description"] for t in completed] == ["parent"]
    assert [s["description"] for s in completed[0]["subtasks"]] == ["child"]


def test_history_is_ordered_most_recently_completed_first(client):
    token = auth_token(client)
    for description, completed_on in [("oldest", "2026-01-05"), ("newest", "2026-01-14"), ("middle", "2026-01-09")]:
        task_id = json.loads(create_task(client, token, description=description, date="2026-01-01").data)["id"]
        update_task(client, token, task_id, done=True, completed_date=completed_on)

    completed = get_history(client, token)["completed"]
    assert [t["description"] for t in completed] == ["newest", "middle", "oldest"]


def test_limit_and_offset_page_without_gaps_or_duplicates(client):
    token = auth_token(client)
    for day in range(1, 6):
        task_id = json.loads(create_task(client, token, description=f"task {day}", date=TODAY).data)["id"]
        update_task(client, token, task_id, done=True, completed_date=f"2026-01-0{day}")

    first = get_history(client, token, limit=2, offset=0)
    assert [t["description"] for t in first["completed"]] == ["task 5", "task 4"]
    assert first["has_more"] is True

    second = get_history(client, token, limit=2, offset=2)
    assert [t["description"] for t in second["completed"]] == ["task 3", "task 2"]
    assert second["has_more"] is True

    # has_more flips false exactly on the page that exhausts the rows
    last = get_history(client, token, limit=2, offset=4)
    assert [t["description"] for t in last["completed"]] == ["task 1"]
    assert last["has_more"] is False


def test_history_rejects_non_integer_paging_params(client):
    token = auth_token(client)
    for params in ({"limit": "all"}, {"offset": "later"}, {"limit": "0"}, {"offset": "-1"}):
        query = "&".join(f"{key}={value}" for key, value in params.items())
        resp = client.get(
            f"/api/tasks/completed/?{query}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400, params


def test_deleting_a_completed_task_clears_it_and_its_subtasks_from_history(client):
    token = auth_token(client)
    parent_id = json.loads(create_task(client, token, description="parent", date=TODAY).data)["id"]
    child_id = json.loads(create_task(client, token, description="child", parent_id=parent_id).data)["id"]
    update_task(client, token, child_id, done=True, completed_date=TODAY)  # auto-completes the parent

    assert len(get_history(client, token)["completed"]) == 1

    resp = client.delete(f"/api/tasks/{parent_id}/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert get_history(client, token)["completed"] == []
    resp = client.get(f"/api/tasks/{child_id}/", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404


def test_history_is_scoped_to_the_requesting_user(client):
    token_a = auth_token(client, username="userA", email="a@example.com")
    token_b = auth_token(client, username="userB", email="b@example.com")

    task_id = json.loads(create_task(client, token_a, description="A's finished task", date=TODAY).data)["id"]
    update_task(client, token_a, task_id, done=True, completed_date=TODAY)

    assert len(get_history(client, token_a)["completed"]) == 1
    assert get_history(client, token_b)["completed"] == []
