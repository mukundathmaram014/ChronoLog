# 0020 — Habit XP / level system (model + level curve)

## Problem / Goal
Add a Solo-Leveling-style progression layer on top of habits: completing habits grants weighted XP into
a **single shared pool**, and that XP maps to a **level** via a defined curve. This spec covers **only
the foundation — the data model, XP accrual from habit completion, and the level curve**. The momentum
buff, big-achievement jumps, and the derived "strength" readout are explicitly **deferred to later
specs** (this is the agreed first slice of the larger design).

## Source design (author's "Habit Scoring Protocol")
- One XP pool, one level. Every habit grants **value-weighted** XP so the hardest habits dominate the
  day: a small number of heavy habits carry large weights (e.g. ~50 each) and the rest carry smaller
  weights (~10–30), so a typical day tops out around a couple hundred XP and the heavy habits are the
  bulk of it. (Concrete per-habit weights are user data — configured in-app per Decision 1, not
  hard-coded here.)
- **Level curve:** cost to reach the next level `cost(L) = round(B × L^p)`; defaults **B = 20, p = 1.3**
  (level ~10 in ~2 weeks, never maxes out).
- Deferred (NOT in this spec): momentum combo multiplier for consecutive heavy-habit days; big-
  achievement XP injections; "strength" as a derived readout; optional later split into physical/
  intellect/vitality stats.

## Context — current model
- `Habit` (`backend/src/db.py:27-59`) has `description`, `done`, `date`, `user_id` only — no XP weight.
- Habit completion is the `done` toggle (`backend/src/routes/habits.py`).
- Stats are computed in `backend/src/routes/statistics.py`; this is the natural home for an XP/level
  endpoint.

## ⚠️ Decision needed
1. **Where the per-habit XP weight lives.**
   - **(Recommended) `xp_weight` column on `Habit`** with a sensible default (e.g. 10), editable in the
     habit add/edit form. Simple; weight travels with the habit (and its carry-forward copies).
   - Alternative: a separate weight table keyed by habit description (so renaming/recreating keeps the
     weight). More robust to the per-day-row model but more machinery.
2. **Is total XP stored or derived?**
   - **(Recommended) Derived on read:** sum `xp_weight` over the user's completed (`done = True`) habits
     across all time; compute level from the curve. No stored counter to keep in sync; no migration of
     historical XP. Cost: a sum query.
   - Alternative: a stored running `xp` total on `User`, incremented on completion. Faster reads but
     needs careful sync on toggle/un-toggle/delete and a backfill.
3. **Level-curve helper location & exact mapping.** Recommended: a small pure helper (given total XP →
   level + progress to next) in `utils.py`, using `cost(L) = round(B·L^p)`, B=20, p=1.3, starting at
   level 1. Confirm B/p and whether to expose "XP into current level / XP to next".
4. **Default weight for existing/`description`-based habits** (so historical completions yield sensible
   XP). Recommended: default weight 10 for all unless edited.

## Affected files
- `backend/src/db.py` — (if Decision 1 = column) add `Habit.xp_weight` (default 10); `__init__` +
  `serialize`. **Schema change** — see Risks.
- `backend/src/utils.py` — pure level-curve helper(s): total XP → `{level, xp_into_level, xp_to_next}`.
- `backend/src/routes/statistics.py` (or a new `routes/level.py` blueprint registered under `/api`) — a
  `@jwt_required()` endpoint returning the user's total XP + level (+ progress), scoped by `user_id`.
- `backend/src/routes/habits.py` — accept `xp_weight` on create/edit (if Decision 1 = column).
- `frontend/src/Pages/habitpage.jsx` — XP-weight input in the habit add/edit form (if column).
- Frontend level display — minimal in this slice (e.g. show level + progress on the habit or home page);
  rich UI can be a later spec.

## Approach
1. Decide weight storage + XP storage (Decisions 1–2) — recommended: `xp_weight` column + derived total.
2. Add the level-curve helper in `utils.py` (B=20, p=1.3): invert cumulative `cost(L)` to get level from
   total XP, plus progress into the current level.
3. Add the XP/level endpoint: sum weights over the user's completed habits → total XP → level via helper.
4. Surface `xp_weight` in the habit form (default 10) and a minimal level/XP readout in the UI.

## Acceptance criteria
- Each habit has an XP weight (default 10), editable, persisted.
- An endpoint returns the user's total XP (sum of weights of completed habits) and the derived level +
  progress, scoped to that user.
- The level curve matches `cost(L)=round(B·L^p)` with B=20, p=1.3 (verified against a few hand
  computations).
- Toggling a habit done/undone changes total XP/level consistently (and stays correct if derived).

## Testing / verification
- Unit-test the curve helper: total XP 0 → level 1; verify the XP thresholds for the first several
  levels against `round(20·L^1.3)`.
- Complete/uncomplete habits of known weights and confirm the endpoint's total XP and level update.
- Confirm XP is per-user (no cross-user leakage).

## Risk
- **Involvement:** Involved — schema (`xp_weight`), a level-curve helper, a new XP/level endpoint, a habit-form input, and a minimal readout.
- **Review attention:** High — prod migration, curve math needs unit tests, several design decisions, and strict scope discipline (defer momentum/achievements/strength).

## Risks & notes
- **SQLite migration** for `Habit.xp_weight` (no Alembic; `create_all` won't alter `habits`) — `ALTER
  TABLE` + backfill existing rows to the default weight.
- **Scope discipline:** this is deliberately just model + curve + accrual. Do NOT build momentum buffs,
  big-achievement jumps, or the strength readout here — each is a follow-up spec layered on this
  foundation.
- If XP is derived (recommended), there's nothing to migrate for historical completions — they
  automatically count at the default weight.
- Per-day habit rows mean a habit completed on many days sums many weights — that's intended (daily
  habits should pay out daily); just confirm the protocol's "≈210 XP/day" expectation matches summing
  per-day rows.
