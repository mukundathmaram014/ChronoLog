from flask import Blueprint
from utils import success_response, failure_response, VALID_DIFFICULTIES
import json
from db import db
from flask import request
from db import Goal
from datetime import date
from flask_jwt_extended import jwt_required, get_jwt_identity
from xp import recompute_from


goal_routes = Blueprint('goal', __name__)


@goal_routes.route("/goals/")
@jwt_required()
def get_goals():
    """
    Endpoint for getting all of a user's goals (active and completed)
    """
    user_id = int(get_jwt_identity())
    goals = []
    for goal in Goal.query.filter_by(user_id=user_id).order_by(Goal.id).all():
        goals.append(goal.serialize())
    return success_response({"goals": goals})


@goal_routes.route("/goals/", methods=["POST"])
@jwt_required()
def create_goal():
    """
    Endpoint for creating a new goal
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)

    description = body.get("description", "")
    if not description.strip():
        return failure_response("description is required", 400)

    difficulty = body.get("difficulty", "medium")
    if difficulty not in VALID_DIFFICULTIES:
        return failure_response("difficulty must be one of: easy, medium, hard", 400)

    new_goal = Goal(description=description, difficulty=difficulty, user_id=user_id)
    db.session.add(new_goal)
    db.session.commit()
    return success_response(new_goal.serialize(), 201)


@goal_routes.route("/goals/<int:goal_id>/")
@jwt_required()
def get_goal(goal_id):
    """
    Endpoint for getting a goal by id
    """
    user_id = int(get_jwt_identity())
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if goal is None:
        return failure_response("Goal not found")
    return success_response(goal.serialize())


@goal_routes.route("/goals/<int:goal_id>/", methods=["PUT"])
@jwt_required()
def update_goal(goal_id):
    """
    Endpoint for updating a goal by id (toggle done / edit description +
    difficulty). Completing grants its XP once on the completion date
    (body "date", defaulting to today); un-completing removes it.
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if goal is None:
        return failure_response("Goal not found")

    goal.description = body.get("description", goal.description)

    new_difficulty = body.get("difficulty", goal.difficulty)
    if new_difficulty not in VALID_DIFFICULTIES:
        return failure_response("difficulty must be one of: easy, medium, hard", 400)
    difficulty_changed = new_difficulty != goal.difficulty
    goal.difficulty = new_difficulty

    was_done = goal.done
    goal.done = body.get("done", goal.done)

    if goal.done and not was_done:
        goal.completed_date = date.fromisoformat(body["date"]) if "date" in body else date.today()
        recompute_from(user_id, goal.completed_date)
    elif was_done and not goal.done:
        old_completed_date = goal.completed_date
        goal.completed_date = None
        if old_completed_date is not None:
            recompute_from(user_id, old_completed_date)
    elif goal.done and difficulty_changed and goal.completed_date is not None:
        recompute_from(user_id, goal.completed_date)

    db.session.commit()
    return success_response(goal.serialize())


@goal_routes.route("/goals/<int:goal_id>/", methods=["DELETE"])
@jwt_required()
def delete_goal(goal_id):
    """
    Endpoint for deleting a goal by id (removes its XP if it was completed)
    """
    user_id = int(get_jwt_identity())
    goal = Goal.query.filter_by(id=goal_id, user_id=user_id).first()
    if goal is None:
        return failure_response("Goal not found")
    serialized = goal.serialize()
    completed_date = goal.completed_date if goal.done else None
    db.session.delete(goal)
    if completed_date is not None:
        recompute_from(user_id, completed_date)
    db.session.commit()
    return success_response(serialized)
