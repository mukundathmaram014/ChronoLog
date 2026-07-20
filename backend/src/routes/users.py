from flask import Blueprint
from utils import success_response, failure_response, process_date, ensure_utc
import json
import os
import secrets
from db import db, User, Habit, Task, Goal, DailyXP, Stopwatch, DeletedDay, TokenBlocklist
from flask import Flask, request
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, set_refresh_cookies, decode_token, get_jwt, unset_jwt_cookies
from flask import make_response
from datetime import datetime, timedelta, timezone

user_routes = Blueprint('user', __name__)

# guest accounts and all their data are purged this many days after creation
GUEST_TTL_DAYS = int(os.environ.get("GUEST_TTL_DAYS", "7"))


def purge_expired_guests():
    """
    Deletes guest users older than GUEST_TTL_DAYS along with all their data.
    Runs at app startup and whenever a new guest is provisioned.
    """

    cutoff = datetime.now(timezone.utc) - timedelta(days=GUEST_TTL_DAYS)
    expired = []
    for user in User.query.filter_by(is_guest=True).all():
        created = ensure_utc(user.created_at)
        if created is not None and created < cutoff:
            expired.append(user)
    for user in expired:
        for model in (Habit, Task, Goal, DailyXP, Stopwatch, DeletedDay, TokenBlocklist):
            model.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
    if expired:
        db.session.commit()

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

@user_routes.route("/guest", methods = ["POST"])
def guest():
    """
    Provisions a throwaway guest user and logs it in like a normal user.
    Guest accounts and their data are purged GUEST_TTL_DAYS after creation.
    """

    purge_expired_guests()

    while True:
        username = f"guest-{secrets.token_hex(4)}"
        if not User.query.filter_by(username = username).first():
            break
    # reserved TLD: can never collide with a real registered email
    email = f"{username}@guest.invalid"
    # random password, never disclosed — guests re-enter via the refresh cookie only
    user = User(username = username, email = email, password_hash = generate_password_hash(secrets.token_urlsafe(32)), is_guest = True)
    db.session.add(user)
    db.session.commit()

    refresh_token = create_refresh_token(identity = str(user.id))
    refresh_decoded = decode_token(refresh_token)
    refresh_jti = refresh_decoded["jti"]
    refresh_exp = refresh_decoded["exp"]  # epoch seconds
    access_token = create_access_token(identity= str(user.id), additional_claims={"refresh_jti": refresh_jti, "refresh_exp": refresh_exp})
    resp = make_response(success_response({"user": user.serialize(), "access_token": access_token}, 201))
    set_refresh_cookies(resp, refresh_token)
    return resp

@user_routes.route("/refresh", methods = ["POST"])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh the access token using a valid refresh token.

    Rotates the refresh token: every successful refresh issues a new 30-day
    refresh cookie, so any visit resets the inactivity clock. The old refresh
    token is deliberately left valid until its own expiry — revoking it would
    log out concurrent tabs/devices racing to refresh. Logout still revokes the
    current refresh token via the refresh_jti claim below.
    """

    user_id = int(get_jwt_identity())
    user = User.query.filter_by(id=user_id).first()
    if not user:
        # e.g. a purged guest holding a still-valid refresh token
        return failure_response("User not found", 401)

    new_refresh_token = create_refresh_token(identity = str(user_id))
    refresh_decoded = decode_token(new_refresh_token)
    refresh_jti = refresh_decoded["jti"]
    refresh_exp = refresh_decoded["exp"]  # epoch seconds
    new_access_token = create_access_token(identity= str(user_id), additional_claims={"refresh_jti": refresh_jti, "refresh_exp": refresh_exp})
    resp = make_response(success_response({"access_token": new_access_token, "username": user.username, "email" : user.email, "is_guest": bool(user.is_guest) }))
    set_refresh_cookies(resp, new_refresh_token)
    return resp

@user_routes.route("/note", methods = ["GET"])
@jwt_required()
def get_note():
    """
    Returns the current user's homepage note
    """

    user_id = int(get_jwt_identity())
    user = User.query.filter_by(id = user_id).first()
    if not user:
        return failure_response("User not found", 404)
    return success_response({"homepage_note": user.homepage_note})

@user_routes.route("/note", methods = ["PUT"])
@jwt_required()
def update_note():
    """
    Updates the current user's homepage note
    """

    user_id = int(get_jwt_identity())
    user = User.query.filter_by(id = user_id).first()
    if not user:
        return failure_response("User not found", 404)
    body = json.loads(request.data)
    user.homepage_note = body.get("homepage_note", "")
    db.session.commit()
    return success_response({"homepage_note": user.homepage_note})

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