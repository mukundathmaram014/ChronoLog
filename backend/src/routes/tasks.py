from flask import Blueprint
from utils import success_response, failure_response
import json
from db import db
from flask import request
from db import Task
from datetime import date, timedelta
import calendar
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func


task_routes = Blueprint('task', __name__)

VALID_RECURRENCES = {"none", "daily", "weekly", "monthly"}

# history page size: the default, and the ceiling a client can ask for
DEFAULT_HISTORY_LIMIT = 50
MAX_HISTORY_LIMIT = 200


def add_months(d, months):
    """
    Returns d shifted forward by months, clamping the day to the target
    month's length (e.g. Jan 31 + 1 month = Feb 28).
    """
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def next_occurrence_date(current_date, recurrence):
    if recurrence == "daily":
        return current_date + timedelta(days=1)
    if recurrence == "weekly":
        return current_date + timedelta(days=7)
    if recurrence == "monthly":
        return add_months(current_date, 1)
    return None


def spawn_next_occurrence(task):
    """
    Creates the next occurrence of a periodic top-level task: a fresh, undone
    task dated per its recurrence, with fresh undone copies of its sub-tasks.
    """
    next_date = next_occurrence_date(task.date, task.recurrence)
    if next_date is None:
        return None

    # guards against double-spawning (e.g. a task unchecked and re-completed)
    duplicate = Task.query.filter_by(description=task.description, date=next_date, user_id=task.user_id, parent_id=None).first()
    if duplicate is not None:
        return None

    next_task = Task(description=task.description, done=False, date=next_date, recurrence=task.recurrence, user_id=task.user_id)
    db.session.add(next_task)
    for subtask in task.subtasks:
        subtask_copy = Task(description=subtask.description, done=False, date=next_date, recurrence="none", user_id=task.user_id)
        subtask_copy.parent = next_task
        db.session.add(subtask_copy)
    return next_task


@task_routes.route("/tasks/completed/")
@jwt_required()
def get_completed_tasks():
    """
    Endpoint for paging back through a user's completed top-level tasks, most
    recently completed first. Ordered (and grouped by the client) on the
    effective completion day: completed_date, falling back to the due date for
    rows finished before that column existed. limit/offset come from the query
    string; one extra row is fetched to report has_more without a second call.
    """
    user_id = int(get_jwt_identity())

    try:
        limit = int(request.args.get("limit", DEFAULT_HISTORY_LIMIT))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return failure_response("limit and offset must be integers", 400)
    if limit < 1 or offset < 0:
        return failure_response("limit must be positive and offset must not be negative", 400)
    limit = min(limit, MAX_HISTORY_LIMIT)

    effective_date = func.coalesce(Task.completed_date, Task.date)
    # id descending breaks ties so paging stays stable within a single day
    tasks = (Task.query
             .filter_by(user_id=user_id, parent_id=None, done=True)
             .order_by(effective_date.desc(), Task.id.desc())
             .offset(offset)
             .limit(limit + 1)
             .all())

    has_more = len(tasks) > limit
    completed = [task.serialize() for task in tasks[:limit]]
    return success_response({"completed": completed, "has_more": has_more})


@task_routes.route("/tasks/<string:date_string>/")
@jwt_required()
def get_tasks(date_string):
    """
    Endpoint for getting a user's tasks grouped as overdue / today / upcoming,
    relative to the given date (the client's current date). Sub-tasks are
    nested under their parents. An undone task with a past date stays in
    overdue until completed or deleted; a completed past task is not shown.
    """
    user_id = int(get_jwt_identity())
    today = date.fromisoformat(date_string)

    overdue = []
    today_tasks = []
    upcoming = []
    for task in Task.query.filter_by(user_id=user_id, parent_id=None).order_by(Task.date, Task.id).all():
        if task.date < today:
            if not task.done:
                overdue.append(task.serialize())
        elif task.date == today:
            today_tasks.append(task.serialize())
        else:
            upcoming.append(task.serialize())

    return success_response({"overdue": overdue, "today": today_tasks, "upcoming": upcoming})


