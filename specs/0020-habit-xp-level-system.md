# 0020 — Habit XP / level system (model, level curve, streaks, goals)

## Problem / Goal
Add a Solo-Leveling-style progression layer on top of habits: completing habits grants weighted XP into
a **single shared pool**, and that XP maps to a **level** via a defined curve. This spec now covers three
layers:
1. **Foundation** — the data model, XP accrual from habit completion, and the level curve.
2. **Streak / momentum** — a multiplier that rewards consecutive "qualifying" days, boosting the XP earned
   on a day when you keep a run going.
3. **Goals** — user-defined objectives with a **self-configured XP reward** that inject a burst of XP into
   the same pool when completed.

Still **deferred** to a later spec: the derived **"strength"** readout, and any optional split of the
single pool into physical/intellect/vitality stats. Those are UI/analytics on top of this and don't
change the model below.

## Source design (author's "Habit Scoring Protocol")
- One XP pool, one level. Every habit grants **value-weighted** XP so the hardest habits dominate the
  day: a small number of heavy habits carry large weights (e.g. ~50 each) and the rest carry smaller
  weights (~10–30), so a typical day tops out around a couple hundred XP and the heavy habits are the
  bulk of it. (Concrete per-habit weights are user data — configured in-app per Decision 1, not
  hard-coded here.)
- **Level curve:** cost to reach the next level `cost(L) = round(B × L^p)`; defaults **B = 20, p = 1.3**
  (level ~10 in ~2 weeks, never maxes out).
- **Momentum / streak:** consecutive qualifying days build a multiplier applied to that day's *habit* XP,
  capped — so keeping a run going is worth more than isolated good days, but it can't run away.
- **Goals:** one-off, user-defined objectives with a reward the user sets themselves; completing one
  injects that reward into the shared pool. (This is the configurable form of the earlier "big-achievement
  XP injection" idea — now user-driven rather than hard-coded.)
- Still deferred (NOT in this spec): "strength" as a derived readout; optional later split into
  physical/intellect/vitality stats.

## Context — current model
- `Habit` (`backend/src/db.py:27-59`) has `description`, `done`, `date`, `user_id` only — no XP weight.
- Habit completion is the `done` toggle (`backend/src/routes/habits.py`); habits carry forward per day, so
  a habit lives as **one row per day**.
- There is **no `Goal` model** yet — this spec adds one (a brand-new table, like `Task` in spec 0021).
- Stats are computed in `backend/src/routes/statistics.py`; that (or a new `routes/level.py`) is the
  natural home for the XP/level/streak endpoint.

## The three layers (design detail)

### A. Base habit XP (foundation)
Each habit carries an `xp_weight` (default 10). A day's **base XP** = sum of `xp_weight` over that day's
completed (`done = True`) habits. Because habits are per-day rows, a daily habit pays out every day it's
done — intended.

### B. Streak / momentum multiplier
- **Qualifying day:** a day "counts" toward a streak if it clears a bar (Decision 6). Recommended default:
  the day's **base XP ≥ a configurable daily threshold** (so a day where you did your important habits
  qualifies; a token single-habit day may not). Alternative: "completed at least one *heavy* habit"
  (weight ≥ a threshold).
- **Streak count:** number of consecutive qualifying days ending on a given day. A non-qualifying day (or a
  gap with no completions) **resets the streak to 0**; the next qualifying day restarts at 1.
- **Multiplier:** `mult(streak) = min(1 + step × (streak − 1), cap)` (Decision 7). Recommended default
  `step = 0.1, cap = 2.0` → day 1 = ×1.0, ramping to ×2.0 by an 11-day run.
- **What it multiplies:** that day's **habit base XP only** — *not* goal rewards (Decision 9). So a day's
  XP contribution = `base_xp(day) × mult(streak_through_day)`.
- **Total from habits (derived):** `Σ over days [ base_xp(day) × mult(streak_through_day) ]`.
  ⚠️ Note this makes total XP **path-dependent** (day order matters), so it's no longer a single `SUM`
  query — see Decision 8 and Risks.
- The endpoint also exposes **current streak** and **current multiplier** for the UI.

### C. Goals (configurable XP bursts)
- A **`Goal`** is a one-off objective: `description`, a user-set `xp_reward`, a `done` flag, and (when
  completed) a `completed_date`. Completing it grants `xp_reward` **once**, flat (not streak-multiplied,
  per Decision 9). Un-completing removes it again.
- **Total from goals (derived):** `Σ xp_reward where done = True`, scoped to the user.
- **Grand total XP** = habit total (A×B) + goal total (C), fed into the level curve.

