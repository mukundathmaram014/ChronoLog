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

## ⚠️ Decision needed
1. **Representation of repeat days.** Recommended: a 7-bit set stored as a small string/int (e.g. CSV
   `"0,2,4"` of `date.weekday()` indices, or a 7-char bitmask). Confirm the encoding.
2. **Carry-forward semantics.** Recommended: on opening a day, a habit is present iff that day's weekday
   is in its repeat set (default = all 7 days, matching today's behavior). Must keep the DeletedDay
   behavior and the duplicate guard. Confirm.
3. **Editing applies forward only?** Recommended: changing a habit's repeat days affects future
   carry-forward, not already-created past rows. Confirm.

## Affected files
- `backend/src/db.py` — add `repeat_days` to `Habit` (per Decision 1); `__init__` + `serialize`.
  **Schema change** — see Risks.
- `backend/src/routes/habits.py` — create/edit accept `repeat_days`; carry-forward only creates the
  habit when the target day's weekday is in its set; preserve DeletedDay + duplicate guard.
- `frontend/src/Pages/habitpage.jsx` — add/edit form: a weekday picker (7 toggles); send `repeat_days`.
- (Maybe) `frontend/src/Components/HabitItem.jsx` — optional small indicator of repeat days.

## Approach
1. Add `repeat_days` to the model (default = all days) + serialize.
2. Create/edit routes parse and store the set.
3. In carry-forward, compute the target day's `weekday()` and only create habits whose set includes it;
   keep Total-less habit logic, DeletedDay, and duplicate-title guard intact.
4. Add the weekday toggle UI to the habit add/edit form.

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
- **Review attention:** High — alters carry-forward semantics + prod migration + an encoding decision; carry-forward is easy to regress, so add tests.

## Risks & notes
- **SQLite migration** (no Alembic; `create_all` won't alter `habits`): adding `repeat_days` needs an
  `ALTER TABLE`/backfill defaulting existing rows to all-days (= current behavior).
- Carry-forward is easy to regress; add tests for: all-days default, a subset, a deleted day, and a
  multi-day gap.
