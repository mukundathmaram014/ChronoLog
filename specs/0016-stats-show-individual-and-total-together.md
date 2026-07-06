# 0016 — Show individual + total statistics together

## Problem / Goal
The statistics page currently shows **one** thing at a time: the dropdown picks either "All / Total" or a
single habit/stopwatch, and stats render for just that selection
(`frontend/src/Pages/statisticspage.jsx:54-73, 284-301`). The author wants a view that lists **each
individual habit/stopwatch alongside the total, all on one page**.

Additionally, the author wants a **calendar / heatmap view for a single habit**: for the currently
selected date period (month or year — whatever window is chosen), render a calendar grid where each day
is visually marked to show **whether that habit was done on that day**. This turns the aggregate
percentage into a glanceable day-by-day picture of consistency (which stretches were completed, which
were missed). Habit completion history is already stored day-by-day — each `Habit` row is one
`(description, date, user_id)` with a `done` boolean (`backend/src/db.py:27-63`) — so the per-day
status a calendar needs is a direct query over the same date window the existing stats loops already
walk (`backend/src/routes/statistics.py:39-81`). The `repeat_days` weekday bitmask (`db.py:38`) also
lets the view distinguish a **scheduled-but-missed** day from a day the habit wasn't scheduled at all.

## Context
- `get_habits_stats` / `get_stopwatchs_stats` (`backend/src/routes/statistics.py`) compute for a single
  description/title (via query param) or the aggregate — one result per call.
- The dropdown currently lists only the **selected day's** items (this is also what 0017 wants to
  broaden to the period).

## Decisions (made)
1. **Backend "all" mode.** A single `@jwt_required()` response returns the **total plus a list of
   per-item stats** for the selected date + period — one round-trip, no N-calls fan-out from the
   frontend.
2. **Layout:** the Total/aggregate at top (existing ring), then a list/grid of per-item cards below.
3. **Items = all items in the selected period** (not just the selected day), matching **0017**. This
   combined view is built together with 0017 (period item set) and shares the same period-aware source
   as **0015** (the pie) — see the shared-source note in Affected files / Risks.

### Calendar / heatmap view (per-habit)
4. **Scope: habits only, one habit at a time.** The calendar shows a single selected habit's per-day
   done/missed history. Stopwatches are out of scope for this view (a time-intensity heatmap could be a
   later spec). Reuse the existing habit-selection dropdown to pick which habit the calendar renders.
5. **Backend returns per-day status, not a rollup.** A period-scoped endpoint returns, for the selected
   habit + window, a list of `{ date, status }` — one entry per day in the window — so the frontend can
   paint the grid directly without N calls.
6. **Grid shape follows the period.** `month` → a standard month calendar grid (weeks × 7, aligned to
   weekday). `year` → a compact GitHub-contributions-style heatmap (columns = weeks, rows = weekdays).
   `week`/`day` still work but are trivially small (a single row / single cell).

## Decisions needed
- [ ] **Day status vocabulary.** Minimum is `done` vs `not-done`. Recommended richer set using
  `repeat_days`: `done` (row exists, `done=True`), `missed` (scheduled that weekday but `done=False`),
  `not-scheduled` (weekday bit is 0), `no-data` (no `Habit` row for that date — e.g. before the habit
  existed, or a deleted day). Confirm which distinctions to render and their colors.
- [ ] **What counts as "the selected habit".** Habits are keyed by `description` (there's no stable
  per-habit id across days). Confirm the calendar keys on `description` for the chosen `user_id`
  (consistent with how `get_habits_stats` filters today).

## Affected files
- `backend/src/routes/statistics.py` — an "all items" mode returning `{ total, items: [...] }` for the
  selected date + period, scoped by `user_id`, reusing the existing period loops. **Build this as the
  one shared period-aware source** that also feeds 0017 (the period item set) and 0015 (the
  per-stopwatch duration breakdown) — don't add three separate queries. **Also add a per-habit calendar
  endpoint** (e.g. `GET /stats/habits/calendar/<date_string>/<time_period>/?description=...`) returning
  `{ days: [{ date, status }, ...] }` for the selected habit over the window — reuse the same
  start-of-period / day-count logic (`get_stopwatches_breakdown` at `statistics.py:189-202` is the
  cleanest existing template for that window computation), scoped by `user_id`.
