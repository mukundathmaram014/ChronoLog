---
title: Record when a task was completed and add an opt-in completed-task history view
status: decided
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
problem (one row per day, plus the calendar endpoints and `HabitCalendar` heatmap), and goals
already show their own completed section (`goalpage.jsx:179-180, 246-251`, backed by
`Goal.completed_date`). The Task subsystem, added in spec 0021, is the only one with no history
surface at all. That gap is what this spec closes.

Two parts. **First**, `Task` gets a `completed_date` column, mirroring the existing `Goal` model
(`db.py:130-166`), which already stores `completed_date` and sets/clears it on the done transition
in `update_goal` (`goals.py:86-98`). Without it the only date available is `date`, the *due* date —
so an overdue task finished today would file itself under a due date weeks ago, which is exactly
wrong for a "what did I actually get done" view. **Second**, the task page gains a collapsed
**"Completed"** disclosure below the task list, lazy-fetched on first expand from a new
`GET /api/tasks/completed/` endpoint. The idea's phrasing — "*if you would like to* see that
history" — asks for something opt-in rather than a fourth always-on group competing with Overdue /
Today / Upcoming, so this follows the spec 0030 session-log pattern: a discreet disclosure plus a
small dedicated component, keeping the rendering out of the already-long page.

**Decided — scope is tasks only.** Goals already have a completed section on their own page, and
habit history is the `HabitCalendar` heatmap plus the stats page; adding either here would be a
second or third view of data that already has a home. Tasks are the only subsystem missing one.

**Decided — no checkbox or edit in the history.** Rows render with their descriptions, dates and
sub-tasks, but are not interactive for completion or editing (delete is the one exception — see
below). Un-completing a past occurrence of a periodic task would resurrect it into Overdue while
its successor already exists, and there is no reason to open that door for a view whose only job is
to show history.

**Decided — history rows get a delete affordance, and deleting resets the disclosure to page 0.**
`DELETE /api/tasks/<id>/` already exists and cascades to sub-tasks, so the backend cost is zero.
The wrinkle is that delete breaks offset paging: `offset` is a *position*, not a bookmark, so
removing a row from a loaded page shifts every later row up one, and the next "Show more"
(`offset=50`) starts past the row that just moved into position 50 — it silently disappears from
the history with no error or visible gap. Resetting to page 0 after each delete (re-fetch from the
top, discard the loaded pages) sidesteps this entirely and reuses the reset already specified after
a toggle. The alternative, keyset paging — "give me the 50 rows older than (date, id)" — anchors
the cursor to a row so deletes above it don't move it, and would preserve the user's scroll depth,
but it is a materially more involved endpoint than `limit`/`offset` for a view that is mostly
browsed a page or two deep. Accepted cost: a user who has clicked "Show more" several times returns
to the top after a delete.

**Decided — accept the same-day overlap.** `get_tasks` only filters completed tasks out of the
*past* bucket; anything dated today stays in `today` whether done or not (tasks.py:81-82). So a task
checked off today appears both in Today (struck through, still interactive) and in the Completed
disclosure. This is accepted rather than designed around. The alternative — starting history at
"before today" — would mean checking a box while the disclosure is open produces no visible result,
which defeats the point of re-fetching on toggle. Since the disclosure is collapsed by default the
overlap is usually invisible, and when it is open the row appearing is confirmation, not noise.

**Decided — pagination, not a period window.** The endpoint takes `limit`/`offset` query params
(default limit 50) and the disclosure renders a "Show more" control that appends the next page,
letting the user walk back as far as they like. The alternative considered was reusing the
day/week/month/year vocabulary from `get_period_range` (`statistics.py:15-31`), but that would
require adding a period selector to the task page, which has no date or period controls today —
new UI chrome purely to browse history. Offset paging needs no controls beyond one link and
degrades gracefully for a daily-repeating task (50 rows ≈ 7 weeks per page).

## Affected files
- `backend/src/db.py` — add `completed_date = db.Column(db.Date, nullable=True)` to `Task`
  (currently lines 79-126), set it in `__init__` from kwargs, and include it in `serialize()`.
- `backend/src/app.py` — new `ensure_task_completed_date_column()` following the eleven existing
  `ensure_*` helpers (lines 28-115), called from the startup block (lines 161-172). Required:
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
  lazy fetch on first expand; "Show more" paging; refresh while expanded after a task is completed;
  delete handler that resets the history to page 0.
- `frontend/src/Components/CompletedTaskLog.jsx` — new component for the grouped list, taking the
  rows and a delete callback as props (taskpage.jsx is already ~370 lines with two modals).
- `frontend/src/Pages/taskpage.css` — styles for the disclosure, the history rows, the row delete
  button and "Show more".

## Decisions needed
- [x] Scope — tasks only. Goals and habits already have history surfaces.
- [x] Range contract — `limit`/`offset` paging with "Show more", not a period window.
- [x] Same-day overlap — accepted; a task completed today shows in both Today and Completed.
- [x] Delete affordance on history rows — yes, with a reset to page 0 after each delete. Keyset
  paging rejected as disproportionate. Un-complete and edit remain out.

