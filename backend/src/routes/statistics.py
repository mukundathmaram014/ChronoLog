from flask import Blueprint
from utils import success_response, failure_response, level_from_xp, rank_from_level, rank_visible
import json
from db import db
from flask import Flask, request
from db import Stopwatch
from db import Habit
from db import DailyXP, User, WeekNote
from datetime import datetime, date, timedelta
import calendar
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func
from xp import current_streak

statistic_routes = Blueprint('statistics', __name__)

MAX_WEEK_NOTE_LENGTH = 500


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


def client_today():
    """
    The user's local date from the ?today= param, or the server's date if it's
    missing or implausible. The server runs in UTC, so its date can be a day off
    from the user's -- which would count a day that hasn't started yet. Only
    accepted within a day of the server's date, the most any timezone differs.
    """

    server_today = date.today()
    try:
        today = date.fromisoformat(request.args.get("today", ""))
    except ValueError:
        return server_today
    return today if abs((today - server_today).days) <= 1 else server_today


def elapsed_tracked_days(user_id, start_day, num_days, today):
    """
    Calendar days of the period that have passed since the user started tracking
    time. A day with no stopwatch scheduled still counts: nothing was worked on
    it, so it belongs in a per-day average as a zero, not out of it.
    """

    return days_elapsed_since(first_tracked_day(user_id), start_day, num_days, today)


def first_tracked_day(user_id):
    """
    The earliest day the user has a Total stopwatch row, or None.
    """

    return db.session.query(func.min(Stopwatch.date)).filter(
        Stopwatch.user_id == user_id, Stopwatch.isTotal == True
    ).scalar()


