# 0008 — Stopwatch left running on a past day runs forever

## Problem / Goal
If a stopwatch isn't stopped (e.g. tab closed abnormally and the `pagehide` stop never lands), its
`end_time` stays `NULL`. When you later open that day, the frontend keeps accruing live time against
it, so it appears to run forever. Stale running stopwatches on days other than today should be
finalized so they stop accumulating.

## Root cause
- Stopping relies on best-effort client calls (`pagehide`/navigation `stop` requests in
  `frontend/src/Pages/stopwatchpage.jsx:124-157`). If one doesn't complete, `end_time` remains `NULL`.
- `getElapsed` adds `Date.now() - interval_start` whenever `end_time == null`, regardless of the
  stopwatch's date (`stopwatchpage.jsx:430-439`) — so a past-day stopwatch with `end_time NULL` grows
  unbounded.

## Scope
- In scope: (a) backend finalizes non-Total stopwatches with `end_time IS NULL` whose `date` is before
  today; (b) frontend only accrues live time for stopwatches on the currently-selected day.
- Out of scope / non-goals: the live midnight rollover (tab open) is spec 0007; no schema change; no
  XP recomputation (see Risks & notes — freezing leaves worked time unchanged, so spec 0020's XP
  ledger is unaffected by design).

## Decisions (made)
When finalizing a stale running stopwatch, **freeze it**: set `end_time = interval_start` so
`curr_duration` is left unchanged — no bogus overnight time is added. This is the simple option and
avoids inflating stats. (The considered alternative — crediting up to end-of-its-day — was rejected as
speculative and messier.) Post-0020, freezing has a second payoff: because `curr_duration` doesn't
change, the day's work-time XP is already correct and no `recompute_from` call is needed.

## Affected files
- `backend/src/routes/stopwatch.py` — in `get_stopwatches` (or a small helper run on fetch), finalize
  any non-Total stopwatch with `end_time IS NULL` and `date < today`, scoped by `user_id`; keep the
  Total consistent. Use `ensure_utc` for any datetime math, `success_response`/`failure_response`.
  **Note (spec 0020):** this file now imports `recompute_from` from `backend/src/xp.py` and calls it
  in every route that changes a day's `curr_duration` (`update`, `delete`, `stop`, `reset`). The
  freeze sweep leaves `curr_duration` untouched, so it must **not** call `recompute_from`; but if the
  Total-consistency step ever adjusts a `curr_duration`, it must call `recompute_from(user_id, that_date)`
  before commit, matching the pattern in the other routes.
- `frontend/src/Pages/stopwatchpage.jsx` — `getElapsed` (`stopwatchpage.jsx:430-439`): only add live
  elapsed when the stopwatch's `date` equals `selectedDate`/`today`; otherwise return `curr_duration`.
  (The browser-tab title effect at `stopwatchpage.jsx:173-185` goes through `getElapsed` and picks up
  the guard for free.)

## Approach
1. Backend: when listing stopwatches for a date, sweep the user's stopwatches with `end_time IS NULL`
   and `date < date.today()` and finalize by freezing them — set `end_time = interval_start`, leaving
   `curr_duration` as-is. Commit. Keep Total in sync if it was the one left running.
2. Frontend: guard `getElapsed` so only same-day running stopwatches tick; past/future return the
   stored `curr_duration` (future already returns 0 via the existing `isFuture` early return).

## Acceptance criteria
- Opening a past day that had a stopwatch left running shows a fixed time, not an ever-increasing one.
- No extra/overnight time is silently added to past days (frozen at `end_time = interval_start`).
- Today's running stopwatch is unaffected and still ticks live.
- Past days' XP (spec 0020 `DailyXP` ledger and `User.total_xp`) is unchanged by the sweep.

## Testing / verification
- Simulate a stuck stopwatch (set a stopwatch's `end_time` to NULL on a past date in the DB), open
  that day → time is frozen, not climbing.
- Normal start/stop on today still works.
- With XP in place: fetch a past day with a stranded stopwatch, then hit `/api/level/` (or check
  `DailyXP` for that date) → no XP delta from the sweep.

## Risk
- **Involvement:** Moderate — a backend finalize-on-fetch sweep plus a frontend `getElapsed` guard.
- **Review attention:** Medium — it mutates persisted rows (freezing stale runs) and must stay consistent with 0007, the Total, and the 0020 XP recompute pattern.

## Risks & notes
- Coordinate with 0007 so the two midnight/cross-day behaviors don't fight: 0007 handles the **live**
  midnight rollover (finalize the old day, restart the new day) when the tab is open; 0008 finalizes
  stopwatches stranded on *earlier* days when the tab was closed at midnight. Freezing here (rather than
  crediting overnight time) is what keeps a closed-tab run from inflating a past day.
- Make sure the Total stopwatch's `curr_duration` stays consistent if it was the stranded one.
- **Interaction with spec 0020 (XP / level system):** work-time XP is derived from the day's Total
  stopwatch `curr_duration` (`backend/src/xp.py`, `_day_inputs`), and every existing route that changes
  a day's worked time calls `recompute_from(user_id, date)` before commit. The freeze decision keeps
  this spec out of the XP path entirely; do not "helpfully" credit time during the sweep, as that would
  both inflate stats and require a ledger recompute. Spec 0020 currently lives on branch
  `spec/0020-habit-xp-level-system` (not yet merged to `main` as of 2026-07-06) — build 0008 on top of
  it or rebase after it merges, since both touch `backend/src/routes/stopwatch.py`.