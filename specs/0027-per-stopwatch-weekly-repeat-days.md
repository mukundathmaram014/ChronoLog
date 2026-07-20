---
title: Let a stopwatch repeat only on chosen weekdays, like habits
status: decided
---

# Let a stopwatch repeat only on chosen weekdays, like habits

## Summary
Habits gained per-weekday recurrence in spec 0014: a 7-bit `repeat_days` bitmask (bit i =
`date.weekday()` i, 0 = Mon … 6 = Sun, default `127` = every day) on the model, weekday-gated
carry-forward, and a 7-toggle day picker in the add/edit form. Stopwatches today only have a
boolean `is_recurring` (spec 0013): a recurring stopwatch carries forward to *every* new day, a
non-recurring one to none. This spec mirrors the habit mechanism onto stopwatches so a stopwatch
can repeat on a chosen subset of weekdays (e.g. Mon/Wed/Fri only).

The carry-forward mirror is the substantial part. During 0014 the habit lookback was upgraded to a
weekday-aware scan (`backend/src/routes/habits.py:60-113`): it walks back to the most recent
non-empty day, then keeps scanning up to 7 more days (one full weekday cycle) collecting the most
recent row per description, and infers deletion when a scheduled day between a candidate's last row
and the first filled day has no row. The stopwatch carry-forward
(`backend/src/routes/stopwatch.py:109-158`) still stops at the first day holding more than just a
Total row — without the extended scan, a Mon-only stopwatch would be lost forever the first time
Tuesday is opened. The stopwatch version is complicated by the Total row: its emptiness test is
`len(prev_stopwatches) <= 1`, and carried goals are folded into the day's Total goal (unless
overridden), so the scan rewrite must keep specs 0004/0023 Total-goal accounting intact.

## Affected files
- `backend/src/db.py` — add `repeat_days` (Integer, default 127) to `Stopwatch`: column,
  `__init__`, `serialize` (mirror `Habit`, db.py:42-43/58/72).
- `backend/src/app.py` — new `ensure_stopwatch_repeat_days_column()` startup migration
  (`ALTER TABLE stopwatches ADD COLUMN repeat_days INTEGER NOT NULL DEFAULT 127`), called from
  `create_app` alongside the existing `ensure_*` functions. **Prod schema change.**
- `backend/src/utils.py` — move `validate_repeat_days` here from `routes/habits.py` so both
  blueprints share it (utils already hosts `VALID_DIFFICULTIES`).
- `backend/src/routes/habits.py` — import `validate_repeat_days` from utils instead of defining it.
- `backend/src/routes/stopwatch.py` — `create_stopwatch_for_date` takes/stores `repeat_days`;
  create/update endpoints accept + validate it (update applies forward only, like habits.py:199-203);
  rewrite the carry-forward in `get_stopwatches` to the habit-style weekday-aware candidate scan;
  return `repeat_days` from `/stopwatches/titles/` for the reuse-dropdown prefill.
- `backend/tests/test_stopwatch_carryforward.py` — new cases: weekday-gated carry, off-day
  stopwatch survives an extra-lookback window, deletion inference, gap fill skips unscheduled days,
  Total goal correct when only a subset of stopwatches lands on a day.
- `backend/tests/test_migrations.py` — cover the new `ensure_stopwatch_repeat_days_column()`
  (same drop-column-then-migrate pattern as the position-column test).
- `frontend/src/Pages/stopwatchpage.jsx` — `repeatDays` state; weekday picker in the add form
  (near the recurring checkbox, ~line 803) and edit form (~line 940); send `repeat_days` in the
  create (~line 267) and edit (~line 460) payloads; prefill on edit (~line 547); reset after add.
- `frontend/src/Pages/stopwatchpage.css` — weekday-toggle styles (copy the
  `.weekday-picker`/`.weekday-toggle` pattern from `frontend/src/Pages/habitpage.css:125-148`).
- `frontend/src/Components/StopwatchItem.jsx` — small repeat-days indicator when the stopwatch
  is recurring and the mask ≠ 127, mirroring `HabitItem.jsx:26-31`.

## Decisions needed
_None — settled in spec-chat (2026-07-19):_
- **`repeat_days` composes with `is_recurring` (Option A, keep both).** `is_recurring = False`
  means "never carries" and `repeat_days` is ignored (stays 127). When recurring, `repeat_days`
  gates which weekdays. The UI shows the 7-day picker only while the recurring checkbox is on,
  in both the add and edit forms. No change to existing rows' semantics, no migration of
  `is_recurring`, and validation matches habits exactly (1–127; 0 rejected).
