---
title: Record and show each stopwatch's start/stop intervals during the day
status: decided
---

# Record and show each stopwatch's start/stop intervals during the day

## Summary
Today the app only keeps a cumulative `curr_duration` per stopwatch: `Stopwatch.interval_start`
and `end_time` (db.py:216-217) are overwritten on every start/stop cycle, so "when exactly did I
work" is unrecoverable — after a stop, only the total survives. This spec adds a persistent
per-interval history: every completed run segment (start → stop) is recorded as a row in a new
`StopwatchInterval` table, and the stopwatch page gains a per-day session log ("10:04–10:52
Deep Work · 48m") built from those rows.

**Decided:** the log is a chronological session list, and it is **discreet** — a collapsed
disclosure ("Session log") below the stopwatch grid, hidden by default. The user opts in to look
at it; it never competes with the main grid. This also de-emphasizes the accepted mismatch where
manual `curr_duration` edits create no intervals, so the log shows only real timed segments.
**Reset deletes** that stopwatch's interval rows for the day, keeping "sum of intervals ≈
curr_duration" true for untouched-by-manual-edit days.

The write path is narrow by design: all stops funnel through the `stop_stopwatch` endpoint
(stopwatch.py:341-365) — the Pause button, date-change stop, pagehide/navigation stops, and the
midnight-rollover stop all call it — so recording the interval there (using the same
`interval_start`/`end_time` pair the endpoint already uses to compute the duration increment)
captures every real segment. The Total row starts/stops in lockstep with its child, so intervals
are recorded only for non-Total stopwatches and the day view is just their union. Stale
stopwatches frozen by `finalize_stale_stopwatches` (stopwatch.py:45-62) credit no time and get no
interval. History starts at deployment; pre-existing days simply show an empty log.

## Affected files
- `backend/src/db.py` — new `StopwatchInterval` model: `id`, `stopwatch_id` (FK →
  `stopwatches.id`), `user_id` (FK → `users.id`), `date` (Date, the stopwatch's day),
  `start_time` / `end_time` (both `DateTime(timezone=True)`, non-null), `serialize()`. Add a
  `db.relationship` on `Stopwatch` with `cascade="all, delete-orphan"` so deleting a stopwatch
  removes its intervals.
- `backend/src/routes/stopwatch.py` — record an interval in `stop_stopwatch` (skip `isTotal` and
  zero-length segments); delete the stopwatch's rows for the day in `reset_stopwatch`; new
  `GET /stopwatches/intervals/<date_string>/` endpoint returning the day's intervals (joined with
  the stopwatch title) ordered by `start_time`, scoped by `user_id`.
- `backend/tests/test_stopwatch_intervals.py` — new test module (see notes).
- `frontend/src/Pages/stopwatchpage.jsx` — collapsed "Session log" disclosure below the stopwatch
  grid; lazy-fetch the day's intervals on first expand; refresh after stop/reset/delete while
  expanded.
- `frontend/src/Components/StopwatchSessionLog.jsx` — new presentational component for the
  session list (the page is already ~1000 lines; keep the rendering out of it).
- `frontend/src/Pages/stopwatchpage.css` — styles for the disclosure + session list.

## Decisions needed
_None — presentation (collapsed session list) and reset behavior (delete the day's rows) are
decided._

## Risk
- **Involvement:** Moderate — a new table + model, one new endpoint, small inserts/deletes in the
  stop and reset paths, and one new collapsed frontend section/component. No changes to XP,
  carry-forward, or the Total-goal accounting.
- **Review attention:** Medium — it touches `stop_stopwatch`, the single hottest write path in the
  stopwatch flow (every pause, navigation, pagehide, and midnight rollover goes through it), so a
  bug there loses tracked time; but the addition is append-only, the schema change is a brand-new
  table picked up by the existing `db.create_all()` (app.py:146) with no `ALTER TABLE` against
  prod, and the main-grid read path is untouched.

## Implementation notes
- **Model:** follow the existing model shape in `db.py` (kwargs `__init__`, `serialize` returning
  ISO strings). Wrap both datetimes with `ensure_utc(...)` in `serialize` — SQLite drops tzinfo
  (see CLAUDE.md / docs/architecture.md). `date` duplicates the parent stopwatch's `date` so the
  day query needs no join for filtering; still join to `Stopwatch` for the title.
- **No `ensure_*` migration needed:** the `ensure_*` helpers in `app.py` exist for new *columns*
  on existing tables; a brand-new table is created by `db.create_all()` on startup. Don't add one.
- **Recording (stop_stopwatch):** after computing `increment`, insert
  `StopwatchInterval(stopwatch_id=stopwatch.id, user_id=user_id, date=stopwatch.date,
  start_time=ensure_utc(stopwatch.interval_start), end_time=ensure_utc(stopwatch.end_time))`
  in the same commit. Guards: skip when `stopwatch.isTotal` (the frontend never stops the Total
  directly, but the endpoint doesn't forbid it), and skip zero-length intervals
  (`end_time == interval_start`) — which is also exactly what a stale-finalized stopwatch looks
  like (`finalize_stale_stopwatches` sets `end_time = interval_start` and must record nothing).
- **Reset:** delete `StopwatchInterval` rows for (`stopwatch_id`, `stopwatch.date`) inside
  `reset_stopwatch`, same commit as the zeroing. Reset-while-running stops the watch without
  crediting time, so no interval exists for the in-flight segment — nothing extra to handle.
- **Manual edits (accepted quirk):** `curr_duration` edits via the PUT endpoint create no
  interval, so the log reflects only real timed segments, not edited totals. Do **not** invent
  synthetic intervals for edits. The collapsed-by-default presentation is deliberate cover for
  this: the log is an opt-in detail view, not a second source of truth shown alongside the totals.
- **Delete:** the cascade relationship covers `delete_stopwatch`; no route change needed beyond
  verifying with a test.
- **Read endpoint:** mirror `get_stopwatches`' shape — `@jwt_required()`, parse
  `date.fromisoformat`, filter by `user_id` and date, `success_response({"intervals": [...]})`
  with each item as `{id, stopwatch_id, title, start_time, end_time}`. No carry-forward or other
  side effects here.
- **Frontend (discreet + lazy):** render a small disclosure row ("Session log ▸") below the
  stopwatch grid, collapsed by default on every visit/date change (no persistence of the open
  state). Fetch via the existing `fetchWithAuth` (`useFetch`) **only when the user expands it**,
  not in the date-change data effect (stopwatchpage.jsx:110-172); collapse resets to unloaded on
  date change so re-expanding refetches. While expanded, re-fetch after `handleStop` /
  `handleReset` / `deleteStopwatch` resolve. Render times with `toLocaleTimeString` (stored UTC →
  shown local). A currently running stopwatch's open segment isn't in the table yet; while
  expanded, show it as "started 10:04 · running" derived from the running stopwatch's
  `interval_start`. For a past `selectedDate`, just render the fetched rows; for a future date,
  show nothing (mirror the existing `isFuture` guards). Empty state: "No sessions recorded."
- **Tests (`backend/tests/test_stopwatch_intervals.py`):** follow the style of
  `test_stopwatch_stale_finalize.py` / `test_stopwatch_carryforward.py` (client fixture from
  `conftest.py`). Cover: stop records one interval with the expected bounds; two start/stop
  cycles record two ordered intervals; the Total row gets no interval rows; stale finalize
  records nothing; reset deletes that stopwatch's rows for the day (and only that stopwatch's,
  only that day's); deleting a stopwatch removes its intervals (cascade); GET endpoint returns
  only the requesting user's rows (add a case to the user-scoping pattern in
  `test_user_scoping.py` or inline here); zero-length segments are skipped; a manual
  `curr_duration` PUT creates no interval.
- **XP:** untouched — intervals are a pure record; `recompute_from` calls stay exactly as they
  are.
