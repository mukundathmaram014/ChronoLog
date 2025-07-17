from flask import Blueprint
from utils import success_response, failure_response, process_date
import json
from db import db
from flask import Flask, request
from db import Stopwatch, DeletedDay
from datetime import datetime, date, timedelta
from sqlalchemy import func


stopwatch_routes = Blueprint('stopwatch', __name__)

def create_stopwatch_for_date(requested_date, title, start_time, goal_time):
    stopwatches = []
    new_stopwatch = Stopwatch(title = title, start_time = start_time , date = requested_date, goal_time = goal_time)

    if Stopwatch.query.filter_by(date=requested_date).first() is None:
        # creating total time stopwatch
        total_stopwatch = Stopwatch(title = "Total Time", start_time = datetime.now(), date = requested_date, isTotal = True, goal_time = goal_time)
        db.session.add(total_stopwatch)
        db.session.commit()
    else:
        # adds to total stopwatch's goal time if already exists
        total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True).first()
        total_stopwatch.goal_time = total_stopwatch.goal_time + goal_time
        db.session.commit()

    db.session.add(new_stopwatch)
    db.session.commit()
    stopwatches.append(total_stopwatch.serialize())
    stopwatches.append(new_stopwatch.serialize())
    return stopwatches

#only converts when in form HH:MM
def convert_time_string_to_milliseconds(time_string):
    goal_time_milli = (int(time_string[0:2]) * 3600000) + (int(time_string[3:5]) * 60000) # 3600000 milliseconds in an hour and 60000 milliseconds in a minute
    return goal_time_milli

@stopwatch_routes.route("/")
def test():
    return success_response("hello worldhh")

@stopwatch_routes.route("/stopwatches/<string:date_string>/")
def get_stopwatches(date_string):
    """
    Endpoint for getting all stopwatches for a specified date
    """
    requested_date = date.fromisoformat(date_string)
    stopwatches = []

    for stopwatch in Stopwatch.query.filter_by(date=requested_date).all():
        stopwatches.append(stopwatch.serialize())
    
    # gets previous days stopwatches if empty and date is today
    if not stopwatches:
        deleted_marker = DeletedDay.query.filter_by(date=requested_date, type = "stopwatch").first()
        #dosent repopulate if user intentionally deleted everything
        if not deleted_marker:
            earliest_date = db.session.query(func.min(Stopwatch.date)).scalar()
            prev_date = requested_date - timedelta(days=1)
            prev_stopwatches = []
            # keeps going back until finds day with non empty stopwatches list
            if earliest_date:
                while (len(prev_stopwatches) <= 1) and (prev_date >= earliest_date):
                    prev_stopwatches = Stopwatch.query.filter_by(date=prev_date).all()
                    prev_date = prev_date - timedelta(days=1)

            new_stopwatches = []

            for prev_stopwatch in prev_stopwatches:
                if not prev_stopwatch.isTotal:
                    stopwatches = create_stopwatch_for_date(requested_date=requested_date, title = prev_stopwatch.title, start_time= prev_stopwatch.start_time, goal_time= prev_stopwatch.goal_time)
         
                    #only adds total stopwatch once
                    if not total_added:
                        new_stopwatches.append(stopwatches[0])
                        total_added = True
                    new_stopwatches.append(stopwatches[1])
            
            db.session.commit()
            stopwatches = new_stopwatches


    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/", methods = ["POST"])
def create_stopwatch():
    """
    Endpoint for creating a stopwatch
    """

    body = json.loads(request.data)
    requested_date = process_date(request)
    stopwatches = []

    goal_time_string = body.get("goal_time", "01:00") # goal time defaults to one hour
    goal_time_milli = convert_time_string_to_milliseconds(goal_time_string)

    stopwatches = create_stopwatch_for_date(requested_date=requested_date, title= body.get("title", ""), start_time= body.get("start_time", datetime.now()), goal_time= goal_time_milli) 
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/<int:stopwatch_id>/")
def get_stopwatch(stopwatch_id):
    """
    Endpoint for getting a stopwatch by id
    """

    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    return success_response(stopwatch.serialize())

