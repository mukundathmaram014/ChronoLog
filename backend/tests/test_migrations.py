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
    ensure_stopwatch_repeat_days_column,
    ensure_task_completed_date_column,
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


def test_stopwatch_repeat_days_migration_adds_missing_column(app):
    with app.app_context():
        # simulate an older DB from before per-stopwatch repeat days (spec 0027)
        db.session.execute(text("ALTER TABLE stopwatches DROP COLUMN repeat_days"))
        db.session.commit()
        assert "repeat_days" not in _columns("stopwatches")

        ensure_stopwatch_repeat_days_column()
        assert "repeat_days" in _columns("stopwatches")

        # idempotent: running again on an up-to-date schema is a no-op
        ensure_stopwatch_repeat_days_column()
        assert "repeat_days" in _columns("stopwatches")

        # existing rows fall back to "every day", preserving pre-flag behavior
        default = db.session.execute(
            text("SELECT dflt_value FROM pragma_table_info('stopwatches') WHERE name = 'repeat_days'")
        ).scalar()
        assert int(default) == 127


def test_task_completed_date_migration_adds_missing_column(app):
    with app.app_context():
        # simulate an older DB from before completed-task history (spec 0031)
        db.session.execute(text("ALTER TABLE tasks DROP COLUMN completed_date"))
        db.session.commit()
        assert "completed_date" not in _columns("tasks")

        ensure_task_completed_date_column()
        assert "completed_date" in _columns("tasks")

        # idempotent: running again on an up-to-date schema is a no-op
        ensure_task_completed_date_column()
        assert "completed_date" in _columns("tasks")

        # nullable with no backfill: pre-existing completed rows have no recorded
        # completion day and fall back to their due date in the history endpoint
        default = db.session.execute(
            text("SELECT dflt_value FROM pragma_table_info('tasks') WHERE name = 'completed_date'")
        ).scalar()
        assert default is None
