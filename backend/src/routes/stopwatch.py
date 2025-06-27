from flask import Blueprint
from utils import success_response, failure_response
import json
from db import db
from flask import Flask, request
from db import Stopwatch
from datetime import datetime


stopwatch_routes = Blueprint('stopwatch', __name__)

@stopwatch_routes.route("/")
def test():
    return success_response("hello worldhh")

@stopwatch_routes.route("/stopwatches/")
def get_stopwatches():
    """
    Endpoint for getting all stopwatches
    """
    stopwatches = []

    for stopwatch in Stopwatch.query.all():
        stopwatches.append(stopwatch.serialize())
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/", methods = ["POST"])
def create_stopwatch():
    """
    Endpoint for creating a stopwatch
    """

    body = json.loads(request.data)
    new_stopwatch = Stopwatch(title = body.get("title", ""), start_time = body.get("start_time", datetime.now()))
    db.session.add(new_stopwatch)
    db.session.commit()
    return success_response(new_stopwatch.serialize(), 201)

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
    db.session.delete(stopwatch)
    db.session.commit()
    return success_response(stopwatch.serialize())

@stopwatch_routes.route("/stopwatches/stop/<int:stopwatch_id>/", methods = ["PATCH", "POST"])
def stop_stopwatch(stopwatch_id):
    """
    Endpoint for stopping a stopwatch by id.
    """
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    stopwatch.end_time = datetime.now()
    increment = stopwatch.end_time - stopwatch.interval_start
    stopwatch.curr_duration = stopwatch.curr_duration + (increment.total_seconds() * 1000)
    db.session.commit()
    return success_response(stopwatch.serialize())

@stopwatch_routes.route("/stopwatches/start/<int:stopwatch_id>/", methods = ["PATCH"])
def start_stopwatch(stopwatch_id):
    """
    Endpoint for starting a stopwatch by id.
    """
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    stopwatch.interval_start = datetime.now()
    stopwatch.end_time = None
    db.session.commit()
    return success_response(stopwatch.serialize())

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
    if (state == None):
        stopwatch.end_time = datetime.now()
    stopwatch.curr_duration = 0.0
    db.session.commit()
    return success_response(stopwatch.serialize())