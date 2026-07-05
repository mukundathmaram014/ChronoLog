---
status: built
---

# 0014 — Per-habit weekly repeat days

## Problem / Goal
Habits currently carry forward to every day. The author wants, when creating/editing a habit, to choose
**which days of the week** it repeats on (e.g. "Mon/Wed/Fri only"). On days not selected, the habit
shouldn't appear.

## Context — current behavior
- Habit carry-forward mirrors the stopwatch logic: when a new day is opened, the previous day's habits
  are copied forward (`backend/src/routes/habits.py`), gated by the DeletedDay "intentionally emptied"
  marker.
- Habit model (`backend/src/db.py:27-59`) has only `description`, `done`, `date`, `user_id` — no
  recurrence info.
- Add/edit habit UI lives in `frontend/src/Pages/habitpage.jsx`; the row renders via
  `frontend/src/Components/HabitItem.jsx`.

## Decisions (made)
1. **Representation: a 7-bit bitmask** stored as an integer `repeat_days`, one bit per weekday
   (`date.weekday()`, 0 = Mon … 6 = Sun); bit set = repeats that day. Default `127` (`0b1111111`, all
   seven days = today's behavior). Membership test: `repeat_days & (1 << target_weekday)`.
2. **Carry-forward semantics:** on opening a day, a habit is present **iff** that day's weekday bit is
   set in its `repeat_days`. Keep the DeletedDay "intentionally emptied" behavior and the duplicate
   guard intact.
3. **Editing applies forward only:** changing a habit's repeat days affects **future** carry-forward
   only — already-created past rows are left untouched.

## Affected files
- `backend/src/db.py` — add `repeat_days` (Integer, 7-bit bitmask, default `127`) to `Habit`;
  `__init__` + `serialize`. **Schema change** — see Risks.
- `backend/src/app.py` — run a startup SQLite migration for existing DBs:
  `ALTER TABLE habits ADD COLUMN repeat_days INTEGER NOT NULL DEFAULT 127`.
- `backend/src/routes/habits.py` — create/edit accept `repeat_days`; carry-forward only creates the
  habit when the target day's weekday is in its set; preserve DeletedDay + duplicate guard.
- `frontend/src/Pages/habitpage.jsx` — add/edit form: a weekday picker (7 toggles); send `repeat_days`.
- (Maybe) `frontend/src/Components/HabitItem.jsx` — optional small indicator of repeat days.

## Approach
1. Add `repeat_days` (Integer bitmask, default `127` = all days) to the model + `serialize`.
2. Create/edit routes parse the 7 weekday toggles into the bitmask and store it (edits apply forward
   only — don't rewrite past rows).
3. In carry-forward, compute the target day's `weekday()` and only create a habit when its bit is set
   (`repeat_days & (1 << weekday)`); keep DeletedDay and the duplicate-title guard intact.
4. Add the weekday toggle UI (7 checkboxes) to the habit add/edit form, reading/writing the bitmask.

## Acceptance criteria
- A habit can be created/edited with a chosen set of weekdays; the set persists.
- The habit appears only on matching weekdays going forward; default (all days) matches current
  behavior.
- Intentionally-deleted days stay empty; no duplicate habits created.

## Testing / verification
- Create a Mon/Wed/Fri habit; advance across a week; confirm it appears only on those days.
- A default habit still appears every day.
- Edit the day set and confirm future days reflect it while past rows are unchanged.

## Risk
- **Involvement:** Involved — schema change (`repeat_days`), weekday-gated carry-forward, and a weekday-picker UI.
- **Review attention:** High — alters carry-forward semantics + prod migration; carry-forward is easy to regress, so add tests (all-days default, a weekday subset, deleted day, multi-day gap).

## Risks & notes
- **SQLite migration** (no Alembic; `create_all` won't alter `habits`): add `repeat_days` with a one-off
  `ALTER TABLE habits ADD COLUMN repeat_days INTEGER NOT NULL DEFAULT 127` so existing rows default to
  all-days (= current behavior). Call out the exact statement in the PR.
- Carry-forward is easy to regress; add tests for: all-days default, a subset, a deleted day, and a
  multi-day gap.
