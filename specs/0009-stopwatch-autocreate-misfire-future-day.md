# 0009 — Stopwatches don't auto-create for a day that already has only a Total

## Problem / Goal
Author note: "there is a glitch where it doesn't auto-create stopwatches for a new day if you've
looked at this future date when in the past." A day that was previously "touched" doesn't get the
carry-forward of recurring stopwatches it should. Make carry-forward populate such days.

## Likely cause (investigate first)
`get_stopwatches` only runs the previous-day carry-forward when the day's list is empty
(`backend/src/routes/stopwatch.py:58-65`: `if not stopwatches:`). But a day can end up holding **only
a Total stopwatch** with no regular ones (e.g. it was created/visited earlier, or via the in-between
backfill in `create_stopwatch_for_date`). In that case `stopwatches` is non-empty, the `if not
stopwatches` block is skipped, and the regular stopwatches never carry forward — leaving a day with a
lone Total. The backfill loop and the `while (len(prev_stopwatches) <= 1)` guard
(`stopwatch.py:71-94`) are the surrounding logic to check.

`/build` should reproduce this precisely (navigate across days to create a Total-only day) and confirm
before changing logic.

## Scope
- In scope: ensure a day that has only a Total stopwatch (no regular ones) still receives carried-
  forward stopwatches, without creating duplicates or redundant Totals.
- Out of scope / non-goals: no change to the DeletedDay "intentionally emptied" behavior; don't break
  the existing in-between backfill.

## Affected files
- `backend/src/routes/stopwatch.py` — `get_stopwatches` carry-forward condition and/or
  `create_stopwatch_for_date` interaction; keep `user_id` scoping and the duplicate guard.

## Approach (pending repro)
1. Reproduce a Total-only day and trace why carry-forward is skipped.
2. Adjust the trigger so "only a Total exists" counts as needing carry-forward (e.g. treat a day with
   zero **non-Total** stopwatches like an empty day), while still respecting the `DeletedDay` marker
   so intentionally-emptied days are not repopulated.
3. Reuse `create_stopwatch_for_date` (it already guards duplicates and handles the Total) so no
   duplicate Total or stopwatch is produced.

## Acceptance criteria
- Visiting a day that previously held only a Total stopwatch carries forward the user's recurring
  stopwatches.
- No duplicate Total stopwatch and no duplicate-title stopwatches are created.
- Intentionally-deleted days (DeletedDay marker) are still NOT repopulated.

## Testing / verification
- Reproduce the Total-only day, refetch `GET /stopwatches/<date>/`, confirm regular stopwatches appear.
- Verify a day intentionally emptied stays empty, and a normal new day still carries forward.

## Risk
- **Involvement:** Moderate — one backend route, but the carry-forward/backfill logic it changes is intricate.
- **Review attention:** High — carry-forward + backfill is easy to regress (duplicate Totals, runaway backfill); reproduce first and add focused tests.

## Risks & notes
- Carry-forward + backfill logic is intricate and easy to regress (duplicate Totals, infinite/extra
  backfill). Add focused tests around: empty day, Total-only day, deleted day, and a multi-day gap.
- Confirm the exact repro before editing — the fix differs if the real trigger is the backfill loop
  rather than the `if not stopwatches` guard.
