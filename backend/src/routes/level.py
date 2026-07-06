from flask import Blueprint
from utils import success_response, level_from_xp, streak_multiplier
from db import db, User
from datetime import date
from flask_jwt_extended import jwt_required, get_jwt_identity
from xp import current_streak


level_routes = Blueprint('level', __name__)


@level_routes.route("/level/<string:date_string>/")
@jwt_required()
def get_level(date_string):
    """
    Endpoint for the user's XP/level readout: running XP total, derived level
    + progress on the fixed curve, and the current streak/multiplier as of
    the given (client-local) date.
    """
    user_id = int(get_jwt_identity())
    today = date.fromisoformat(date_string)
    user = db.session.get(User, user_id)
    total_xp = user.total_xp or 0
    progress = level_from_xp(total_xp)
    streak = current_streak(user_id, today)
    return success_response({
        "total_xp": total_xp,
        "level": progress["level"],
        "xp_into_level": progress["xp_into_level"],
        "xp_to_next": progress["xp_to_next"],
        "streak": streak,
        "multiplier": streak_multiplier(streak),
    })