@stopwatch_routes.route("/stopwatches/<int:stopwatch_id>/", methods = ["PUT"])
def update_stopwatch(stopwatch_id):
    """
    Endpoint for updating a stopwatch by id
    """

    body = json.loads(request.data)
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    stopwatch.title = body.get("title", stopwatch.title)
    stopwatch.start_time = body.get("start_time", stopwatch.start_time)
    stopwatch.interval_start = body.get("interval_start", stopwatch.interval_start)
    stopwatch.end_time = body.get("end_time", stopwatch.end_time)

    new_duration = body.get("curr_duration", stopwatch.curr_duration)
    change_in_duration = new_duration - stopwatch.curr_duration
    stopwatch.curr_duration = new_duration

    stopwatch.date = body.get("date", date.today())
    stopwatch.isTotal = body.get("isTotal", stopwatch.isTotal)
    goal_time_string = body.get("goal_time")

    new_goal_time = convert_time_string_to_milliseconds(goal_time_string) if goal_time_string else stopwatch.goal_time
    change_in_goal_time = new_goal_time - stopwatch.goal_time
    stopwatch.goal_time = new_goal_time

    # updates total stopwatch with changes
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True).first()
    total_stopwatch.curr_duration = total_stopwatch.curr_duration + change_in_duration
    total_stopwatch.goal_time = total_stopwatch.goal_time + change_in_goal_time
    db.session.commit()
    
    stopwatches = [total_stopwatch.serialize(), stopwatch.serialize()]
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/<int:stopwatch_id>/", methods = ["DELETE"])
def delete_stopwatch(stopwatch_id):
    """
    Endpoint for deleting a stopwatch by id
    """
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True).first()
    if (stopwatch.end_time is None):
        total_stopwatch.end_time = datetime.now() #stops total stopwatch if stopwatch being deleted was running
    total_stopwatch.curr_duration = total_stopwatch.curr_duration - stopwatch.curr_duration
    total_stopwatch.goal_time = total_stopwatch.goal_time - stopwatch.goal_time
    db.session.delete(stopwatch)
    db.session.commit()

    # checks if day is a deleted day (intentionally made empty)
    remaining_stopwatches = Stopwatch.query.filter_by(date=requested_date).all()
    # only total stopwatch remains
    if (len(remaining_stopwatches) == 1):
        deleted_marker = DeletedDay(date=requested_date, type = "stopwatch")
        db.session.add(deleted_marker)
        db.session.commit()
    
    stopwatches = []
    stopwatches.append(total_stopwatch.serialize())
    stopwatches.append(stopwatch.serialize())
    
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/stop/<int:stopwatch_id>/", methods = ["PATCH", "POST"])
def stop_stopwatch(stopwatch_id):
    """
    Endpoint for stopping a stopwatch by id.
    """

    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True).first()
    total_stopwatch.end_time = stopwatch.end_time = datetime.now()
    increment = (stopwatch.end_time - stopwatch.interval_start).total_seconds() * 1000
    stopwatch.curr_duration = stopwatch.curr_duration + increment
    total_stopwatch.curr_duration = total_stopwatch.curr_duration + increment
    db.session.commit()

    stopwatches = []
    stopwatches.append(total_stopwatch.serialize())
    stopwatches.append(stopwatch.serialize())
    
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/start/<int:stopwatch_id>/", methods = ["PATCH"])
def start_stopwatch(stopwatch_id):
    """
    Endpoint for starting a stopwatch by id.
    """
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True).first()
    now = datetime.now()
    total_stopwatch.interval_start = stopwatch.interval_start = now
    total_stopwatch.end_time = stopwatch.end_time = None
    db.session.commit()

    stopwatches = []
    stopwatches.append(total_stopwatch.serialize())
    stopwatches.append(stopwatch.serialize())
    
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/reset/<int:stopwatch_id>/", methods = ["PATCH"])
def reset_stopwatch(stopwatch_id):
    """
    Endpoint for starting a stopwatch by id.
    """
    body = json.loads(request.data)
    state = body.get("state")
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True).first()
    if (state == None):
        total_stopwatch.end_time = stopwatch.end_time = datetime.now()
    total_stopwatch.curr_duration = total_stopwatch.curr_duration - stopwatch.curr_duration
    stopwatch.curr_duration = 0.0
    db.session.commit()

    stopwatches = []
    stopwatches.append(total_stopwatch.serialize())
    stopwatches.append(stopwatch.serialize())
    
    
    return success_response({"stopwatches" : stopwatches})