- **The two "optional" items are in scope:** `/stopwatches/titles/` returns `repeat_days` so the
  reuse dropdown prefills the picker, and `StopwatchItem` shows a small repeat-days indicator
  when the mask ≠ 127 (mirroring `HabitItem.jsx:26-31`).

## Risk
- **Involvement:** Involved — prod schema migration, a rewrite of the stopwatch carry-forward scan
  (the most intricate logic in `stopwatch.py`, interleaved with Total-goal accounting), and day-picker
  UI in two forms.
- **Review attention:** High — stopwatch carry-forward has needed four fix specs already
  (0007/0008/0009/0013) and now interacts with weekday gating, DeletedDay markers, gap backfill, and
  spec 0023's overridden Total goal; plus a production SQLite `ALTER TABLE`.

## Implementation notes
- **Bitmask convention is fixed:** bit i = Python `date.weekday()` i (0 = Mon … 6 = Sun), 127 =
  every day, membership `repeat_days & (1 << weekday)`. The frontend already encodes this order in
  `habitpage.jsx` (`WEEKDAY_LABELS = ["Mo", …, "Su"]`) — reuse the identical pattern, including the
  "select at least one repeat day" client-side guard (habitpage.jsx:97-100) and server-side
  `validate_repeat_days` (1–127, reject bools).
- **Carry-forward rewrite:** port the habit algorithm (habits.py:60-113) onto stopwatches:
  1. Walk back to the most recent day that has non-Total stopwatches (`len(rows) > 1` given the
     leftover-Total quirk), note it as `first_filled_date`, then continue up to 7 more days
     collecting the most recent row per *title* into a candidates dict; stop at a stopwatch-type
     DeletedDay.
  2. Skip candidates that are non-recurring (`is_recurring == False`; their `repeat_days` is
     ignored) — this preserves `test_only_recurring_stopwatches_carry_forward`.
  3. Deletion inference: if any *scheduled* weekday strictly after a candidate's last row and ≤
     `first_filled_date` has no row for that title, the user deleted it there — don't carry it.
  4. Gap backfill from `first_filled_date` to the requested day creates a row only on scheduled
     weekdays; the requested day itself only gets the stopwatch if its weekday bit is set. Keep
     using `create_stopwatch_for_date` so per-day Total creation/goal folding stays centralized.
  5. Preserve the existing leftover-Total handling: zero a non-overridden Total's goal before
     folding carried goals in (stopwatch.py:131-137), and keep the final "serialize the Total once"
     response shape. Note the current code backfills from a single `prev_date`; with per-title
     candidates from different days, backfill must start from `first_filled_date` like habits do.
- **Total row:** never give the Total a meaningful mask; it is created per-day by
  `create_stopwatch_for_date` and excluded from carry (it stays default 127, unused).
- **Update endpoint:** mirror habits — validate, assign, applies forward only (past rows untouched).
  The Total-row edit branch (stopwatch.py:260-273) should ignore `repeat_days`.
- **Reuse dropdown:** `/stopwatches/titles/` currently returns `{title, goal_time}`; add the most
  recent `repeat_days` so picking a previous title prefills the day picker.
- **Tests:** extend `backend/tests/test_stopwatch_carryforward.py` following its existing style
  (it already covers recurring/non-recurring, deleted days, gap fill, overridden Total goal, XP
  invariance — each of those needs a weekday-gated variant, plus: an off-day stopwatch found via the
  7-day extended scan, and deletion inference). Mirror assertions from
  `backend/tests/test_habits_carryforward.py` where the semantics are shared. Also assert
  carry-forward still leaves day XP unchanged (`test_carry_forward_leaves_day_xp_unchanged`).
- **Frontend:** stopwatchpage.jsx keeps per-form state exactly like habitpage.jsx does
  (`newRepeatDays`, default `ALL_DAYS = 127`); send `repeat_days` alongside `is_recurring`; reset to
  127 after a successful add (the add-form reset block, ~line 293-298). The day picker renders only
  while the recurring checkbox is checked (add and edit forms); when unchecked, send/keep
  `repeat_days = 127` so toggling recurring back on returns to the every-day default. Picking a
  previous title from the reuse dropdown prefills the picker from that title's returned
  `repeat_days`. All API calls go through `useFetch`'s `fetchWithAuth` as already done.
