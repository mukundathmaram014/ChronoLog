---
title: Support a per-weekday goal time for each stopwatch
status: decided
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
decide what `goal_time` a new row gets.

That containment holds for reads, but not for XP writes, and this spec fixes that too. Every
`recompute_from` call in `stopwatch.py` is gated on a **duration** change (`:341`, `:368`, `:406`,
`:446`, `:501`), and `create_stopwatch_for_date` never calls it at all — yet `xp.py:38` feeds the
Total's `goal_time` into `goal_hours`, which drives `GOAL_TIME_BONUS` and the normal/overtime split.
So a goal change today leaves the persisted `DailyXP` row stale until something *else* touches that
day's duration. That is a pre-existing gap, but it is rare today (goals only change when the user
deliberately edits one) and routine after this spec: carry-forward will land a *different* goal on a
day with no user action at all. Shipping the weekday schedule without this fix would ship a feature
whose headline effect — a lighter Saturday goal — silently fails to reach XP. So this spec also makes
the day's XP recompute whenever the Total row's `goal_time` actually changes.

## Affected files
- `backend/src/db.py` — add `weekday_goal_times` to `Stopwatch` (nullable `db.String` holding a JSON
  list of 7 millisecond values, index = `date.weekday()`; NULL = one uniform goal, the current
  behavior): column, `__init__`, and `serialize` (emit a parsed list of 7 numbers or `null`). Add
  `weekday_goal_times_list()` next to it so routes never parse the JSON inline.
- `backend/src/app.py` — new `ensure_stopwatch_weekday_goal_times_column()`
  (`ALTER TABLE stopwatches ADD COLUMN weekday_goal_times VARCHAR`), called from `create_app`
  alongside the other `ensure_*` migrations (app.py:171-183). **Prod schema change.**
- `backend/src/utils.py` — two additions next to `validate_repeat_days` (utils.py:15):
  `validate_weekday_goal_times(value)` (`None`, or a list of exactly 7 entries, each `None` or a
  well-formed `"HH:MM"` string) and `effective_goal_time(schedule, base_goal_time, target_date)`
  (the single derivation point — see notes).
- `backend/src/routes/stopwatch.py` — the bulk of the change: `create_stopwatch_for_date` takes/stores
  the schedule and derives the row's `goal_time` from the target date's weekday; `POST /stopwatches/`
  and `PUT /stopwatches/<id>/` accept + validate it; carry-forward (`get_stopwatches`, both the
  gap-backfill loop and the requested-day create) passes the schedule through so each created day gets
  its own weekday's goal; `/stopwatches/titles/` returns it for the reuse-dropdown prefill. Plus the
  XP fix: recompute when the Total's `goal_time` changed, not only its `curr_duration` (create, update,
  delete, and one post-loop call for carry-forward).
- `backend/src/xp.py` — comment/docstring accuracy only (`_day_inputs`, xp.py:31-39, describes the
  day's goal hours as "the sum of the individual stopwatch goals"; note that those per-day goals can
  now differ by weekday). No logic change — it already reads the Total row's per-day `goal_time`.
- `backend/tests/test_stopwatch_carryforward.py` — carry-forward lands the correct per-weekday goal
  on the requested day and on backfilled gap days; the Total's summed goal matches the weekday's
  goals; a schedule with a 0 entry means "no goal" that weekday; a NULL schedule behaves exactly as
  today; edit/delete goal deltas against the Total stay correct.
- `backend/tests/test_migrations.py` — cover `ensure_stopwatch_weekday_goal_times_column()` with the
  existing drop-column-then-migrate pattern.
- `backend/tests/test_utils.py` — `validate_weekday_goal_times` and `effective_goal_time` cases.
- `backend/tests/test_xp.py` — a day whose per-weekday goal is smaller/larger shifts the overtime
  split and the `GOAL_TIME_BONUS` threshold accordingly; **and** the recompute fix: a goal-only edit
  (no duration change) updates `DailyXP`, as do a create and a delete that move the Total's goal, and
  carry-forward landing a weekday goal on a day that already had a ledger row.
