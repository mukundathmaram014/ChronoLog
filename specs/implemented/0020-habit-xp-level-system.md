---
status: built
---

# 0020 — XP / level system (habits + work time, streaks, goals)

## Problem / Goal
Add a Solo-Leveling-style progression layer: your activity grants XP into a **single shared pool**, and
that XP maps to a **level** via a fixed curve. XP comes from three sources — completing **habits**
(weighted by a per-habit difficulty), **time worked** on stopwatches (XP per hour), and completing
**goals** (weighted by difficulty). A **streak multiplier** rewards consecutive good days. The level
curve is **fixed in code** (the user cannot tune how hard it is to level up) and is calibrated so a
dedicated user reaches ~level 100 (a "theoretical peak") in ~4–5 years.

Explicitly **not** in scope (and not planned): the "strength" readout and any physical/intellect/
vitality stat split — a single XP pool / single level only.

## Decisions (made)
- **Per-habit XP = a difficulty tier on the `Habit` row** (a column). The user picks **Easy / Medium /
  Hard** when creating/editing a habit (discrete choice — a 3-way toggle/segmented control; a slider is
  an optional UI flourish). Each tier maps to a fixed XP value.
- **Stopwatches have no difficulty** — time worked simply grants XP at a fixed **XP-per-hour** rate
  (total hours worked that day → XP). Keeps stopwatch XP simple.
- **Goals use the same Easy / Medium / Hard tiers**, one-time (complete once → its XP; un-complete
  removes it; no repeating goals).
- **The level curve is fixed / not user-configurable.** `cost(L) = round(B · L^p)` with B, p **hard-coded**
  (see Calibration). Users never see or set B/p or any XP constant — only the per-item difficulty tier.
- **Storage is stored, not derived:** `User.total_xp` holds a running total, incremented by each day's
  earned XP; a **per-day XP ledger** records how much was earned on each day.
- **Level readout:** an **XP bar + level** on the **home page**.
- **Goals live on a dedicated Goals page** (nav link + route, like Tasks in 0021).

