---
title: Add an Overview section to statistics with weekly charts, XP curve and week notes
status: built
---

# Add an Overview section to statistics with weekly charts, XP curve and week notes

## Summary
The Habits, Stopwatches and XP sections each go deep on one period at a time, so there's
no way to see how the weeks compare or spot a trend. Add a high-level **Overview** section
for one year, which the other sections become the drill-down from:

- a line chart of habit completion % by week
- a line chart of average hours worked per day by week
- a smooth curve of level or total XP over the year, with a toggle
- a week-by-week table: done, completion %, average per day, XP earned and a note

Weeks can carry a short free-text note, which explains a dip when reading the charts.
Notes can also be pasted in bulk, for moving them over from a log kept elsewhere.

## Affected files
- `backend/src/db.py` — new `WeekNote` model
- `backend/src/routes/statistics.py` — new `GET /stats/overview/<year>/`,
  `PUT /stats/overview/notes/<week_start>/`, `POST /stats/overview/notes/import/`
- `backend/src/routes/users.py` — delete `WeekNote` rows with expired guest accounts
- `backend/tests/test_statistics_overview.py` — new
- `frontend/src/Pages/statisticspage.jsx` — new default section, year selector, fetch
- `frontend/src/Components/StatsOverview.jsx` — new
- `frontend/src/Components/StatsOverview.css` — new

## Decisions needed
None. Resolved while speccing:
- [x] Overview is the first dropdown option and the page's default, since it's the summary
  the other sections drill down from. Those sections keep their layouts.
- [x] The XP curve lives in Overview only. The XP section is unchanged.
- [x] A week counts towards the year holding its Thursday, so each week is in exactly one
  year. Weeks start on Monday, like the existing week stats.
- [x] The table starts at the user's first tracked week, not at an empty January.
- [x] A bulk import never overwrites an existing note, so running it twice is harmless.
- [x] Notes are plain text, up to 500 characters, and clearing one deletes it.

## Risk
- **Involvement:** Moderate — a new table, three endpoints and a new section, mostly in new
  files.
- **Review attention:** Medium — the new table is created by `db.create_all()` on boot, and
  the statistics page now opens on a different section.

## Implementation notes
- Numbers must match the existing week views: habit totals count rows, and the average
  uses the same elapsed-days rule as spec 0038.
- `/stats/overview/<year>/` reads each table once over the range instead of looping per day
  like the older stats routes, since it covers up to 53 weeks.
- The XP series is anchored to `User.total_xp` minus the XP earned since the range began, so
  the curve ends on the level shown elsewhere. Level progress comes from the backend, so the
  level formula isn't duplicated in the frontend. Rank isn't included (spec 0035).
- The curve uses monotone interpolation so smoothing can't suggest XP went down.
- Fetches go through the page's `fetchAfterSync` (spec 0038), so skipped days are filled first.
