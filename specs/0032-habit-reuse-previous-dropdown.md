---
title: Add a "reuse previous" dropdown to the add-habit form
status: draft
---

# Add a "reuse previous" dropdown to the add-habit form

## Summary
**Answer to "was this already built?": only for stopwatches, not for habits.** Spec 0013 shipped a
"reuse previous" dropdown on the add-stopwatch form, backed by `GET /api/stopwatches/titles/`
(`backend/src/routes/stopwatch.py:73-92`), which returns the user's distinct prior stopwatch titles
(most-recent first) along with each one's latest `goal_time` and `repeat_days`. The frontend fetches it
into `previousTitles` and `prefillFromPrevious` fills the add form
(`frontend/src/Pages/stopwatchpage.jsx:351-362`, `:966-981`). The add-**habit** form has no equivalent:
it is free-text description + weekday picker + difficulty picker, with nothing to pull from history
(`frontend/src/Pages/habitpage.jsx:301-327`).

This spec mirrors the stopwatch feature onto habits: a new `GET /api/habits/titles/` endpoint returning
the user's distinct prior habit **descriptions**, most-recent first, each with its most recent
`repeat_days` and `difficulty`; and a "Reuse previous" `<select>` at the top of the add-habit form that
prefills description, repeat days, and difficulty. The one thing that does *not* transfer cleanly is
duplicate handling: habits carry forward day to day, so on a typical day most prior descriptions are
already on the list, and re-adding one hits the existing per-day duplicate guard
(`create_habit_for_date` → 409, surfaced as "A habit with this description already exists.") — see
Decisions needed.

## Affected files
- `backend/src/routes/habits.py` — new `GET /habits/titles/` endpoint: distinct prior descriptions for
  the user, most-recent first, each with latest `repeat_days` + `difficulty`. Scope by `user_id`.
- `frontend/src/Pages/habitpage.jsx` — `previousDescriptions` state, a fetch of `/habits/titles/`, a
  `prefillFromPrevious` handler, and the `<select>` rendered inside the `addHabit` block.
- `frontend/src/Pages/habitpage.css` — styling for the select (mirror `.reuse-previous-select` in
  `frontend/src/Pages/stopwatchpage.css:411-424` and its mobile rule at `:503`).
- `backend/tests/test_habits_carryforward.py` — tests for the new endpoint (distinct, most-recent
  first, user-scoped, returns repeat_days + difficulty), mirroring
  `backend/tests/test_stopwatch_carryforward.py:126-144` and `:418-424`.

## Decisions needed
- [ ] Should the dropdown hide descriptions already present on the selected day? Habits carry forward,
      so unfiltered the list will usually be dominated by habits already on today's list, and picking
      one just produces the 409 duplicate error. Options: (a) mirror stopwatch exactly — show all, let
      the existing 409 message handle it; (b) filter out descriptions already in `allHabits` for the
      selected day so only genuinely re-addable ones appear (fewer dead options, but a shorter/emptier
      dropdown on a typical day). Filtering can be done client-side from `allHabits` — no endpoint
      change either way.

## Risk
- **Involvement:** Minimal — one read-only endpoint, one form addition, one CSS block, one test file.
  No schema change, no carry-forward logic touched.
- **Review attention:** Low — additive and read-only; the only real judgment call is the duplicate
  filtering question above. Confirm the endpoint is `user_id`-scoped like every other habit query.

## Implementation notes
- **Backend.** Copy the shape of `get_previous_stopwatch_titles` (`backend/src/routes/stopwatch.py:73`):
  query `Habit.query.filter_by(user_id=user_id).order_by(Habit.date.desc(), Habit.id.desc()).all()`,
  walk the rows keeping the first occurrence of each `description` in a `seen` set, and return
  `success_response({"titles": [{"description", "repeat_days", "difficulty"}, ...]})`. Habits have no
  `isTotal` analogue, so there is nothing to exclude. Register nothing new — `habit_routes` is already
  mounted under `/api` in `app.py`. Note the route must not collide with
  `@habit_routes.route("/habits/<string:date_string>/")`; Flask's static-vs-converter ordering makes
  `/habits/titles/` win, but the same pattern already works for stopwatches — keep the trailing slash.
- **Frontend.** In `habitpage.jsx`, add `const [previousDescriptions, setPreviousDescriptions] =
  useState([])` and fetch `/habits/titles/` via `fetchWithAuth` in an effect. The stopwatch page
  re-fetches its titles whenever the add form opens (`stopwatchpage.jsx:816-822`) so a habit added this
  session shows up — do the same rather than fetching once on mount. `prefillFromPrevious(description)`
  sets `newDescription`, `newRepeatDays` (`?? ALL_DAYS`) and `newDifficulty` (`?? "medium"`), matching
  the existing `onEdit` prefill at `habitpage.jsx:362`. Render the `<select>` with `value=""` and a
  disabled placeholder option, guarded by `previousDescriptions.length > 0`, directly above the
  "Description" label — exactly as `stopwatchpage.jsx:966-981` does.
- **Scope.** Add form only, matching 0013. Do not touch the edit-habit form, the carry-forward logic in
  `get_habits`, or the stats `/stats/items/` endpoint (which returns a similar-looking list but is
  period-scoped and description-only, so it is not reusable here).
- **Tests.** Follow the `get_titles` helper style in `backend/tests/test_stopwatch_carryforward.py:49`.
  Cover: distinct descriptions most-recent first; `repeat_days` and `difficulty` come from the most
  recent row; the endpoint is user-scoped (another user's habits never appear).
