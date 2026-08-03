---
title: Add an XP section to the statistics page, backed by a persisted per-day XP breakdown
status: decided
---

# Add an XP section to the statistics page, backed by a persisted per-day XP breakdown

## Summary

The XP engine (spec 0020) already writes a `DailyXP` ledger row per user-day, but the only
consumer is `/level/<date>/` on the homepage — the statistics page has no XP view at all.

Add a third **XP** option to the statistics page's section dropdown, rendering a period-aware
XP readout: total XP for the period, average XP/day, best day, streak stats, a per-day XP
heatmap, and a pie showing where the XP came from (habits / worked time / goals / bonuses).

To make the pie cheap and exact, the **source split is persisted** rather than recomputed at
query time: `DailyXP` gains four component columns that `xp.recompute_from` writes alongside
`xp_earned`. The stats route then reads the ledger with a single range query.

## Affected files

**Backend**
- `backend/src/utils.py` — `compute_day_xp` returns the component split (`habit_xp`, `work_xp`,
  `goal_xp`, `bonus_xp`) alongside `xp_earned`.
- `backend/src/db.py` — `DailyXP` gains the four component columns; `serialize` includes them.
- `backend/src/app.py` — new `ensure_daily_xp_breakdown_columns()` startup migration, registered
  in `create_app` next to the existing `ensure_*` calls.
- `backend/src/xp.py` — `recompute_from` persists the components on the ledger row.
- `backend/src/routes/statistics.py` — new `GET /api/stats/xp/<date_string>/<time_period>/`.
- `backend/src/backfill_xp.py` — docstring only: note it now also backfills the breakdown columns.

**Frontend**
- `frontend/src/Pages/statisticspage.jsx` — `xp` option in the section dropdown, its fetch effect,
  its `renderStats()` case; hide the item / calendar-view selectors for XP; generalize
  `StopwatchPie` so the XP pie reuses it.
- `frontend/src/Components/HabitCalendar.jsx` — new `mode="xp"` (window-relative color ramp).
- `frontend/src/Pages/statisticspage.css` — styles for the XP stat rows and level bar.

**Tests**
- `backend/tests/test_statistics_xp.py` — **new**: route shape, period aggregation, average
  excludes future days, user scoping.
- `backend/tests/test_xp.py` — components sum to `xp_earned`; `recompute_from` persists them.
- `backend/tests/test_migrations.py` — new case for the `daily_xp` breakdown columns.

## Decisions needed

*(none — settled in chat: dropdown option, persisted breakdown, pie chart in)*

## Risk

- **Involvement:** Moderate — a schema change plus a touch to the XP formula's rounding, a new
  route, and a new frontend section. Each piece is small and follows an existing pattern
  (`ensure_*_column`, `get_period_range`, `HabitCalendar` modes), but it spans the stack.
- **Review attention:** High — the change alters how `xp_earned` is rounded and therefore feeds
  `User.total_xp`, and it needs a manual backfill run against production after deploy.

## Implementation notes

### 1. Component split in `compute_day_xp` (`utils.py`)

Today the function ends with a single rounding:

```python
xp_earned = round(habit_base * multiplier + work_xp + goal_xp + bonus)
```

Change it to round each component and make the total their sum, so the pie always reconciles
to the displayed total:

```python
habit_xp = round(habit_base * multiplier)
work_xp  = round(work_xp)
goal_xp  = sum(GOAL_XP[d] for d in goal_difficulties)   # already integral
bonus_xp = bonus                                         # already integral
xp_earned = habit_xp + work_xp + goal_xp + bonus_xp
```

Return `{"xp_earned", "streak", "multiplier", "habit_xp", "work_xp", "goal_xp", "bonus_xp"}`.

**Accepted drift:** rounding twice can differ from the old single rounding by ±1 XP on a day.
This is deliberate — a pie whose slices don't add up to the headline number is worse than a
1-XP shift. The backfill (step 5) re-syncs `User.total_xp` to the new values, so no account ends
up with a stale total.

The two bonuses (`ALL_HABITS_BONUS`, `GOAL_TIME_BONUS`) stay merged into one `bonus_xp` — four
pie slices is the right granularity.

### 2. `DailyXP` columns (`db.py`)

Four `db.Integer, nullable=False, default=0` columns: `habit_xp`, `work_xp`, `goal_xp`,
`bonus_xp`. Add them to `__init__` (defaulting to 0) and `serialize`.

### 3. Startup migration (`app.py`)

Follow the established pattern exactly — `PRAGMA table_info(daily_xp)`, then one
`ALTER TABLE daily_xp ADD COLUMN <name> INTEGER NOT NULL DEFAULT 0` per missing column, in a
single `ensure_daily_xp_breakdown_columns()`. Existing rows get 0s until the backfill runs.
Add the matching case to `test_migrations.py` (drop the columns, run, assert re-added, assert
idempotent).

### 4. Persisting in `recompute_from` (`xp.py`)

