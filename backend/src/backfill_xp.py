"""
One-time backfill (spec 0020 follow-up): apply the XP engine to habit /
stopwatch / goal history that predates the XP feature.

The XP ledger (DailyXP rows + User.total_xp) is only written by
`recompute_from`, which the routes call "from the edited day forward" whenever
an item is toggled *after* the XP feature shipped. Days recorded before then
still have their Habit / Stopwatch / Goal rows in the DB, but were never fed
through the engine, so they contributed no XP -- which is why an account with
years of history still reads as level 1.

This walks every user's history once, starting from their earliest XP-relevant
day, and lets the normal engine recompute the ledger over the whole range. It
reuses `recompute_from` (same code path as production), so it is idempotent:
once the ledger has caught up, running it again recomputes the same values and
changes nothing.

Note: habits recorded before spec 0020 have no stored difficulty, so the
migration defaulted them to "medium" -- the backfill values every historical
completed habit at the medium tier. Stopwatch hours are used exactly as
recorded.

Run once, inside the backend container:
    docker exec <container> python backfill_xp.py
"""
from sqlalchemy import func

from app import app
from db import db, User, Habit, Stopwatch, Goal
from utils import level_from_xp
from xp import recompute_from


def earliest_activity_date(user_id):
    """
    Earliest date with any XP-relevant data for the user (completed habit,
    Total stopwatch day, or completed goal), or None if they have no history.
    Mirrors xp._last_activity_date but takes the minimum.
    """
    dates = [
        db.session.query(func.min(Habit.date)).filter(Habit.user_id == user_id, Habit.done == True).scalar(),
        db.session.query(func.min(Stopwatch.date)).filter(Stopwatch.user_id == user_id, Stopwatch.isTotal == True).scalar(),
        db.session.query(func.min(Goal.completed_date)).filter(Goal.user_id == user_id, Goal.done == True).scalar(),
    ]
    dates = [d for d in dates if d is not None]
    return min(dates) if dates else None


def backfill():
    users = User.query.order_by(User.id).all()
    print(f"Backfilling XP for {len(users)} user(s)...")
    for user in users:
        start = earliest_activity_date(user.id)
        before = user.total_xp or 0
        if start is None:
            print(f"  user {user.id} ({user.username}): no history -- skipped")
            continue
        recompute_from(user.id, start)
        db.session.commit()
        after = user.total_xp or 0
        level = level_from_xp(after)["level"]
        print(
            f"  user {user.id} ({user.username}): recomputed {start} -> today | "
            f"total_xp {before} -> {after} (level {level})"
        )
    print("Done.")


if __name__ == "__main__":
    with app.app_context():
        backfill()
