from flask import Blueprint
from utils import success_response, failure_response, process_date, ensure_utc, validate_repeat_days
import json
from db import db
from flask import Flask, request
from db import Stopwatch, DeletedDay, StopwatchInterval
from datetime import datetime, date, timedelta, timezone
from sqlalchemy import func
from flask_jwt_extended import jwt_required, get_jwt_identity
from xp import recompute_from


stopwatch_routes = Blueprint('stopwatch', __name__)

def create_stopwatch_for_date(requested_date, title, start_time, goal_time, user_id, is_recurring = True, repeat_days = 127):

    duplicate = Stopwatch.query.filter_by(title = title, date = requested_date, user_id = user_id).first()
    if duplicate is not None:
        return failure_response("Stopwatch already exists for this day", 409)
    stopwatches = []
    # new rows append at the end of that day's list (the Total is excluded from ordering)
    max_position = db.session.query(func.max(Stopwatch.position)).filter(Stopwatch.user_id == user_id, Stopwatch.date == requested_date, Stopwatch.isTotal == False).scalar()
    position = 0 if max_position is None else max_position + 1
    new_stopwatch = Stopwatch(title = title, start_time = start_time , date = requested_date, goal_time = goal_time, user_id = user_id, is_recurring = is_recurring, repeat_days = repeat_days, position = position)

    if Stopwatch.query.filter_by(date=requested_date, user_id = user_id).first() is None:
        # creating total time stopwatch
        total_stopwatch = Stopwatch(title = "Total Time", start_time = datetime.now(timezone.utc), date = requested_date, isTotal = True, goal_time = goal_time, user_id = user_id)
        db.session.add(total_stopwatch)
        db.session.commit()
    else:
        # adds to total stopwatch's goal time if already exists, unless the user
        # has manually overridden the Total's goal (spec 0023)
        total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
        if not total_stopwatch.goal_overridden:
            total_stopwatch.goal_time = total_stopwatch.goal_time + goal_time
        db.session.commit()

    db.session.add(new_stopwatch)
    db.session.commit()
    stopwatches.append(total_stopwatch.serialize())
    stopwatches.append(new_stopwatch.serialize())
    return stopwatches

def finalize_stale_stopwatches(user_id):
    """
    Freeze any stopwatch left running on a past day (e.g. the tab closed before
    the pagehide stop landed): set end_time = interval_start so curr_duration is
    left unchanged and no overnight time is credited. The Total starts/stops in
    lockstep with its child, so it gets frozen by the same sweep, keeping the
    pair consistent. No curr_duration changes, so the day's work XP is already
    correct — recompute_from must not be called here.
    """
    stale_stopwatches = Stopwatch.query.filter(
        Stopwatch.user_id == user_id,
        Stopwatch.end_time.is_(None),
        Stopwatch.date < date.today(),
    ).all()
    for stopwatch in stale_stopwatches:
        stopwatch.end_time = ensure_utc(stopwatch.interval_start)
    if stale_stopwatches:
        db.session.commit()

#only converts when in form HH:MM
def convert_time_string_to_milliseconds(time_string):
    goal_time_milli = (int(time_string[0:2]) * 3600000) + (int(time_string[3:5]) * 60000) # 3600000 milliseconds in an hour and 60000 milliseconds in a minute
    return goal_time_milli

@stopwatch_routes.route("/")
def test():
    return success_response("hello worldhh")

@stopwatch_routes.route("/stopwatches/titles/")
@jwt_required()
def get_previous_stopwatch_titles():
    """
    Endpoint for getting the user's distinct prior stopwatch titles (+ most recent
    goal time and repeat days), most-recent first, to feed the add-form
    "reuse previous" dropdown
    """
    user_id = int(get_jwt_identity())
    rows = (Stopwatch.query
            .filter_by(user_id = user_id, isTotal = False)
            .order_by(Stopwatch.date.desc(), Stopwatch.id.desc())
            .all())
    seen = set()
    titles = []
    for stopwatch in rows:
        if stopwatch.title not in seen:
            seen.add(stopwatch.title)
            titles.append({"title": stopwatch.title, "goal_time": stopwatch.goal_time, "repeat_days": stopwatch.repeat_days})
    return success_response({"titles": titles})

