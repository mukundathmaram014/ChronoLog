---
title: Add an all-time Overview, an XP projection and goal details on the XP curve
status: built
---

# Add an all-time Overview, an XP projection and goal details on the XP curve

## Summary
Overview shows one year at a time, which hides the long-term trend, and the XP curve
stops at today and doesn't explain its jumps. This adds three things:

- **All time:** a year picker option that shows every week of the user's history in the
  same charts and table.
- **Projection:** a dashed continuation of the XP curve at the user's recent rate, plus a
  line saying when they'd reach the next level and what level they'd be in a year.
- **Goal details:** a marker on the curve for each day a goal was completed. Hovering or
  tapping it shows the goals and the XP they gave.

The notes import box also accepts M/D/YYYY dates, which is how a spreadsheet copies them.

## Affected files
- `backend/src/routes/statistics.py` — new `GET /stats/overview/all/`; shared
  `build_overview`; `build_projection`; goals on the XP series
- `backend/tests/test_statistics_overview.py` — more tests
- `frontend/src/Pages/statisticspage.jsx` — All time option in the year picker
- `frontend/src/Components/StatsOverview.jsx` — all-time axis labels, projection, goal
  markers and snapping, import date formats
- `frontend/src/Components/StatsOverview.css` — projection summary

## Decisions needed
None. Resolved while speccing:
- [x] The projection rate is the average daily XP over the last 28 complete days, or fewer
  for a newer account. Today is left out because it isn't over.
- [x] Goal XP is left out of the rate. Goals are one-time, so a large one would otherwise
  predict the same XP every day.
- [x] The dashed line runs to the end of the current year, or 6 months ahead in the all-time
  view. A finished year has no projection.
- [x] Streak multipliers aren't modelled: the rate already reflects the current streak, and
  this is a straight line at that rate rather than a forecast.

## Risk
- **Involvement:** Moderate — a refactor of the overview route plus a larger XP chart.
- **Review attention:** Low — read-only stats on top of existing data, with no schema change.

## Implementation notes
- A marked day is about a pixel wide on a long chart, so the chart's hover snaps to a marked
  day within a few pixels of the pointer.
- The weekly charts end at today in the all-time view, while the XP chart's axis runs on to
  the end of the projection.