- `frontend/src/Pages/stopwatchpage.jsx` — a "Different goal per day" checkbox beside the existing
  "No goal" toggle; when on, the single Hours/Minutes pair (add form ~line 996, edit form ~line 858)
  is replaced by seven compact pairs. Send `weekday_goal_times` in the create (~line 305) and edit
  (~line 523) payloads; prefill from the reuse dropdown (`prefillFromPrevious`, ~line 353) and from
  the edited row (`openEditStopwatch`, ~line 597); reset after a successful add (~line 337-343) and
  edit (~line 543-556).
- `frontend/src/Pages/stopwatchpage.css` — styles for the per-weekday goal rows, matching the
  existing `.weekday-picker` / `.weekday-toggle` block, plus a dimmed state for unscheduled weekdays.
- `frontend/src/Components/StopwatchItem.jsx` — the "Goal: Xh Ym" line (line 37-41) already shows the
  row's own goal, so it stays correct; add a small "varies by day" hint when the row has a schedule,
  mirroring the existing repeat-days indicator (line 42-48).
- `docs/implementation_details.md` — the "How the Goal Time Feature was Implemented for Stopwatches"
  section (~line 36) gains a paragraph on the per-weekday schedule and the goal-change recompute.

## Decisions needed
- [x] **Does editing a stopwatch's weekday schedule change the day currently being viewed?** → **Yes.**
  Saving an edit rewrites the open day's `goal_time` to that weekday's entry and folds the delta into
  the Total (unless `goal_overridden`), consistent with how a plain `goal_time` edit behaves today.
  Editing a *different* weekday's slot changes nothing visible until that weekday comes around.
- [x] **Form shape for seven goals.** → A "Different goal per day" checkbox that swaps the single
  Hours/Minutes pair for seven compact pairs. All seven are always shown, with unscheduled weekdays
  dimmed but still editable, so re-enabling a day in the picker restores its remembered goal.
- [x] **What does the single goal field mean in per-day mode?** → Nothing; it is hidden. The seven
  values are authoritative and the row's goal is always `schedule[date.weekday()]`, so there is no
  second number that can disagree with it.
- [x] **Is the XP-recompute-on-goal-change fix in scope here?** → **Yes**, included in this spec
  rather than split out: this feature is what turns the stale-ledger gap from rare into routine.

## Risk
- **Involvement:** Involved — a production SQLite `ALTER TABLE`, changes threaded through every
  stopwatch write path (create, update, delete deltas, carry-forward, backfill, titles), a new
  repeating input group in two frontend forms, and new XP-ledger write triggers.
- **Review attention:** High — this lands in the same carry-forward + Total-goal accounting that has
  needed repeated fix specs (0007/0008/0009/0013/0027), and it now also *writes* to the XP ledger on a
  new trigger. A wrong weekday index, a schedule dropped during backfill, or a recompute fired from
  the wrong start date silently mis-scores days.

## Implementation notes

### Storage and derivation
- **Weekday index convention is fixed and shared with `repeat_days`:** index i = Python
  `date.weekday()` i (0 = Mon … 6 = Sun), matching `WEEKDAY_LABELS` (`stopwatchpage.jsx:28`). The
  schedule is a *dense* 7-element list — always 7 values, even for unscheduled weekdays — so lookup is
  a total function with no fallback branch. `0` in a slot means "no goal that day", matching the
  existing `goal_time = 0` convention (`stopwatch.py:238`); `StopwatchItem.jsx:38` already renders
  that as "No goal". NULL/absent column means "one uniform goal", i.e. every existing row and every
  stopwatch created without the feature keeps today's behavior exactly.