## Risk
- **Involvement:** Moderate — one nullable column plus its startup migration, a write-path change
  in `update_task`, one new read endpoint, and one new collapsed frontend section/component wired to
  the existing delete endpoint. Spread across backend and frontend but each piece is small and
  follows an existing template.
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
  distinct key — `completed_date` — and fall back to `date.today()` when absent. The server may run
  in a different timezone than the user, which is why the client passes its own day rather than the
  server assuming. `handleToggleTask` (taskpage.jsx:108) already has `today` in scope to send.
- **Write path (`update_task`, around lines 176-189):** mirror `update_goal`'s branch shape
  (goals.py:86-98, minus the `recompute_from` calls). On `task.done and not was_done` set
  `task.completed_date`; on `was_done and not task.done` set it back to `None`. Do this for
  sub-tasks too, and critically also set it on the **parent** in the auto-complete branch (lines
  184-189) — a parent completed indirectly by its last sub-task must get a `completed_date` or it
  silently disappears from the history. No `recompute_from` call: unlike goals and habits, tasks
  grant no XP, so `xp.py` is not involved at all.
- **`spawn_next_occurrence`** creates rows with `done=False`, so the new column defaults to `NULL`
  there — no change needed to that helper.
- **Legacy rows:** every already-completed task has `completed_date = NULL` after the migration,
  and it cannot be backfilled (the information was never recorded). Have the endpoint fall back to
  `date` — `COALESCE(completed_date, date)` in spirit — so pre-deploy history still appears, keyed
  by due date. Note this in the PR; it means early entries are approximate. The same expression
  drives the ordering, so legacy rows interleave sensibly rather than sinking to the bottom.
- **Read endpoint (`GET /api/tasks/completed/`):** follow `get_tasks`' shape — `@jwt_required()`,
  `int(get_jwt_identity())`, `success_response(...)`, and filter `parent_id=None` so sub-tasks nest
  under their parents via `serialize()` rather than appearing as top-level entries. Filter
  `done=True`, scope by `user_id`, order by the effective completion date descending, then `id`
  descending as a tiebreak (several tasks finished the same day need a stable order for paging).
  Read `limit` and `offset` from `request.args` with defaults 50 and 0; clamp `limit` to a sane
  ceiling and reject non-integers rather than 500ing. Return
  `{"completed": [...], "has_more": <bool>}` — `has_more` lets the frontend decide whether to
  render "Show more" without a second round trip (fetch `limit + 1` rows and trim).
- **Frontend:** register nothing new in `App.js` or `Navbar.jsx` — the disclosure lives on the
  existing task page. Fetch through `useFetch` (`fetchWithAuth`), never bare `fetch`. Collapsed by
  default on every visit, with no persistence of the open state; fetch page 0 only on first expand.
  "Show more" appends the next page rather than replacing. While expanded, re-fetch **page 0 only**
  after `handleToggleTask` resolves so a task just checked off appears — do not try to re-fetch
  every loaded page; simplest correct behavior is to reset back to the first page. Do **not** filter
  the history against what the Today group is already rendering: the same-day overlap is accepted
  (see above), so no cross-group deduplication is needed anywhere. Group rows by
  their effective completion date with the existing `formatDateHeading` helper (taskpage.jsx:180-182)
  for visual consistency with the Overdue/Upcoming headings. Empty state: "No completed tasks yet."
  Reuse the `completed` CSS class already applied to done task rows.
- **Delete from history:** reuse the existing `DELETE /api/tasks/<id>/` — no backend change. Add a
  handler alongside `handleDeleteTask` (taskpage.jsx:118-125) that, once the delete resolves, does
  **both** `fetchTasks()` and a history reset to page 0. Both are needed: a task completed *today*
  lives in the Today bucket and the history simultaneously (the accepted overlap), so deleting it
  from one place must clear it from the other. Pass the handler into `CompletedTaskLog` as a prop —
  this makes it not-quite-purely-presentational, which is fine, but keep the fetching and paging
  state in `taskpage.jsx` and let the component stay a render-plus-callback. Delete acts on
  top-level history rows; nested sub-task rows get no separate button, since deleting the parent
  cascades to them.
- **Sub-task dates:** a parent's history entry is filed under the *parent's* completion date even
  if its sub-tasks were finished on earlier days. That is intentional — the parent is the unit of
  history — and sub-task rows should render without their own date to avoid implying otherwise.
- **Tests (`backend/tests/test_task_history.py`):** use the `client` fixture and the
  `create_task`/`update_task`/`auth_token` helpers already in `test_tasks.py`. Cover: a completed
  past task appears in history but still not in `get_tasks`' overdue bucket; an undone past task
  appears in overdue but not in history; completing a periodic task yields exactly one history
  entry while its spawned successor stays out; a legacy row with `completed_date = NULL` falls back
  to its due date; sub-tasks nest rather than appearing top-level; results are ordered most-recent
  first; `limit`/`offset` page without dropping or duplicating rows across page boundaries and
  `has_more` flips false on the last page; deleting a completed task removes it (and its sub-tasks)
  from history; and another user's completed tasks are never returned.
