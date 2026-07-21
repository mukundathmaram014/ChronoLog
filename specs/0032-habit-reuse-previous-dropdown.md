---
title: Add a "reuse previous" dropdown to the add-habit form
status: decided
---

# Add a "reuse previous" dropdown to the add-habit form

## Summary
Spec 0013 shipped a "reuse previous" dropdown on the add-**stopwatch** form, backed by
`GET /api/stopwatches/titles/` (`backend/src/routes/stopwatch.py:73-92`), which returns the user's
distinct prior stopwatch titles (most-recent first) with each one's latest `goal_time` and
`repeat_days`; the frontend fetches it into `previousTitles` and `prefillFromPrevious` fills the add
form (`frontend/src/Pages/stopwatchpage.jsx:351-362`, `:966-981`). The add-**habit** form has no
equivalent — it is free-text description + weekday picker + difficulty picker, with nothing to pull
from history (`frontend/src/Pages/habitpage.jsx:301-327`).

This spec mirrors that onto habits, with one deliberate divergence. **The point of the habit dropdown
is bringing back habits you deleted** — ones that no longer appear anywhere on your list. Habits carry
forward day to day, so every habit you currently keep is already on the day; an unfiltered
most-recent-first list would be dominated by those, burying the deleted ones at the bottom and
offering mostly dead options (re-picking one just hits the per-day duplicate guard in
`create_habit_for_date` → 409, "A habit with this description already exists."). So the dropdown
**filters out descriptions already present on the selected day**, which leaves exactly the
re-addable set: habits deleted previously, habits whose `repeat_days` exclude today (addable as a
one-off), and habits that aged out of carry-forward.

Delivered as: a new `GET /api/habits/titles/` endpoint returning the user's distinct prior habit
descriptions, most-recent first, each with its most recent `repeat_days` and `difficulty`; and a
"Reuse previous" `<select>` at the top of the add-habit form that prefills description, repeat days,
and difficulty.

**Known limitation (accepted, not worked around):** `delete_habit` removes only that day's row
(`backend/src/routes/habits.py:219-246`), so prior days' rows survive and keep a deleted habit
visible in the dropdown. But a habit that existed on *only one day* and was deleted that same day
leaves no row anywhere and therefore cannot appear. Anything that survived to a second day is
recoverable.

## Affected files
- `backend/src/routes/habits.py` — new `GET /habits/titles/` endpoint: distinct prior descriptions for
  the user, most-recent first, each with latest `repeat_days` + `difficulty`. Scope by `user_id`.
- `frontend/src/Pages/habitpage.jsx` — `previousDescriptions` state, a fetch of `/habits/titles/`, a
  `useMemo` filtering it against `allHabits`, a `prefillFromPrevious` handler, and the `<select>`
  rendered inside the `addHabit` block.
- `frontend/src/Pages/habitpage.css` — styling for the select (mirror `.reuse-previous-select` in
  `frontend/src/Pages/stopwatchpage.css:411-424` and its mobile rule at `:502-506`).
- `backend/tests/test_habits_carryforward.py` — tests for the new endpoint (distinct, most-recent
  first, user-scoped, returns repeat_days + difficulty), mirroring
  `backend/tests/test_stopwatch_carryforward.py:126-144` and `:418-424`.

## Decisions needed
- [x] Should the dropdown hide descriptions already present on the selected day? **Yes — filter.**
      The feature exists to resurrect deleted habits; carry-forward means unfiltered the list is
      mostly habits you already have. Filtering is client-side against `allHabits`, so no endpoint
      change. On days where nothing is re-addable the `<select>` simply does not render (the existing
      `length > 0` guard), which reads as "nothing to reuse" rather than a list of dead options.

## Risk
- **Involvement:** Minimal — one read-only endpoint, one form addition, one CSS block, one test file.
  No schema change, no carry-forward logic touched.
- **Review attention:** Low — additive and read-only. Confirm the endpoint is `user_id`-scoped like
  every other habit query, and that the client-side filter is derived from `allHabits` (so it stays
  correct as habits are added or deleted during the session) rather than computed once.

## Implementation notes
- **Backend.** Copy the shape of `get_previous_stopwatch_titles` (`backend/src/routes/stopwatch.py:73`):
  query `Habit.query.filter_by(user_id=user_id).order_by(Habit.date.desc(), Habit.id.desc()).all()`,
  walk the rows keeping the first occurrence of each `description` in a `seen` set, and return
  `success_response({"titles": [{"description", "repeat_days", "difficulty"}, ...]})`. Habits have no
  `isTotal` analogue, so there is nothing to exclude. Register nothing new — `habit_routes` is already
  mounted under `/api` in `app.py`. Note the route must not collide with
  `@habit_routes.route("/habits/<string:date_string>/")`; Flask's static-vs-converter ordering makes
  `/habits/titles/` win, but the same pattern already works for stopwatches — keep the trailing slash.
  Deliberately unfiltered server-side: the endpoint returns *all* prior descriptions and the client
  decides what to hide, keeping the endpoint independent of which day is selected.
- **Frontend.** In `habitpage.jsx`, add `const [previousDescriptions, setPreviousDescriptions] =
  useState([])` and fetch `/habits/titles/` via `fetchWithAuth` in an effect. The stopwatch page
  re-fetches its titles whenever the add form opens (`stopwatchpage.jsx:816-822`) so an item added
  this session shows up — do the same rather than fetching once on mount.
- **The filter.** Derive the rendered options with a `useMemo` over `previousDescriptions` and
  `allHabits` (`habitpage.jsx:45`), dropping any entry whose `description` matches one already in
  `allHabits`. Because it is a memo over live state, deleting a habit from the day makes it reappear
  in the dropdown immediately, and adding one makes it vanish — no refetch needed. Match on exact
  description string, the same equality the backend duplicate guard uses.
- **Prefill.** `prefillFromPrevious(description)` sets `newDescription`, `newRepeatDays`
  (`?? ALL_DAYS`) and `newDifficulty` (`?? "medium"`), matching the existing `onEdit` prefill at
  `habitpage.jsx:362`. Render the `<select>` with `value=""` and a disabled placeholder option,
  guarded by the *filtered* list being non-empty, directly above the "Description" label — exactly as
  `stopwatchpage.jsx:966-981` does.
- **Scope.** Add form only, matching 0013. Do not touch the edit-habit form, the carry-forward logic in
  `get_habits`, or the stats `/stats/items/` endpoint (which returns a similar-looking list but is
  period-scoped and description-only, so it is not reusable here).
- **Tests.** Follow the `get_titles` helper style in `backend/tests/test_stopwatch_carryforward.py:49`.
  Cover: distinct descriptions most-recent first; `repeat_days` and `difficulty` come from the most
  recent row; the endpoint is user-scoped (another user's habits never appear); and a habit deleted
  from the current day still appears (its prior-day row survives) — the core use case. The filtering
  itself is client-side and needs no backend test.