## ⚠️ Decisions needed
1. **Where the per-habit XP weight lives.**
   - **(Recommended) `xp_weight` column on `Habit`** with a sensible default (e.g. 10), editable in the
     habit add/edit form. Weight travels with the habit (and its carry-forward copies).
   - Alternative: a separate weight table keyed by habit description (renaming/recreating keeps the
     weight). More robust to the per-day-row model but more machinery.
2. **Level-curve helper location & exact mapping.** Recommended: a pure helper (total XP → level +
   progress) in `utils.py`, `cost(L) = round(B·L^p)`, B=20, p=1.3, starting at level 1. Confirm B/p and
   whether to expose "XP into current level / XP to next".
3. **Default weight for existing/back-dated habits.** Recommended: default weight 10 for all unless edited.
4. **Level/XP readout placement.** Minimal in this slice — e.g. level + progress + current streak/
   multiplier on the habit or home page. Rich UI is a later spec.
5. **(Streak) Qualifying-day definition.** Recommended: day **base XP ≥ a configurable daily threshold**.
   Alternative: "completed ≥ 1 heavy habit (weight ≥ H)". Pick one and set the default threshold/H.
6. **(Streak) Multiplier formula + cap.** Recommended `mult = min(1 + 0.1·(streak−1), 2.0)`. Confirm
   `step` and `cap` (and that the streak counts the current day inclusive).
7. **(Streak) Does momentum apply to habit XP only?** Recommended **yes** — goals are flat bursts, habits
   carry the streak. Confirm.
8. **(Architecture) Total XP: derived-on-read vs stored daily ledger.** The multiplier makes the habit
   total path-dependent, so a plain `SUM` no longer works. Two options:
   - **(Recommended for now) Derived on read:** group completed habits by day, walk days chronologically
     tracking the running streak, apply the multiplier, then add goal rewards. No stored counter to sync;
     cost is an O(days) walk per read. Fine at personal scale.
   - **Stored daily XP ledger** (a per-day row of earned XP + streak state), updated on toggle. Faster
     reads, but adds sync/backfill complexity. Consider only if the derived walk gets slow.
9. **(Goals) Model fields.** Recommended MVP: `description`, `xp_reward`, `done`, `completed_date`,
   `user_id` — no deadline/priority/sub-goals yet. Confirm (a deadline could be a fast follow-up).
10. **(Goals) Repeatable or one-time?** Recommended: **one-time toggle** — completing grants the reward,
    un-completing removes it; no auto-reset/repeat in v1.
11. **(Goals) UI placement.** Recommended: a **dedicated Goals page** (nav link + route, like Tasks in
    0021) with an add-goal form (description + XP-reward input), complete checkbox, edit/delete. Alternative:
    a section on the habit or stats page.

## Affected files
- `backend/src/db.py` —
  - (Decision 1 = column) add `Habit.xp_weight` (default 10) to `__init__` + `serialize`. **Schema change
    on an existing table** — see Risks.
  - **New `Goal` model**: `id`, `description` (String), `xp_reward` (Integer), `done` (Boolean, default
    False), `completed_date` (Date/DateTime, nullable), `user_id` (FK). `__init__` + `serialize`. **New
    table** — auto-created by `create_all`, no migration (unlike the column above).
- `backend/src/utils.py` —
  - pure **level-curve** helper: total XP → `{level, xp_into_level, xp_to_next}`.
  - pure **streak/momentum** helper: given the per-day base-XP series (chronological) → `{habit_total_xp,
    current_streak, current_multiplier}`, applying the qualifying rule + multiplier (Decisions 5–7).
- `backend/src/routes/statistics.py` (or a new `routes/level.py` blueprint under `/api`) — a
  `@jwt_required()` endpoint returning the user's **total XP** (habits×streak + goals), **level +
  progress**, and **current streak + multiplier**, all scoped by `user_id`.
- `backend/src/routes/habits.py` — accept `xp_weight` on create/edit (if Decision 1 = column).
- `backend/src/routes/goals.py` — **new** blueprint `goal_routes`: list, create, get-one, update (toggle
  done / edit description+reward), delete — all `@jwt_required()`, `user_id`-scoped,
  `success_response`/`failure_response`, bodies via `json.loads(request.data)`.
- `backend/src/app.py` — register `goal_routes` under `/api` (`app.py:63-66`).
- `frontend/src/Pages/habitpage.jsx` — XP-weight input in the habit add/edit form (if column).
- `frontend/src/Pages/goalpage.jsx` + `goalpage.css` — **new** Goals page: add-goal form (description +
  XP-reward), list with complete/edit/delete, all calls via `useFetch`.
