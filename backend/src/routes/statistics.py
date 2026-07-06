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


def get_period_range(requested_date, time_period):
    """
    Returns (start_day, num_days) for the period containing requested_date,
    or None if time_period is invalid. Shared by the period-aware stats
    endpoints (specs 0015/0016/0017).
    """

    if (time_period == "day"):
        return (requested_date, 1)
    elif (time_period == "week"):
        return (requested_date - timedelta(days = requested_date.weekday()), 7)
    elif (time_period == "month"):
        return (requested_date.replace(day = 1), calendar.monthrange(requested_date.year, requested_date.month)[1])
    elif (time_period == "year"):
        return (requested_date.replace(month = 1, day = 1), 366 if calendar.isleap(requested_date.year) else 365)
    else:
        return None


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
            if current_day_in_week > date.today():
                break
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
            if current_day_in_month > date.today():
                break
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
            if current_day_in_year > date.today():
                break
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

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range

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


@statistic_routes.route("/stats/items/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_period_items(date_string, time_period):
    """
    Endpoint for getting the distinct habits and stopwatches that existed on any
    day within the selected period, for populating the stats selector (spec 0017).
    Stopwatches exclude the per-day Total rows; a single "Total Time" entry is
    prepended instead (the frontend maps it to the no-filter query).
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range
    end_day = start_day + timedelta(days = num_days - 1)

    habit_rows = Habit.query.with_entities(Habit.description).filter(
        Habit.user_id == user_id,
        Habit.date >= start_day,
        Habit.date <= end_day,
    ).distinct().all()
    habits = sorted(row.description for row in habit_rows)

    stopwatch_rows = Stopwatch.query.with_entities(Stopwatch.title).filter(
        Stopwatch.user_id == user_id,
        Stopwatch.isTotal == False,
        Stopwatch.date >= start_day,
        Stopwatch.date <= end_day,
    ).distinct().all()
    stopwatches = ["Total Time"] + sorted(row.title for row in stopwatch_rows)

    return success_response({"habits" : habits, "stopwatches" : stopwatches})



    

@statistic_routes.route("/stats/habits/all/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_habits_all(date_string, time_period):
    """
    Combined habits view (spec 0016): the aggregate total plus per-habit stats
    for the selected date + period, in one request. Shares the period walk with
    the other 0015/0016/0017 stats endpoints.
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range

    per = {}  # description -> [total, completed]
    total_all = 0
    completed_all = 0
    current_day = start_day
    for i in range(num_days):
        if current_day > date.today() and time_period != "day":
            break
        for habit in Habit.query.filter_by(date = current_day, user_id = user_id).all():
            counts = per.setdefault(habit.description, [0, 0])
            counts[0] += 1
            total_all += 1
            if habit.done:
                counts[1] += 1
                completed_all += 1
        current_day += timedelta(days = 1)

    items = []
    for description in sorted(per):
        total_habits, completed_habits = per[description]
        items.append({
            "description": description,
            "total_habits": total_habits,
            "completed_habits": completed_habits,
            "percentage": (completed_habits / total_habits * 100) if total_habits > 0 else 0,
        })
    total = {
        "total_habits": total_all,
        "completed_habits": completed_all,
        "percentage": (completed_all / total_all * 100) if total_all > 0 else 0,
    }
    return success_response({"total": total, "items": items})


@statistic_routes.route("/stats/stopwatches/all/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_stopwatches_all(date_string, time_period):
    """
    Combined stopwatches view (spec 0016): the aggregate Total plus per-stopwatch
    time worked / goal for the selected date + period, in one request.
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range

    per = {}  # title -> [duration, goal]
    total_time = 0
    total_goal = 0
    days_with_data = 0
    current_day = start_day
    for i in range(num_days):
        if current_day > date.today() and time_period != "day":
            break
        total_row = Stopwatch.query.filter_by(date = current_day, isTotal = True, user_id = user_id).first()
        if total_row:
            total_time += total_row.curr_duration
            total_goal += total_row.goal_time
            days_with_data += 1
        for stopwatch in Stopwatch.query.filter_by(date = current_day, isTotal = False, user_id = user_id).all():
            counts = per.setdefault(stopwatch.title, [0, 0])
            counts[0] += stopwatch.curr_duration
            counts[1] += stopwatch.goal_time
        current_day += timedelta(days = 1)

    items = [
        {"title": title, "total_time_worked": duration, "total_goal_time": goal}
        for title, (duration, goal) in sorted(per.items())
    ]
    total = {
        "total_time_worked": total_time,
        "total_goal_time": total_goal,
        "average_time_worked_per_day": (total_time / days_with_data) if days_with_data > 0 else total_time,
    }
    return success_response({"total": total, "items": items})


@statistic_routes.route("/stats/habits/calendar/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_habits_calendar(date_string, time_period):
    """
    Per-day habit calendar over the selected window (spec 0016). Read-only over
    existing Habit rows; a single pass over the period.

    - ?description=<habit>  -> single-habit STATUS: {mode:"status", start, days:[{date, status}]}
      status in {done, missed, not-scheduled, no-data}, classified from the row's
      `done` flag and its `repeat_days` weekday bit.
    - no description        -> Total INTENSITY: {mode:"intensity", start, days:[{date, completed, scheduled}]}
      counts over all the user's habits scheduled that date; frontend derives
      intensity = completed / scheduled (scheduled == 0 renders neutral).
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range
    description = request.args.get("description")

    days = []
    current_day = start_day
    for i in range(num_days):
        weekday_bit = 1 << current_day.weekday()
        if description:
            habit = Habit.query.filter_by(
                date = current_day, description = description, user_id = user_id).first()
            if habit is None:
                status = "no-data"
            elif not (habit.repeat_days & weekday_bit):
                status = "not-scheduled"
            elif habit.done:
                status = "done"
            else:
                status = "missed"
            days.append({"date": current_day.isoformat(), "status": status})
        else:
            scheduled = 0
            completed = 0
            for habit in Habit.query.filter_by(date = current_day, user_id = user_id).all():
                if habit.repeat_days & weekday_bit:
                    scheduled += 1
                    if habit.done:
                        completed += 1
            days.append({"date": current_day.isoformat(), "scheduled": scheduled, "completed": completed})
        current_day += timedelta(days = 1)

    return success_response({
        "mode": "status" if description else "intensity",
        "start": start_day.isoformat(),
        "days": days,
    })
