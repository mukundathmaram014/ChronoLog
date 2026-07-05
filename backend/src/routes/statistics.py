from flask import Blueprint
from utils import success_response, failure_response
import json
from db import db
from flask import Flask, request
from db import Stopwatch
from db import Habit
from datetime import datetime, date, timedelta
import calendar
from flask_jwt_extended import jwt_required, get_jwt_identity

statistic_routes = Blueprint('statistics', __name__)

@statistic_routes.route("/")
def test():
    return success_response("hello worldww")

@statistic_routes.route("/stats/habits/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_habits_stats(date_string, time_period):
    """
    Endpoint for getting statistics on habits
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)
    total_habits = 0
    completed_habits = 0
    description = request.args.get("description")

    if (time_period == "day"):
        query = Habit.query.filter_by(date=requested_date, user_id = user_id)
        if description:
            query = query.filter_by(description = description)
        for habit in query.all():
            total_habits += 1
            if (habit.done):
                completed_habits += 1
    elif (time_period == "week"):
        start_of_week = requested_date - timedelta(days = requested_date.weekday())
        current_day_in_week = start_of_week
        days_in_week = 7

        for i in range(days_in_week):
            query = Habit.query.filter_by(date=current_day_in_week, user_id = user_id)
            if description:
                query = query.filter_by(description = description)
            for habit in query.all():
                total_habits += 1
                if (habit.done):
                    completed_habits += 1
            current_day_in_week += timedelta(days=1)
    elif (time_period == "month"):
        start_of_month = requested_date.replace(day = 1)
        current_day_in_month = start_of_month
        days_in_month = calendar.monthrange(requested_date.year, requested_date.month)[1]

        for i in range(days_in_month):
            query = Habit.query.filter_by(date=current_day_in_month, user_id = user_id)
            if description:
                query = query.filter_by(description = description)
            for habit in query.all():
                total_habits += 1
                if (habit.done):
                    completed_habits += 1
            current_day_in_month += timedelta(days=1)
        
    elif (time_period == "year"):
        start_of_year = requested_date.replace(month = 1, day = 1)
        current_day_in_year = start_of_year
        days_in_year = 366 if calendar.isleap(requested_date.year) else 365

        for i in range(days_in_year):
            query = Habit.query.filter_by(date=current_day_in_year, user_id = user_id)
            if description:
                query = query.filter_by(description = description)
            for habit in query.all():
                total_habits += 1
                if (habit.done):
                    completed_habits += 1
            current_day_in_year += timedelta(days=1)
    else:
        return failure_response("Invalid time period")
    
    percentage_done = ((completed_habits / total_habits) * 100) if (total_habits > 0) else 0

    return success_response({"total_habits" : total_habits, "completed_habits" : completed_habits, "percentage" : percentage_done})
    




@statistic_routes.route("/stats/stopwatches/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_stopwatchs_stats(date_string, time_period):
    """
    Endpoint for getting statistics on stopwatches. returns time in milliseconds.
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)
    total_time_worked = 0
    average_time_worked_per_day = 0
    total_goal_time = 0
    days_with_data = 0
    title = request.args.get("title")

    if (time_period == "day"):
        if title:
            stopwatch = Stopwatch.query.filter_by(date = requested_date, title = title, user_id = user_id).first()
        else:
            stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
        if stopwatch:
            total_time_worked = stopwatch.curr_duration
            total_goal_time = stopwatch.goal_time
    elif (time_period == "week"):
        start_of_week = requested_date - timedelta(days = requested_date.weekday())
        current_day_in_week = start_of_week
        days_in_week = 7

        for i in range(days_in_week):
            if current_day_in_week > date.today():
                break
            if title:
                stopwatch = Stopwatch.query.filter_by(date = current_day_in_week, title = title, user_id = user_id).first()
            else:
                stopwatch = Stopwatch.query.filter_by(date = current_day_in_week, isTotal = True, user_id = user_id).first()
            if stopwatch:
                total_time_worked += stopwatch.curr_duration
                total_goal_time += stopwatch.goal_time
                days_with_data += 1
            current_day_in_week += timedelta(days=1)

    elif (time_period == "month"):
        start_of_month = requested_date.replace(day = 1)
        current_day_in_month = start_of_month
        days_in_month = calendar.monthrange(requested_date.year, requested_date.month)[1]

        for i in range(days_in_month):
            if current_day_in_month > date.today():
                break
            if title:
                stopwatch = Stopwatch.query.filter_by(date = current_day_in_month, title = title, user_id = user_id).first()
            else:
                stopwatch = Stopwatch.query.filter_by(date = current_day_in_month, isTotal = True, user_id = user_id).first()
            if stopwatch:
                total_time_worked += stopwatch.curr_duration
                total_goal_time += stopwatch.goal_time
                days_with_data += 1
            current_day_in_month += timedelta(days=1)
        
    elif (time_period == "year"):
        start_of_year = requested_date.replace(month = 1, day = 1)
        current_day_in_year = start_of_year
        days_in_year = 366 if calendar.isleap(requested_date.year) else 365

        for i in range(days_in_year):
            if current_day_in_year > date.today():
                break
            if title:
                stopwatch = Stopwatch.query.filter_by(date = current_day_in_year, title = title, user_id = user_id).first()
            else:
                stopwatch = Stopwatch.query.filter_by(date = current_day_in_year, isTotal = True, user_id = user_id).first()
            if stopwatch:
                total_time_worked += stopwatch.curr_duration 
                total_goal_time += stopwatch.goal_time
                days_with_data += 1
            current_day_in_year += timedelta(days=1)
                
    else:
        return failure_response("Invalid time period")
    
    average_time_worked_per_day = total_time_worked / days_with_data if days_with_data > 0 else total_time_worked
    return success_response({"total_time_worked" : total_time_worked, "average_time_worked_per_day" : average_time_worked_per_day, "total_goal_time" : total_goal_time})


@statistic_routes.route("/stats/stopwatches/breakdown/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_stopwatches_breakdown(date_string, time_period):
    """
    Endpoint for getting the per-stopwatch time breakdown over a period.
    Returns a list of {title, duration} (milliseconds), excluding the Total stopwatch.
    Shared source for the pie chart / per-item period stats (specs 0015/0016/0017).
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    if (time_period == "day"):
        start_day = requested_date
        num_days = 1
    elif (time_period == "week"):
        start_day = requested_date - timedelta(days = requested_date.weekday())
        num_days = 7
    elif (time_period == "month"):
        start_day = requested_date.replace(day = 1)
        num_days = calendar.monthrange(requested_date.year, requested_date.month)[1]
    elif (time_period == "year"):
        start_day = requested_date.replace(month = 1, day = 1)
        num_days = 366 if calendar.isleap(requested_date.year) else 365
    else:
        return failure_response("Invalid time period")

    durations = {}
    current_day = start_day
    for i in range(num_days):
        if current_day > date.today() and time_period != "day":
            break
        for stopwatch in Stopwatch.query.filter_by(date = current_day, isTotal = False, user_id = user_id).all():
            durations[stopwatch.title] = durations.get(stopwatch.title, 0) + stopwatch.curr_duration
        current_day += timedelta(days=1)

    breakdown = [{"title" : title, "duration" : duration} for title, duration in durations.items()]
    return success_response({"breakdown" : breakdown})



    