# 0008 — Stopwatch left running on a past day runs forever

## Problem / Goal
If a stopwatch isn't stopped (e.g. tab closed abnormally and the `pagehide` stop never lands), its
`end_time` stays `NULL`. When you later open that day, the frontend keeps accruing live time against
it, so it appears to run forever. Stale running stopwatches on days other than today should be
finalized so they stop accumulating.

## Root cause
- Stopping relies on best-effort client calls (`pagehide`/navigation/date-change `stop` requests in
  `frontend/src/Pages/stopwatchpage.jsx:124-156`). If one doesn't complete, `end_time` remains `NULL`.
- `getElapsed` adds `Date.now() - interval_start` whenever `end_time == null`, regardless of the
  stopwatch's date (`stopwatchpage.jsx:407-416`) — so a past-day stopwatch with `end_time NULL` grows
  unbounded.

## Scope
- In scope: (a) backend finalizes non-Total stopwatches with `end_time IS NULL` whose `date` is before
  today; (b) frontend only accrues live time for stopwatches on the currently-selected day.
- Out of scope / non-goals: the live midnight rollover (tab open) is spec 0007; no schema change.

## Decisions (made)
When finalizing a stale running stopwatch, **freeze it**: set `end_time = interval_start` so
`curr_duration` is left unchanged — no bogus overnight time is added. This is the simple option and
avoids inflating stats. (The considered alternative — crediting up to end-of-its-day — was rejected as
speculative and messier.)

## Affected files
- `backend/src/routes/stopwatch.py` — in `get_stopwatches` (or a small helper run on fetch), finalize
  any non-Total stopwatch with `end_time IS NULL` and `date < today`, scoped by `user_id`; keep the
  Total consistent. Use `ensure_utc` for any datetime math, `success_response`/`failure_response`.
- `frontend/src/Pages/stopwatchpage.jsx` — `getElapsed`: only add live elapsed when the stopwatch's
  `date` equals `selectedDate`/`today`; otherwise return `curr_duration`.

## Approach
1. Backend: when listing stopwatches for a date, sweep the user's stopwatches with `end_time IS NULL`
   and `date < date.today()` and finalize by freezing them — set `end_time = interval_start`, leaving
   `curr_duration` as-is. Commit. Keep Total in sync if it was the one left running.
2. Frontend: guard `getElapsed` so only same-day running stopwatches tick; past/future return the
   stored `curr_duration` (future already returns 0).

## Acceptance criteria
- Opening a past day that had a stopwatch left running shows a fixed time, not an ever-increasing one.
- No extra/overnight time is silently added to past days (frozen at `end_time = interval_start`).
- Today's running stopwatch is unaffected and still ticks live.

## Testing / verification
- Simulate a stuck stopwatch (set a stopwatch's `end_time` to NULL on a past date in the DB), open
  that day → time is frozen, not climbing.
- Normal start/stop on today still works.

## Risk
- **Involvement:** Moderate — a backend finalize-on-fetch sweep plus a frontend `getElapsed` guard.
- **Review attention:** Medium — it mutates persisted durations (freezing stale runs) and must stay consistent with 0007 and the Total.

## Risks & notes
- Coordinate with 0007 so the two midnight/cross-day behaviors don't fight: 0007 handles the **live**
  midnight rollover (finalize the old day, restart the new day) when the tab is open; 0008 finalizes
  stopwatches stranded on *earlier* days when the tab was closed at midnight. Freezing here (rather than
  crediting overnight time) is what keeps a closed-tab run from inflating a past day.
- Make sure the Total stopwatch's `curr_duration` stays consistent if it was the stranded one.