## XP sources (detail)
### A. Habit XP (difficulty tiers)
- `Habit.difficulty` ∈ {easy, medium, hard} → fixed XP (starting values **easy = 10, medium = 25,
  hard = 50**, matching the author's "heavy habits ~50, others ~10–30"; final values set by Calibration).
- A day's **habit base XP** = Σ (difficulty XP) over that day's completed (`done = True`) habits. Habits
  are per-day rows, so a daily habit pays out each day it's done.

### B. Work-time XP (stopwatch hours)
- A day's **work XP** = (total hours worked that day across stopwatches) × a fixed **XP-per-hour** rate
  (starting value **~20 XP/hour**; set by Calibration). Uses the day's total stopwatch duration; **no**
  per-stopwatch difficulty. Flat (not streak-multiplied).

### C. Goal XP (difficulty tiers, one-time)
- `Goal.difficulty` ∈ {easy, medium, hard} → fixed XP (starting values **easy = 50, medium = 100,
  hard = 200**; set by Calibration). Completing a goal grants its XP once on its `completed_date`;
  un-completing removes it. Flat (not streak-multiplied). No repeating goals.

### D. Streak multiplier (applies to habit XP only)
- **Qualifying day:** a day counts toward a streak if its habit base XP ≥ a fixed threshold (so a real
  effort day qualifies, a token single-habit day may not). A non-qualifying day or a gap **resets** the
  streak to 0.
- **Multiplier:** `mult(streak) = min(1 + step·(streak − 1), cap)`, starting values **step = 0.1,
  cap = 2.0** (ramps to ×2 over ~11 days). Applies to **habit XP only** — work XP and goal XP are flat.
- A day's earned XP = `habit_base × mult(streak) + work_xp + goal_xp_completed_that_day`.

## Level curve (fixed) & calibration
- `cost(L) = round(B · L^p)` = XP to go from level L to L+1; cumulative to reach level N = Σ_{L=1}^{N−1}.
- **Calibration target:** a **dedicated user** — a standard list of **3 easy + 3 medium + 3 hard** habits
  done daily, **~5–6 h/day** of tracked work, a **sustained streak**, and a **reasonable cadence of
  goals** — reaches **~level 100 in ~4–5 years** (mirrors real-world "years to mastery"). Level 100 is the
  calibration anchor / theoretical peak, **not** a hard cap (the curve keeps going).
- **Illustrative constants that hit the target** (to be confirmed by the calibration simulation below):
  with the XP values above and a sustained ×2 streak, a dedicated day ≈ 255×2 (habits) + ~110 (5.5 h × 20)
  + ~15 (goals) ≈ **~635 XP/day**; over ~4.3 years that's ≈ 1.0 M XP, which `cost(L) = round(25 · L^1.5)`
  reaches at L ≈ 100. So **B ≈ 25, p ≈ 1.5** is the starting curve. Early levels are cheap (fast,
  satisfying start); late levels are expensive (never maxes out).
- These constants (habit/goal tier XP, XP-per-hour, streak step/cap/threshold, B, p) are **fixed in code**
  and must be **tuned together via the calibration simulation** so the dedicated-user profile lands in the
  4–5-year window. They are not user-facing.

## Storage / architecture (stored total + daily ledger)
- `User.total_xp` (Integer, default 0) — running total; **level is derived from it** via the curve helper
  (cheap: invert cumulative `cost`).
- **`DailyXP`** table (new): one row per user per day — `id`, `date`, `xp_earned` (Integer), `streak`
  (Integer, that day's streak count), `user_id` (FK). Records what each day contributed.
- **Accrual:** for a given day, `xp_earned` is a pure function of that day's completed habits (× streak),
  hours worked, and goals completed. When a day's inputs change (habit toggle, stopwatch stop, goal
  completed on that date), **recompute that day's `DailyXP` row and adjust `User.total_xp` by the delta**.
  Because the streak is path-dependent, a change to a day's qualifying status **recomputes that day
  forward** (subsequent days' multipliers/streak may shift). See Risks — this sync is the main complexity
  of the stored approach.

## Affected files
- `backend/src/db.py` —
  - add `Habit.difficulty` (String enum: easy/medium/hard, default `medium`) to `__init__` + `serialize`.
    **Schema change on `habits`** — see Risks.
  - add `User.total_xp` (Integer, default 0) to `serialize`. **Schema change on `users`** — see Risks.
  - **new `Goal` model**: `id`, `description`, `difficulty` (String enum), `done` (Boolean, default
    False), `completed_date` (Date, nullable), `user_id` (FK). `__init__` + `serialize`. **New table** —
    auto-created by `create_all`, no migration.
  - **new `DailyXP` model** (per-user-per-day ledger). **New table** — auto-created, no migration.
- `backend/src/utils.py` —
  - a pure **level-curve helper**: `total_xp → {level, xp_into_level, xp_to_next}` using
    `cost(L)=round(B·L^p)` with the fixed B/p.
  - a pure **day-XP helper**: given a day's completed-habit difficulties, hours worked, goals completed,
    and the running streak → `{xp_earned, streak, multiplier}` (applies the tier XP, per-hour rate,
    streak rule). Central home for all the fixed XP constants.
- `backend/src/xp.py` — **new** (added during build): the DB-touching accrual engine
  (`recompute_from(user_id, day)` forward-recompute + `current_streak`). Split out of `utils.py`
  because `db.py` imports `utils.py`, so the pure helpers can't reach the models without a circular
  import; routes import it directly.
- `backend/src/routes/level.py` (new blueprint under `/api`) — a `@jwt_required()`
  `GET /api/level/<date>/` endpoint returning the user's `total_xp`, derived level + progress, and
  current streak/multiplier, scoped by `user_id`.
- `backend/src/routes/habits.py` — accept `difficulty` on create/edit (carry-forward inherits it); on
  any `done` toggle / difficulty change / delete of a done habit, recompute that day's `DailyXP` +
  adjust `total_xp` (recompute forward for streak).
- `backend/src/routes/stopwatch.py` — when a day's worked time changes (stop, duration edit, reset,
  delete), recompute that day's `DailyXP` + `total_xp`.
- `backend/src/routes/goals.py` — **new** blueprint `goal_routes`: list/create/get/update (toggle done /
  edit description + difficulty)/delete, all `@jwt_required()`, `user_id`-scoped,
  `success_response`/`failure_response`; on complete/uncomplete, adjust that day's `DailyXP` + `total_xp`.
- `backend/src/app.py` — register `goal_routes` (and `level.py` if separate) under `/api`.
- `frontend/src/Pages/habitpage.jsx` — an Easy/Medium/Hard control in the habit add/edit form.
- `frontend/src/Pages/goalpage.jsx` + `goalpage.css` — **new** Goals page: add-goal form (description +
  Easy/Medium/Hard), list with complete/edit/delete, via `useFetch`.
- `frontend/src/App.js` — protected `/goalpage` route; `frontend/src/Components/Navbar.jsx` — "Goals" link.
- `frontend/src/Pages/homepage.jsx` + `homepage.css` — an **XP bar + level** readout (fed by the level
  endpoint); `frontend/src/Pages/habitpage.css` — difficulty-picker styles.
- `backend/tests/test_xp.py` — **new**: curve/day-XP helper tests, accrual-sync tests (habit toggle,
  past-day forward recompute, worked time, goals), user isolation, and the calibration simulation.

## Approach
1. **Model + migrations.** Add `Habit.difficulty` and `User.total_xp` (ALTER TABLE on `habits` / `users`);
   add `Goal` and `DailyXP` tables (auto-created). Serialize all.
2. **Helpers (`utils.py`).** The level-curve helper (fixed B/p) and the day-XP helper (tier XP, per-hour
   rate, streak rule) — the single home for the fixed constants.
3. **Accrual wiring.** On habit toggle / stopwatch stop / goal complete, recompute the affected day's
   `DailyXP` (recompute forward for streak) and adjust `User.total_xp` by the delta.
4. **Endpoint.** Return `total_xp`, derived level + progress, current streak/multiplier, `user_id`-scoped.
5. **Goals pillar.** `goals.py` CRUD + blueprint + Goals page + nav link + route.
6. **Home readout.** XP bar + level on the home page.
7. **Calibration.** A simulation/unit test that runs the dedicated-user profile (3/3/3 habits, 5–6 h/day,
   sustained streak, goal cadence) day by day and asserts it reaches ~level 100 at ~4–5 years; tune the
   fixed constants (tier XP, per-hour rate, streak step/cap/threshold, B, p) until it does.

## Acceptance criteria
- A habit has an Easy/Medium/Hard difficulty (a column), editable and persisted; goals likewise.
- A day's earned XP = (Σ completed-habit tier XP × streak multiplier) + (hours worked × per-hour rate) +
  (tier XP of goals completed that day); stored in `DailyXP`, and summed into `User.total_xp`.
- The streak multiplier follows `min(1 + step·(streak−1), cap)`, applies to habit XP only, and resets
  after a non-qualifying day.
- `User.total_xp` and the daily ledger stay consistent when habits/goals are toggled or worked time
  changes (including editing a past day — recomputed forward).
- Level is derived from `total_xp` via `cost(L)=round(B·L^p)` with the fixed B/p.
- The home page shows an XP bar + level; Goals has its own page; XP/goals are `user_id`-scoped (no
  cross-user leakage).
- **Calibration:** the dedicated-user simulation reaches ~level 100 in ~4–5 years.

## Testing / verification
- **Curve helper:** total_xp 0 → level 1; verify thresholds for the first several levels against
  `round(B·L^p)`.
- **Day-XP helper:** known habit tiers + hours + goals + streak → expected `xp_earned`, multiplier, and
  streak; the multiplier ramps and caps; a non-qualifying day resets it.
- **Accrual sync:** toggling a habit/goal or changing worked time updates `DailyXP` and `total_xp` by the
  right delta, including editing a past day (streak recomputed forward).
- **Calibration simulation:** run the dedicated-user profile over ~4–5 years and assert level ≈ 100;
  assert early levels come quickly and late levels slowly.
- **Isolation:** a second user can't see the first's habits/goals/XP.

## Risk
- **Involvement:** Involved — the largest spec in the queue: two `ALTER TABLE`s (`Habit.difficulty`,
  `User.total_xp`), two new tables (`Goal`, `DailyXP`), two `utils.py` helpers, an XP/level endpoint,
  accrual wiring across the habit/stopwatch/goal routes, a new Goals page/nav/route, a habit-form control,
  and a home-page XP bar.
- **Review attention:** High — two prod migrations; the **stored total + daily ledger must stay in sync**
  on every toggle/stop/goal (and on past-day edits, with the streak recomputed forward) — this is the
  central risk of the stored approach; plus the **calibration** (fixed constants tuned by simulation to the
  4–5-year target). Needs unit tests for the helpers and the calibration.

## Risks & notes
- **Two SQLite migrations** (no Alembic): `ALTER TABLE habits ADD COLUMN difficulty VARCHAR NOT NULL
  DEFAULT 'medium'` and `ALTER TABLE users ADD COLUMN total_xp INTEGER NOT NULL DEFAULT 0`. `Goal` and
  `DailyXP` are brand-new tables (`create_all` makes them, no migration). Spell out the ALTERs in the PR.
- **Stored-vs-derived tradeoff (the main complexity).** Storing `total_xp` + the daily ledger gives fast
  reads and a per-day history, but every input change must keep them in sync — and because the streak is
  path-dependent, a change to a past day's qualifying status recomputes that day **forward**. Keep the
  day-XP computation a pure function so recompute-and-diff is straightforward; add tests for past-day edits.
- **Difficulty stored as a tier label** (not a raw XP number) so the fixed XP values can be re-tuned during
  calibration without migrating rows; already-finalized `DailyXP` amounts stay as earned (past is locked,
  future uses the new mapping).
- **All balancing constants are fixed in code** (tier XP, per-hour rate, streak step/cap/threshold, B, p) —
  users only pick per-item difficulty, never how fast they level. Tune constants only via the calibration
  simulation.
- **No strength/vitality split and no repeating goals** — single pool, single level, one-time goals; these
  are deliberately excluded (not merely deferred).
- Per-day habit rows mean a daily habit pays out each day; the streak then scales each qualifying day.

---

## Addendum — difficulty badges, extreme goals, ranks & XP note (follow-up)

A follow-up pass after the initial ship (and after the historical-data XP backfill), covering
visibility and goal-balance gaps found in daily use. Deltas from the spec above:

- **Goal XP rescaled.** The original goal tiers (easy 50 / medium 100 / hard 200) made even a hard
  goal worth roughly a single ordinary day (~200 XP/day for an active user). Goals now represent
  days-to-months of effort: **easy 500, medium 2,000, hard 5,000**. Historical goal XP only re-values
  when its day is next recomputed (e.g. a later toggle); no forced re-backfill.
- **New "extreme" goal tier (goal-only).** A fourth tier, **20,000 XP**, for rare life-changing goals.
  Habits stay easy/medium/hard. Validation is split: `VALID_DIFFICULTIES` (habits) vs
  `VALID_GOAL_DIFFICULTIES` (goals) in `utils.py`.
- **Habit difficulty is now visible.** Each habit row shows a coloured difficulty badge, mirroring the
  goal rows (the habit page already had the picker; only the badge was missing).
- **Streak cue on the level bar.** When a streak is active the homepage XP bar burns orange and glows,
  in addition to the existing "🔥 N-day streak · ×M XP" header text.
- **Letter ranks (Solo Leveling-style).** Levels map to ranks **E → D → C → B → A → S**: E 1–9,
  D 10–24, C 25–49, B 50–74, A 75–99, **S 100+ (ultimate)**. `rank_from_level()` in `utils.py`, exposed
  as `rank` on `GET /level/<date>/`, shown next to the level on the homepage.
- **XP-rules note.** The profile popup (👤, present on every page) gains an expandable "How XP & ranks
  work" section documenting the XP sources, the streak rule, and the rank table.
- **Calibration test updated.** The dedicated-user calibration now excludes goals (they became large,
  occasional bonuses rather than a weekly grind input); the habit + time grind alone still lands level
  100 in the 4–5 year window.
- **Streak made demanding + now counts worked time.** `STREAK_THRESHOLD` 50 → **250**, and a day now
  qualifies on its **habit + worked-time XP** (goals excluded), not habit XP alone. The old bar (50 =
  two medium habits) was a formality; 250 sits near a strong day's output (a full habit list ≈ 240 plus
  a few tracked hours), so keeping a streak takes a genuinely productive day. Note this reverses the
  earlier "work alone never counts toward the streak" rule — worked time now contributes to
  qualification (though clearing 250 on work alone would take ~12.5 h).
