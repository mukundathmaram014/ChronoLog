# 0023 — Settable total-time goal (sum by default, manual override)

## Problem / Goal
The daily total-time goal is currently *derived* as the sum of the individual stopwatch goals, which
conflates two different intentions: a **per-activity** target ("study 3h") and a **whole-day** target
("work 6h total"). The XP goal-time bonus + overtime (spec 0012) key off that sum, so there's no way to
set a standalone daily target. Let the user set the **Total** goal directly — defaulting to the sum of
individual goals, but overridable to any value. Per-stopwatch goals stay (optional; they drive only
their own rings).

## Context
- Each `Stopwatch` has a `goal_time`. The per-day **Total** row (`isTotal = True`) currently holds
  `goal_time = sum(children goal_time)`, maintained incrementally in `create_stopwatch_for_date` /
  `update_stopwatch` / `delete_stopwatch` (`backend/src/routes/stopwatch.py`).
- The XP engine derives the daily goal by summing children with `goal_time > 0` in `xp._day_inputs`, for
  the goal-time bonus (`GOAL_TIME_BONUS`) and the overtime split (spec 0012).
- A no-goal individual stopwatch stores `goal_time = 0` (spec 0012); its ring circles on a 1-hour visual
  cycle (PR #26 — folded in here; that PR is superseded by this spec).

## Decisions (made)
1. **Total goal = sum by default, overridable.** Add `Stopwatch.goal_overridden` (Boolean, default
   `False`) — only meaningful on the Total row. While `False`, the Total's `goal_time` stays the
   auto-maintained sum of individual goals (today's behavior). The moment the user sets the Total's goal,
   `goal_overridden = True` and that value is fixed — later individual-goal changes no longer touch it.
2. **Editing the Total's goal sets the override.** The Total is editable via the existing edit form;
   changing its goal flips `goal_overridden = True`. A **"Match sum of stopwatch goals"** toggle (checked
   by default while not overridden) clears the override and re-derives `goal_time` from the current sum.
3. **XP reads the Total row's `goal_time`.** `_day_inputs` uses the Total row's `goal_time` as
   `goal_hours` (correct for both the sum and an override), replacing the sum-of-children query. The
   `GOAL_TIME_BONUS` and overtime rules are otherwise unchanged.
4. **Per-stopwatch goals stay** — optional, driving only their own rings. A no-goal individual stopwatch
   (`goal_time = 0`) circles on a 1-hour visual cycle (folds in PR #26).
5. **New-day default = sum.** A fresh day's Total goal is the sum of that day's individual goals (which
   carry forward via existing logic). Overrides are per-day and do not carry forward.

## Affected files
- `backend/src/db.py` — add `goal_overridden` to `Stopwatch` (+ `__init__` + `serialize`).
- `backend/src/app.py` — `ensure_stopwatch_goal_overridden_column()` (additive
  `ALTER TABLE stopwatches ADD COLUMN goal_overridden BOOLEAN NOT NULL DEFAULT 0`).
- `backend/src/routes/stopwatch.py` — guard the incremental Total-sum maintenance with
  `if not total.goal_overridden`; when the edited row **is** the Total, set its `goal_time` directly and
  flip `goal_overridden = True`; support clearing the override (re-derive `goal_time` from the sum).
- `backend/src/xp.py` — `_day_inputs` reads the Total row's `goal_time` for `goal_hours`.
- `frontend/src/Pages/stopwatchpage.jsx` — Total edit form: set the daily goal + a "Match sum of
  stopwatch goals" toggle; keep per-stopwatch goal editing; no-goal individual rings circle (from #26).
- `frontend/src/Components/StopwatchItem.jsx` — Total goal label wording (e.g. "Daily goal").
- `backend/tests/test_xp.py` — the goal-time bonus/overtime now key off the Total's `goal_time`; add
  override tests (custom total unaffected by individual-goal changes; XP uses the override).

## Approach
1. **Schema + migration:** add `goal_overridden` (default `False`); additive `ALTER TABLE` on startup.
2. **Backend sum-maintenance:** in the three routes that adjust `total.goal_time`, only do so
   `if not total.goal_overridden`. When the request targets the Total row itself, treat the submitted
   goal as an explicit override (`goal_overridden = True`, set `goal_time`), and don't run the
   child→Total sync for that request. A "match sum" request clears the flag and recomputes the sum.
3. **XP:** `_day_inputs` returns `goal_hours` from the Total row's `goal_time`. (Same value as before
   when not overridden, since Total = sum then.) Bonus/overtime logic in `compute_day_xp` unchanged.
4. **Frontend:** the Total's edit form sets the daily goal and shows the "Match sum" toggle; individual
   stopwatch edit is unchanged (optional goal, "No goal" → ring circles on 1h).

## Acceptance criteria
- The Total goal shows the sum of individual goals by default and tracks changes to them.
- Setting a custom Total goal fixes it; changing/adding/removing individual goals no longer alters it.
- Clearing the override ("Match sum") re-derives the Total goal from the current sum.
- The goal-time bonus + overtime key off the Total goal (sum or override), not the raw child sum.
- Per-stopwatch goals still drive their own rings; a no-goal stopwatch circles on a 1-hour cycle.

## Testing / verification
- Default day: Total goal == sum of individual goals; add a stopwatch → Total goal grows.
- Override the Total goal → add/edit an individual goal → Total goal stays at the override.
- "Match sum" → Total goal snaps back to the current sum; `goal_overridden` cleared.
- XP: with a Total goal of N hours (sum or override), working ≥ N earns the goal-time bonus and hours
  past N earn overtime; individual goals don't independently trigger either.

## Risk
- **Involvement:** Moderate — one additive migration + the three stopwatch routes + `_day_inputs` + the
  Total edit UI.
- **Additive migration only** (`ADD COLUMN ... DEFAULT 0`) — the safe class (same as `repeat_days` /
  `difficulty` / `total_xp`), not a table rebuild. Existing Totals keep their current (sum) value with
  `goal_overridden = False`.
- **Editing the Total row directly** wasn't well-defined before (the update route assumes you edit a
  child and syncs to the Total). Handle the "edited row is the Total" case explicitly so the child/Total
  sync doesn't double-apply.
