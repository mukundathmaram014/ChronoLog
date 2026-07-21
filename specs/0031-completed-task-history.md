---
title: Record when a task was completed and add an opt-in completed-task history view
status: draft
---

# Record when a task was completed and add an opt-in completed-task history view

## Summary
Completed tasks currently vanish. `get_tasks` (`backend/src/routes/tasks.py:77-86`) buckets a
user's top-level tasks into overdue / today / upcoming, and the past bucket deliberately drops
anything done:

```python
if task.date < today:
    if not task.done:
        overdue.append(task.serialize())
```

The rows are still in the database — nothing deletes them — but no endpoint ever returns them
again, so once the due date passes there is no way to see what you finished. This bites hardest on
periodic tasks: completing one calls `spawn_next_occurrence` (tasks.py:39-59), which creates the
next occurrence and leaves the completed one behind, invisible forever. Habits do not have this
problem (one row per day, plus the calendar endpoints and `HabitCalendar` heatmap); the Task
subsystem, added in spec 0021, has no history surface at all. That gap is what this spec closes.

Two parts. **First**, `Task` gets a `completed_date` column, mirroring the existing `Goal` model
(`db.py:130-166`), which already stores `completed_date` and sets/clears it on the done transition
in `update_goal` (`goals.py:86-98`). Without it the only date available is `date`, the *due* date —
so an overdue task finished today would file itself under a due date weeks ago, which is exactly
wrong for a "what did I actually get done" view. **Second**, the task page gains a collapsed
**"Completed"** disclosure below the task list, lazy-fetched on first expand from a new
`GET /api/tasks/completed/...` endpoint. The idea's phrasing — "*if you would like to* see that
history" — asks for something opt-in rather than a fourth always-on group competing with Overdue /
Today / Upcoming, so this follows the spec 0030 session-log pattern: a discreet disclosure plus a
small presentational component, keeping the rendering out of the already-long page.

**Decided:** the history is **read-only** — rows render with their descriptions, dates and
sub-task counts, but no checkbox, edit or delete affordance. Un-completing a past occurrence of a
periodic task would resurrect it into Overdue while its successor already exists, and there is no
reason to open that door for a view whose only job is to show history. This matches
`StopwatchSessionLog`, which is likewise purely presentational.

## Affected files
- `backend/src/db.py` — add `completed_date = db.Column(db.Date, nullable=True)` to `Task`
  (currently lines 79-126), set it in `__init__` from kwargs, and include it in `serialize()`.
- `backend/src/app.py` — new `ensure_task_completed_date_column()` following the eleven existing
  `ensure_*` helpers (lines 28-115), called from the startup block (lines 159-172). Required:
  `create_all()` never adds columns to an existing table, so prod breaks without it.
- `backend/src/routes/tasks.py` — set/clear `completed_date` on the done transition in
  `update_task` (including the auto-complete-parent branch at lines 184-189); new
  `get_completed_tasks` endpoint.
- `backend/tests/test_tasks.py` — extend: `completed_date` set on completion, cleared on
  un-completion, set on the auto-completed parent, and not clobbered by an unrelated edit.
- `backend/tests/test_task_history.py` — new; covers the history endpoint (see notes).
- `backend/tests/test_migrations.py` — add a case for the new column, matching the existing
  drop-column → `ensure_*` → re-added → idempotent shape.
- `backend/tests/test_user_scoping.py` — add the new endpoint to the per-user scoping coverage.
- `frontend/src/Pages/taskpage.jsx` — collapsed "Completed" disclosure below the three task groups;
  lazy fetch on first expand; refresh while expanded after a task is completed.
- `frontend/src/Components/CompletedTaskLog.jsx` — new presentational component for the grouped
  list (taskpage.jsx is already ~370 lines with two modals).
- `frontend/src/Pages/taskpage.css` — styles for the disclosure and the history rows.

## Decisions needed
- [ ] **Scope: tasks only, or a unified "completed" feed?** The idea says "completed tasks", which
  most directly means the `Task` subsystem. But `Goal` already carries `completed_date` and
  finished goals are arguably the same kind of history, and habits have their own calendars.
  Tasks-only is the smaller, cleaner change; a combined feed means a cross-model endpoint and a
  mixed-type list. Recommend tasks-only for this spec.
