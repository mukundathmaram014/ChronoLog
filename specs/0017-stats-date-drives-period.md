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

## ⚠️ Decision needed
1. **Item set for a period.** Recommended: list the **distinct** habits/stopwatches that existed on *any*
   day within the selected period (by description/title), scoped by `user_id`. Confirm.
2. **Day period behavior.** For `period = day`, keep today's single-day list (no change). Confirm.
3. **Relationship to 0016.** Recommended to build these together: 0017 provides "the right set of items
   for the period," 0016 renders "all of them + total." Confirm they ship as a pair.

## Affected files
- `backend/src/routes/statistics.py` — (likely) a small endpoint returning the distinct
  habits/stopwatches present in a given period (date + period), scoped by `user_id`, for populating the
  selector / combined view.
- `frontend/src/Pages/statisticspage.jsx` — when period ≠ day, populate the dropdown/list from the
  period's item set instead of the single day's fetch (`:29-52`), keyed on `selectedTimePeriod` +
  `selectedDate`.

## Approach
1. Add the period-items source (Decision 1) — distinct items across the period.
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
- Pairs with **0016** (combined individual+total) and feeds **0015** (pie over a period). Plan them as a
  cluster touching `statistics.py` + `statisticspage.jsx`.
- Distinct-by-name across a period can be a bit query-heavy; reuse the existing per-day queries / keep it
  scoped by `user_id`.
