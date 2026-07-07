# 0012 — Optional goal time per stopwatch + overtime work-XP boost

## Problem / Goal
Two related goal-time changes.

**(A) Optional goal time.** Every stopwatch currently must have a goal time (defaults to 1 hour). The
author wants the option, when adding/editing a stopwatch, to give it **no goal** — in which case the
goal effectively equals the current elapsed time, so progress is always "complete" and the
goal/progress math simplifies. Let a stopwatch opt out of having a goal.

**(B) Overtime work-XP boost.** A day's **total goal time** is the sum of that day's individual
stopwatch goal times (e.g. a daily target of 6 h across all stopwatches). Once worked time passes that
total, every additional hour should earn **more XP than the standard `XP_PER_HOUR` (20)** — a reward for
pushing past the day's committed target. This extends the XP engine (spec 0020).

## Context
- `goal_time` is a non-nullable `Float` on the Stopwatch model, defaulting to `3600000` ms
  (`backend/src/db.py:75,90`).
- The Total stopwatch aggregates goal time; stats sum `goal_time` across days
  (`backend/src/routes/statistics.py`), and `total_goal_time` is shown on the stats page.
- Progress rings use `time / goal_time`: `CircularProgress` per stopwatch (`StopwatchItem.jsx:27`) and
  `CircularProgressTotal` (`statisticspage.jsx:139-200`, `StopwatchItem.jsx:12`).
- XP engine: a day's work XP is `hours_worked * XP_PER_HOUR` (flat, 20/hr) in `utils.compute_day_xp`;
  `xp._day_inputs` gathers the day's inputs and `recompute_from` re-runs on any stopwatch edit
  (`backend/src/utils.py`, `backend/src/xp.py`).

## Decisions (made)
1. **Represent "no goal" as `goal_time = NULL`** — a nullable `goal_time`, `NULL` = no goal. (The
   separate `has_goal` boolean was rejected to avoid a second source of truth.) Every spot that reads
   `goal_time` (ring math, Total aggregation, stats sums) treats `NULL` as "goal = current elapsed".
2. **No-goal ring renders as full / 100%** (complete), with the "Goal: Xh Ym" label hidden.
3. **Total + stats:** a no-goal stopwatch contributes **its own elapsed time** to the Total's goal, so it
   reads as complete and never drags the Total under 100%.
4. **Overtime work XP.** Split a day's worked time at the day's total goal time. Hours up to the goal
   earn `XP_PER_HOUR` (20); hours **beyond** it earn `XP_PER_HOUR_OVERTIME`. Per day:
   `work_xp = normal_hours * 20 + overtime_hours * OVERTIME`, where
   `overtime_hours = max(0, worked_hours − goal_hours)` and `normal_hours = worked_hours − overtime_hours`.
   Overtime XP is flat (not streak-multiplied), like all work XP.
   **Overtime rate (decided): `XP_PER_HOUR_OVERTIME = 30` (1.5×).**
5. **"Total goal time" for XP = sum of *set* goal times only.** No-goal stopwatches contribute **0** to
   the XP threshold — a stopwatch with no committed target shouldn't raise the bar you have to clear.
   This deliberately differs from the display Total (Decision 3), where a no-goal stopwatch contributes
   its own elapsed time so the ring reads complete. **Guard:** if the day's total set-goal time is 0 (no
   goals that day), there is no overtime — every worked hour earns the standard 20/hr.

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
- `backend/src/utils.py` — add `XP_PER_HOUR_OVERTIME`; `compute_day_xp` splits worked time into
  normal/overtime at the day's goal hours (a new argument). (spec 0020)
- `backend/src/xp.py` — `_day_inputs` also returns the day's total set-goal hours (sum of the day's
  non-Total stopwatches' non-NULL `goal_time`), passed into `compute_day_xp`.
- `backend/tests/test_xp.py` — overtime-XP tests; update the `compute_day_xp` signature-dependent tests
  and the dedicated-user calibration (see notes).

## Approach
1. Make `goal_time` nullable in the model + `serialize` (`NULL` = no goal).
2. Backend create/edit: when "no goal" is chosen, store `goal_time = NULL`; everywhere `goal_time` feeds
   progress, treat no-goal as `goal = current curr_duration` so progress reads as complete.
3. Frontend: add the toggle to the add/edit forms; when on, store no goal, hide the goal input and the
   goal label, and render the ring as full/100%.
4. Total + stats: a no-goal stopwatch contributes its own elapsed time to `total_goal_time`, so the
   Total ring and stats stay coherent (never NaN or under 100% from a no-goal item).
5. **Overtime XP (spec 0020 engine):** `_day_inputs` computes the day's total set-goal hours (sum of the
   day's stopwatches' non-NULL `goal_time`, excluding the Total row) and passes it to `compute_day_xp`,
   which splits worked hours at the goal — `XP_PER_HOUR` below it, `XP_PER_HOUR_OVERTIME` above, guarded
   so goal = 0 → no overtime. Recompute paths are unchanged (any stopwatch edit already calls
   `recompute_from` for the day, so today's XP updates live as time is logged).

## Acceptance criteria
- A stopwatch can be created/edited with no goal; its ring shows complete and no goal label.
- Goal-bearing stopwatches behave exactly as before.
- Total ring and stopwatch stats don't break or show negative/NaN progress with mixed goals.
- With a day's total set-goal of N hours: working ≤ N earns 20/hr; each hour past N earns the overtime
  rate; a day with no goals set earns the standard 20/hr for all hours (no overtime).

## Testing / verification
- Create a no-goal stopwatch, run it, confirm ring + Total + stats render sanely.
- Edit a goal stopwatch to no-goal and back; confirm persistence and display.
- A day mixing goal and no-goal stopwatches shows a coherent Total.
- Overtime XP: a day with a 6 h total goal — work 5 h → 100 XP; work 8 h → `6·20 + 2·OVERTIME`; a day
  with no goals set → flat 20/hr. No-goal stopwatches don't raise the overtime threshold.

## Risk
- **Involvement:** Involved — schema change + two backend routes + three frontend files + the XP engine;
  every `goal_time` read must be audited.
- **Review attention:** High — prod `ALTER TABLE` migration plus divide-by-zero/NaN risk across rings,
  Total, and stats sums (every `goal_time` read must treat `NULL` as "goal = elapsed"), plus the XP
  split must use the *set-goal* total (Decision 5), not the display Total.

## Risks & notes
- **SQLite migration:** the app uses `db.create_all()` (no Alembic); `create_all` won't alter the
  existing `stopwatches` table. Relaxing `goal_time` from `NOT NULL` to nullable **can't** be done with a
  simple `ALTER TABLE ... ADD COLUMN` — SQLite needs a **table rebuild** (create a new table with the
  nullable column, copy rows over, drop the old, rename), or a documented reset. Spell out the exact
  steps in the PR (same migration class as spec 0003); coordinate with spec 0013, which also alters
  `stopwatches`.
- Audit every `goal_time` read (rings, Total, stats day/week/month/year sums) so none divides by zero or
  produces NaN for no-goal stopwatches.
- **XP calibration:** `compute_day_xp` gains a goal-hours argument, so the dedicated-user calibration test
  (spec 0020) and every `compute_day_xp` call site must be updated. The calibration sim currently models
  no goal (hence no overtime); decide whether the dedicated profile should carry a daily goal + some
  overtime, and re-check the level-100-in-4-5-years window after setting `XP_PER_HOUR_OVERTIME`.
