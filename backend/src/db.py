from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timezone
from utils import ensure_utc
db = SQLAlchemy()


#User model
class User(db.Model):
    """
    User model
    """
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable = False)
    email = db.Column(db.String, nullable = False)
    password_hash = db.Column(db.String, nullable = False)
    homepage_note = db.Column(db.String, nullable = True)
    total_xp = db.Column(db.Integer, nullable=False, default=0)
    is_guest = db.Column(db.Boolean, nullable=False, default=False)
    # needed for the guest TTL purge; nullable because pre-existing rows have no value
    created_at = db.Column(db.DateTime(timezone=True), nullable=True, default=lambda: datetime.now(timezone.utc))

    def serialize(self):
        """
        Serializing a user to be returned
        """

        return {"id": self.id, "username": self.username, "email": self.email, "homepage_note": self.homepage_note, "total_xp": self.total_xp or 0, "is_guest": bool(self.is_guest)}


# Habit model
class Habit(db.Model):
    """
    Habit model
    """

    __tablename__ = "habits"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.String, nullable = False)
    done = db.Column(db.Boolean, nullable=False)
    date = db.Column(db.Date, nullable=False)
    # 7-bit weekday bitmask: bit i = date.weekday() i (0 = Mon ... 6 = Sun); 127 = every day
    repeat_days = db.Column(db.Integer, nullable=False, default=127)
    # difficulty tier (easy/medium/hard) mapping to a fixed XP value in utils.py
    difficulty = db.Column(db.String, nullable=False, default="medium")
    # display order within a (user, date) list; new rows append at the end
    position = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a habit object
        """

        self.description = kwargs.get("description", "")
        self.done = kwargs.get("done", False)
        self.date = kwargs.get("date", date.today())
        self.repeat_days = kwargs.get("repeat_days", 127)
        self.difficulty = kwargs.get("difficulty", "medium")
        self.position = kwargs.get("position", 0)
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializing a habit to be returned
        """
        return {
            "id": self.id,
            "description" : self.description,
            "done" : self.done,
            "date": self.date.isoformat(),
            "repeat_days": self.repeat_days,
            "difficulty": self.difficulty,
            "position": self.position,
            "user_id": self.user_id
        }
    