@stopwatch_routes.route("/stopwatches/<string:date_string>/")
@jwt_required()
def get_stopwatches(date_string):
    """
    Endpoint for getting all stopwatches for a specified date
    """
    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    # stopwatches stranded running on earlier days would otherwise accrue forever
    finalize_stale_stopwatches(user_id)

    # Total first, then the user's saved order (spec 0003)
    day_stopwatches = Stopwatch.query.filter_by(date=requested_date, user_id = user_id).order_by(Stopwatch.isTotal.desc(), Stopwatch.position, Stopwatch.id).all()
    stopwatches = [stopwatch.serialize() for stopwatch in day_stopwatches]

    # gets previous days stopwatches if the day has no regular ones — either
    # truly empty or holding only a leftover Total
    if all(stopwatch.isTotal for stopwatch in day_stopwatches):
        deleted_marker = DeletedDay.query.filter_by(date=requested_date, type = "stopwatch", user_id = user_id).first()
        #dosent repopulate if user intentionally deleted everything
        if not deleted_marker:
            earliest_date = db.session.query(func.min(Stopwatch.date)).filter(Stopwatch.user_id == user_id).scalar()

            # walks back to the most recent day holding regular (non-Total) stopwatches, then
            # keeps scanning up to 7 more days (one full weekday cycle) so stopwatches whose
            # repeat days skip that day arent lost. collects the most recent row per title;
            # stops at a deleted day
            candidates = {}
            first_filled_date = None
            if earliest_date:
                prev_date = requested_date
                while prev_date > earliest_date:
                    prev_date = prev_date - timedelta(days=1)
                    if first_filled_date and (first_filled_date - prev_date).days >= 7:
                        break
                    # Stop if a deleted day is found
                    prev_deleted = DeletedDay.query.filter_by(date=prev_date, type="stopwatch", user_id = user_id).first()
                    if prev_deleted:
                        break
                    day_rows = Stopwatch.query.filter_by(date=prev_date, user_id = user_id).order_by(Stopwatch.isTotal.desc(), Stopwatch.position, Stopwatch.id).all()
                    regulars = [row for row in day_rows if not row.isTotal]
                    if regulars and first_filled_date is None:
                        first_filled_date = prev_date
                    for row in regulars:
                        if row.title not in candidates:
                            candidates[row.title] = row

            # only recurring stopwatches carry forward; a non-recurring one is one-off
            # and its repeat_days is ignored
            carried = []
            for prev_stopwatch in candidates.values():
                if not prev_stopwatch.is_recurring:
                    continue

                # a scheduled day after the stopwatch's last row (up to the most recent
                # filled day) with no row means the user deleted it there — dont carry it
                was_deleted = False
                check_date = prev_stopwatch.date + timedelta(days=1)
                while check_date <= first_filled_date:
                    if prev_stopwatch.repeat_days & (1 << check_date.weekday()):
                        was_deleted = True
                        break
                    check_date += timedelta(days=1)
                if not was_deleted:
                    carried.append(prev_stopwatch)

            # create_stopwatch_for_date adds each carried goal onto an existing
            # Total, so zero a leftover Total's goal first — a non-overridden
            # Total goal is the sum of the day's stopwatch goals, and this day
            # has none yet. Only zero it if something actually lands today.
            landing_today = [prev_stopwatch for prev_stopwatch in carried
                             if prev_stopwatch.repeat_days & (1 << requested_date.weekday())]
            existing_total = next((stopwatch for stopwatch in day_stopwatches if stopwatch.isTotal), None)
            if landing_today and existing_total is not None and not existing_total.goal_overridden:
                existing_total.goal_time = 0

            new_stopwatches = []

            #repopulates today with previous days' stopwatches, gated by their repeat days
            for prev_stopwatch in carried:
                repeat_days = prev_stopwatch.repeat_days

                # repopulates days in between, skipping weekdays outside the repeat set
                temp_date = first_filled_date
                while (temp_date < (requested_date - timedelta(days=1))):
                    temp_date += timedelta(days=1)
                    if repeat_days & (1 << temp_date.weekday()):
                        create_stopwatch_for_date(requested_date=temp_date, title = prev_stopwatch.title, start_time= prev_stopwatch.start_time, goal_time= prev_stopwatch.goal_time, user_id = user_id, is_recurring = True, repeat_days = repeat_days)

                if repeat_days & (1 << requested_date.weekday()):
                    created = create_stopwatch_for_date(requested_date=requested_date, title = prev_stopwatch.title, start_time= prev_stopwatch.start_time, goal_time= prev_stopwatch.goal_time, user_id= user_id, is_recurring = True, repeat_days = repeat_days)
                    # a (body, code) failure tuple means a duplicate title — nothing was created
                    if not isinstance(created, tuple):
                        new_stopwatches.append(created[1])
            db.session.commit()
            if new_stopwatches:
                # serialize the Total once, after every carried goal is folded in
                total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
                stopwatches = [total_stopwatch.serialize()] + new_stopwatches


    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/intervals/<string:date_string>/")
