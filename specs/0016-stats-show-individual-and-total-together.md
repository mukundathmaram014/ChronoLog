# 0016 — Show individual + total statistics together

## Problem / Goal
The statistics page currently shows **one** thing at a time: the dropdown picks either "All / Total" or a
single habit/stopwatch, and stats render for just that selection
(`frontend/src/Pages/statisticspage.jsx:54-73, 284-301`). The author wants a view that lists **each
individual habit/stopwatch alongside the total, all on one page**.

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

## Affected files
- `backend/src/routes/statistics.py` — an "all items" mode returning `{ total, items: [...] }` for the
  selected date + period, scoped by `user_id`, reusing the existing period loops. **Build this as the
  one shared period-aware source** that also feeds 0017 (the period item set) and 0015 (the
  per-stopwatch duration breakdown) — don't add three separate queries.
- `frontend/src/Pages/statisticspage.jsx` — render the total plus a per-item list; a dropdown/toggle to
  switch into this combined view.
- `frontend/src/Pages/statisticspage.css` — layout for the per-item list.

## Approach
1. Backend: add the "all items" mode returning `{ total: {...}, items: [{name, ...stats}, ...] }` for the
   selected date + period, reusing the existing per-period aggregation — the shared source for 0015/0017.
2. Frontend: a combined view showing the Total readout (ring) at top and each item's stats below; keep
   the existing single-select view available or fold it in.
3. Drive the item list from the period item set (0017) so period ≠ day shows every item in the period.

## Acceptance criteria
- One page shows the aggregate plus every individual habit/stopwatch's stats for the chosen window.
- Switching statistic type (habits/stopwatches) and period still works.
- Performance is acceptable (prefer one request over N).

## Testing / verification
- With several habits and stopwatches, confirm each appears with correct numbers alongside a correct
  total, for day/week/month.
- Confirm consistency with the existing single-select stats.

## Risk
- **Involvement:** Moderate — a backend "all items" mode (new response shape) plus per-item frontend rendering + CSS.
- **Review attention:** Medium — no schema, but part of the 0015/0016/0017 cluster (share one period-aware source); watch performance (one request, not N).

## Risks & notes
- Part of the **0015/0016/0017 cluster** — build them together with **one** period-aware `statistics.py`
  source (total + per-item stats + per-stopwatch breakdown + distinct period items) rather than three
  separate queries.
- The item list iterates over the period's items (from 0017), not just today's — that's the resolved
  behavior.
