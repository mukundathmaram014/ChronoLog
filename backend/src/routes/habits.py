from flask import Blueprint
from utils import success_response, failure_response
import json
from db import db
from flask import Flask, request
from db import Habit



habit_routes = Blueprint('habit', __name__)

@habit_routes.route("/")
def test():
    return success_response("hello world")

@habit_routes.route("/habits/")
def get_habits():
    """
    Endpoint for getting all habits
    """
    habits = []
    for habit in Habit.query.all():
        habits.append(habit.serialize())

    return success_response({"habits": habits})

@habit_routes.route("/habits/", methods=["POST"])
def create_habit():
    """
    Endpoint for creating a new habit
    """
    body = json.loads(request.data)
    new_habit = Habit(description = body.get("description",""), done = body.get("done", False))
    db.session.add(new_habit)
    db.session.commit()
    return success_response(new_habit.serialize(), 201)

@habit_routes.route("/habits/<int:habit_id>/")
def get_habit(habit_id):
    """
    Endpoint for getting a habit by id
    """
    habit = Habit.query.filter_by(id=habit_id).first()
    if habit is None:
        return failure_response("Habit not found")
    return success_response(habit.serialize())

@habit_routes.route("/habits/<int:habit_id>/", methods=["PUT"])
def update_habit(habit_id):
    """
    Endpoint for updating a habit by id
    """
    body = json.loads(request.data)
    habit = Habit.query.filter_by(id=habit_id).first()
    if habit is None:
        return failure_response("Habit not found")
    habit.description = body.get("description", habit.description)
    habit.done = body.get("done", habit.done)
    db.session.commit()
    return success_response(habit.serialize())

@habit_routes.route("/habits/<int:habit_id>/", methods=["DELETE"])
def delete_habit(habit_id):
    """
    Endpoint for deleting a habit by id
    """
    habit = Habit.query.filter_by(id=habit_id).first()
    if habit is None:
        return failure_response("Habit not found")
    db.session.delete(habit)
    db.session.commit()
    return success_response(habit.serialize())