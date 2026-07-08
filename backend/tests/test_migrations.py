"""
Guards against the recurring "added a db.Column but forgot the ALTER TABLE
startup migration" bug: create_all() only creates missing *tables*, never adds
columns to existing ones, so a new column silently works on fresh (test) DBs
but breaks every query on the existing prod DB.

Each case drops a column to mimic an older prod schema, runs the ensure_*
migration, and checks it is re-added (and is idempotent).
"""
from sqlalchemy import text

from app import (
    ensure_habit_position_column,
    ensure_stopwatch_position_column,
)
from db import db


def _columns(table):
    return {row[1] for row in db.session.execute(text(f"PRAGMA table_info({table})"))}


def test_position_migrations_add_missing_columns(app):
    with app.app_context():
        # simulate an older DB where the position columns don't exist yet
        db.session.execute(text("ALTER TABLE habits DROP COLUMN position"))
        db.session.execute(text("ALTER TABLE stopwatches DROP COLUMN position"))
        db.session.commit()
        assert "position" not in _columns("habits")
        assert "position" not in _columns("stopwatches")

        ensure_habit_position_column()
        ensure_stopwatch_position_column()
        assert "position" in _columns("habits")
        assert "position" in _columns("stopwatches")

        # idempotent: running again on an up-to-date schema is a no-op
        ensure_habit_position_column()
        ensure_stopwatch_position_column()
        assert "position" in _columns("habits")
        assert "position" in _columns("stopwatches")
