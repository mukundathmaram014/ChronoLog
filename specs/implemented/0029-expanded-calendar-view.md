---
title: Add per-habit calendar view and a stopwatch time calendar to the statistics page
status: built
---

# Add per-habit calendar view and a stopwatch time calendar to the statistics page

## Summary
The statistics page shows exactly one calendar at a time: the `HabitCalendar`
component (`frontend/src/Components/HabitCalendar.jsx`) rendered from
`/api/stats/habits/calendar/<date>/<period>/`, which returns either a single
habit's per-day status (`done` / `missed` / `not-scheduled` / `no-data`) or an
all-habits intensity heatmap. To compare habits you have to flip the selector
one habit at a time, and there is no calendar view of stopwatch time at all.

This spec extends the statistics page in place (no new page or route):

1. **Per-habit calendar view.** When "All Habits" is selected in the habit
   selector, a new view dropdown appears next to it with two options:
   **Combined** (the existing intensity heatmap, unchanged, default) and
   **Per-habit** (a grid of small status calendars, one per habit in the
   window, side by side). The dropdown is hidden when a specific habit is
   selected — that case renders the single status calendar exactly as today.
2. **Stopwatch time calendar.** On the stopwatches side, when "Total Time" is
   selected, a new calendar section shades each day by total time worked —
   backed by a new per-day time endpoint in
   `backend/src/routes/statistics.py`, since the existing stopwatch stats
   endpoints only return period aggregates, never a per-day series.

## Affected files
- `backend/src/routes/statistics.py` — add
  `/stats/stopwatches/calendar/<date_string>/<time_period>/` (per-day Total
  time series); extend the habits calendar logic with a batch "all habits,
  per-habit status" response (see notes) so the per-habit view is one
  request, not N. *Built as the sibling route
  `/stats/habits/calendar/all/<date_string>/<time_period>/` (of the two
  options the notes allowed), leaving the existing route untouched.*
- `backend/tests/test_statistics_calendar.py` — **new**: tests for the new
  stopwatch calendar endpoint and the batch habits response (there are
  currently no dedicated tests for the existing calendar endpoint; cover its
  batch extension here).
- `frontend/src/Components/HabitCalendar.jsx` — add a `time` mode that shades
  cells by a duration ratio (the existing `intensity` mode is hardwired to
  `completed / scheduled`); tooltip formats hours/minutes; add a `compact`
  size variant for the per-habit grid.
- `frontend/src/Components/HabitCalendar.css` — compact size variant so many
  mini-calendars fit side by side.
- `frontend/src/Pages/statisticspage.jsx` — the view dropdown (visible only
  when stats = habits and All Habits selected), `calendarView` state, batch
  calendar fetch for the per-habit view, the per-habit grid rendering, and
  the stopwatch time calendar section + its fetch.
- `frontend/src/Pages/statisticspage.css` — grid layout for the side-by-side
  mini-calendars and the new stopwatch calendar section.

## Decisions needed
_None — all resolved (2026-07-19):_
- **Where it lives:** on the statistics page itself — no new page, route, or
  nav item. The per-habit view is a dropdown toggle (Combined / Per-habit)
  that appears only when "All Habits" is selected; the stopwatch time
  calendar is a section shown when "Total Time" is selected. (Supersedes an
  earlier draft that proposed a separate `/calendarpage`.)
- **Stopwatch shading:** hybrid — when the day's Total row has a nonzero
  `goal_time`, alpha = `min(duration / goal, 1)`; otherwise alpha =
  `duration / max-duration-in-window`. All-zero window → every cell no-data.
- **Periods:** all four (day/week/month/year), inherited from the page's
  existing period selector — no new period control. Year heatmaps (~53
  columns) don't fit side by side, so in the year period the per-habit view
  stacks one full-width calendar per row instead of the compact grid.
