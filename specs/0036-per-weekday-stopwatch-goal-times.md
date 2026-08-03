---
title: Support a per-weekday goal time for each stopwatch
status: draft
---

# Support a per-weekday goal time for each stopwatch

## Summary
A stopwatch carries one `goal_time` (`Stopwatch.goal_time`, a Float of milliseconds — `db.py:226`),
and spec 0027 gave it a `repeat_days` bitmask deciding *which* weekdays it carries to. There is no way
to say "this stopwatch runs Mon–Sun but I want 2h on weekdays and 30m on Saturday": carry-forward
copies the previous row's single `goal_time` onto every scheduled day
(`backend/src/routes/stopwatch.py:182,185`), so a heavier or lighter day has to be edited by hand each
time. This spec adds an optional per-weekday goal schedule alongside `repeat_days`, so the goal a
carried row lands with depends on the weekday it lands on.

The row-level `goal_time` stays the single source of truth for *that day* — every downstream consumer
already reads it per day and keeps working unchanged: the Total row's goal is the sum of the day's
children's goals (`create_stopwatch_for_date`, `stopwatch.py:36`, plus the update/delete deltas), and
`xp.py:_day_inputs` reads the Total's `goal_time` for the goal-time bonus and the normal/overtime split
in `utils.compute_day_xp`. The new column is a *template* consulted at creation/carry-forward time to
decide what `goal_time` a new row gets. That keeps the change contained to the stopwatch write paths,
but it also means the daily goal a user sees in the Total, in stats, and in XP now varies by weekday —
worth an explicit test at each of those seams rather than assuming it falls out.

## Affected files
- `backend/src/db.py` — add `weekday_goal_times` to `Stopwatch` (nullable `db.String` holding a JSON
  list of 7 millisecond values, index = `date.weekday()`; NULL = one uniform goal, the current
  behavior): column, `__init__`, and `serialize` (emit a parsed list of 7 numbers or `null`). Add a
  small helper (`goal_time_for_weekday(weekday)`) next to it so routes never parse the JSON inline.
- `backend/src/app.py` — new `ensure_stopwatch_weekday_goal_times_column()`
  (`ALTER TABLE stopwatches ADD COLUMN weekday_goal_times VARCHAR`), called from `create_app`
  alongside the other `ensure_*` migrations (app.py:171-183). **Prod schema change.**
- `backend/src/utils.py` — `validate_weekday_goal_times(value)` next to `validate_repeat_days`:
  `None`, or a list of exactly 7 non-negative numbers (reject bools/strings/negatives).
- `backend/src/routes/stopwatch.py` — the bulk of the change:
  `create_stopwatch_for_date` takes/stores the schedule and derives the row's `goal_time` from the
  target date's weekday; `POST /stopwatches/` and `PUT /stopwatches/<id>/` accept + validate it;
  carry-forward (`get_stopwatches`, both the gap-backfill loop and the requested-day create) passes
  the schedule through so each created day gets its own weekday's goal; `/stopwatches/titles/`
  returns it for the reuse-dropdown prefill.
- `backend/src/xp.py` — comment/docstring accuracy only (`_day_inputs`, xp.py:31-39, describes the
  day's goal hours as "the sum of the individual stopwatch goals"; note that those per-day goals can
  now differ by weekday). No logic change — it already reads the Total row's per-day `goal_time`.
- `backend/tests/test_stopwatch_carryforward.py` — carry-forward lands the correct per-weekday goal
  on the requested day and on backfilled gap days; the Total's summed goal matches the weekday's
  goals; a schedule with a 0 entry means "no goal" that weekday; a NULL schedule behaves exactly as
  today; edit/delete goal deltas against the Total stay correct.
- `backend/tests/test_migrations.py` — cover `ensure_stopwatch_weekday_goal_times_column()` with the
  existing drop-column-then-migrate pattern.
- `backend/tests/test_utils.py` — `validate_weekday_goal_times` cases.
- `backend/tests/test_xp.py` — a day whose per-weekday goal is smaller/larger shifts the
  overtime split and the `GOAL_TIME_BONUS` threshold accordingly (guards the seam this spec relies on).
- `frontend/src/Pages/stopwatchpage.jsx` — per-weekday goal inputs in the add form and the child-edit
  form (near `renderWeekdayPicker`, ~line 620); send `weekday_goal_times` in the create (~line 305)
  and edit (~line 523) payloads; prefill from the reuse dropdown (`prefillFromPrevious`, ~line 353)
  and from the edited row (`openEditStopwatch`, ~line 597); reset after a successful add
  (~line 337-343) and edit (~line 543-556).
- `frontend/src/Pages/stopwatchpage.css` — styles for the per-weekday goal rows, matching the
  existing `.weekday-picker` / `.weekday-toggle` block.
- `frontend/src/Components/StopwatchItem.jsx` — the "Daily goal: Xh Ym" line (line 38-41) already
  shows the row's own goal, so it stays correct; add a small "varies by day" hint when the row has a
  schedule, mirroring the existing repeat-days indicator (line 42-47).
