---
title: Show individual + total statistics together
status: built
---

# 0016 — Show individual + total statistics together

## Problem / Goal
The statistics page currently shows **one** thing at a time: the dropdown picks either "All / Total" or a
single habit/stopwatch, and stats render for just that selection
(`frontend/src/Pages/statisticspage.jsx:54-73, 284-301`). The author wants a view that lists **each
individual habit/stopwatch alongside the total, all on one page**.

Additionally, the author wants a **calendar / heatmap view driven by the statistics page's current
selection**. This is a modification to the existing statistics page: when the user has a **single habit**
selected for a period (e.g. a month), the calendar shows a grid for that window where each day is
visually marked to show **whether that habit was done on that day** — turning the aggregate percentage
into a glanceable day-by-day picture of consistency (which stretches were completed, which were missed).
The grid follows whatever period is selected (a month grid for `month`, a single week row for `week`, a
year heatmap for `year`). When the selection is **Total / All habits** instead of one habit, the same
area shows an **intensity heatmap**: each day shaded by the fraction of that day's scheduled habits the
user completed (empty → none done, full → all done), so the overall consistency picture reads at a
glance without stacking one calendar per habit.

Habit completion history is already stored day-by-day — each `Habit` row is one
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

### Calendar / heatmap view (driven by the stats-page selection)
4. **Habits only; the calendar tracks the statistics page's current selection.** The view keys off
   whatever is chosen in the existing statistics habit dropdown — no separate picker. Stopwatches are out
   of scope for this view (a time-intensity heatmap could be a later spec).
   - **Single habit selected** → a per-day **status** calendar for that habit's `description`.
   - **Total / All habits selected** → a per-day **intensity** heatmap (fraction of that day's scheduled
     habits completed). This is the resolved answer to "a calendar for each habit?" — a single intensity
     heatmap is more intuitive and far more compact than N small-multiple calendars, and it mirrors the
     existing Total percentage.
5. **Day status vocabulary (single habit) — the richer 4-state set, each a distinct color:**
   - `done` — a `Habit` row exists for that date with `done=True`.
   - `missed` — scheduled that weekday (its `repeat_days` bit is set) but the row is `done=False`.
   - `not-scheduled` — the habit's `repeat_days` weekday bit is 0 for that date.
   - `no-data` — no `Habit` row for that date (before the habit existed, or a deleted day).
   Render all four with visually distinct treatments — suggested: `done` green, `missed` red,
   `not-scheduled` muted/neutral gray, `no-data` empty/very faint outline — plus a legend. (Exact hex is
   an implementation detail; the requirement is four clearly distinguishable states.)
6. **Intensity vocabulary (Total).** Per day, `intensity = completed_scheduled / total_scheduled` over
   all the user's habits scheduled that date (days with nothing scheduled render like `not-scheduled`;
   days before any habit existed render like `no-data`). Frontend maps the ratio to a shade ramp of the
   `done` color, GitHub-contributions style.
