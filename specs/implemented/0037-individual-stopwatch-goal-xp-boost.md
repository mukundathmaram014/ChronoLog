---
title: Small capped XP boost for hitting individual stopwatch goals
status: built
---

# Small capped XP boost for hitting individual stopwatch goals

## Summary

Today the day's XP already rewards hitting your **total** daily goal time with a flat
`GOAL_TIME_BONUS` (+50) — earned once, when hours worked ≥ the day's total goal time (the Total
stopwatch's goal, i.e. the sum of individual stopwatch goals by default; specs 0012 / 0023 / 0036).

Add a second, **smaller** reward for hitting an **individual** stopwatch's own goal time, so
balanced days that meet several per-stopwatch goals feel recognized — without letting the total-goal
reward lose its place as the bigger prize. Each non-Total stopwatch that has a goal set and whose
logged time reaches that goal earns a flat `INDIVIDUAL_GOAL_BONUS` (+10). To stop users farming XP by
creating many trivially-short stopwatches, the per-day sum of these individual bonuses is **capped**
at `INDIVIDUAL_GOAL_BONUS_CAP` (+40 — four stopwatches' worth, still below the +50 total-goal bonus).

So on a given day:

- Hit the **total** daily goal time → **+50** (unchanged, the big reward).
- Each **individual** stopwatch that hits its own goal → **+10**, summed but capped at **+40**.

Both can stack (hitting your total goal usually means hitting several individual goals too), but the
individual contribution can never exceed +40, keeping the total-goal bonus the headline.

Values chosen to fit the existing balance (habits 10/25/50, all-habits +25, total-goal +50, a normal
productive day ~200 XP): an individual goal (+10) is an easy-habit's worth, and the whole individual
layer caps just under the total-goal bonus.

## Affected files

- `backend/src/utils.py` — add `INDIVIDUAL_GOAL_BONUS = 10` and `INDIVIDUAL_GOAL_BONUS_CAP = 40`.
  `compute_day_xp` takes a new `individual_goals_hit` count and adds
  `min(individual_goals_hit * INDIVIDUAL_GOAL_BONUS, INDIVIDUAL_GOAL_BONUS_CAP)` to the day's flat
  bonus. Keep it OUT of the streak "grind" calculation (the streak stays habits + worked-time-to-goal
  only).
- `backend/src/xp.py` — `_day_inputs` also counts the day's individual stopwatch goals hit: non-Total
  stopwatches with `goal_time` > 0 whose `curr_duration >= goal_time`. Thread it through
  `recompute_from` into `compute_day_xp`.
- `backend/tests/test_xp.py` — cover: one / several individual goals hit add +10 each; the cap holds
  at +40 no matter how many; individual + total bonuses stack; a stopwatch with no goal or an unmet
  goal adds nothing; the Total row is never counted as an individual goal. Keep the existing
  balance / calibration tests green.
- `frontend/src/Components/Navbar.jsx` — in the "How XP works" breakdown, add a line under the
  existing "Hit daily goal time (bonus) +50": **"Hit a stopwatch's own goal (bonus, capped) +10 (max
  +40)"**, and extend the explanatory copy to say individual stopwatch goals earn a small capped
  bonus on top of the daily-goal bonus.

## Decisions needed

- [x] Individual-goal bonus value and cap? → **+10 per stopwatch goal hit, capped at +40/day** (kept
  below the +50 total-goal bonus; the cap prevents short-goal farming).
- [x] Does hitting individual goals affect the streak? → **No.** The streak rule (grind XP vs the
  day's max) is unchanged; this is a flat reward only.

## Risk

- **Involvement:** Moderate — a new balancing constant pair plus a new day-input count threaded
  through `xp.py` → `utils.py`, and a copy change. Touches the XP core that specs 0034 / 0035 / 0036
  also touch.
- **Review attention:** Medium — verify the cap holds and the individual bonus is excluded from the
  streak calc; confirm the Total stopwatch is never double-counted as an individual goal.