- **Interactivity:** none in v1 — the mini-calendars are read-only. (A
  possible follow-up: clicking a mini-calendar selects that habit in the
  selector — cheap since it's the same page, but out of scope here.)

## Risk
- **Involvement:** Moderate — one new backend endpoint plus a batch
  extension, a component-mode addition, and statistics-page state/render
  changes; ~6 files, all additive, no routing or nav changes.
- **Review attention:** Low — read-only analytics over existing rows: no
  migration, no writes, no auth changes, no carry-forward interaction. The
  only sharp edges are the standard ones (scope every query by `user_id`,
  follow the existing period-walk pattern). One coordination point: spec 0028
  (year heatmap month labels) also modifies `HabitCalendar.jsx`/`.css` — if
  both build in the same batch, expect a small merge in that component (and
  the year per-habit calendars here inherit its month labels for free).

## Implementation notes

### Backend
- **New stopwatch calendar endpoint.** Follow `get_habits_calendar`
  (`statistics.py:370`) exactly: `@jwt_required()`, `int(get_jwt_identity())`,
  `get_period_range(...)` for the window, walk day by day, and return via
  `success_response`. For each day read the `isTotal=True` row's
  `curr_duration` (and `goal_time`, for goal-relative shading):

  ```
  GET /api/stats/stopwatches/calendar/<date_string>/<time_period>/
  -> {"mode": "time", "start": "...", "days": [{"date": ..., "duration": ms, "goal": ms}]}
  ```

  Days with no Total row return `duration: 0, goal: 0` (renders as the
  no-data cell). `curr_duration` is safe to read directly — it's only
  nonzero-stale while running, and per CLAUDE.md live elapsed time stays a
  frontend concern; this endpoint reports stored durations like every other
  stats endpoint. Milliseconds, like the rest of the stats API.
- **Batch per-habit calendars.** Don't have the frontend fire one
  `?description=` request per habit — a year window × N habits is N × 365-row
  scans and N round trips. Instead add a batch response (either
  `?all=true` on the existing route or a sibling
  `/stats/habits/calendar/all/...`) returning
  `{"start": ..., "habits": [{"description": ..., "days": [{date, status}]}]}`.
  One pass per day over `Habit.query.filter_by(date=..., user_id=...)`
  bucketing by description (the same single-pass shape as `get_habits_all`,
  `statistics.py:273`), classifying each row with the same
  `repeat_days & weekday_bit` logic already in `get_habits_calendar`. Habits
  with no row on a day get `no-data`. Keep the existing single-habit and
  intensity behaviors byte-identical — the combined view still uses them.
- **Tests** (`backend/tests/`, pattern per `test_statistics_breakdown.py`):
  stopwatch calendar — day/week/month windows, missing Total rows → 0,
  another user's rows excluded, invalid period → failure; batch habits —
  statuses match the single-habit endpoint for the same data, habit absent on
  some days → `no-data`, user scoping.

### Frontend
- `HabitCalendar` already takes `{mode, days, period}` and renders plain divs;
  add `mode === "time"`: color = the "done" green with alpha scaled by the
  hybrid ratio (goal-relative when `goal > 0`, else max-in-window-relative;
  see Decisions), `duration === 0` → `NO_DATA`. Reuse `intensityColor`'s
  alpha ramp (0.18–1.0). Tooltip: `"<date> — 3h 24m"`, appending
  `" / 5h goal"` when a goal exists. Add a `compact` prop (or size variant
  class) shrinking cells for the side-by-side grid.
- **View dropdown.** New `calendarView` state (`"combined" | "per-habit"`,
  default `"combined"`) in `statisticspage.jsx`. Render the dropdown in the
  existing `.selection-bar` (matching the other three selects) only when
  `selectedStatistics === "habits" && !selectedHabit`. Selecting a specific
  habit hides the dropdown and renders the single status calendar as today —
  no need to reset `calendarView`; it simply doesn't apply.
- **Per-habit grid.** When the per-habit view is active, the calendar effect
  (`statisticspage.jsx:121`) fetches the batch endpoint instead of the
  existing route, and the calendar section renders a CSS-grid of cards — one
  compact `HabitCalendar` (status mode) per habit, its description as the
  card title. Year period: one full-width calendar per row (conditional
  class), standard cell size. All calls via `useFetch` — never raw `fetch`.
- **Stopwatch time calendar.** Mirror the habit calendar section on the
  stopwatches side: when `selectedStatistics === "stopwatches"` and no
  specific stopwatch is selected ("Total Time"), fetch the new endpoint and
  render one `HabitCalendar` in `time` mode under a "Time worked" heading.
  Same effect-per-fetch structure as the existing calendar effect (there is
  deliberately no shared abstraction — don't invent one).
