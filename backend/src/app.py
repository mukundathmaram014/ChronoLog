import json

from db import db
from flask import Flask, request
from flask_cors import CORS
from routes.habits import habit_routes
from routes.stopwatch import stopwatch_routes

# define db filename
db_filename = "productivity.db"
app = Flask(__name__)
CORS(app)


# setup config
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_filename}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

# initialize app
db.init_app(app)
with app.app_context():
    db.create_all()

app.register_blueprint(habit_routes)
app.register_blueprint(stopwatch_routes)



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)