- `docs/implementation_details.md` — the `goal_time` note (line 36) gains a sentence on the
  per-weekday schedule.

## Decisions needed
- [ ] **Does editing a stopwatch's weekday schedule change the day currently being viewed?**
  `repeat_days` edits are forward-only (past/present rows untouched), but a `goal_time` edit today
  *does* apply today and adjusts the Total. Options: (a) editing the schedule also rewrites the open
  day's `goal_time` to that weekday's entry and folds the delta into the Total (consistent with how
  goal edits behave now, but one action silently moves today's goal and today's XP), or (b) the
  schedule applies forward only and today's goal only changes if the user also edits the goal field.
- [ ] **Form shape for seven goals.** The add/edit form currently has one hours/minutes pair plus a
  "no goal" toggle. Options: (a) a "different goal per day" checkbox that expands the single pair into
  one compact hours/minutes pair per *scheduled* weekday (unscheduled days get no input), or (b) always
  show seven rows. Related: should an unscheduled weekday be editable at all, so that re-enabling it in
  the day picker restores a remembered goal?

## Risk
- **Involvement:** Involved — a production SQLite `ALTER TABLE`, changes threaded through every
  stopwatch write path (create, update, delete deltas, carry-forward, backfill, titles), and a new
  repeating input group in two frontend forms.
- **Review attention:** High — this lands in the same carry-forward + Total-goal accounting that has
  needed repeated fix specs (0007/0008/0009/0013/0027) and now also feeds the XP goal bonus and
  overtime split; a wrong weekday index or a schedule dropped during backfill silently mis-scores days.

## Implementation notes
- **Weekday index convention is fixed and shared with `repeat_days`:** index i = Python
  `date.weekday()` i (0 = Mon … 6 = Sun). The schedule is a *dense* 7-element list — always 7 values,
  even for unscheduled weekdays — so lookup is a total function with no fallback branch. `0` in a slot
  means "no goal that day", matching the existing `goal_time = 0` convention (`stopwatch.py:238`).
  NULL/absent column means "one uniform goal", i.e. every existing row and every stopwatch created
  without the feature keeps today's behavior exactly.
- **Single derivation point.** Add one helper used by every write path:
  `effective_goal_time(schedule, base_goal_time, target_date)` → `schedule[target_date.weekday()]` when
  a schedule exists, else `base_goal_time`. `create_stopwatch_for_date` should call it once and store
  both the derived `goal_time` and the schedule on the new row; the existing Total-goal folding
  (`stopwatch.py:26-37`) then needs no change, because it already sums whatever `goal_time` the child
  landed with.
- **Carry-forward** (`get_stopwatches`, stopwatch.py:171-188): the candidate row carries its schedule
  forward unchanged; only the derived `goal_time` differs per created day. Both create sites — the gap
  backfill loop (line 182) and the requested-day create (line 185) — must pass the schedule, and each
  gets its own weekday's goal. The leftover-Total zeroing (line 165-169) and the "serialize the Total
  once" response shape stay as they are.
- **Update endpoint** (stopwatch.py:290-373): validate the schedule up front like `repeat_days`;
  ignore it entirely in the Total-row branch (a Total has no weekday schedule, and its `match_sum` path
  keeps summing children's `goal_time`). In the child branch, `change_in_goal_time` must be the delta
  of the row's *effective* goal for its own date, so the Total stays the exact sum of its children —
  this is the easiest place to introduce drift. Deleting a stopwatch (line 375-412) already subtracts
  the row's stored `goal_time`, so it needs no change.
- **Reuse dropdown:** `/stopwatches/titles/` currently returns `{title, goal_time, repeat_days}`; add
  `weekday_goal_times` so picking a prior title prefills the whole schedule.
- **Validation:** reject a schedule whose length ≠ 7, non-numeric or negative entries, and bools
  (same `isinstance(x, bool)` guard `validate_repeat_days` uses). An all-zero schedule is legal — it is
  "no goal any day", which the single-goal path already permits via `goal_time: null`.
- **Tests:** follow the style of `backend/tests/test_stopwatch_carryforward.py` (its
  `create_stopwatch` helper takes optional kwargs — extend it with `weekday_goal_times`). Cover at
  minimum: a Mon-heavy schedule carried to a Tue lands the Tue goal; a multi-day gap backfill gives
  each day its own goal; the Total's goal equals the sum of that day's landed goals (and is untouched
  when `goal_overridden`); a schedule survives a chain of carried days; and — via `test_xp.py` — that
  a lighter goal day reaches `GOAL_TIME_BONUS` sooner and tips into `XP_PER_HOUR_OVERTIME` sooner.
- **Frontend:** all calls stay on `useFetch`'s `fetchWithAuth`. Keep the existing single-goal path as
  the default so the form is unchanged for users who don't want this; only send `weekday_goal_times`
  when the per-day mode is on, and send `null` to clear it. Reuse the `WEEKDAY_LABELS`
  (`stopwatchpage.jsx:28`) ordering so the goal rows line up with the repeat-day toggles, and keep the
  same "Select at least one repeat day" style client-side guard for any new invalid state.
