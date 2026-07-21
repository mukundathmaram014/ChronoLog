---
title: Add a "reuse previous" dropdown to the add-habit form
status: decided
---

# Add a "reuse previous" dropdown to the add-habit form

## Summary
**Why this exists: statistics identify a habit purely by its exact `description` string.** There is no
ID lineage — `get_habits_*` filters with `filter_by(description = description)`
(`backend/src/routes/statistics.py:53-54`) and buckets with `per.setdefault(habit.description, ...)`
(`:298`, `:460`). So if you stop a habit and later restart it under a slightly different name —
"Read" vs "Reading" — the stats treat them as two unrelated habits and the earlier history is
stranded. Typing the name from memory is exactly where that goes wrong.

This adds a "Reuse previous" `<select>` to the add-habit form that inserts a prior description
**verbatim**, so a restarted habit rejoins its own history instead of forking. It mirrors the
add-stopwatch dropdown from spec 0013 (`backend/src/routes/stopwatch.py:73-92`,
`frontend/src/Pages/stopwatchpage.jsx:351-362`, `:966-981`), which the add-habit form currently has
no equivalent of (`frontend/src/Pages/habitpage.jsx:301-327`).

Two deliberate divergences from the stopwatch version, both driven by that goal:

- **The list is filtered to habits not already on the selected day.** Habits carry forward, so
  unfiltered, the currently-kept habits dominate a most-recent-first list and bury the dormant ones —
  and re-picking an active one just hits the per-day duplicate guard in `create_habit_for_date`
  (409, "A habit with this description already exists."). Filtering leaves exactly the re-addable
  set: habits deleted previously, habits whose `repeat_days` exclude today (addable as a one-off),
  and habits that aged out of carry-forward.
- **Each option shows when that habit was last active** — `Read — last: 2026-03-14`. The problem
  being solved is *not remembering the old name*; with `Read`, `Reading`, and `Read books` all in
  history, a bare list of strings means guessing, and a wrong guess re-splits the stats. The date
  disambiguates. It is nearly free: the backend query already orders by `Habit.date.desc()`, so the
  row kept per description is already the most recent one.

Delivered as: a new `GET /api/habits/titles/` endpoint returning the user's distinct prior habit
descriptions, most-recent first, each with its most recent `date`, `repeat_days` and `difficulty`;
and the `<select>` at the top of the add-habit form, which prefills description, repeat days, and
difficulty.

### Scope boundary: this prevents splits, it does not repair them
If a habit's history is *already* split across two spellings, this feature does not merge them.
`update_habit` renames only the single row it is given (`backend/src/routes/habits.py:186-190`), so
renaming one day's "Reading" to "Read" fixes that day and leaves every other stray row split.
Genuine retroactive merging would have to rewrite a whole run of rows and is a separate feature.

**Known data limitation (accepted):** `delete_habit` removes only that day's row
(`backend/src/routes/habits.py:219-246`), so prior days' rows survive and keep a deleted habit
visible in the dropdown. But a habit that existed on *only one day* and was deleted that same day
leaves no row anywhere and cannot appear. Anything that survived to a second day is recoverable.

## Affected files
- `backend/src/routes/habits.py` — new `GET /habits/titles/` endpoint: distinct prior descriptions for
  the user, most-recent first, each with latest `date`, `repeat_days` + `difficulty`. Scope by
  `user_id`.
- `frontend/src/Pages/habitpage.jsx` — `previousDescriptions` state, a fetch of `/habits/titles/`, a
  `useMemo` filtering it against `allHabits`, a `prefillFromPrevious` handler, and the `<select>`
  rendered inside the `addHabit` block.
- `frontend/src/Pages/habitpage.css` — styling for the select (mirror `.reuse-previous-select` in
  `frontend/src/Pages/stopwatchpage.css:411-424` and its mobile rule at `:502-506`).
- `backend/tests/test_habits_carryforward.py` — tests for the new endpoint (distinct, most-recent
  first, user-scoped, returns date + repeat_days + difficulty), mirroring
  `backend/tests/test_stopwatch_carryforward.py:126-144` and `:418-424`.

## Decisions needed
- [x] Hide descriptions already present on the selected day? **Yes — filter**, client-side against
      `allHabits`, so no endpoint change. On days where nothing is re-addable the `<select>` does not
      render, which reads as "nothing to reuse" rather than a list of dead options.
- [x] Show last-active date per option? **Yes**, as an option label suffix. The stored description
      remains the option `value`.

## Risk
- **Involvement:** Minimal — one read-only endpoint, one form addition, one CSS block, one test file.
  No schema change, no carry-forward logic touched.
- **Review attention:** Medium — additive and read-only, but the feature's whole value depends on one
  easily-broken invariant: the description must be inserted byte-identical. Review specifically that
  no trimming, case-folding, or whitespace tidying is applied anywhere on the path from the endpoint
  to `newDescription`. Also confirm the endpoint is `user_id`-scoped like every other habit query, and
  that the client-side filter derives from `allHabits` rather than being computed once.

## Implementation notes
- **Exact-string fidelity is the requirement, not a detail.** The description that reaches
  `newDescription` must equal the stored string byte for byte — the stats grouping is exact-match, so
  any normalization silently re-splits the history this feature exists to preserve. In particular the
  displayed last-active date is *label only*: the `<option>`'s `value` stays the raw description, and
  `prefillFromPrevious` receives that raw value (same split the stopwatch version already uses, where
  `value={previous.title}`). Never parse the description back out of the label.
- **Backend.** Copy the shape of `get_previous_stopwatch_titles` (`backend/src/routes/stopwatch.py:73`):
  query `Habit.query.filter_by(user_id=user_id).order_by(Habit.date.desc(), Habit.id.desc()).all()`,
  walk the rows keeping the first occurrence of each `description` in a `seen` set, and return
  `success_response({"titles": [{"description", "date", "repeat_days", "difficulty"}, ...]})` with
  `date` as an ISO `YYYY-MM-DD` string. Because the ordering is already most-recent-first, the kept
  row supplies all three trailing fields. Habits have no `isTotal` analogue, so nothing is excluded.
  Register nothing new — `habit_routes` is already mounted under `/api` in `app.py`. The route must
  not collide with `@habit_routes.route("/habits/<string:date_string>/")`; Flask's static-vs-converter
  ordering makes `/habits/titles/` win, but the same pattern already works for stopwatches — keep the
  trailing slash. Deliberately unfiltered server-side: the endpoint returns *all* prior descriptions
  and the client decides what to hide, keeping the endpoint independent of which day is selected.
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
  Cover: distinct descriptions most-recent first; `date`, `repeat_days` and `difficulty` all come from
  the most recent row; the endpoint is user-scoped (another user's habits never appear); and a habit
  deleted from the current day still appears via its prior-day row — the core use case. Include a
  description with leading/trailing whitespace or mixed case to pin the no-normalization contract.
  The filtering itself is client-side and needs no backend test.
