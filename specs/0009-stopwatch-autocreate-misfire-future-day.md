The carry-forward logic that spec 0009 targets (`get_stopwatches` and `create_stopwatch_for_date`) was left untouched by spec 0020, so the diagnosis stands — but 0020 added XP `recompute_from` hooks throughout `stopwatch.py`, shifted line numbers, and established a pytest suite the spec's testing section should now point at. Here's the revised spec:

# 0009 — Stopwatches don't auto-create for a day that already has only a Total

## Problem / Goal
Author note: "there is a glitch where it doesn't auto-create stopwatches for a new day if you've
looked at this future date when in the past." A day that was previously "touched" doesn't get the
carry-forward of recurring stopwatches it should. Make carry-forward populate such days.

## Likely cause (investigate first)
`get_stopwatches` only runs the previous-day carry-forward when the day's list is empty
(the `if not stopwatches:` block in `backend/src/routes/stopwatch.py`, ~line 62 on `main`, one line
lower once spec 0020's branch merges — locate by the comment `# gets previous days stopwatches if
empty`). But a day can end up holding **only a Total stopwatch** with no regular ones (e.g. it was
created/visited earlier, or via the in-between backfill in `create_stopwatch_for_date`). In that case
`stopwatches` is non-empty, the `if not stopwatches` block is skipped, and the regular stopwatches
never carry forward — leaving a day with a lone Total. The backfill loop and the
`while (len(prev_stopwatches) <= 1)` guard immediately below that block are the surrounding logic to
check.

Spec 0020 (XP/level system) modified `stopwatch.py` but did **not** touch `get_stopwatches` or
`create_stopwatch_for_date` — the carry-forward logic and this diagnosis are unchanged. 0020 only
added `recompute_from(user_id, date)` XP hooks to the update/delete/stop/reset routes.

`/build` should reproduce this precisely (navigate across days to create a Total-only day) and confirm
before changing logic.

## Scope
- In scope: ensure a day that has only a Total stopwatch (no regular ones) still receives carried-
  forward stopwatches, without creating duplicates or redundant Totals.
- Out of scope / non-goals: no change to the DeletedDay "intentionally emptied" behavior; don't break
  the existing in-between backfill; no XP recomputation changes (see below).

## Affected files
- `backend/src/routes/stopwatch.py` — `get_stopwatches` carry-forward condition and/or
  `create_stopwatch_for_date` interaction; keep `user_id` scoping and the duplicate guard.
  Since spec 0020, mutation routes in this file call `recompute_from` from `backend/src/xp.py`;
  the carry-forward fix should **not** need to add such a call — carried-forward stopwatches are
  created with zero `curr_duration`, so the day's worked time (and hence its work XP) is unchanged.
- `backend/tests/test_stopwatch_carryforward.py` (new) — focused tests; model on the existing
  `backend/tests/test_habits_carryforward.py` and use `conftest.py`'s auth helpers.

## Approach (pending repro)
1. Reproduce a Total-only day and trace why carry-forward is skipped.
2. Adjust the trigger so "only a Total exists" counts as needing carry-forward (e.g. treat a day with
   zero **non-Total** stopwatches like an empty day), while still respecting the `DeletedDay` marker
   so intentionally-emptied days are not repopulated.
3. Reuse `create_stopwatch_for_date` (it already guards duplicates and handles the Total) so no
   duplicate Total or stopwatch is produced. Note the duplicate-Total path adds the carried
   stopwatch's `goal_time` onto the existing Total — verify the Total's goal time comes out right
   when repopulating a Total-only day.

## Acceptance criteria
- Visiting a day that previously held only a Total stopwatch carries forward the user's recurring
  stopwatches.
- No duplicate Total stopwatch and no duplicate-title stopwatches are created.
- Intentionally-deleted days (DeletedDay marker) are still NOT repopulated.
- Day-level XP is unaffected by carry-forward (no spurious `recompute_from` churn; carried
  stopwatches start at zero duration).

## Testing / verification
- Add pytest cases to the existing suite under `backend/tests/` (it has a working `conftest.py`,
  auth helpers, and `test_habits_carryforward.py` as a direct pattern): empty day, Total-only day,
  deleted day, and a multi-day gap.
- Reproduce the Total-only day, refetch `GET /stopwatches/<date>/`, confirm regular stopwatches appear.
- Verify a day intentionally emptied stays empty, and a normal new day still carries forward.
- Run the full `backend/tests/` suite — `test_xp.py` (from spec 0020) exercises the stopwatch
  mutation routes and will catch XP regressions if the fix touches more than intended.

## Risk
- **Involvement:** Moderate — one backend route, but the carry-forward/backfill logic it changes is intricate.
- **Review attention:** High — carry-forward + backfill is easy to regress (duplicate Totals, runaway backfill); reproduce first and add focused tests.

## Risks & notes
- Carry-forward + backfill logic is intricate and easy to regress (duplicate Totals, infinite/extra
  backfill). Add focused tests around: empty day, Total-only day, deleted day, and a multi-day gap.
- Confirm the exact repro before editing — the fix differs if the real trigger is the backfill loop
  rather than the `if not stopwatches` guard.
- Spec 0020 (`spec/0020-habit-xp-level-system`) also modifies `stopwatch.py` (XP hooks in the
  update/delete/stop/reset routes) and is not yet merged to `main`. Branch this fix from a point that
  includes 0020 (or rebase after it merges) to avoid textual conflicts — 0020's addition in
  `delete_stopwatch` sits directly beside the DeletedDay-marker block.