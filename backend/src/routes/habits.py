from flask import Blueprint
from utils import success_response, failure_response, process_date
import json
from db import db
from flask import Flask, request
from db import Habit
from datetime import date, datetime, timedelta



habit_routes = Blueprint('habit', __name__)

@habit_routes.route("/")
def test():
    return success_response("hello world")

def create_habit_for_date(requested_date, done, description):
    new_habit = Habit(description = description, done = done, date = requested_date)

    db.session.add(new_habit)
    db.session.commit()
    return new_habit

@habit_routes.route("/habits/<string:date_string>/")
def get_habits(date_string):
    """
    Endpoint for getting all habits for a specific date
    """
    requested_date = date.fromisoformat(date_string)

    habits = []
    for habit in Habit.query.filter_by(date=requested_date).all():
        habits.append(habit.serialize())

    #gets previous days habits if empty and date is today
    if not habits and (requested_date == date.today()):
        prev_date = requested_date - timedelta(days=1)
        new_habits = []

        for prev_habit in Habit.query.filter_by(date=prev_date).all():
            new_habit = create_habit_for_date(requested_date=requested_date, done = False, description = prev_habit.description)
            new_habits.append(new_habit)

        db.session.commit()
        habits = new_habits


    return success_response({"habits": habits})

@habit_routes.route("/habits/", methods=["POST"])
def create_habit():
    """
    Endpoint for creating a new habit
    """
    body = json.loads(request.data)
    requested_date = process_date(request)
    new_habit = create_habit_for_date(requested_date=requested_date, done = body.get("done", False), description= body.get("description",""))
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
    habit.date = body.get("date", habit.date)
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