def days_elapsed_since(first_day, start_day, num_days, today):
    if first_day is None:
        return 0
    begin = max(start_day, first_day)
    end = min(start_day + timedelta(days = num_days - 1), today)
    return max(0, (end - begin).days + 1)


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
    
    # a single stopwatch averages over the days it had a row, since it may only be
    # scheduled on some weekdays; the overall figure averages over every elapsed day
    if title:
        days_for_average = days_with_data
    else:
        start_day, num_days = get_period_range(requested_date, time_period)
        days_for_average = elapsed_tracked_days(user_id, start_day, num_days, client_today())
    average_time_worked_per_day = total_time_worked / days_for_average if days_for_average > 0 else total_time_worked
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
    current_day = start_day
    for i in range(num_days):
        if current_day > date.today() and time_period != "day":
            break
        total_row = Stopwatch.query.filter_by(date = current_day, isTotal = True, user_id = user_id).first()
        if total_row:
            total_time += total_row.curr_duration
            total_goal += total_row.goal_time
        for stopwatch in Stopwatch.query.filter_by(date = current_day, isTotal = False, user_id = user_id).all():
            counts = per.setdefault(stopwatch.title, [0, 0])
            counts[0] += stopwatch.curr_duration
            counts[1] += stopwatch.goal_time
        current_day += timedelta(days = 1)

    items = [
        {"title": title, "total_time_worked": duration, "total_goal_time": goal}
        for title, (duration, goal) in sorted(per.items())
    ]
    days_for_average = elapsed_tracked_days(user_id, start_day, num_days, client_today())
    total = {
        "total_time_worked": total_time,
        "total_goal_time": total_goal,
        "average_time_worked_per_day": (total_time / days_for_average) if days_for_average > 0 else total_time,
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


@statistic_routes.route("/stats/habits/calendar/all/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_habits_calendar_all(date_string, time_period):
    """
    Batch per-habit calendars over the selected window (spec 0029): the same
    status classification as the ?description= branch of get_habits_calendar,
    for every habit in the window, in one request instead of N.

    -> {start, habits: [{description, days: [{date, status}]}]}

    A single pass per day bucketed by description (same shape as get_habits_all);
    days where a habit has no row report "no-data", matching the single-habit
    route. Where a description has several rows on one day the first wins, again
    matching that route's `.first()`.
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range

    dates = []
    per = {}  # description -> {date_iso -> status}
    current_day = start_day
    for i in range(num_days):
        weekday_bit = 1 << current_day.weekday()
        day_iso = current_day.isoformat()
        dates.append(day_iso)
        for habit in Habit.query.filter_by(date = current_day, user_id = user_id).all():
            statuses = per.setdefault(habit.description, {})
            if day_iso in statuses:
                continue
            if not (habit.repeat_days & weekday_bit):
                statuses[day_iso] = "not-scheduled"
            elif habit.done:
                statuses[day_iso] = "done"
            else:
                statuses[day_iso] = "missed"
        current_day += timedelta(days = 1)

    habits = [
        {
            "description": description,
            "days": [{"date": d, "status": per[description].get(d, "no-data")} for d in dates],
        }
        for description in sorted(per)
    ]

    return success_response({"start": start_day.isoformat(), "habits": habits})


@statistic_routes.route("/stats/stopwatches/calendar/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_stopwatches_calendar(date_string, time_period):
    """
    Per-day Total time worked over the selected window (spec 0029). Read-only
    over existing Stopwatch rows; mirrors get_habits_calendar's period walk.

    -> {mode:"time", start, days:[{date, duration, goal}]}  (milliseconds)

    Days with no Total row report duration 0 / goal 0, which the frontend renders
    as a no-data cell. `curr_duration` is the stored duration — live elapsed time
    stays a frontend concern (CLAUDE.md), as in every other stats endpoint.
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range

    days = []
    current_day = start_day
    for i in range(num_days):
        total_row = Stopwatch.query.filter_by(
            date = current_day, isTotal = True, user_id = user_id).first()
        days.append({
            "date": current_day.isoformat(),
            "duration": total_row.curr_duration if total_row else 0,
            "goal": total_row.goal_time if total_row else 0,
        })
        current_day += timedelta(days = 1)

    return success_response({"mode": "time", "start": start_day.isoformat(), "days": days})


@statistic_routes.route("/stats/xp/<string:date_string>/<string:time_period>/")
@jwt_required()
def get_xp_stats(date_string, time_period):
    """
    Endpoint for the XP section of the statistics page (spec 0034): period
    total / average XP, best day, streak stats, the per-day series for the
    heatmap, and the source breakdown for the pie. Unlike the habit/stopwatch
    routes, this reads the persisted `DailyXP` ledger with a single range
    query instead of a per-day loop, since there's at most one row per
    user-day (see xp.recompute_from).
    """

    user_id = int(get_jwt_identity())
    requested_date = date.fromisoformat(date_string)

    period_range = get_period_range(requested_date, time_period)
    if period_range is None:
        return failure_response("Invalid time period")
    start_day, num_days = period_range
    end_day = start_day + timedelta(days = num_days - 1)

    rows = DailyXP.query.filter(
        DailyXP.user_id == user_id,
        DailyXP.date >= start_day,
        DailyXP.date <= end_day,
    ).all()
    by_date = {row.date: row for row in rows}

    # days_counted / totals only look at *elapsed* days -- a future day earning
    # 0 XP is missing data, not a real zero (unlike the "days" series below,
    # which covers the whole period so the heatmap grid stays complete)
    today = date.today()
    elapsed_end = min(end_day, today)
    days_counted = (elapsed_end - start_day).days + 1 if elapsed_end >= start_day else 0
    elapsed_rows = [row for row in rows if row.date <= elapsed_end]

    total_xp = sum(row.xp_earned for row in elapsed_rows)
    average_per_day = (total_xp / days_counted) if days_counted > 0 else 0

    best_day = None
    for row in elapsed_rows:
        if best_day is None or row.xp_earned > best_day.xp_earned:
            best_day = row

    qualified_days = sum(1 for row in elapsed_rows if row.streak > 0)
    longest_streak = max((row.streak for row in elapsed_rows), default=0)

    days = []
    current_day = start_day
    for i in range(num_days):
        row = by_date.get(current_day)
        days.append({"date": current_day.isoformat(), "xp": row.xp_earned if row else 0})
        current_day += timedelta(days = 1)

    user = db.session.get(User, user_id)
    total_user_xp = user.total_xp or 0
    progress = level_from_xp(total_user_xp)
    # Gate the rank the same way the level endpoint does (spec 0035): only
    # allowlisted accounts see it, so the stats page can't leak it either.
    level_obj = {
        "total_xp": total_user_xp,
        "level": progress["level"],
        "xp_into_level": progress["xp_into_level"],
        "xp_to_next": progress["xp_to_next"],
    }
    if rank_visible(user):
        level_obj["rank"] = rank_from_level(progress["level"])

    return success_response({
        "total": {"xp": total_xp, "average_per_day": average_per_day, "days_counted": days_counted},
        "best_day": {"date": best_day.date.isoformat(), "xp": best_day.xp_earned} if best_day else None,
        "streak": {
            "qualified_days": qualified_days,
            "longest": longest_streak,
            "current": current_streak(user_id, requested_date),
        },
        "breakdown": [
            {"source": "Habits", "xp": sum(row.habit_xp for row in elapsed_rows)},
            {"source": "Work", "xp": sum(row.work_xp for row in elapsed_rows)},
            {"source": "Goals", "xp": sum(row.goal_xp for row in elapsed_rows)},
            {"source": "Bonuses", "xp": sum(row.bonus_xp for row in elapsed_rows)},
        ],
        "days": days,
        "level": level_obj,
    })


def monday_of(day):
    return day - timedelta(days = day.weekday())


def overview_year_of(monday):
    """
    The year a week counts towards: the one holding its Thursday, so each week
    belongs to exactly one year and a week straddling New Year has most of its
    days in the year it's listed under.
    """

    return (monday + timedelta(days = 3)).year


def parse_week_start(value):
    """
    The date for a YYYY-MM-DD string if it's a Monday, otherwise None.
    """

    try:
        day = date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return day if day.weekday() == 0 else None


@statistic_routes.route("/stats/overview/<int:year>/")
@jwt_required()
def get_overview(year):
    """
    Endpoint for the Overview section: per-week habit completion, average time
    per day, XP and note for one year, plus the daily XP series for the curve.
    Reads each table once over the whole range rather than per day, since this
    covers up to 53 weeks.
    """

    user_id = int(get_jwt_identity())
    if year < 1 or year > 9998:
        return failure_response("Invalid year", 400)
    today = client_today()

    first_habit_day = db.session.query(func.min(Habit.date)).filter(Habit.user_id == user_id).scalar()
    first_time_day = first_tracked_day(user_id)
    first_days = [day for day in (first_habit_day, first_time_day) if day is not None]

    # Jan 4 is always in the year's first week, Dec 28 always in its last
    year_first_monday = monday_of(date(year, 1, 4))
    year_last_monday = monday_of(date(year, 12, 28))
    response = {
        "year": year,
        "axis_start": year_first_monday.isoformat(),
        "axis_end": (year_last_monday + timedelta(days = 6)).isoformat(),
        "years": [overview_year_of(monday_of(today))],
        "weeks": [],
        "xp_days": [],
    }
    if not first_days:
        return success_response(response)

    first_week = monday_of(min(first_days))
    response["years"] = list(range(overview_year_of(first_week), overview_year_of(monday_of(today)) + 1))

    range_start = max(year_first_monday, first_week)
    range_end = min(year_last_monday + timedelta(days = 6), today)
    if range_start > range_end:
        return success_response(response)

    habit_totals = {}  # date -> [total, completed]
    habit_rows = db.session.query(Habit.date, Habit.done).filter(
        Habit.user_id == user_id, Habit.date >= range_start, Habit.date <= range_end
    ).all()
    for day, done in habit_rows:
        counts = habit_totals.setdefault(day, [0, 0])
        counts[0] += 1
        if done:
            counts[1] += 1

    time_rows = db.session.query(Stopwatch.date, Stopwatch.curr_duration).filter(
        Stopwatch.user_id == user_id, Stopwatch.isTotal == True,
        Stopwatch.date >= range_start, Stopwatch.date <= range_end
    ).all()
    time_by_day = {day: duration for day, duration in time_rows}

    xp_rows = DailyXP.query.filter(DailyXP.user_id == user_id, DailyXP.date >= range_start).all()
    xp_by_day = {row.date: row.xp_earned for row in xp_rows}

    notes = {note.week_start: note.text for note in WeekNote.query.filter(
        WeekNote.user_id == user_id, WeekNote.week_start >= range_start, WeekNote.week_start <= range_end
    ).all()}

    monday = range_start
    while monday <= range_end:
        days = [monday + timedelta(days = i) for i in range(7)]
        total_habits = sum(habit_totals.get(day, [0, 0])[0] for day in days)
        completed_habits = sum(habit_totals.get(day, [0, 0])[1] for day in days)
        total_time = sum(time_by_day.get(day, 0) for day in days)
        days_for_average = days_elapsed_since(first_time_day, monday, 7, today)
        response["weeks"].append({
            "week_start": monday.isoformat(),
            "total_habits": total_habits,
            "completed_habits": completed_habits,
            "total_time_worked": total_time,
            "average_time_worked_per_day": total_time / days_for_average if days_for_average > 0 else total_time,
            "xp": sum(xp_by_day.get(day, 0) for day in days if day <= range_end),
            "note": notes.get(monday),
            "in_progress": days[-1] >= today,
        })
        monday += timedelta(days = 7)

    # anchored to the user's current total, so the curve ends on the level shown elsewhere
    user = db.session.get(User, user_id)
    running_xp = max(0, (user.total_xp or 0) - sum(xp_by_day.values()))
    current_day = range_start
    while current_day <= range_end:
        earned = xp_by_day.get(current_day, 0)
        running_xp += earned
        progress = level_from_xp(running_xp)
        response["xp_days"].append({
            "date": current_day.isoformat(),
            "xp_earned": earned,
            "total_xp": running_xp,
            "level": progress["level"],
            "xp_into_level": progress["xp_into_level"],
            "xp_to_next": progress["xp_to_next"],
        })
        current_day += timedelta(days = 1)

    return success_response(response)


@statistic_routes.route("/stats/overview/notes/<string:week_start>/", methods=["PUT"])
@jwt_required()
def set_week_note(week_start):
    """
    Endpoint for setting one week's note. An empty note removes it.
    """

    user_id = int(get_jwt_identity())
    monday = parse_week_start(week_start)
    if monday is None:
        return failure_response("Week must be a Monday in YYYY-MM-DD format", 400)

    body = json.loads(request.data)
    text = body.get("note", "")
    if not isinstance(text, str):
        return failure_response("Note must be text", 400)
    text = text.strip()
    if len(text) > MAX_WEEK_NOTE_LENGTH:
        return failure_response(f"Note must be at most {MAX_WEEK_NOTE_LENGTH} characters", 400)

    note = WeekNote.query.filter_by(user_id = user_id, week_start = monday).first()
    if not text:
        if note is not None:
            db.session.delete(note)
    elif note is None:
        db.session.add(WeekNote(user_id = user_id, week_start = monday, text = text))
    else:
        note.text = text
    db.session.commit()
    return success_response({"week_start": monday.isoformat(), "note": text or None})


@statistic_routes.route("/stats/overview/notes/import/", methods=["POST"])
@jwt_required()
def import_week_notes():
    """
    Endpoint for adding many week notes at once. Weeks that already have a note
    keep it, so running an import twice changes nothing.
    """

    user_id = int(get_jwt_identity())
    body = json.loads(request.data)
    items = body.get("notes")
    if not isinstance(items, list):
        return failure_response("notes must be a list", 400)

    taken = {note.week_start for note in WeekNote.query.filter_by(user_id = user_id).all()}
    imported = 0
    skipped = 0
    errors = []
    for item in items:
        week_start = item.get("week_start") if isinstance(item, dict) else None
        text = item.get("note") if isinstance(item, dict) else None
        monday = parse_week_start(week_start)
        if monday is None or not isinstance(text, str) or not text.strip() or len(text.strip()) > MAX_WEEK_NOTE_LENGTH:
            errors.append(str(week_start))
        elif monday in taken:
            skipped += 1
        else:
            db.session.add(WeekNote(user_id = user_id, week_start = monday, text = text.strip()))
            taken.add(monday)
            imported += 1
    db.session.commit()
    return success_response({"imported": imported, "skipped": skipped, "errors": errors})