- `frontend/src/App.js` — new protected `/goalpage` route under `RequireAuth` + `Layout` (`App.js:22-28`).
- `frontend/src/Components/Navbar.jsx` — add a "Goals" nav link (`Navbar.jsx:39-47`).
- Frontend level display — minimal readout: level + progress + current streak/multiplier (habit or home
  page); rich UI deferred.

## Approach
1. **Layer A (foundation).** Decide weight storage (Decision 1). Add the level-curve helper in `utils.py`
   (B=20, p=1.3): invert cumulative `cost(L)` to get level from total XP + progress into current level.
2. **Layer B (streak).** Add the streak/momentum helper in `utils.py` implementing the qualifying rule
   (Decision 5) and multiplier (Decision 6/7): take completed habits, group by day, walk chronologically
   tracking the running streak, sum `base_xp(day) × mult(streak)`. Derive `current_streak` /
   `current_multiplier` from the tail (Decision 8 = derived-on-read).
3. **Layer C (goals).** Add the `Goal` model (new table — `create_all` auto-creates it, no migration).
   Build `routes/goals.py` CRUD following the habits conventions; register the blueprint; verify all
   routes are `user_id`-scoped. Goal XP = `Σ xp_reward where done` (flat).
4. **Endpoint.** Assemble the XP/level payload: habit total (A×B) + goal total (C) → level via helper;
   include streak + multiplier. Scope everything by `user_id`.
5. **Frontend.** Surface `xp_weight` in the habit form (default 10); add the Goals page + nav link +
   route; add a minimal level/XP/streak readout.

## Acceptance criteria
- Each habit has an XP weight (default 10), editable, persisted.
- A day's habit XP is `Σ xp_weight` of that day's completed habits, **multiplied** by the streak
  multiplier for that day; the multiplier follows `min(1 + step·(streak−1), cap)` with the agreed
  step/cap, and **resets after a non-qualifying day**.
- Goals can be created with a user-set `xp_reward`; completing a goal adds exactly that reward to total XP
  (flat, not streak-multiplied), and un-completing removes it.
- An endpoint returns, scoped to the user: total XP (habits×streak + goals), derived level + progress,
  and current streak + multiplier.
- The level curve matches `cost(L)=round(B·L^p)` with B=20, p=1.3 (verified against hand computations).
- Toggling a habit or goal done/undone changes total XP/level consistently (stays correct because
  derived).
- No cross-user leakage (habits, goals, and the XP endpoint all `user_id`-scoped).

## Testing / verification
- **Curve helper:** total XP 0 → level 1; verify the XP thresholds for the first several levels against
  `round(20·L^1.3)`.
- **Streak helper (unit):** a run of qualifying days ramps the multiplier and caps at `cap`; a
  non-qualifying day or gap resets the streak; a known day/weight sequence yields the expected habit
  total and current streak/multiplier.
- **Goals:** create goals with known rewards, complete/uncomplete them, and confirm the endpoint's total
  XP moves by exactly the reward each time.
- **Integration:** complete/uncomplete habits of known weights across several days and confirm total XP,
  level, streak, and multiplier update as expected.
- **Isolation:** a second user can't see the first user's habits, goals, or XP.

## Risks & notes
- **SQLite migration for `Habit.xp_weight`** (no Alembic; `create_all` won't alter `habits`) — `ALTER
  TABLE` + backfill existing rows to the default weight. The **`Goal` table needs no migration** —
  `create_all` creates brand-new tables automatically on boot (same as `Task` in spec 0021).
- **Streak makes the habit total path-dependent (main new complexity).** Because the multiplier depends
  on the running streak, total XP is **no longer a single `SUM`** — the endpoint must group completed
  habits by day and walk chronologically. Derived-on-read (Decision 8) keeps everything in sync with no
  backfill, at the cost of an O(days) walk per read; if that ever gets slow, switch to a stored daily
  ledger. Flagging this because it's the one part that isn't a trivial query.
- **Un-toggling stays correct automatically** if XP is derived — no counters to reconcile on
  toggle/delete for either habits or goals.
- **Streak feel is tunable** — the qualifying threshold and step/cap set how punishing/rewarding momentum
  is; expect to adjust the defaults after using it.
- **Scope discipline:** this spec is model + curve + accrual + streak + goals. The **"strength" readout**
  and any **physical/intellect/vitality split** remain deferred — they're presentation/analytics over this
  same pool and don't change the model.
- Per-day habit rows mean a habit completed on many days pays out each day — intended; the streak
  multiplier then scales each qualifying day on top of that.
