"""
XP accrual engine (spec 0020): keeps the DailyXP ledger and User.total_xp in
sync with a day's inputs (completed habits, worked time, completed goals).
The pure XP math lives in utils.py; this module is the DB-touching half.
"""
from datetime import timedelta

from sqlalchemy import func

from db import db, Habit, Stopwatch, Goal, DailyXP, User
from utils import compute_day_xp, HABIT_XP

MS_PER_HOUR = 3600000.0


def _day_inputs(user_id, day):
    """
    The XP inputs for one user-day: completed-habit difficulty tiers, hours
    worked (from the day's Total stopwatch), completed-goal tiers, the day's
    total goal hours (sum of the day's individual stopwatch goal times, for the
    overtime work-XP boost), and whether every habit that day is done (for the
    all-habits bonus).
    """
    day_habits = Habit.query.filter_by(user_id=user_id, date=day).all()
    habit_difficulties = [habit.difficulty for habit in day_habits if habit.done]
    all_habits_done = bool(day_habits) and all(habit.done for habit in day_habits)
    # max habit XP if every one of the day's habits were done (for the streak %)
    max_habit_xp = sum(HABIT_XP[habit.difficulty] for habit in day_habits)
    total_stopwatch = Stopwatch.query.filter_by(user_id=user_id, date=day, isTotal=True).first()
    hours_worked = (total_stopwatch.curr_duration / MS_PER_HOUR) if total_stopwatch else 0.0
    goal_difficulties = [
        goal.difficulty
        for goal in Goal.query.filter_by(user_id=user_id, done=True, completed_date=day).all()
    ]
    # the day's total goal time is the Total row's goal_time -- the sum of the
    # individual stopwatch goals by default, or the user's override (spec 0023);
    # drives the goal-time bonus + overtime split
    goal_ms = total_stopwatch.goal_time if total_stopwatch else 0
    goal_hours = (goal_ms or 0) / MS_PER_HOUR
    return habit_difficulties, hours_worked, goal_difficulties, goal_hours, all_habits_done, max_habit_xp


def _last_activity_date(user_id):
    """
    The latest date with any XP-relevant data for the user (ledger rows,
    completed habits, stopwatch days, completed goals), or None.
    """
    dates = [
        db.session.query(func.max(DailyXP.date)).filter(DailyXP.user_id == user_id).scalar(),
        db.session.query(func.max(Habit.date)).filter(Habit.user_id == user_id, Habit.done == True).scalar(),
        db.session.query(func.max(Stopwatch.date)).filter(Stopwatch.user_id == user_id, Stopwatch.isTotal == True).scalar(),
        db.session.query(func.max(Goal.completed_date)).filter(Goal.user_id == user_id, Goal.done == True).scalar(),
    ]
    dates = [d for d in dates if d is not None]
    return max(dates) if dates else None


def recompute_from(user_id, day):
    """
    Recompute the DailyXP ledger from `day` forward and adjust User.total_xp
    by the delta. Forward because the streak is path-dependent: changing a
    past day's qualifying status shifts subsequent days' streaks/multipliers.
    The caller commits.
    """
    end = _last_activity_date(user_id)
    if end is None or end < day:
        end = day

    prev_row = DailyXP.query.filter_by(user_id=user_id, date=day - timedelta(days=1)).first()
    prev_streak = prev_row.streak if prev_row else 0

    delta = 0
    current = day
    while current <= end:
        habit_difficulties, hours_worked, goal_difficulties, goal_hours, all_habits_done, max_habit_xp = _day_inputs(user_id, current)
        result = compute_day_xp(habit_difficulties, hours_worked, goal_difficulties, prev_streak, goal_hours, all_habits_done, max_habit_xp)
        row = DailyXP.query.filter_by(user_id=user_id, date=current).first()
        old_xp = row.xp_earned if row else 0
        if row is not None:
            row.xp_earned = result["xp_earned"]
            row.streak = result["streak"]
        elif result["xp_earned"] != 0 or result["streak"] != 0:
            db.session.add(DailyXP(date=current, xp_earned=result["xp_earned"], streak=result["streak"], user_id=user_id))
        delta += result["xp_earned"] - old_xp
        prev_streak = result["streak"]
        current += timedelta(days=1)

    if delta != 0:
        user = db.session.get(User, user_id)
        user.total_xp = (user.total_xp or 0) + delta


def day_xp(user_id, day):
    """
    The XP earned on `day` (0 if that day has no ledger row yet).
    """
    row = DailyXP.query.filter_by(user_id=user_id, date=day).first()
    return row.xp_earned if row else 0


def current_streak(user_id, today):
    """
    The user's live streak as of `today`: today's ledger streak once today
    qualifies, else yesterday's (still extendable today); older rows are a
    gap, which means the streak is broken (0).
    """
    today_row = DailyXP.query.filter_by(user_id=user_id, date=today).first()
    yesterday_row = DailyXP.query.filter_by(user_id=user_id, date=today - timedelta(days=1)).first()
    today_streak = today_row.streak if today_row else 0
    yesterday_streak = yesterday_row.streak if yesterday_row else 0
    return max(today_streak, yesterday_streak)
