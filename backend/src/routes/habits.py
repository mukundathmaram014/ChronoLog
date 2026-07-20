from flask import Blueprint
from utils import success_response, failure_response, process_date, validate_repeat_days, VALID_DIFFICULTIES
import json
from db import db
from flask import Flask, request
from db import Habit, DeletedDay
from datetime import date, timedelta
from sqlalchemy import func
from flask_jwt_extended import jwt_required, get_jwt_identity
from xp import recompute_from



habit_routes = Blueprint('habit', __name__)

@habit_routes.route("/")
def test():
    return success_response("hello world")

def create_habit_for_date(requested_date, done, description, user_id, repeat_days = 127, difficulty = "medium"):

    duplicate = Habit.query.filter_by(description = description, date = requested_date, user_id = user_id).first()
    if duplicate is not None:
        return failure_response("Habit already exists for this day", 409)

    # new rows append at the end of that day's list
    max_position = db.session.query(func.max(Habit.position)).filter(Habit.user_id == user_id, Habit.date == requested_date).scalar()
    position = 0 if max_position is None else max_position + 1

    new_habit = Habit(description = description, done = done, date = requested_date, user_id = user_id, repeat_days = repeat_days, difficulty = difficulty, position = position)

    db.session.add(new_habit)
    db.session.commit()
    return new_habit.serialize()

@habit_routes.route("/habits/<string:date_string>/")
@jwt_required()
def get_habits(date_string):
    """
    Endpoint for getting all habits for a specific date
    """
    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    habits = []
    for habit in Habit.query.filter_by(date=requested_date, user_id = user_id).order_by(Habit.position, Habit.id).all():
        habits.append(habit.serialize())

    #gets previous days habits if empty
    if not habits:
        deleted_marker = DeletedDay.query.filter_by(date=requested_date, type = "habit", user_id = user_id).first()
        #dosent repopulate if user intentionally deleted everything
        if not deleted_marker:
            earliest_date = db.session.query(func.min(Habit.date)).filter(Habit.user_id == user_id).scalar()

            # walks back to the most recent non empty day, then keeps scanning up to 7 more days
            # (one full weekday cycle) so habits whose repeat days skip that day arent lost.
            # collects the most recent row per description; stops at a deleted day
            candidates = {}
            first_filled_date = None
            if earliest_date:
                prev_date = requested_date
                while prev_date > earliest_date:
                    prev_date = prev_date - timedelta(days=1)
                    if first_filled_date and (first_filled_date - prev_date).days >= 7:
                        break
                    # Stop if a deleted day is found
                    prev_deleted = DeletedDay.query.filter_by(date=prev_date, type="habit", user_id = user_id).first()
                    if prev_deleted:
                        break
                    day_habits = Habit.query.filter_by(date=prev_date, user_id = user_id).order_by(Habit.position, Habit.id).all()
                    if day_habits and first_filled_date is None:
                        first_filled_date = prev_date
                    for day_habit in day_habits:
                        if day_habit.description not in candidates:
                            candidates[day_habit.description] = day_habit

            new_habits = []

            for prev_habit in candidates.values():
                repeat_days = prev_habit.repeat_days

                # a scheduled day after the habits last row (up to the most recent non empty day)
                # with no row means the user deleted it there — dont carry it forward
                was_deleted = False
                check_date = prev_habit.date + timedelta(days=1)
                while check_date <= first_filled_date:
                    if repeat_days & (1 << check_date.weekday()):
                        was_deleted = True
                        break
                    check_date += timedelta(days=1)
                if was_deleted:
                    continue

                # repopulates days in between, skipping weekdays outside the habits repeat set
                temp_date = first_filled_date
                while (temp_date < (requested_date - timedelta(days=1))):
                    temp_date += timedelta(days=1)
                    if repeat_days & (1 << temp_date.weekday()):
                        create_habit_for_date(requested_date=temp_date, done = False, description=prev_habit.description, user_id = user_id, repeat_days = repeat_days, difficulty = prev_habit.difficulty)

                if repeat_days & (1 << requested_date.weekday()):
                    new_habit = create_habit_for_date(requested_date=requested_date, done = False, description = prev_habit.description, user_id = user_id, repeat_days = repeat_days, difficulty = prev_habit.difficulty)
                    new_habits.append(new_habit)

            db.session.commit()
            habits = new_habits


    return success_response({"habits": habits})

