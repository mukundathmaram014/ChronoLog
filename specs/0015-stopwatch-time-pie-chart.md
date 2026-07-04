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

## ⚠️ Decision needed
1. **Where it lives.** Recommended: the statistics page (alongside the existing Total ring). Alternative:
   the stopwatch page under the Total. Pick one.
2. **Charting approach.** Recommended: hand-rolled SVG pie (consistent with the existing SVG rings, no
   new dependency). Alternative: add a lib (e.g. `recharts`) — faster to build legends/tooltips but adds
   a dependency. Pick one.
3. **Data window.** Just the selected day, or the selected period (ties into 0016/0017)? Recommended:
   start with the selected day's stopwatches; generalize to period if 0016/0017 land.

## Affected files
- `frontend/src/Pages/statisticspage.jsx` (or `stopwatchpage.jsx` per Decision 1) — a pie chart
  component + legend, fed by per-stopwatch durations.
- (Maybe) `backend/src/routes/statistics.py` — if a per-stopwatch breakdown over a period is needed, add
  it (return a list of `{title, duration}`); for the single-day case the frontend can use the already-
  fetched stopwatches.
- (If Decision 2 = lib) `frontend/package.json`.

## Approach
1. Gather per-stopwatch durations for the chosen window (reuse the day's fetched stopwatches, excluding
   the Total; or a new endpoint for a period).
2. Render slices proportional to each stopwatch's share of the total; show a legend with title + time +
   percentage; reuse the existing color treatment where sensible.
3. Handle the empty/zero-total case (no time logged) gracefully.

## Acceptance criteria
- The selected window's time is shown as a pie split per stopwatch, slices summing to the total.
- A legend maps slices to stopwatch titles with their time/percentage.
- Zero-time and single-stopwatch cases render without error.

## Testing / verification
- A day with several stopwatches shows proportional slices that sum to the Total.
- A day with no logged time shows an empty/placeholder state.

## Risk
- **Involvement:** Moderate — mainly a new frontend pie/legend component; optionally a period-breakdown endpoint or a charting lib.
- **Review attention:** Medium — additive and visual (no schema), but confirm the SVG-vs-library and placement/data-window decisions.

## Risks & notes
- Exclude the Total stopwatch from the slices (it's the sum, not a slice).
- Keep it consistent with the existing SVG style if hand-rolling; if adding a lib, justify it in the PR
  per the working agreement.
