---
status: built
---

# 0017 — Date change drives the statistics period

## Problem / Goal
On the statistics page, changing the date should change **what data is available**, not just shift a
single day. The author wants: pick a date + period (e.g. month) and see data for *all* habits/stopwatches
in that whole period — including items that existed on other days of the period, not only the ones
present on the selected day.

## Context
- The stats endpoints already aggregate over the period (`week`/`month`/`year` loops in
  `backend/src/routes/statistics.py`), so the *numbers* already span the period.
- The gap is the **item list / dropdown**: `statisticspage.jsx` fetches only the selected day's habits
  (`:29-37`) and stopwatches (`:40-52`) to populate the selector (`:284-301`). So an item that existed
  earlier in the month but not on the selected day can't be picked, and a combined view (0016) keyed off
  the day's items would miss it.

## Decisions (made)
1. **Item set for a period = the distinct habits/stopwatches** that existed on *any* day within the
   selected period (by description/title), scoped by `user_id`.
2. **Day period unchanged:** for `period = day`, keep today's single-day list.
3. **Ships as a cluster with 0016 and 0015:** 0017 provides the period's item set, 0016 renders all of
   them + the total, and 0015 draws the per-stopwatch pie — all fed by one shared period-aware
   `statistics.py` source.

## Affected files
- `backend/src/routes/statistics.py` — new `GET /stats/items/<date>/<period>/` returning the distinct
  habit descriptions / stopwatch titles present in the period, scoped by `user_id` (single range query
  with `DISTINCT`, not a per-day loop). 0016 wasn't built yet at implementation time, so the "shared
  period-aware source" took the form of a `get_period_range()` helper extracted from and reused by the
  0015 breakdown endpoint; 0016 should build on both.
- `frontend/src/Pages/statisticspage.jsx` — the two single-day selector fetches merged into one
  effect keyed on `selectedTimePeriod` + `selectedDate`: day keeps the existing per-day fetches,
  longer periods populate the dropdown from `/stats/items/`. A selection that disappears from the new
  list resets to the All/Total view instead of silently filtering on an absent item.
- `backend/tests/test_statistics_items.py` — endpoint tests (period membership, distinct collapse,
  day unchanged, user scoping, invalid period).

## Approach
1. Add the period-items source — distinct items across the period — as part of the shared period-aware
   `statistics.py` endpoint (with 0016).
2. Frontend: drive the selector/list from that source when a multi-day period is selected; keep the
   single-day fetch for `day`.
3. Ensure the existing per-item stats query still works for any item chosen from the broadened list.

## Acceptance criteria
- Selecting a period shows/【selectable】 every habit/stopwatch that appeared anywhere in that period.
- The `day` period is unchanged.
- Stats for a chosen item still compute correctly over the period.

## Testing / verification
- Create an item that exists early in a month but not on the selected day; select `month`; confirm it's
  listed and its stats are correct.
- `day` still lists only that day's items.

## Risk
- **Involvement:** Moderate — a distinct-items-in-period source plus selector logic driven by the period.
- **Review attention:** Medium — no schema; coupled with 0016, and the distinct-by-name query can get heavy — keep it `user_id`-scoped.

## Risks & notes
- Part of the **0015/0016/0017 cluster** — one shared period-aware `statistics.py` source (distinct
  period items + per-item stats + total + per-stopwatch breakdown) feeding `statisticspage.jsx`; build
  them together, not as three queries.
- Distinct-by-name across a period can be a bit query-heavy; reuse the existing per-day queries / keep it
  scoped by `user_id`.