7. **"Selected habit" = the habit's `description` for the current `user_id`.** Habits are keyed by
   `description` (there's no stable per-habit id across days), consistent with how `get_habits_stats`
   filters today — the calendar reuses that same key.
8. **Grid shape follows the period.** `month` → a standard month calendar grid (weeks × 7, aligned to
   weekday). `week` → a single 7-day row. `year` → a compact GitHub-contributions-style heatmap
   (columns = weeks, rows = weekdays). `day` → a single cell.

## Decisions needed
_None — the day-status vocabulary (richer 4-state, distinct colors), the Total-selection UX (single
intensity heatmap), and the selected-habit key (`description`) are all resolved above._

## Affected files
- `backend/src/routes/statistics.py` — an "all items" mode returning `{ total, items: [...] }` for the
  selected date + period, scoped by `user_id`, reusing the existing period loops. **Build this as the
  one shared period-aware source** that also feeds 0017 (the period item set) and 0015 (the
  per-stopwatch duration breakdown) — don't add three separate queries. **Also add a habit calendar
  endpoint** (e.g. `GET /stats/habits/calendar/<date_string>/<time_period>/`) that reuses the same
  start-of-period / day-count logic (`get_stopwatches_breakdown` at `statistics.py:189-202` is the
  cleanest existing template), scoped by `user_id`, with two modes:
  - **`?description=<habit>`** → single habit: `{ days: [{ date, status }, ...] }` where `status` is one
    of `done | missed | not-scheduled | no-data` (classified via the `Habit` row's `done` and the
    `repeat_days` bit for that weekday).
  - **no `description`** → Total: `{ days: [{ date, completed, scheduled }, ...] }` (counts over all the
    user's habits scheduled that date); the frontend derives `intensity = completed / scheduled`.
- `frontend/src/Pages/statisticspage.jsx` — render the total plus a per-item list; a dropdown/toggle to
  switch into this combined view; and the calendar block, which reads the page's current habit selection
  and renders either the single-habit status calendar or the Total intensity heatmap.
- `frontend/src/Components/HabitCalendar.jsx` — new: a presentational grid that takes the per-day array
  and a mode (`status` vs `intensity`), and renders the month grid / week row / year heatmap with the
  appropriate per-day color + legend.
- `frontend/src/Pages/statisticspage.css` — layout for the per-item list **and** the calendar grid /
  heatmap cells (or a co-located `HabitCalendar.css` if kept with the component).

## Approach
1. Backend: add the "all items" mode returning `{ total: {...}, items: [{name, ...stats}, ...] }` for the
   selected date + period, reusing the existing per-period aggregation — the shared source for 0015/0017.
2. Frontend: a combined view showing the Total readout (ring) at top and each item's stats below; keep
   the existing single-select view available or fold it in.
3. Drive the item list from the period item set (0017) so period ≠ day shows every item in the period.
4. Calendar: backend walks the selected window day-by-day (same start/count logic as the other period
   endpoints). For a single habit it classifies each date into a status; for Total it counts
   scheduled/completed habits per date. Frontend `HabitCalendar` lays the days out as a month grid, week
   row, or year heatmap and colors each cell — by status (single habit) or by intensity ramp (Total) —
   with a small legend. The block reads the statistics page's existing habit selection to decide which
   mode to request/render.

## Acceptance criteria
- One page shows the aggregate plus every individual habit/stopwatch's stats for the chosen window.
- Switching statistic type (habits/stopwatches) and period still works.
- Performance is acceptable (prefer one request over N).
- Selecting a single habit shows a calendar for the current period where each day is visibly marked with
  one of the four states (`done` / `missed` / `not-scheduled` / `no-data`), each a distinct color, with a
  legend.
- Selecting Total / All habits shows an intensity heatmap for the same window, each day shaded by the
  fraction of that day's scheduled habits completed.
- Changing the period (day ↔ week ↔ month ↔ year) re-shapes the calendar to match the window; changing
  the selected habit (or switching to Total) re-renders it in the right mode.

## Testing / verification
- With several habits and stopwatches, confirm each appears with correct numbers alongside a correct
  total, for day/week/month.
- Confirm consistency with the existing single-select stats.
- Pick a habit with a known mix of done/missed days across a month; confirm each day's cell matches the
  underlying `Habit.done` rows, and that a month with a partial habit history renders the missing days
  as `no-data` (not as `missed`).
- For a habit with a restricted `repeat_days` mask, confirm non-scheduled weekdays render as
  `not-scheduled` rather than `missed`.
- With Total selected, confirm a day where all scheduled habits were done renders at full intensity, a
  half-done day at a mid shade, and a day with nothing done (but something scheduled) at empty; a day
  with no habits scheduled reads as neutral, not as 0%.

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
  "row with `done=False`", and fold `repeat_days` in for `not-scheduled`. The Total intensity mode has
  the analogous edge: a day with **no scheduled habits** is neutral, not 0% (which would misleadingly
  read as "missed everything"). A `year` window is 365+ cells; keep the endpoint a single pass over the
  window and the frontend render lightweight (plain divs, no per-cell requests).
- The single-habit (`?description=`) and Total (no `description`) branches of the calendar endpoint
  should share the same window walk and, where possible, the same per-day habit fetch — classify for one
  habit vs. count across all in the same loop rather than two separate passes.
