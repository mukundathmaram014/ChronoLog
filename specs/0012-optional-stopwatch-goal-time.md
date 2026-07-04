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

## ⚠️ Decision needed
1. **How to represent "no goal".** Options:
   - **(Recommended) `goal_time` nullable**, `NULL` = no goal. Cleanest semantically; touches every spot
     that reads `goal_time` (ring math, Total aggregation, stats sums) to treat `NULL`/no-goal as
     "goal = current time".
   - A separate `has_goal` boolean, leaving `goal_time` populated but ignored. Less invasive to math but
     adds a second source of truth.
2. **What a no-goal ring shows.** Recommended: render it as full/100% (or a neutral "no goal" ring) and
   hide the "Goal: Xh Ym" label. Confirm the visual.
3. **Total + stats with mixed goals.** How `total_goal_time` behaves when some stopwatches have no goal —
   recommended: a no-goal stopwatch contributes its own elapsed time to the Total's goal (so it never
   drags the Total under 100%). Confirm.

## Affected files
- `backend/src/db.py` — `Stopwatch.goal_time` (make nullable, or add `has_goal`); update `__init__` +
  `serialize`. **Schema change** — see Risks.
- `backend/src/routes/stopwatch.py` — accept the no-goal choice on create/edit; keep the Total's goal
  consistent when summing children.
- `backend/src/routes/statistics.py` — `total_goal_time` aggregation must handle no-goal stopwatches.
- `frontend/src/Pages/stopwatchpage.jsx` — add-stopwatch + edit-stopwatch forms: a "no goal time" toggle
  that disables/omits the goal input.
- `frontend/src/Components/StopwatchItem.jsx` — goal label + `CircularProgress` rendering for no-goal.
- `frontend/src/Pages/statisticspage.jsx` — `CircularProgressTotal` / goal display for no-goal.

## Approach
1. Pick the representation (Decision 1) and update the model + serialize accordingly.
2. Backend create/edit: when "no goal" is chosen, store it; everywhere `goal_time` feeds progress,
   treat no-goal as `goal = current curr_duration` so progress reads as complete.
3. Frontend: add the toggle to the add/edit forms; when on, hide the goal input and the goal label, and
   render the ring per Decision 2.
4. Verify the Total ring and the stats `total_goal_time` behave per Decision 3.

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
- **Review attention:** High — prod `ALTER TABLE` migration plus divide-by-zero/NaN risk across rings, Total, and stats sums; several representation decisions to lock.

## Risks & notes
- **SQLite migration:** the app uses `db.create_all()` (no Alembic); `create_all` won't alter the
  existing `stopwatches` table. Changing/adding a column needs a one-off `ALTER TABLE` (or documented
  reset) — same migration concern flagged in spec 0003. Coordinate if built alongside other schema
  specs (0013).
- Audit every `goal_time` read (rings, Total, stats day/week/month/year sums) so none divides by zero or
  produces NaN for no-goal stopwatches.
