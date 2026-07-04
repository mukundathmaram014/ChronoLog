# 0012 — Optional goal time per stopwatch

## Problem / Goal
Every stopwatch currently must have a goal time (defaults to 1 hour). The author wants the option, when
adding/editing a stopwatch, to give it **no goal** — in which case the goal effectively equals the
current elapsed time, so progress is always "complete" and the goal/progress math simplifies. Let a
stopwatch opt out of having a goal.

## Context
- `goal_time` is a non-nullable `Float` on the Stopwatch model, defaulting to `3600000` ms
  (`backend/src/db.py:75,90`).
- The Total stopwatch aggregates goal time; stats sum `goal_time` across days
  (`backend/src/routes/statistics.py`), and `total_goal_time` is shown on the stats page.
- Progress rings use `time / goal_time`: `CircularProgress` per stopwatch (`StopwatchItem.jsx:27`) and
  `CircularProgressTotal` (`statisticspage.jsx:139-200`, `StopwatchItem.jsx:12`).

## Decisions (made)
1. **Represent "no goal" as `goal_time = NULL`** — a nullable `goal_time`, `NULL` = no goal. (The
   separate `has_goal` boolean was rejected to avoid a second source of truth.) Every spot that reads
   `goal_time` (ring math, Total aggregation, stats sums) treats `NULL` as "goal = current elapsed".
2. **No-goal ring renders as full / 100%** (complete), with the "Goal: Xh Ym" label hidden.
3. **Total + stats:** a no-goal stopwatch contributes **its own elapsed time** to the Total's goal, so it
   reads as complete and never drags the Total under 100%.

## Affected files
- `backend/src/db.py` — make `Stopwatch.goal_time` nullable (`NULL` = no goal); update `__init__` +
  `serialize`. **Schema change** — see Risks.
- `backend/src/routes/stopwatch.py` — accept the no-goal choice on create/edit; keep the Total's goal
  consistent when summing children.
- `backend/src/routes/statistics.py` — `total_goal_time` aggregation must handle no-goal stopwatches.
- `frontend/src/Pages/stopwatchpage.jsx` — add-stopwatch + edit-stopwatch forms: a "no goal time" toggle
  that disables/omits the goal input.
- `frontend/src/Components/StopwatchItem.jsx` — goal label + `CircularProgress` rendering for no-goal.
- `frontend/src/Pages/statisticspage.jsx` — `CircularProgressTotal` / goal display for no-goal.

## Approach
1. Make `goal_time` nullable in the model + `serialize` (`NULL` = no goal).
2. Backend create/edit: when "no goal" is chosen, store `goal_time = NULL`; everywhere `goal_time` feeds
   progress, treat no-goal as `goal = current curr_duration` so progress reads as complete.
3. Frontend: add the toggle to the add/edit forms; when on, store no goal, hide the goal input and the
   goal label, and render the ring as full/100%.
4. Total + stats: a no-goal stopwatch contributes its own elapsed time to `total_goal_time`, so the
   Total ring and stats stay coherent (never NaN or under 100% from a no-goal item).

## Acceptance criteria
- A stopwatch can be created/edited with no goal; its ring shows complete and no goal label.
- Goal-bearing stopwatches behave exactly as before.
- Total ring and stopwatch stats don't break or show negative/NaN progress with mixed goals.

## Testing / verification
- Create a no-goal stopwatch, run it, confirm ring + Total + stats render sanely.
- Edit a goal stopwatch to no-goal and back; confirm persistence and display.
- A day mixing goal and no-goal stopwatches shows a coherent Total.

## Risk
- **Involvement:** Involved — schema change + two backend routes + three frontend files; every `goal_time` read must be audited.
- **Review attention:** High — prod `ALTER TABLE` migration plus divide-by-zero/NaN risk across rings, Total, and stats sums (every `goal_time` read must treat `NULL` as "goal = elapsed").

## Risks & notes
- **SQLite migration:** the app uses `db.create_all()` (no Alembic); `create_all` won't alter the
  existing `stopwatches` table. Relaxing `goal_time` from `NOT NULL` to nullable **can't** be done with a
  simple `ALTER TABLE ... ADD COLUMN` — SQLite needs a **table rebuild** (create a new table with the
  nullable column, copy rows over, drop the old, rename), or a documented reset. Spell out the exact
  steps in the PR (same migration class as spec 0003); coordinate with spec 0013, which also alters
  `stopwatches`.
- Audit every `goal_time` read (rings, Total, stats day/week/month/year sums) so none divides by zero or
  produces NaN for no-goal stopwatches.
