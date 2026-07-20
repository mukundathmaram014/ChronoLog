---
title: Add month labels to the year-period statistics heatmap
status: built
---

# Add month labels to the year-period statistics heatmap

## Summary
The Statistics page's year time period renders habit consistency as a GitHub-style
heatmap (7 weekday rows, one column per week). Right now the grid is an unbroken run
of ~53 columns with no indication of where months fall, so locating "March" means
counting columns. Add month labels ("Jan" … "Dec") above the year heatmap, each
aligned to the week-column containing that month's first day — the same treatment
GitHub's contribution graph uses.

Note a divergence from the idea as stated: the graph is **not** in
`statisticspage.jsx`. That page fetches the calendar data and delegates rendering to
the presentational `HabitCalendar` component (spec 0016), whose `period === "year"`
branch builds the heatmap. The change lives in `HabitCalendar.jsx`/`.css`;
`statisticspage.jsx` needs no changes (props are unchanged, and the `days` array
already carries ISO dates from which month starts are computed).

"Boundaries" are deliberately rendered as labels only, not gaps or divider lines
between columns: weeks straddle month ends, so a single column routinely contains
days from two months and a hard visual boundary between columns cannot represent
month edges honestly. Labels above the first full-or-partial column of each month
(GitHub's convention) are the correct rendering.

## Affected files
- `frontend/src/Components/HabitCalendar.jsx` — in the year branch, compute each
  month's starting week-column from the `days` dates and render a month-label row
  above the grid.
- `frontend/src/Components/HabitCalendar.css` — styles for the new
  `.cal-month-labels` row, sized to line up with the year grid's columns.

## Decisions needed
_None — labels-only (no column gaps/dividers) is settled by the fact that week
columns straddle month boundaries; label style follows the existing
`.cal-weekday-label` convention._

## Risk
- **Involvement:** Minimal — one presentational component plus its stylesheet;
  no backend, no data flow, no props changes.
- **Review attention:** Low — worst failure mode is misaligned labels, which is
  visually obvious and harmless. One coordination point: draft spec 0024
  (mobile overflow) also lists `HabitCalendar.css` in its affected files, so if
  both build in the same batch expect a trivial CSS merge conflict.

## Implementation notes
- Entry point: `HabitCalendar.jsx` `period === "year"` branch (`HabitCalendar.jsx:89`).
  It already computes `pad = weekdayIndex(days[0].date)`; a day at index `i` sits in
  week column `Math.floor((pad + i) / 7)`. The backend's year period is always the
  calendar year (Jan 1 → today or Dec 31, see `get_start_date` in
  `backend/src/routes/statistics.py`), so `days[0]` is Jan 1 and month starts are
  found by scanning `days` for `date` ending in `-01`, or equivalently deriving the
  12 first-of-month indices from the year. Prefer scanning the actual `days` array —
  it may end early (backend stops at today), and months with no data yet should
  simply get no label.
- Rendering: a `.cal-month-labels` div above the existing `.cal-grid.cal-year`,
  itself a grid with the **same column sizing** as the year grid
  (`grid-auto-columns: 12px; gap: 3px;` — keep these in sync, or factor them into a
  shared CSS custom property so they can't drift). Place each label with
  `gridColumnStart: column + 1` and let it span a few columns
  (`grid-column: X / span 4`, `overflow: visible; white-space: nowrap;`). A month is
  ~4.3 columns ≈ 65px wide, so 3-letter labels at the existing `.cal-weekday-label`
  size (0.7rem, #888) fit without collisions; match that class's look.
- Wrap the label row and grid in a common container so they stay left-aligned as a
  unit inside the centered `.habit-calendar` flex column.
- Both year modes (single-habit status and all-habits intensity) share the same grid
  path, so labels apply to both with no extra work. `week`/`month`/`day` periods are
  out of scope — leave their branches untouched.
- No tests exist for frontend components in this repo; verify visually (Statistics →
  period "Year", both All Habits and a single habit) checking that each label sits
  over the column containing the 1st of its month, including a leap year and a
  partial current year.
