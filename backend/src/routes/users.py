from flask import Blueprint
from utils import success_response, failure_response, process_date
import json
from db import db, User, TokenBlocklist
from flask import Flask, request
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_refresh_cookies, decode_token, get_jwt, unset_jwt_cookies
from flask import make_response
from datetime import datetime

user_routes = Blueprint('user', __name__)

def revoke_token(jti: str, ttype: str, user_id: int, exp_epoch: int):
    if not jti:
        return
    if not TokenBlocklist.query.filter_by(jti=jti).one_or_none():
        expires_at = datetime.fromtimestamp(exp_epoch)
        db.session.add(TokenBlocklist(
            jti=jti, type=ttype, user_id=user_id, expires_at=expires_at, revoked=True
        ))
        db.session.commit()


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
    username_or_email = body.get("usernameOrEmail")
    password = body.get("password")

    user = User.query.filter_by(username = username_or_email).first()
    if not user:
        user = User.query.filter_by(email = username_or_email).first()
    if user and check_password_hash(user.password_hash, password):
        refresh_token = create_refresh_token(identity = str(user.id))
        refresh_decoded = decode_token(refresh_token)
        refresh_jti = refresh_decoded["jti"]
        refresh_exp = refresh_decoded["exp"]  # epoch seconds
        access_token = create_access_token(identity= str(user.id), additional_claims={"refresh_jti": refresh_jti, "refresh_exp": refresh_exp})
        resp = make_response(success_response({"user": user.serialize(), "access_token": access_token}))
        set_refresh_cookies(resp, refresh_token)  
        return resp
    return failure_response("Invalid credentials", 401)

@user_routes.route("/refresh", methods = ["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh the access token using a valid refresh token.
    """

    rt_claims   = get_jwt()                 # claims of the *refresh* token
    refresh_jti = rt_claims["jti"]          # JWT ID of the refresh token
    refresh_exp = rt_claims["exp"] 

    user_id = int(get_jwt_identity())
    user = User.query.filter_by(id=user_id).first()
    username = user.username
    email = user.email
    new_access_token = create_access_token(identity= str(user_id), additional_claims={"refresh_jti": refresh_jti, "refresh_exp": refresh_exp})
    return success_response({"access_token": new_access_token, "username": username, "email" : email })

@user_routes.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jwt_payload = get_jwt()
    user_id     = int(get_jwt_identity())
    access_jti  = jwt_payload["jti"]
    access_exp  = jwt_payload["exp"]                 # epoch seconds
    refresh_jti = jwt_payload.get("refresh_jti")
    refresh_exp = jwt_payload.get("refresh_exp")

    revoke_token(jti=access_jti, ttype= "access", user_id= user_id, exp_epoch= access_exp)
    revoke_token(jti=refresh_jti, ttype= "refresh", user_id=user_id, exp_epoch= refresh_exp )
    
    response = make_response("Logout successful", 200)
    unset_jwt_cookies(response)

    return response, 200