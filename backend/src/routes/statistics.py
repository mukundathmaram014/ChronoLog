from flask import Blueprint
from utils import success_response, failure_response
import json
from db import db
from flask import Flask, request
from db import Stopwatch
from db import Habit
from datetime import datetime, date, timedelta
import calendar


statistic_routes = Blueprint('statistics', __name__)

@statistic_routes.route("/")
def test():
    return success_response("hello worldww")

@statistic_routes.route("/stats/habits/<string:date_string>/<string:time_period>/")
def get_habits_stats(date_string, time_period):
    """
    Endpoint for getting statistics on habits
    """

    requested_date = date.fromisoformat(date_string)
    total_habits = 0
    completed_habits = 0

    if (time_period == "day"):
        for habit in Habit.query.filter_by(date=requested_date).all():
            total_habits += 1
            if (habit.done):
                completed_habits += 1
    elif (time_period == "week"):
        start_of_week = requested_date - timedelta(days = requested_date.weekday())
        current_day_in_week = start_of_week
        days_in_week = 7
        for i in range(days_in_week):
            for habit in Habit.query.filter_by(date=current_day_in_week).all():
                total_habits += 1
                if (habit.done):
                    completed_habits += 1
            current_day_in_week += timedelta(days=1)
    elif (time_period == "month"):
        start_of_month = requested_date.replace(day = 1)
        current_day_in_month = start_of_month
        days_in_month = calendar.monthrange(requested_date.year, requested_date.month)[1]

        for i in range(days_in_month):
            for habit in Habit.query.filter_by(date=current_day_in_month).all():
                total_habits += 1
                if (habit.done):
                    completed_habits += 1
            current_day_in_month += timedelta(days=1)
        
    elif (time_period == "year"):
        start_of_year = requested_date.replace(month = 1, day = 1)
        current_day_in_year = start_of_year
        days_in_year = 366 if calendar.isleap(requested_date.year) else 365

        for i in range(days_in_year):
            for habit in Habit.query.filter_by(date=current_day_in_year).all():
                total_habits += 1
                if (habit.done):
                    completed_habits += 1
            current_day_in_year += timedelta(days=1)
    else:
        return failure_response("Invalid time period")
    
    percentage_done = ((completed_habits / total_habits) * 100) if (total_habits > 0) else 0

    return success_response({"total_habits" : total_habits, "completed_habits" : completed_habits, "percentage" : percentage_done})
    




@statistic_routes.route("/stats/stopwatches/<string:date_string>/<string:time_period>/")
def get_stopwatchs_stats(date_string, time_period):
    """
    Endpoint for getting statistics on stopwatches. returns time in milliseconds.
    """

    requested_date = date.fromisoformat(date_string)
    total_time_worked = 0
    average_time_worked_per_day = 0
    days_with_data = 0

    if (time_period == "day"):
        total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True).first()
        total_time_worked = total_stopwatch.curr_duration if total_stopwatch else 0
        average_time_worked_per_day = total_time_worked
    elif (time_period == "week"):
        start_of_week = requested_date - timedelta(days = requested_date.weekday())
        current_day_in_week = start_of_week
        days_in_week = 7

        for i in range(days_in_week):
            if current_day_in_week > date.today():
                break
            total_stopwatch = Stopwatch.query.filter_by(date = current_day_in_week, isTotal = True).first()
            total_time_worked += total_stopwatch.curr_duration if total_stopwatch else 0
            current_day_in_week += timedelta(days=1)
            days_with_data += 1
    elif (time_period == "month"):
        start_of_month = requested_date.replace(day = 1)
        current_day_in_month = start_of_month
        days_in_month = calendar.monthrange(requested_date.year, requested_date.month)[1]

        for i in range(days_in_month):
            if current_day_in_month > date.today():
                break
            total_stopwatch = Stopwatch.query.filter_by(date = current_day_in_month, isTotal = True).first()
            total_time_worked += total_stopwatch.curr_duration if total_stopwatch else 0
            current_day_in_month += timedelta(days=1)
            days_with_data += 1
        
    elif (time_period == "year"):
        start_of_year = requested_date.replace(month = 1, day = 1)
        current_day_in_year = start_of_year
        days_in_year = 366 if calendar.isleap(requested_date.year) else 365

        for i in range(days_in_year):
            if current_day_in_year > date.today():
                break
            total_stopwatch = Stopwatch.query.filter_by(date = current_day_in_year, isTotal = True).first()
            total_time_worked += total_stopwatch.curr_duration if total_stopwatch else 0
            current_day_in_year += timedelta(days=1)
            days_with_data += 1
    else:
        return failure_response("Invalid time period")
    
    average_time_worked_per_day = total_time_worked / days_with_data if days_with_data > 0 else total_time_worked
    return success_response({"total_time_worked" : total_time_worked, "average_time_worked_per_day" : average_time_worked_per_day})



    