`recompute_from` already computes `result` per day and writes `xp_earned` / `streak` — extend
both the update and the insert branches to carry the four components. The `delta` bookkeeping
against `User.total_xp` is unchanged (still driven by `xp_earned`).

### 5. Backfill (operational, post-deploy)

No new script. `backend/src/backfill_xp.py` walks every user's history through `recompute_from`
and is idempotent, so re-running it populates the new columns and re-syncs totals:

```
docker exec <container> python backfill_xp.py
```

**This must be run once immediately after the backend deploy.** Until it does, historical ledger
rows carry a non-zero `xp_earned` with zeroed components, so the pie reads empty for any past
period while the headline totals look fine. Update the script's docstring to say so.

### 6. New route: `GET /api/stats/xp/<date_string>/<time_period>/`

In `statistics.py`, reusing `get_period_range` like every other period-aware route. Unlike the
habit/stopwatch routes, this one does **not** need a per-day query loop — `DailyXP` has at most
one row per user-day, so fetch the whole window at once and bucket by date:

```python
rows = DailyXP.query.filter(
    DailyXP.user_id == user_id,
    DailyXP.date >= start_day,
    DailyXP.date <= end_day,
).all()
```

Response:

```json
{
  "total": {"xp": 1234, "average_per_day": 176.3, "days_counted": 7},
  "best_day": {"date": "2026-08-01", "xp": 410},
  "streak": {"qualified_days": 5, "longest": 12, "current": 3},
  "breakdown": [
    {"source": "Habits", "xp": 500},
    {"source": "Work",   "xp": 560},
    {"source": "Goals",  "xp": 100},
    {"source": "Bonuses","xp": 74}
  ],
  "days": [{"date": "2026-08-01", "xp": 410}, {"date": "2026-08-02", "xp": 0}],
  "level": {"total_xp": 48210, "level": 27, "rank": "C", "xp_into_level": 900, "xp_to_next": 3509}
}
```

Semantics:

- **`days`** covers the *whole* period including future days (0 XP), so the heatmap grid stays
  complete — matching `get_habits_calendar` / `get_stopwatches_calendar`, which also don't cut off.
- **`days_counted`** is the number of *elapsed* days in the period: `start_day` through
  `min(end_day, date.today())` inclusive. `average_per_day = total_xp / days_counted`. Averaging
  over elapsed days (not days-with-a-ledger-row) is the honest reading — a day you earned nothing
  is a real zero, not missing data. This differs from the stopwatch route's `days_with_data`
  denominator, deliberately.
- **`best_day`** is the highest-XP day in the period; `null` when the period has no XP at all.
- **`streak.qualified_days`** counts rows in the window with `streak > 0` (a day counted toward
  the streak iff its ledger `streak` is non-zero).
- **`streak.longest`** is `max(row.streak)` over the window — the peak streak *reached* during the
  period. A run that started before the period still shows its true length, which is what a user
  wants to read.
- **`streak.current`** reuses `xp.current_streak(user_id, requested_date)`, i.e. as of the selected
  date, consistent with `/level/<date>/`.
- **`level`** reuses `level_from_xp` / `rank_from_level` on `User.total_xp` — lifetime context, not
  period-scoped, so the XP section is self-contained and doesn't need a second `/level` fetch.
- Invalid `time_period` → `failure_response("Invalid time period")`, matching the siblings.
- Scope every query by `user_id` (CLAUDE.md).

### 7. Frontend (`statisticspage.jsx`)

- Add `<option value="xp">XP</option>` to the section select.
- **Guard the existing effects.** Two effects build URLs from `selectedStatistics` directly —
  `/stats/${selectedStatistics}/...` and `/stats/${selectedStatistics}/all/...`. The `all` variant
  doesn't exist for XP, so both must early-return when `selectedStatistics === "xp"`; a new effect
  fetches `/stats/xp/${selectedDate}/${selectedTimePeriod}/` into `xpData`.
- Hide the item selector (`habits-or-stopwatches-select-bar`) and the calendar-view toggle when XP
  is selected — neither applies. The date and period selects stay.
- New `case "xp"` in `renderStats()`: level/rank line with an XP progress bar, the total /
  average / best-day / streak figures, the `HabitCalendar` in `mode="xp"`, and the breakdown pie.
- **Pie reuse.** `StopwatchPie` is hardcoded to `{title, duration}` items and formats values as
  `Xh Ym`. Generalize it (rename to `BreakdownPie`, taking `items` of `{label, value}` plus a
  `formatValue` callback) and have the stopwatch section pass its existing formatter while XP
  passes `v => \`${v} XP\``. Keeping one pie component is worth the small refactor; `PIE_COLORS`
  and the single-slice full-circle special case are shared as-is.

### 8. `HabitCalendar` `mode="xp"`

Days are `{date, xp}`. Colour ramp is window-relative — mirror the existing `timeColor` fallback
path (ratio against the max value in the window, same faint-to-full green ramp), since XP has no
per-day goal to normalise against. Tooltip: `${date} — ${xp} XP`, or `${date} — no XP` at zero.
Add the `xp` branch to `cellColor` / `cellTitle` and a legend variant.