@habit_routes.route("/habits/", methods=["POST"])
@jwt_required()
def create_habit():
    """
    Endpoint for creating a new habit
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    requested_date = process_date(request)
    repeat_days = body.get("repeat_days", 127)
    if not validate_repeat_days(repeat_days):
        return failure_response("repeat_days must be an integer between 1 and 127", 400)
    difficulty = body.get("difficulty", "medium")
    if difficulty not in VALID_DIFFICULTIES:
        return failure_response("difficulty must be one of: easy, medium, hard", 400)
    new_habit = create_habit_for_date(requested_date=requested_date, done = body.get("done", False), description= body.get("description",""), user_id=user_id, repeat_days=repeat_days, difficulty=difficulty)
    # If result is a failure response, return it directly
    if isinstance(new_habit, tuple):
        return new_habit
    if new_habit["done"]:
        recompute_from(user_id, requested_date)
        db.session.commit()
    return success_response(new_habit, 201)

@habit_routes.route("/habits/reorder/", methods=["PATCH"])
@jwt_required()
def reorder_habits():
    """
    Endpoint for persisting a user's drag-reordering of a day's habits.
    Body: {"date": "...", "order": [habit ids in display order]}
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    requested_date = process_date(request)
    order = body.get("order")
    if not isinstance(order, list):
        return failure_response("order must be a list of habit ids", 400)

    habits = Habit.query.filter_by(date=requested_date, user_id = user_id).all()
    habits_by_id = {habit.id: habit for habit in habits}
    for index, habit_id in enumerate(order):
        habit = habits_by_id.get(habit_id)
        if habit is not None:
            habit.position = index
    db.session.commit()

    habits.sort(key=lambda habit: (habit.position, habit.id))
    return success_response({"habits": [habit.serialize() for habit in habits]})

@habit_routes.route("/habits/<int:habit_id>/")
@jwt_required()
def get_habit(habit_id):
    """
    Endpoint for getting a habit by id
    """
    user_id = int(get_jwt_identity())
    habit = Habit.query.filter_by(id=habit_id, user_id = user_id).first()
    if habit is None:
        return failure_response("Habit not found")
    return success_response(habit.serialize())

@habit_routes.route("/habits/<int:habit_id>/", methods=["PUT"])
@jwt_required()
def update_habit(habit_id):
    """
    Endpoint for updating a habit by id
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    habit = Habit.query.filter_by(id=habit_id, user_id = user_id).first()
    if habit is None:
        return failure_response("Habit not found")
    
    # dosent allow a duplicate habit to be created
    new_description = body.get("description", habit.description)
    if new_description != habit.description:
        duplicate = Habit.query.filter_by(description = new_description, date = habit.date, user_id = user_id).first()
        if duplicate is not None:
            return failure_response("Habit already exists for this day", 409)
    habit.description = new_description
    
    new_repeat_days = body.get("repeat_days", habit.repeat_days)
    if not validate_repeat_days(new_repeat_days):
        return failure_response("repeat_days must be an integer between 1 and 127", 400)
    # applies forward only: future carry-forward reads this value; past rows are untouched
    habit.repeat_days = new_repeat_days

    new_difficulty = body.get("difficulty", habit.difficulty)
    if new_difficulty not in VALID_DIFFICULTIES:
        return failure_response("difficulty must be one of: easy, medium, hard", 400)

    old_done = habit.done
    old_difficulty = habit.difficulty
    old_date = habit.date
    habit.difficulty = new_difficulty
    habit.done = body.get("done", habit.done)
    new_date = body.get("date", habit.date)
    if isinstance(new_date, str):
        new_date = date.fromisoformat(new_date)
    habit.date = new_date

    # a done toggle, or a difficulty/date change while done, changes that day's XP
    if (habit.done != old_done) or (habit.done and (habit.difficulty != old_difficulty or habit.date != old_date)):
        recompute_from(user_id, min(old_date, habit.date))
    db.session.commit()
    return success_response(habit.serialize())

@habit_routes.route("/habits/<int:habit_id>/", methods=["DELETE"])
@jwt_required()
def delete_habit(habit_id):
    """
    Endpoint for deleting a habit by id
    """
    user_id = int(get_jwt_identity())
    habit = Habit.query.filter_by(id=habit_id, user_id = user_id).first()
    if habit is None:
        return failure_response("Habit not found")
    habit_date = habit.date
    was_done = habit.done
    db.session.delete(habit)
    db.session.commit()

    # checks if day is a deleted day (intentionally made empty)
    remaining_habits = Habit.query.filter_by(date=habit_date, user_id = user_id).all()
    if (not remaining_habits):
        deleted_marker = DeletedDay(date=habit_date, type = "habit", user_id = user_id)
        db.session.add(deleted_marker)
        db.session.commit()

    # a deleted done habit no longer contributes to that day's XP
    if was_done:
        recompute_from(user_id, habit_date)
        db.session.commit()

    return success_response(habit.serialize())
