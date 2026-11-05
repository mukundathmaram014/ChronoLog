---
title: Fill skipped days before reading stats; average time over elapsed days
status: built
---

# Fill skipped days before reading stats; average time over elapsed days

## Summary
Two bugs make statistics depend on which pages were opened, rather than on what
happened.

**Stale stats.** Rows for a day are created lazily: `GET /habits/<date>/` and
`GET /stopwatches/<date>/` carry recurring items forward onto an empty date and fill
every skipped day in between. The statistics endpoints only read rows, so opening
Statistics before a day page after a gap reports those days as if they didn't exist
(a skipped week reads 0 of 0 habits).

**Average time per day.** `average_time_worked_per_day` divides by the days that have
a Total stopwatch row. Weekdays with no stopwatch scheduled have no row, so a
Monday-only stopwatch with 7 h averages 7 h/day instead of 1 h/day.

Filling lazily on read gives the same result as a background job, because nothing can
be seen without opening the app, so no scheduled job is needed.

## Affected files
- `frontend/src/Pages/statisticspage.jsx` — fill today's habits and stopwatches once on
  load, and make every read wait for it; send the user's local date for the average
- `backend/src/routes/statistics.py` — average the Total over elapsed days in
  `get_stopwatchs_stats` and `get_stopwatches_all`; new `client_today` and
  `elapsed_tracked_days` helpers
- `backend/tests/test_statistics_average.py` — new

## Decisions needed
None. Resolved while speccing:
- [x] The Total averages over every elapsed day of the period, starting from the user's
  first tracked day so a year isn't diluted by the months before they started.
- [x] A single selected stopwatch keeps averaging over the days it had a row, since it
  may only be scheduled on some weekdays.
- [x] Habit percentages need no formula change. A weekday outside a habit's repeat days
  wasn't possible, so it correctly stays out of the total once gaps are filled.

## Risk
- **Involvement:** Minimal — one page's fetch path and one stats formula.
- **Review attention:** Medium — every read on the statistics page now goes through the
  sync, and the numbers shown for existing periods change.

## Implementation notes
- Fill through the existing day endpoints instead of moving the carry-forward logic. The
  frontend already knows the user's local date, and the backend's clock is UTC, so a
  backend fill could create rows for what is still tomorrow for the user (the misfire
  fixed in spec 0009).
- The selector fetch must run after the sync as well, not alongside it: it reads the same
  day, and two concurrent carry-forwards would create duplicate habit rows. Hence one
  shared promise that every read on the page chains from.
- `?today=` is only honoured within a day of the server's date, the most any timezone
  differs, and otherwise falls back to the server's date.