@task_routes.route("/tasks/", methods=["POST"])
@jwt_required()
def create_task():
    """
    Endpoint for creating a new task (optionally a sub-task via parent_id,
    optionally periodic via recurrence, optionally future-dated via date)
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)

    description = body.get("description", "")
    if not description.strip():
        return failure_response("description is required", 400)

    recurrence = body.get("recurrence", "none")
    if recurrence not in VALID_RECURRENCES:
        return failure_response("recurrence must be one of: none, daily, weekly, monthly", 400)

    parent_id = body.get("parent_id")
    parent = None
    if parent_id is not None:
        parent = Task.query.filter_by(id=parent_id, user_id=user_id).first()
        if parent is None:
            return failure_response("Parent task not found")
        if parent.parent_id is not None:
            return failure_response("Sub-tasks can only be nested one level deep", 400)
        # recurrence lives on the top-level task
        recurrence = "none"

    if "date" in body:
        requested_date = date.fromisoformat(body.get("date"))
    elif parent is not None:
        # sub-tasks inherit the parent's date
        requested_date = parent.date
    else:
        requested_date = date.today()

    new_task = Task(description=description, done=body.get("done", False), date=requested_date, recurrence=recurrence, parent_id=parent_id, user_id=user_id)
    db.session.add(new_task)
    db.session.commit()
    return success_response(new_task.serialize(), 201)


@task_routes.route("/tasks/<int:task_id>/")
@jwt_required()
def get_task(task_id):
    """
    Endpoint for getting a task by id
    """
    user_id = int(get_jwt_identity())
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if task is None:
        return failure_response("Task not found")
    return success_response(task.serialize())


@task_routes.route("/tasks/<int:task_id>/", methods=["PUT"])
@jwt_required()
def update_task(task_id):
    """
    Endpoint for updating a task by id (toggle done / edit / reschedule /
    change recurrence). Completing a periodic top-level task spawns its next
    occurrence; completing the last undone sub-task auto-completes the parent.
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if task is None:
        return failure_response("Task not found")

    task.description = body.get("description", task.description)

    new_recurrence = body.get("recurrence", task.recurrence)
    if new_recurrence not in VALID_RECURRENCES:
        return failure_response("recurrence must be one of: none, daily, weekly, monthly", 400)
    if task.parent_id is None:
        # applies to future occurrences only: the next spawn copies this value
        task.recurrence = new_recurrence

    if "date" in body:
        new_date = date.fromisoformat(body.get("date"))
        if new_date != task.date:
            task.date = new_date
            # sub-tasks follow the parent's date
            for subtask in task.subtasks:
                subtask.date = new_date

    was_done = task.done
    task.done = body.get("done", task.done)

    if task.done and not was_done:
        # the client's own day, since the server may sit in a different timezone.
        # NB: a distinct key from "date", which above means the *due* date.
        task.completed_date = date.fromisoformat(body["completed_date"]) if "completed_date" in body else date.today()
        if task.parent_id is None:
            if task.recurrence != "none":
                spawn_next_occurrence(task)
        else:
            # completing the last undone sub-task auto-completes the parent
            parent = task.parent
            if not parent.done and all(subtask.done for subtask in parent.subtasks):
                parent.done = True
                # without this the indirectly-completed parent has no completion
                # day and would never surface in the history
                parent.completed_date = task.completed_date
                if parent.recurrence != "none":
                    spawn_next_occurrence(parent)
    elif was_done and not task.done:
        task.completed_date = None

    db.session.commit()
    return success_response(task.serialize())


@task_routes.route("/tasks/<int:task_id>/", methods=["DELETE"])
@jwt_required()
def delete_task(task_id):
    """
    Endpoint for deleting a task by id (cascades to its sub-tasks)
    """
    user_id = int(get_jwt_identity())
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if task is None:
        return failure_response("Task not found")
    serialized = task.serialize()
    db.session.delete(task)
    db.session.commit()
    return success_response(serialized)