@jwt_required()
def get_stopwatch_intervals(date_string):
    """
    Endpoint for getting a day's recorded stopwatch intervals (the session log),
    chronologically, each carrying its stopwatch's title
    """
    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    rows = (db.session.query(StopwatchInterval, Stopwatch.title)
            .join(Stopwatch, Stopwatch.id == StopwatchInterval.stopwatch_id)
            .filter(StopwatchInterval.user_id == user_id, StopwatchInterval.date == requested_date)
            .order_by(StopwatchInterval.start_time, StopwatchInterval.id)
            .all())

    intervals = [{
        "id": interval.id,
        "stopwatch_id": interval.stopwatch_id,
        "title": title,
        "start_time": ensure_utc(interval.start_time).isoformat(),
        "end_time": ensure_utc(interval.end_time).isoformat(),
    } for interval, title in rows]

    return success_response({"intervals": intervals})

@stopwatch_routes.route("/stopwatches/", methods = ["POST"])
@jwt_required()
def create_stopwatch():
    """
    Endpoint for creating a stopwatch
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    requested_date = process_date(request)
    stopwatches = []

    # goal time defaults to one hour; an explicit null means "no goal" (stored as 0)
    goal_time_raw = body.get("goal_time", "01:00")
    goal_time_milli = 0 if goal_time_raw is None else convert_time_string_to_milliseconds(goal_time_raw)

    repeat_days = body.get("repeat_days", 127)
    if not validate_repeat_days(repeat_days):
        return failure_response("repeat_days must be an integer between 1 and 127", 400)

    stopwatches = create_stopwatch_for_date(requested_date=requested_date, title= body.get("title", ""), start_time= body.get("start_time", datetime.now(timezone.utc)), goal_time= goal_time_milli, user_id=user_id, is_recurring= bool(body.get("is_recurring", True)), repeat_days= repeat_days)
    
    # If result is a failure response, return it directly
    if isinstance(stopwatches, tuple):
        return stopwatches
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/reorder/", methods=["PATCH"])
@jwt_required()
def reorder_stopwatches():
    """
    Endpoint for persisting a user's drag-reordering of a day's stopwatches.
    Body: {"date": "...", "order": [stopwatch ids in display order]}
    The Total stopwatch never participates: its id is ignored if sent.
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    requested_date = process_date(request)
    order = body.get("order")
    if not isinstance(order, list):
        return failure_response("order must be a list of stopwatch ids", 400)

    stopwatches = Stopwatch.query.filter_by(date=requested_date, isTotal=False, user_id = user_id).all()
    stopwatches_by_id = {stopwatch.id: stopwatch for stopwatch in stopwatches}
    for index, stopwatch_id in enumerate(order):
        stopwatch = stopwatches_by_id.get(stopwatch_id)
        if stopwatch is not None:
            stopwatch.position = index
    db.session.commit()

    stopwatches.sort(key=lambda stopwatch: (stopwatch.position, stopwatch.id))
    return success_response({"stopwatches": [stopwatch.serialize() for stopwatch in stopwatches]})

@stopwatch_routes.route("/stopwatches/<int:stopwatch_id>/")
@jwt_required()
def get_stopwatch(stopwatch_id):
    """
    Endpoint for getting a stopwatch by id
    """

    user_id = int(get_jwt_identity())
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id, user_id = user_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    return success_response(stopwatch.serialize())