# Task model
class Task(db.Model):
    """
    Task model. Top-level tasks have parent_id = NULL; a sub-task points to its
    parent (one level of nesting). recurrence is one of none/daily/weekly/monthly.
    """

    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.String, nullable = False)
    done = db.Column(db.Boolean, nullable=False)
    date = db.Column(db.Date, nullable=False)
    recurrence = db.Column(db.String, nullable=False, default="none")
    parent_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # deleting a parent deletes its sub-tasks
    subtasks = db.relationship(
        "Task",
        backref=db.backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        """
        Initialize a task object
        """

        self.description = kwargs.get("description", "")
        self.done = kwargs.get("done", False)
        self.date = kwargs.get("date", date.today())
        self.recurrence = kwargs.get("recurrence", "none")
        self.parent_id = kwargs.get("parent_id")
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializing a task to be returned, with sub-tasks nested under the parent
        """
        return {
            "id": self.id,
            "description" : self.description,
            "done" : self.done,
            "date": self.date.isoformat(),
            "recurrence": self.recurrence,
            "parent_id": self.parent_id,
            "user_id": self.user_id,
            "subtasks": [subtask.serialize() for subtask in self.subtasks]
        }


# Goal model
class Goal(db.Model):
    """
    Goal model. One-time: completing a goal grants its difficulty XP once on
    its completed_date; un-completing removes it. No repeating goals.
    """

    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.String, nullable = False)
    difficulty = db.Column(db.String, nullable=False, default="medium")
    done = db.Column(db.Boolean, nullable=False, default=False)
    completed_date = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a goal object
        """

        self.description = kwargs.get("description", "")
        self.difficulty = kwargs.get("difficulty", "medium")
        self.done = kwargs.get("done", False)
        self.completed_date = kwargs.get("completed_date")
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializing a goal to be returned
        """
        return {
            "id": self.id,
            "description": self.description,
            "difficulty": self.difficulty,
            "done": self.done,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
            "user_id": self.user_id
        }


# DailyXP model
class DailyXP(db.Model):
    """
    Per-user-per-day XP ledger: what each day contributed to User.total_xp,
    plus that day's streak count. The streak is path-dependent, so editing a
    past day recomputes that day forward (see xp.recompute_from).
    """

    __tablename__ = "daily_xp"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    xp_earned = db.Column(db.Integer, nullable=False, default=0)
    streak = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a DailyXP object
        """

        self.date = kwargs.get("date", date.today())
        self.xp_earned = kwargs.get("xp_earned", 0)
        self.streak = kwargs.get("streak", 0)
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializing a DailyXP row to be returned
        """
        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "xp_earned": self.xp_earned,
            "streak": self.streak,
            "user_id": self.user_id
        }


#stopwatch model
class Stopwatch(db.Model):
    """
    Stopwatch model. When created stopwatch is paused
    """
    __tablename__ = "stopwatches"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String, nullable = False)
    start_time = db.Column(db.DateTime(timezone=True), nullable = False)
    interval_start = db.Column(db.DateTime(timezone=True), nullable = False)
    end_time = db.Column(db.DateTime(timezone=True), nullable = True)
    curr_duration = db.Column(db.Float, nullable = False)
    date = db.Column(db.Date, nullable = False)
    isTotal = db.Column(db.Boolean, nullable = False)
    goal_time = db.Column(db.Float, nullable = False)
    # (Total row only) True once the user sets a custom daily goal; while False the
    # Total's goal_time tracks the sum of the day's individual stopwatch goals.
    goal_overridden = db.Column(db.Boolean, nullable = False, default = False)
    # recurring stopwatches carry forward to future days; non-recurring are one-off
    is_recurring = db.Column(db.Boolean, nullable = False, default = True)
    # display order within a (user, date) list; new rows append. The Total row
    # keeps 0 — it never participates in ordering (spec 0004).
    position = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # deleting a stopwatch deletes its recorded intervals
    intervals = db.relationship(
        "StopwatchInterval",
        cascade="all, delete-orphan",
    )

    def __init__(self, **kwargs):
        """
        Initialize a stopwatch object
        """

        self.title = kwargs.get("title", "")
        self.start_time = kwargs.get("start_time", datetime.now(timezone.utc))
        self.interval_start = kwargs.get("interval_start", datetime.now(timezone.utc))
        self.end_time = self.start_time
        self.curr_duration = 0.0
        self.date = kwargs.get("date", date.today())
        self.isTotal = kwargs.get("isTotal", False)
        self.goal_time = kwargs.get("goal_time", 3600000) # defaults to one hour
        self.goal_overridden = kwargs.get("goal_overridden", False)
        self.is_recurring = kwargs.get("is_recurring", True)
        self.position = kwargs.get("position", 0)
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializing a stopwatch to be returned
        """

        return {
            "id": self.id,
            "title": self.title,
            "start_time": ensure_utc(self.start_time).isoformat(),
            "interval_start": ensure_utc(self.interval_start).isoformat(),
            "end_time": ensure_utc(self.end_time).isoformat() if (self.end_time != None) else None,
            "curr_duration": self.curr_duration,
            "date": self.date.isoformat(),
            "isTotal": self.isTotal,
            "goal_time": self.goal_time,
            "goal_overridden": self.goal_overridden,
            "is_recurring": self.is_recurring,
            "position": self.position,
            "user_id": self.user_id
        }
    

#stopwatch interval model
class StopwatchInterval(db.Model):
    """
    One completed run segment of a stopwatch (start -> stop). Recorded by
    stop_stopwatch; the day's session log is built from these rows. date
    duplicates the parent stopwatch's day so the day query needs no join.
    """
    __tablename__ = "stopwatch_intervals"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    stopwatch_id = db.Column(db.Integer, db.ForeignKey("stopwatches.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a stopwatch interval object
        """

        self.stopwatch_id = kwargs.get("stopwatch_id")
        self.user_id = kwargs.get("user_id")
        self.date = kwargs.get("date", date.today())
        self.start_time = kwargs.get("start_time")
        self.end_time = kwargs.get("end_time")

    def serialize(self):
        """
        Serializing a stopwatch interval to be returned
        """

        return {
            "id": self.id,
            "stopwatch_id": self.stopwatch_id,
            "date": self.date.isoformat(),
            "start_time": ensure_utc(self.start_time).isoformat(),
            "end_time": ensure_utc(self.end_time).isoformat(),
            "user_id": self.user_id
        }


class DeletedDay(db.Model):
    __tablename__ = "deleted-days"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable = False)
    type = db.Column(db.String, nullable = False) # "habit" or "stopwatch"
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def serialize(self):
        """
        Serializing a stopwatch to be returned
        """

        return {
            "id": self.id,
            "date": self.date.isoformat(),
            "type": self.type,
            "user_id": self.user_id 
        }
    

#revoked tokens
class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"
    id = db.Column(db.Integer , primary_key=True)
    jti = db.Column(db.String , nullable = True)
    created_at = db.Column(db.DateTime(timezone=True) , nullable = False)
    type = db.Column(db.String, nullable = False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked    = db.Column(db.Boolean, nullable=False)
    user_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a TokenBlocklist object
        """

        self.jti = kwargs.get("jti", "")
        self.type = kwargs.get("type")
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.expires_at = kwargs.get("expires_at")
        self.revoked = kwargs.get("revoked")
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializing a TokenBlocklist to be returned
        """

        return {
            "id": self.id,
            "jti": self.jti,
            "type": self.type,
            "created_at": ensure_utc(self.created_at).isoformat(),
            "expires_at": ensure_utc(self.expires_at).isoformat(),
            "revoked": self.revoked,
            "user_id": self.user_id 
        }


