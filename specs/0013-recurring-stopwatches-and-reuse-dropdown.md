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

## ⚠️ Decision needed
1. **Does "recurring" change carry-forward semantics?** This is the core decision.
   - **(Recommended) Yes:** only stopwatches marked recurring carry forward to future days;
     non-recurring ones are one-off for their day. This makes the flag meaningful but **changes existing
     behavior** (today everything carries forward) and must be reconciled with the DeletedDay logic.
   - Alternative: recurrence is metadata only (everything still carries forward as now) — lower value,
     basically just a label.
2. **Dropdown source.** Recommended: distinct stopwatch titles previously created by this user
   (optionally only those marked recurring), most-recent first. Selecting one prefills title + goal.
   Confirm whether it's all past titles or recurring-only.
3. **Default for new stopwatches:** recurring on or off by default? (Recommended: on, to match today's
   "everything recurs" behavior and avoid surprising existing users.)

## Affected files
- `backend/src/db.py` — add `is_recurring` boolean to `Stopwatch`; update `__init__` + `serialize`.
  **Schema change** — see Risks.
- `backend/src/routes/stopwatch.py` — accept `is_recurring` on create/edit; if Decision 1 = yes, gate
  carry-forward (`get_stopwatches` / `create_stopwatch_for_date`) on `is_recurring`, preserving the
  Total and the DeletedDay "intentionally emptied" behavior and the duplicate guard.
- (Maybe) `backend/src/routes/stopwatch.py` — a small endpoint returning the user's distinct prior
  stopwatch titles (+ goal) for the dropdown, scoped by `user_id`.
- `frontend/src/Pages/stopwatchpage.jsx` — add-stopwatch form: a "recurring" toggle and a
  "reuse previous" dropdown that prefills the form.

## Approach
1. Add `is_recurring` to the model + serialize (default per Decision 3).
2. Create/edit routes accept and store it.
3. If Decision 1 = yes: in carry-forward, only propagate recurring non-Total stopwatches; keep Total
   creation and DeletedDay handling intact; keep the duplicate-title guard.
4. Add the reuse dropdown (and its data source) and the recurring toggle to the add form.

## Acceptance criteria
- A stopwatch can be marked recurring at creation (and edited); the flag persists.
- (If Decision 1 = yes) Only recurring stopwatches appear on future days; non-recurring stay one-off;
  intentionally-deleted days remain empty; no duplicate Totals.
- The add form offers prior stopwatches and prefills title/goal when one is picked.

## Testing / verification
- Create recurring vs non-recurring stopwatches, advance to a future day, confirm only recurring ones
  carry forward (and Total still appears).
- Confirm a DeletedDay-emptied day stays empty.
- Pick a previous stopwatch from the dropdown and confirm the form prefills.

## Risks & notes
- **SQLite migration** (no Alembic; `create_all` won't alter `stopwatches`): adding `is_recurring` needs
  an `ALTER TABLE`/backfill — existing rows should default to recurring (= current behavior). Pairs with
  spec 0012 (also a `stopwatches` column) — consider doing the two schema changes in one migration.
- Carry-forward + backfill + DeletedDay is intricate (see 0009); add focused tests: recurring carries,
  non-recurring doesn't, deleted day stays empty, Total always present.