- **Single derivation point.** `effective_goal_time(schedule, base_goal_time, target_date)` →
  `schedule[target_date.weekday()]` when a schedule exists, else `base_goal_time`. Every write path
  calls it; nothing else indexes the list. `create_stopwatch_for_date` calls it once and stores both
  the derived `goal_time` and the schedule on the new row, so the existing Total-goal folding
  (`stopwatch.py:26-37`) needs no change — it already sums whatever `goal_time` the child landed with.
- **Derivation is by weekday alone, independent of `repeat_days`.** A row can exist on a weekday its
  own repeat set excludes (created manually that day, or `repeat_days` was narrowed after it had
  already carried forward — edits are forward-only, `stopwatch.py:349`). Such a row still gets
  `schedule[weekday]` for its actual date. This is exactly why unscheduled slots stay editable rather
  than being forced to `0`: forcing them would silently zero a real row's goal, and its Total
  contribution, the moment a day was unchecked in the picker.
- **Two ways to say "nothing on Saturday", and they differ.** Unchecking Saturday in the day picker
  means *no row is created at all*; setting Saturday to `0h 0m` means *a row with no goal*. Both are
  legal and intentional — the first removes the stopwatch from the day, the second keeps it there to
  log time against without a target. An all-zero schedule is legal too: "no goal any day", the same
  state the single-goal path reaches via `goal_time: null`.

### Wire format and validation
- `weekday_goal_times` travels as **seven `"HH:MM"` strings** (or `null` for a slot), matching the
  existing `goal_time` field's format, and is converted with the existing
  `convert_time_string_to_milliseconds` before being stored as a JSON list of 7 millisecond numbers.
  A `null` slot and `"00:00"` both store `0`. Sending `weekday_goal_times: null` clears the schedule
  and returns the row to uniform mode.
- `validate_weekday_goal_times` rejects: length ≠ 7, non-list, entries that are neither `None` nor a
  `"HH:MM"` string with hours 0-23 / minutes 0-59, and bools (same `isinstance(x, bool)` guard
  `validate_repeat_days` uses). Note this is *stricter* than the existing single-`goal_time` path,
  which doesn't validate its string at all — don't "fix" that here, it's out of scope.
- Validate up front in both `POST` and `PUT`, like `repeat_days` (`stopwatch.py:241,305`), so a bad
  schedule rejects the whole request before any mutation.

### Write paths
- **Carry-forward** (`get_stopwatches`, stopwatch.py:171-188): the candidate row carries its schedule
  forward unchanged; only the derived `goal_time` differs per created day. Both create sites — the gap
  backfill loop (line 182) and the requested-day create (line 185) — must pass the schedule, and each
  gets its own weekday's goal. The leftover-Total zeroing (line 165-169) and the "serialize the Total
  once" response shape stay as they are.
