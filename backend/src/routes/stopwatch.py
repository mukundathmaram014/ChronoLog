from flask import Blueprint
from utils import success_response, failure_response, process_date
import json
from db import db
from flask import Flask, request
from db import Stopwatch
from datetime import datetime, date


stopwatch_routes = Blueprint('stopwatch', __name__)

@stopwatch_routes.route("/")
def test():
    return success_response("hello worldhh")

@stopwatch_routes.route("/stopwatches/<string:date_string>/")
def get_stopwatches(date_string):
    """
    Endpoint for getting all stopwatches
    """
    requested_date = date.fromisoformat(date_string)
    stopwatches = []

    for stopwatch in Stopwatch.query.filter_by(date=requested_date).all():
        stopwatches.append(stopwatch.serialize())
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/", methods = ["POST"])
def create_stopwatch():
    """
    Endpoint for creating a stopwatch
    """

    body = json.loads(request.data)
    requested_date = process_date(request)
    new_stopwatch = Stopwatch(title = body.get("title", ""), start_time = body.get("start_time", datetime.now()), date = requested_date)
    stopwatches = []
    
    # check if any stopwatches exist for this day
    if Stopwatch.query.filter_by(date=requested_date).first() is None:
        # creating total time stopwatch
        total_stopwatch = Stopwatch(title = "Total Time", start_time = datetime.now(), date = requested_date, isTotal = True)
        db.session.add(total_stopwatch)
        stopwatches.append(total_stopwatch.serialize())
    else:
        stopwatches.append(None)
    db.session.add(new_stopwatch)
    db.session.commit()
    stopwatches.append(new_stopwatch.serialize())
    
    
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
    stopwatch.curr_duration = body.get("curr_duration", stopwatch.curr_duration)
    stopwatch.date = body.get("date", date.today())
    stopwatch.isTotal = body.get("isTotal", stopwatch.isTotal)
    db.session.commit()
    return success_response(stopwatch.serialize())

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
        total_stopwatch.end_time = datetime.now()
    total_stopwatch.curr_duration = total_stopwatch.curr_duration - stopwatch.curr_duration
    db.session.delete(stopwatch)
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