- [ ] **Range contract: bounded lookback or paginated all-time?** A task repeating daily produces
  365 completed rows a year, so an unbounded list will not stay usable. Options: a fixed window
  (e.g. `GET /tasks/completed/<date_string>/<period>/` reusing the day/week/month/year vocabulary
  `statistics.py:15` already uses for `get_period_range`), or all-time with a `limit`/`offset` and
  a "load more" button. Recommend the period-based window for consistency with the rest of the app.

## Risk
- **Involvement:** Moderate — one nullable column plus its startup migration, a write-path change
  in `update_task`, one new read endpoint, and one new collapsed frontend section/component. Spread
  across backend and frontend but each piece is small and follows an existing template.
- **Review attention:** Medium — the schema change is an `ALTER TABLE` against the **production
  SQLite DB**, which is the repo's known recurring bug class (`test_migrations.py` exists solely to
  guard it), and the write path touched (`update_task`) is the one every task completion goes
  through, including the periodic-spawn and auto-complete-parent branches. Mitigating: the column
  is nullable with no default backfill, nothing reads it except the new endpoint, XP is untouched
  (tasks earn no XP), and the read path is additive — existing `get_tasks` behavior does not change.

## Implementation notes
- **Do not reuse the `date` body key for completion.** `update_task` already treats `"date" in
  body` as a *reschedule* of the due date (tasks.py:168-174), unlike `update_goal`, where `date`
  means the completion date because goals have no due date. Send the client's local day under a
  distinct key — `completed_date` (or `today`) — and fall back to `date.today()` when absent. The
  server may run in a different timezone than the user, which is why the client passes its own day
  rather than the server assuming.
- **Write path (`update_task`, around lines 176-189):** mirror `update_goal`'s three-branch shape.
  On `task.done and not was_done` set `task.completed_date`; on `was_done and not task.done` set it
  back to `None`. Do this for sub-tasks too, and critically also set it on the **parent** in the
  auto-complete branch (lines 184-189) — a parent completed indirectly by its last sub-task must
  get a `completed_date` or it silently disappears from the history. No `recompute_from` call:
  unlike goals and habits, tasks grant no XP, so `xp.py` is not involved at all.
- **`spawn_next_occurrence`** creates rows with `done=False`, so the new column defaults to `NULL`
  there — no change needed to that helper.
- **Legacy rows:** every already-completed task has `completed_date = NULL` after the migration,
  and it cannot be backfilled (the information was never recorded). Have the endpoint fall back to
  `date` — `COALESCE(completed_date, date)` in spirit — so pre-deploy history still appears, keyed
  by due date. Note this in the PR; it means early entries are approximate.
- **Read endpoint:** follow `get_tasks`' shape — `@jwt_required()`, `int(get_jwt_identity())`,
  `date.fromisoformat`, `success_response(...)`, and filter `parent_id=None` so sub-tasks nest
  under their parents via `serialize()` rather than appearing as top-level entries. Filter
  `done=True`, scope by `user_id`, order by the effective completion date descending (most recent
  first — this is a history, not a queue). Return `{"completed": [...]}`. Exclude future-dated
  rows the way `get_habits_stats` guards with `date.today()`, if the chosen range can reach them.
- **Frontend:** register nothing new in `App.js` or `Navbar.jsx` — the disclosure lives on the
  existing task page. Fetch through `useFetch` (`fetchWithAuth`), never bare `fetch`. Collapsed by
  default on every visit, with no persistence of the open state; fetch only on first expand, and
  while expanded re-fetch after `handleToggleTask` resolves so a task just checked off appears.
  Group rows by their completion date with the existing `formatDateHeading` helper
  (taskpage.jsx:180-182) for visual consistency with the Overdue/Upcoming headings. Empty state:
  "No completed tasks yet." Reuse the `completed` CSS class already applied to done task rows.
- **Tests (`backend/tests/test_task_history.py`):** use the `client` fixture and the
  `create_task`/`update_task`/`auth_token` helpers already in `test_tasks.py`. Cover: a completed
  past task appears in history but still not in `get_tasks`' overdue bucket; an undone past task
  appears in overdue but not in history; completing a periodic task yields exactly one history
  entry while its spawned successor stays out; a legacy row with `completed_date = NULL` falls back
  to its due date; sub-tasks nest rather than appearing top-level; results are ordered most-recent
  first; and another user's completed tasks are never returned.
