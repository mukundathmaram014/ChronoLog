---
status: built
---

# 0013 — Recurring stopwatches + reuse-previous dropdown

## Problem / Goal
Two related additions to creating stopwatches:
1. When creating a stopwatch, choose whether it's **recurring**. (Recurring is the concept that should
   drive whether a stopwatch carries forward to future days.)
2. When adding a stopwatch, offer a **dropdown of previously-created stopwatches** so you can quickly
   re-add one you've used before instead of retyping its title/goal.

## Context — current behavior
- Carry-forward today copies **all** of a day's stopwatches forward when a future day is first opened
  (`backend/src/routes/stopwatch.py` `get_stopwatches` carry-forward at ~`:58-94`, plus
  `create_stopwatch_for_date`). There is currently no notion of "recurring" — everything recurs.
- The add-stopwatch form in `frontend/src/Pages/stopwatchpage.jsx` is free-text only.
- Stopwatch model (`backend/src/db.py:62-109`) has no recurrence flag.

## Decisions (made)
1. **Recurring drives carry-forward.** Only stopwatches marked **recurring** carry forward to future
   days; non-recurring ones are **one-off** for their day. This changes today's "everything carries
   forward" behavior and must be reconciled with the DeletedDay logic (see Risks).
2. **Dropdown source:** the user's **distinct stopwatch titles previously created** (all of them, not
   just recurring ones), most-recent first; selecting one prefills title + goal.
3. **Default for new stopwatches: recurring ON** — matches today's "everything recurs" behavior and
   avoids surprising existing users.

## Affected files
- `backend/src/db.py` — add `is_recurring` boolean to `Stopwatch`; update `__init__` + `serialize`.
  **Schema change** — see Risks.
- `backend/src/routes/stopwatch.py` — accept `is_recurring` on create/edit; gate carry-forward
  (`get_stopwatches` / `create_stopwatch_for_date`) on `is_recurring` so only recurring stopwatches
  propagate, preserving the Total, the DeletedDay "intentionally emptied" behavior, and the duplicate
  guard.
- `backend/src/routes/stopwatch.py` — a small endpoint returning the user's distinct prior stopwatch
  titles (+ goal) for the dropdown, scoped by `user_id`, most-recent first.
- `frontend/src/Pages/stopwatchpage.jsx` — add-stopwatch form: a "recurring" toggle and a
  "reuse previous" dropdown that prefills the form.
- `backend/src/app.py` — `ensure_stopwatch_is_recurring_column()` SQLite migration (ALTER TABLE,
  backfill default 1 = recurring), following the existing `ensure_*_column` pattern. *(Added during build.)*
- `frontend/src/Pages/stopwatchpage.css` — styling for the reuse-previous select. *(Added during build.)*
- `backend/tests/test_stopwatch_carryforward.py` — the focused carry-forward tests called for under
  Risks (recurring carries, non-recurring doesn't, deleted day, Total, titles endpoint). *(Added during build.)*

## Approach
1. Add `is_recurring` (boolean, **default True**) to the model + `serialize`.
2. Create/edit routes accept and store it.
3. In carry-forward, only propagate recurring non-Total stopwatches; non-recurring stay one-off. Keep
   Total creation and DeletedDay handling intact; keep the duplicate-title guard.
4. Add the "reuse previous" dropdown (fed by the distinct-prior-titles endpoint) and the recurring
   toggle (default on) to the add form; picking a prior title prefills title + goal.

## Acceptance criteria
- A stopwatch can be marked recurring at creation (and edited); the flag persists; new stopwatches
  default to recurring.
- Only recurring stopwatches appear on future days; non-recurring stay one-off; intentionally-deleted
  days remain empty; no duplicate Totals.
- The add form offers the user's prior distinct stopwatch titles and prefills title/goal when one is
  picked.

## Testing / verification
- Create recurring vs non-recurring stopwatches, advance to a future day, confirm only recurring ones
  carry forward (and Total still appears).
- Confirm a DeletedDay-emptied day stays empty.
- Pick a previous stopwatch from the dropdown and confirm the form prefills.

## Risk
- **Involvement:** Involved — schema change, carry-forward gating, a new dropdown-source endpoint, and add-form changes.
- **Review attention:** High — changes today's "everything carries forward" behavior, tangles with DeletedDay/backfill, and needs a prod migration; add focused carry-forward tests (recurring vs one-off, deleted day, Total).

## Risks & notes
- **SQLite migration** (no Alembic; `create_all` won't alter `stopwatches`): adding `is_recurring` needs
  an `ALTER TABLE`/backfill — existing rows should default to recurring (= current behavior). Pairs with
  spec 0012 (also a `stopwatches` column) — consider doing the two schema changes in one migration.
- Carry-forward + backfill + DeletedDay is intricate (see 0009); add focused tests: recurring carries,
  non-recurring doesn't, deleted day stays empty, Total always present.
