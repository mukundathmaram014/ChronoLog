from flask import Blueprint
from utils import success_response, failure_response, process_date
import json
from db import db, User
from flask import Flask, request
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

user_routes = Blueprint('user', __name__)

@user_routes.route("/register", methods = ["POST"])
def register():
    """
    Registers a new user
    """

    body = json.loads(request.data)
    username = body.get("username")
    email = body.get("email")
    password = body.get("password")

    if User.query.filter_by(username = username).first():
        return failure_response("Username already exists", 409)
    
    if User.query.filter_by(email = email).first():
        return failure_response("Email already exists", 409)
    
    user = User(username = username, email = email, password_hash = generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return success_response(user.serialize(), 201)

@user_routes.route("/login", methods= ["POST"])
def login():
    """
    Logs in an already existing user
    """

    body = json.loads(request.data)
    username = body.get("username")
    email = body.get("email")
    password = body.get("password")

    user = User.query.filter_by(username = username).first()
    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity= str(user.id))
        return success_response({"user": user.serialize(), "access_token": access_token})
    return failure_response("Invalid credentials", 401)