@stopwatch_routes.route("/stopwatches/<int:stopwatch_id>/", methods = ["PUT"])
@jwt_required()
def update_stopwatch(stopwatch_id):
    """
    Endpoint for updating a stopwatch by id
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id, user_id = user_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")

    # validated up front so a bad mask rejects the whole edit; only applied to a
    # child row below (the Total has no meaningful repeat days)
    new_repeat_days = body.get("repeat_days", stopwatch.repeat_days)
    if not validate_repeat_days(new_repeat_days):
        return failure_response("repeat_days must be an integer between 1 and 127", 400)

    # dosent allow a duplicate stopwatch to be created
    new_title = body.get("title", stopwatch.title)
    if new_title != stopwatch.title:
        duplicate = Stopwatch.query.filter_by(title = new_title, date = stopwatch.date, user_id = user_id).first()
        if duplicate is not None:
            return failure_response("Stopwatch already exists for this day", 409)
    stopwatch.title = new_title
    
    stopwatch.start_time = body.get("start_time", stopwatch.start_time)
    stopwatch.interval_start = body.get("interval_start", stopwatch.interval_start)
    stopwatch.end_time = body.get("end_time", stopwatch.end_time)

    new_duration = body.get("curr_duration", stopwatch.curr_duration)
    change_in_duration = new_duration - stopwatch.curr_duration
    stopwatch.curr_duration = new_duration

    stopwatch.date = body.get("date", stopwatch.date)
    stopwatch.isTotal = body.get("isTotal", stopwatch.isTotal)

    requested_date = stopwatch.date

    # Editing the Total row itself: its goal becomes a manual override, unless the
    # request asks to match the sum of the individual stopwatch goals (spec 0023).
    if stopwatch.isTotal:
        if body.get("match_sum"):
            stopwatch.goal_overridden = False
            children = Stopwatch.query.filter_by(date = requested_date, isTotal = False, user_id = user_id).all()
            stopwatch.goal_time = sum(child.goal_time for child in children)
        elif "goal_time" in body:
            goal_time_raw = body["goal_time"]
            stopwatch.goal_time = 0 if goal_time_raw is None else convert_time_string_to_milliseconds(goal_time_raw)
            stopwatch.goal_overridden = True
        # a curr_duration edit on the Total still changes the day's work XP
        if change_in_duration != 0:
            recompute_from(user_id, requested_date)
        db.session.commit()
        return success_response({"stopwatches" : [stopwatch.serialize(), stopwatch.serialize()]})

    # Editing a child stopwatch: sync its goal/time into the Total.
    stopwatch.is_recurring = bool(body.get("is_recurring", stopwatch.is_recurring))
    # applies forward only: future carry-forward reads this value; past rows are untouched
    stopwatch.repeat_days = new_repeat_days

    # goal_time absent -> keep; explicit null -> "no goal" (0); else parse "HH:MM"
    if "goal_time" in body:
        goal_time_raw = body["goal_time"]
        new_goal_time = 0 if goal_time_raw is None else convert_time_string_to_milliseconds(goal_time_raw)
    else:
        new_goal_time = stopwatch.goal_time
    change_in_goal_time = new_goal_time - stopwatch.goal_time
    stopwatch.goal_time = new_goal_time

    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
    if total_stopwatch is None:
        return failure_response("Total stopwatch is not found")
    total_stopwatch.curr_duration = total_stopwatch.curr_duration + change_in_duration
    # only fold the child's goal into the Total while the Total isn't overridden
    if not total_stopwatch.goal_overridden:
        total_stopwatch.goal_time = total_stopwatch.goal_time + change_in_goal_time
    # the day's worked time changed, so its work XP changes
    if change_in_duration != 0:
        recompute_from(user_id, requested_date)
    db.session.commit()

    stopwatches = [total_stopwatch.serialize(), stopwatch.serialize()]
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/<int:stopwatch_id>/", methods = ["DELETE"])
@jwt_required()
def delete_stopwatch(stopwatch_id):
    """
    Endpoint for deleting a stopwatch by id
    """
    user_id = int(get_jwt_identity())
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id, user_id = user_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
    if (stopwatch.end_time is None):
        total_stopwatch.end_time = datetime.now(timezone.utc) #stops total stopwatch if stopwatch being deleted was running
    total_stopwatch.curr_duration = total_stopwatch.curr_duration - stopwatch.curr_duration
    # only remove the child's goal from the Total while the Total isn't overridden
    if not total_stopwatch.goal_overridden:
        total_stopwatch.goal_time = total_stopwatch.goal_time - stopwatch.goal_time
    db.session.delete(stopwatch)
    db.session.commit()

    # checks if day is a deleted day (intentionally made empty)
    remaining_stopwatches = Stopwatch.query.filter_by(date=requested_date, user_id = user_id).all()
    # only total stopwatch remains
    if (len(remaining_stopwatches) == 1):
        deleted_marker = DeletedDay(date=requested_date, type = "stopwatch", user_id = user_id)
        db.session.add(deleted_marker)
        db.session.commit()

    # the day's worked time changed, so its work XP changes
    if stopwatch.curr_duration != 0:
        recompute_from(user_id, requested_date)
        db.session.commit()

    stopwatches = [total_stopwatch.serialize(), stopwatch.serialize()]
    
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/stop/<int:stopwatch_id>/", methods = ["PATCH", "POST"])
@jwt_required()
def stop_stopwatch(stopwatch_id):
    """
    Endpoint for stopping a stopwatch by id.
    """

    user_id = int(get_jwt_identity())
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id, user_id = user_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
    total_stopwatch.end_time = stopwatch.end_time = datetime.now(timezone.utc)
    increment = (ensure_utc(stopwatch.end_time) - ensure_utc(stopwatch.interval_start)).total_seconds() * 1000
    stopwatch.curr_duration = stopwatch.curr_duration + increment
    total_stopwatch.curr_duration = total_stopwatch.curr_duration + increment

    # record the completed segment for the day's session log (spec 0030). The Total
    # starts/stops in lockstep with its child, so only children get rows. A zero-length
    # segment is what a stale-finalized stopwatch looks like — it credits no time and
    # must record nothing.
    if not stopwatch.isTotal and increment > 0:
        db.session.add(StopwatchInterval(
            stopwatch_id = stopwatch.id,
            user_id = user_id,
            date = stopwatch.date,
            start_time = ensure_utc(stopwatch.interval_start),
            end_time = ensure_utc(stopwatch.end_time),
        ))

    # the day's worked time changed, so its work XP changes
    recompute_from(user_id, requested_date)
    db.session.commit()

    stopwatches = [total_stopwatch.serialize(), stopwatch.serialize()]
    
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/start/<int:stopwatch_id>/", methods = ["PATCH"])
@jwt_required()
def start_stopwatch(stopwatch_id):
    """
    Endpoint for starting a stopwatch by id.
    """

    user_id = int(get_jwt_identity())
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id, user_id = user_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
    now = datetime.now(timezone.utc)
    total_stopwatch.interval_start = stopwatch.interval_start = now
    total_stopwatch.end_time = stopwatch.end_time = None
    db.session.commit()

    stopwatches = [total_stopwatch.serialize(), stopwatch.serialize()]
    
    
    return success_response({"stopwatches" : stopwatches})

@stopwatch_routes.route("/stopwatches/reset/<int:stopwatch_id>/", methods = ["PATCH"])
@jwt_required()
def reset_stopwatch(stopwatch_id):
    """
    Endpoint for starting a stopwatch by id.
    """
    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    state = body.get("state")
    stopwatch = Stopwatch.query.filter_by(id=stopwatch_id, user_id = user_id).first()
    if stopwatch is None:
        return failure_response("Stopwatch is not found")
    requested_date = stopwatch.date
    total_stopwatch = Stopwatch.query.filter_by(date = requested_date, isTotal = True, user_id = user_id).first()
    if (state == None):
        total_stopwatch.end_time = stopwatch.end_time = datetime.now(timezone.utc)
    # we dont need to update the current duration of the stopwatch when we stop it as if is running, total stopwatch is running
    # as well so differences between the two curr durations will be the same.
    total_stopwatch.curr_duration = total_stopwatch.curr_duration - stopwatch.curr_duration
    stopwatch.curr_duration = 0.0
    # the session log follows the total it explains: zeroing the day's time drops
    # that stopwatch's recorded segments for the day (spec 0030)
    StopwatchInterval.query.filter_by(stopwatch_id = stopwatch.id, date = stopwatch.date, user_id = user_id).delete()
    # the day's worked time changed, so its work XP changes
    recompute_from(user_id, requested_date)
    db.session.commit()

    stopwatches = [total_stopwatch.serialize(), stopwatch.serialize()]
    
    
    return success_response({"stopwatches" : stopwatches})