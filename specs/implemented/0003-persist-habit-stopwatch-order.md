---
status: built
---

# 0003 — Persist habit & stopwatch order across reloads

## Problem / Goal
Drag-reordering habits and stopwatches only mutates local React state and is lost on reload.
`handleDragEnd` calls `arrayMove` on state but never tells the backend
(`frontend/src/Pages/stopwatchpage.jsx:548`, `frontend/src/Pages/habitpage.jsx:186`). On the next
fetch, items come back in DB insertion order (`get_habits` / `get_stopwatches` use an unordered
`query.filter_by(...).all()`). Make a user's chosen order stick.

## Scope
- In scope: add a per-row `position` to `Habit` and `Stopwatch`, order reads by it, add reorder
  endpoints, and persist order from the two `handleDragEnd` handlers via `useFetch`.
- Out of scope / non-goals: no DnD library change; no change to carry-forward logic beyond seeding
  `position` on created rows; the Total stopwatch is handled in spec 0004 (it should not participate
  in ordering).

## Affected files
- `backend/src/db.py` — add `position` (Integer) to `Habit` and `Stopwatch`; include in `serialize()`.
- `backend/src/routes/habits.py` — order `get_habits` by `position, id`; set `position` on create
  (`create_habit_for_date`); new reorder route.
- `backend/src/routes/stopwatch.py` — order `get_stopwatches` by `position, id`; set `position` in
  `create_stopwatch_for_date`; new reorder route (regular stopwatches only, never the Total).
- `frontend/src/Pages/habitpage.jsx`, `frontend/src/Pages/stopwatchpage.jsx` — in `handleDragEnd`,
  after `arrayMove`, PATCH the new ordering through `useFetch`.

## Approach
1. Add `position = db.Column(db.Integer, nullable=False, default=0)` to both models and add it to
   each `serialize()`. Follow existing column style.
2. On create, set `position = (max position for that user_id + date) + 1` so new rows append.
   Scope the max query by `user_id` and `date` (per CLAUDE.md, always scope by `user_id`).
3. In `get_habits` / `get_stopwatches`, replace `.all()` with `.order_by(Habit.position, Habit.id)`
   (and the Stopwatch equivalent). Keep the Total stopwatch first regardless (see 0004).
4. Add `PATCH /habits/reorder/` and `PATCH /stopwatches/reorder/`: body `{ "date": ..., "order": [ids] }`,
   scoped by `user_id`; assign `position` by index. Use `success_response`/`failure_response`. For
   stopwatches, ignore/skip the Total id.
5. In both `handleDragEnd`, after `arrayMove`, call the reorder endpoint with the new id list. On
   failure, log (existing pattern) — optionally refetch to resync.

## Acceptance criteria
- Reorder habits/stopwatches, reload the page → order is preserved.
- New items appear at the end of the list.
- The Total stopwatch stays in its fixed position and is never sent in the reorder payload.

## Testing / verification
- Habits page and Stopwatches page: drag to reorder, hard-refresh, confirm order persists.
- `GET /habits/<date>/` and `GET /stopwatches/<date>/` return items in the saved order.

## Risk
- **Involvement:** Moderate — backend schema (`position` column) + reorder endpoints on two routes + two frontend `handleDragEnd` handlers.
- **Review attention:** High — needs a hand-applied prod `ALTER TABLE` (no Alembic); a wrong/omitted migration breaks prod. Pairs with 0004.

## Risks & notes
- **Migration:** schema is created via `db.create_all()` (`backend/src/app.py:61`), which does NOT
  add columns to existing SQLite tables, and there is no Alembic. The new `position` column must be
  added to the live `instance/ChronoLog.db` (e.g. a one-off `ALTER TABLE ... ADD COLUMN position
  INTEGER NOT NULL DEFAULT 0`) or it will break in prod. Call this out in the PR and include the
  exact ALTER statements.
- Decide `position` scoping: per (user, date) is simplest and matches how lists are fetched per day.
- Pairs with **0004** (Total stopwatch should be excluded from the sortable list).