- `frontend/src/Pages/statisticspage.jsx` — render the total plus a per-item list; a dropdown/toggle to
  switch into this combined view; and a calendar/heatmap block for the selected single habit.
- `frontend/src/Components/HabitCalendar.jsx` — new: a presentational grid that takes the
  `{ date, status }[]` and renders the month grid or year heatmap with a per-status color + legend.
- `frontend/src/Pages/statisticspage.css` — layout for the per-item list **and** the calendar grid /
  heatmap cells (or a co-located `HabitCalendar.css` if kept with the component).

## Approach
1. Backend: add the "all items" mode returning `{ total: {...}, items: [{name, ...stats}, ...] }` for the
   selected date + period, reusing the existing per-period aggregation — the shared source for 0015/0017.
2. Frontend: a combined view showing the Total readout (ring) at top and each item's stats below; keep
   the existing single-select view available or fold it in.
3. Drive the item list from the period item set (0017) so period ≠ day shows every item in the period.
4. Calendar: backend walks the selected window day-by-day (same start/count logic as the other period
   endpoints), classifies each date for the chosen habit into a status (see the status-vocabulary
   decision), and returns the `{ date, status }[]`. Frontend `HabitCalendar` lays the days out as a
   month grid or year heatmap and colors each cell by status, with a small legend.

## Acceptance criteria
- One page shows the aggregate plus every individual habit/stopwatch's stats for the chosen window.
- Switching statistic type (habits/stopwatches) and period still works.
- Performance is acceptable (prefer one request over N).
- Selecting a single habit shows a calendar/heatmap for the current period where each day is visibly
  marked done vs not-done (and, if the richer vocabulary is chosen, missed vs not-scheduled vs no-data).
- Changing the period (month ↔ year) re-shapes the calendar to match the window; changing the selected
  habit re-renders it for that habit.

## Testing / verification
- With several habits and stopwatches, confirm each appears with correct numbers alongside a correct
  total, for day/week/month.
- Confirm consistency with the existing single-select stats.
- Pick a habit with a known mix of done/missed days across a month; confirm each day's cell matches the
  underlying `Habit.done` rows, and that a month with a partial habit history renders the missing days
  as `no-data` (not as `missed`).
- For a habit with a restricted `repeat_days` mask, confirm non-scheduled weekdays render as
  `not-scheduled` rather than `missed`.

## Risk
- **Involvement:** Involved — a backend "all items" mode (new response shape) plus a new per-habit
  calendar endpoint, per-item frontend rendering + CSS, and a new `HabitCalendar` grid/heatmap component.
- **Review attention:** Medium — no schema changes (both endpoints are read-only over existing `Habit`
  rows), but part of the 0015/0016/0017 cluster (share one period-aware source); watch performance (one
  request per view, not N) and the day-status classification edge cases (`no-data` vs `missed` vs
  `not-scheduled`).

## Risks & notes
- Part of the **0015/0016/0017 cluster** — build them together with **one** period-aware `statistics.py`
  source (total + per-item stats + per-stopwatch breakdown + distinct period items) rather than three
  separate queries. The calendar endpoint reuses the same window (start-of-period + day-count) logic but
  returns per-day rows instead of a rollup.
- The item list iterates over the period's items (from 0017), not just today's — that's the resolved
  behavior.
- Calendar status classification is the subtle part: a day with **no `Habit` row** (before the habit
  existed, or a deleted day) must not be shown as `missed`. Distinguish "no row" from
  "row with `done=False`", and fold `repeat_days` in for `not-scheduled`. A `year` window is 365+ cells;
  keep the endpoint a single pass over the window and the frontend render lightweight (plain divs, no
  per-cell requests).
