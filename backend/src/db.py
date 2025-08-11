from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
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

    def serialize(self):
        """
        Serializing a user to be returned
        """

        return {"id": self.id, "username": self.username, "email": self.email}


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
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a habit object
        """

        self.description = kwargs.get("description", "")
        self.done = kwargs.get("done", False)
        self.date = kwargs.get("date", date.today())
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
    start_time = db.Column(db.DateTime, nullable = False)
    interval_start = db.Column(db.DateTime, nullable = False)
    end_time = db.Column(db.DateTime, nullable = True)
    curr_duration = db.Column(db.Float, nullable = False)
    date = db.Column(db.Date, nullable = False)
    isTotal = db.Column(db.Boolean, nullable = False)
    goal_time = db.Column(db.Float, nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initialize a stopwatch object
        """

        self.title = kwargs.get("title", "")
        self.start_time = kwargs.get("start_time", datetime.now())
        self.interval_start = kwargs.get("interval_start", datetime.now())
        self.end_time = self.start_time
        self.curr_duration = 0.0
        self.date = kwargs.get("date", date.today())
        self.isTotal = kwargs.get("isTotal", False)
        self.goal_time = kwargs.get("goal_time", 3600000) # defaults to one hour
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializing a stopwatch to be returned
        """

        return {
            "id": self.id,
            "title": self.title,
            "start_time": self.start_time.isoformat(),
            "interval_start": self.interval_start.isoformat(),
            "end_time": self.end_time.isoformat() if (self.end_time != None) else None,
            "curr_duration": self.curr_duration,
            "date": self.date.isoformat(),
            "isTotal": self.isTotal,
            "goal_time": self.goal_time,
            "user_id": self.user_id 
        }
    
    # def get_duration(self):
    #     """
    #     Returns total duration stopwatch has been running
    #     """
    #     if (self.end_time != None):
    #         return self.curr_duration
    #     else:
    #         return (datetime.now() - self.interval_start).total_seconds() + self.curr_duration


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