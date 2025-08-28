import json
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
load_dotenv()

from db import db, Stopwatch, DeletedDay, TokenBlocklist
from flask import Flask, request
from flask_cors import CORS
from routes.habits import habit_routes
from routes.stopwatch import stopwatch_routes
from routes.statistics import statistic_routes
from routes.users import user_routes
from datetime import datetime, timedelta
from utils import success_response
from flask_jwt_extended import jwt_required, get_jwt_identity
import os

# define db filename
db_filename = "ChronoLog.db"
app = Flask(__name__)

FRONTEND_ORIGINS = [
    "http://localhost:3000",                 # dev
    "https://chronologtracker.com",       # prod - Netlify
]

CORS(
    app,
    resources={r"/api/*": {"origins": FRONTEND_ORIGINS}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization", "X-CSRF-TOKEN"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


# setup config
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_filename}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False # set True only when you need SQL debugging

app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
app.config["JWT_SECRET_KEY"] = os.environ['JWT_SECRET_KEY']
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_REFRESH_COOKIE_NAME"] = "refresh_token_cookie"
app.config["JWT_COOKIE_SECURE"] = True   # True in production (HTTPS)
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_COOKIE_CSRF_PROTECT"] = True  # enables double-submit CSRF for cookies

jwt = JWTManager(app)

# initialize app
db.init_app(app)
with app.app_context():
    db.create_all()

app.register_blueprint(habit_routes,  url_prefix="/api")
app.register_blueprint(stopwatch_routes,  url_prefix="/api")
app.register_blueprint(statistic_routes,  url_prefix="/api")
app.register_blueprint(user_routes,  url_prefix="/api")

# gets all deleted days for a user
@app.route("/api/deletedday")
@jwt_required()
def get_deleted_day():

    user_id = int(get_jwt_identity())
    deleteddays = []
    for day in DeletedDay.query.filter_by(user_id=user_id).all():
        deleteddays.append(day.serialize())
    
    return success_response({"deleted days": deleteddays})

# gets all blocked tokens for a user
@app.route("/api/tokenblocklist")
@jwt_required()
def get_token_blocklist():
    user_id = int(get_jwt_identity())
    tokens = []
    for token in TokenBlocklist.query.filter_by(user_id=user_id).all():
        tokens.append(token.serialize())
    
    return success_response({"tokens": tokens})

@jwt.token_in_blocklist_loader
def token_revoked(jwt_header, jwt_data):
    jti = jwt_data.get("jti")
    entry = TokenBlocklist.query.filter_by(jti=jti).one_or_none()
    return entry is not None and entry.revoked


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)