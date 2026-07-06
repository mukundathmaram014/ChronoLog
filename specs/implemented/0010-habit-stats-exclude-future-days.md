---
status: built
---

# 0010 — Habit stats count days that haven't happened yet

## Problem / Goal
Weekly/monthly/yearly habit statistics iterate over the *entire* period including future days, so a
mid-week or mid-month view can include days that haven't occurred yet. Stats should only count days up
to and including today. (The stopwatch stats route already does this correctly; habits don't.)

## Root cause
In `get_habits_stats`, the `week`/`month`/`year` branches loop over every day of the period with no
cutoff (`backend/src/routes/statistics.py:39-81`). The stopwatch equivalent `get_stopwatchs_stats`
already breaks out once `current_day_* > date.today()` (`statistics.py:122, 140, 158`). The habits
route is simply missing that guard.

## Scope
- In scope: add the `> date.today()` cutoff to the week/month/year loops in `get_habits_stats`,
  mirroring the stopwatch stats route.
- Out of scope / non-goals: no change to the `day` branch; no change to stopwatch stats (already
  correct); no change to how habits are stored or carried forward.

## Affected files
- `backend/src/routes/statistics.py` — `get_habits_stats`, the `week`, `month`, and `year` loops.
- `backend/src/routes/statistics.py` — `get_habits_all` (added after this spec was written, in spec
  0016): same missing cutoff, same fix, mirroring `get_stopwatches_all`'s existing guard.
  (`get_habits_calendar` is left alone — the calendar intentionally renders the full period grid.)
- `backend/tests/test_statistics_habits_cutoff.py` — new tests for the cutoff (current-period
  week/month/year, fully-past period unchanged, and the combined `all` endpoint).

## Approach
1. In each of the `week`, `month`, `year` loops, add `if current_day_* > date.today(): break` at the
   top of the loop body, exactly as `get_stopwatchs_stats` does.
2. Leave `percentage_done` as-is; it already divides by the counted `total_habits`.

## Acceptance criteria
- Mid-period habit stats (week/month/year) only include days from the period start through today.
- A fully-past period is unchanged; the `day` view is unchanged.
- Behavior is consistent with stopwatch stats.

## Testing / verification
- With habits earlier in the current week/month, call
  `GET /stats/habits/<today>/week/` and `/month/` and confirm future days aren't counted (totals
  don't include not-yet-occurred days).
- A past month still returns the same totals as before.

## Risk
- **Involvement:** Minimal — add a `> date.today()` break to three loops in one file, mirroring the existing stopwatch-stats code.
- **Review attention:** Low — backend-only, directly copies working logic; small blast radius.

## Risks & notes
- Small, backend-only, low risk — directly mirrors existing, working code in the same file.
- Note: because habits only exist for days the user has visited, the visible effect is small today,
  but this makes the two stats routes consistent and correct if future habits ever exist.