- **Update endpoint** (stopwatch.py:290-373): ignore the schedule entirely in the Total-row branch (a
  Total has no weekday schedule, and its `match_sum` path keeps summing children's `goal_time`). In
  the child branch, `change_in_goal_time` must be the delta of the row's *effective* goal for its own
  date, so the Total stays the exact sum of its children — this is the easiest place to introduce
  drift.
- **Delete** (stopwatch.py:375-412) already subtracts the row's stored `goal_time`, so its goal
  accounting needs no change — only its recompute condition does (below).
- **Reuse dropdown:** `/stopwatches/titles/` (stopwatch.py:91) currently returns
  `{title, goal_time, repeat_days}`; add `weekday_goal_times` so picking a prior title prefills the
  whole schedule and turns per-day mode on.

### XP recompute on goal change
- **The rule: recompute the day when the Total row's `goal_time` *or* `curr_duration` actually
  changed.** Implement it by snapshotting both off the Total before mutating and comparing after,
  rather than by threading more delta flags through each branch — the deltas already exist in some
  paths and not others, and the snapshot is one condition that can't drift out of sync with them.
  This subsumes today's `change_in_duration != 0` checks at `:341`, `:368`, `:406`.
- Concretely this adds a recompute where there is none today: a goal-only edit on a child, a goal edit
  or `match_sum` toggle on the Total itself, a create (its goal folds into the Total), and a delete of
  a zero-duration stopwatch that had a goal. When the Total is `goal_overridden`, a child's goal edit
  does *not* move the Total's goal — so the snapshot compares equal and no recompute fires, which is
  correct.
- **Carry-forward must recompute once, not per created day.** `recompute_from(user_id, day)` walks
  from `day` to the user's last activity date (`xp.py:65-74`), so calling it inside the backfill loop
  would re-walk the whole tail once per created day. Give `create_stopwatch_for_date` a
  `recompute = True` kwarg, pass `recompute = False` from both carry-forward create sites, and after
  the loop issue a single `recompute_from(user_id, earliest_created_date)` — which covers every
  backfilled day *and* the requested day, since the walk goes forward. The `POST /stopwatches/` path
  keeps the default and is unaffected.
- Recompute before `db.session.commit()`, matching every existing caller (`recompute_from`'s docstring
  says the caller commits).

### Tests
- Follow the style of `backend/tests/test_stopwatch_carryforward.py` (its `create_stopwatch` helper
  takes optional kwargs — extend it with `weekday_goal_times`). Cover at minimum: a Mon-heavy schedule
  carried to a Tue lands the Tue goal; a multi-day gap backfill gives each day its own goal; the
  Total's goal equals the sum of that day's landed goals (and is untouched when `goal_overridden`); a
  schedule survives a chain of carried days; a row sitting on a weekday outside its `repeat_days`
  still reads that weekday's slot.
- In `test_xp.py`, cover both halves: that a lighter goal day reaches `GOAL_TIME_BONUS` sooner and
  tips into `XP_PER_HOUR_OVERTIME` sooner, and that the ledger actually moves — a goal-only edit with
  no duration change updates `DailyXP.xp_earned` and `User.total_xp`; a create/delete that shifts the
  Total's goal does too; carry-forward onto a day that already had a ledger row (e.g. from habits)
  rescores it; and a `goal_overridden` Total does *not* rescore on a child goal edit.

### Frontend
- All calls stay on `useFetch`'s `fetchWithAuth`. Keep the existing single-goal path as the default so
  the form is unchanged for users who don't want this; only send `weekday_goal_times` when per-day
  mode is on, and send `null` to clear it.
- Toggling per-day mode **on** seeds all seven slots from the current single Hours/Minutes value (a 2h
  stopwatch becomes 2h × 7 — no surprise jump). Toggling it **off** sends `null`; the seven values are
  not remembered client-side after that.
- The top-level "No goal" checkbox is hidden in per-day mode — `0h 0m` in a slot is how "no goal that
  weekday" is expressed.
- The seven rows use the `WEEKDAY_LABELS` ordering (`stopwatchpage.jsx:28`) so they line up with the
  repeat-day toggles directly below them. Dim rows for weekdays not in `repeatDays`, but keep them
  enabled. Keep the same "Select at least one repeat day" style client-side guard for any new invalid
  state.
- Both forms share the same state (`inputHours`/`inputMinutes`/`noGoal`/`repeatDays`), so the new
  state is written once and appears in both the add form (~line 991-1032) and the edit form
  (~line 846-894). Remember to clear it in both reset paths.

### Coordination
- Spec 0034 (`status: decided`, not yet built) also touches `db.py`, `app.py`, `utils.py`, `xp.py`,
  `test_xp.py` and `test_migrations.py`, and changes `recompute_from` to persist component columns.
  No logical conflict — 0034 changes what the ledger row stores, this spec changes when it is
  rewritten — but whichever lands second needs a rebase, most visibly in `create_app`'s `ensure_*`
  list and in `test_migrations.py`.
