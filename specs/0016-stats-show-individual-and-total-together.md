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

## ⚠️ Decision needed
1. **Per-item fan-out: backend or frontend?**
   - **(Recommended) Backend "all" mode:** add an option to the stats endpoints that returns a list of
     per-item results plus the total in one response. Fewer round-trips, cleaner.
   - Alternative: frontend loops and calls the existing single-item endpoint once per item. No backend
     change but N requests.
2. **Layout.** Recommended: the Total/aggregate at top (existing ring), then a list/grid of per-item
   cards below. Confirm.
3. **Which items are listed.** The selected day's items, or all items in the selected period? This is
   the overlap with **0017** — recommended to decide 0016 and 0017 together so "individual + total" and
   "period-driven data" are consistent.

## Affected files
- `backend/src/routes/statistics.py` — (if Decision 1 = backend) an "all items" mode returning
  per-item stats + the total, scoped by `user_id`, reusing the existing period loops.
- `frontend/src/Pages/statisticspage.jsx` — render the total plus a per-item list; a dropdown/toggle to
  switch into this combined view.
- `frontend/src/Pages/statisticspage.css` — layout for the per-item list.

## Approach
1. Decide fan-out location (Decision 1).
2. Backend (if chosen): return `{ total: {...}, items: [{name, ...stats}, ...] }` for the period,
   reusing existing per-period aggregation.
3. Frontend: a combined view showing the Total readout (ring) and each item's stats together; keep the
   existing single-select view available or fold it in.

## Acceptance criteria
- One page shows the aggregate plus every individual habit/stopwatch's stats for the chosen window.
- Switching statistic type (habits/stopwatches) and period still works.
- Performance is acceptable (prefer one request over N).

## Testing / verification
- With several habits and stopwatches, confirm each appears with correct numbers alongside a correct
  total, for day/week/month.
- Confirm consistency with the existing single-select stats.

## Risks & notes
- Strongly coupled with **0017** (period-driven data) and related to **0015** (the pie is a natural
  visualization of the per-stopwatch breakdown). Sequence/group these in build planning.
- Watch the "which items exist in the period vs just today" question — it determines what the list
  iterates over.
