---
status: built
---

# 0015 — Pie chart of total time split by stopwatch

## Problem / Goal
The total-time readout is a single aggregate. The author wants to see that total **broken into a pie
chart** split across the individual stopwatches, so the share of time per activity is visible at a
glance.

## Context
- Per-stopwatch durations already exist: each non-Total `Stopwatch` has `curr_duration`; the Total is a
  separate `isTotal` stopwatch summing them.
- The app hand-rolls its visualizations in SVG today — `CircularProgress` / `CircularProgressTotal` in
  `frontend/src/Pages/statisticspage.jsx:98-200` (and the stopwatch page) — there is no charting
  library in use.
- The stats endpoints return only aggregates (total/average/goal), not a per-stopwatch breakdown
  (`backend/src/routes/statistics.py`).

## Decisions (made)
1. **Lives on the statistics page**, alongside the existing Total ring.
2. **Hand-rolled SVG pie** (consistent with the existing SVG rings) — no charting library / new
   dependency.
3. **Data window follows the selected statistics period.** The pie reflects whatever period is selected:
   a day → the day's split, a week → the week's split, likewise month/year. So it needs per-stopwatch
   **durations aggregated over the selected period**, not just the selected day — which couples this with
   0017 (period item set) and 0016 (per-item stats). See Affected files / Risks.

## Affected files
- `backend/src/routes/statistics.py` — a per-stopwatch breakdown **over the selected period**
  (day/week/month/year): return a list of `{title, duration}` for the period, scoped by `user_id`,
  reusing the existing period loops. (Required now that the window follows the period — the single-day
  case could reuse the already-fetched stopwatches, but week/month/year needs this aggregate. Share it
  with 0016/0017 rather than duplicating it.)
- `frontend/src/Pages/statisticspage.jsx` — a hand-rolled SVG pie component + legend, fed by that
  per-stopwatch period breakdown; keyed on the selected date + period.
- `frontend/src/Pages/statisticspage.css` — styles for the pie section, legend, and empty state.
- `backend/tests/test_statistics_breakdown.py` — tests for the breakdown endpoint (day/week
  aggregation, Total exclusion, empty period, invalid period, user scoping).

## Approach
1. Add the per-stopwatch period breakdown to `statistics.py` (list of `{title, duration}` over the
   selected period, excluding the Total), scoped by `user_id`, reusing the existing period aggregation.
2. On the statistics page, fetch that breakdown for the current date + period and render a hand-rolled
   SVG pie: slices proportional to each stopwatch's share of the total, plus a legend with title + time
   + percentage; reuse the existing SVG color treatment.
3. Handle the empty/zero-total case (no time logged) gracefully; the pie updates when the period changes.

## Acceptance criteria
- The selected period's time (day/week/month/year) is shown as a pie split per stopwatch, slices
  summing to the period total; changing the period updates the pie accordingly.
- A legend maps slices to stopwatch titles with their time/percentage.
- Zero-time and single-stopwatch cases render without error.

## Testing / verification
- A day with several stopwatches shows proportional slices that sum to the day's Total; switch to
  week/month and confirm the slices re-aggregate over that period.
- A period with no logged time shows an empty/placeholder state.

## Risk
- **Involvement:** Moderate — a new frontend SVG pie/legend component **plus** a per-stopwatch
  period-breakdown endpoint in `statistics.py` (the period window makes the backend part required).
- **Review attention:** Medium — additive and visual (no schema, no new dependency), but it's now coupled
  with 0016/0017; ideally share one period-breakdown source across the three rather than duplicating it.

## Risks & notes
- Exclude the Total stopwatch from the slices (it's the sum, not a slice).
- Keep it consistent with the existing SVG style (hand-rolled, no charting dependency).
- Coupled with 0016/0017 via the period breakdown — build them as a cluster (one `statistics.py`
  period-breakdown source feeding the pie, the per-item stats, and the period item list) instead of
  three separate queries.
