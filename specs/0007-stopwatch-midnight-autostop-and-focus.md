# 0007 — Stopwatches auto-stop and lose focus at midnight

## Problem / Goal
A stopwatch running across midnight stops on its own and loses its "focused" highlight. Two reported
glitches ("stopwatches automatically stop at midnight" and "loses focus when running for a while near
midnight") share one root cause and are fixed together here.

## Root cause
`stopwatchpage.jsx` schedules a timeout to update `today` at midnight
(`frontend/src/Pages/stopwatchpage.jsx:70-78`). The main data effect depends on
`[selectedDate, today, isFuture]` (line 115), so when `today` flips at midnight that effect re-runs,
calls `stopRunning()` (stops any running, non-Total stopwatch) and refetches — which also resets
`runningId` to `null`, removing the focused styling (`focused-stopwatch` vs `not-focused-stopwatch`
in `StopwatchItem.jsx:18`). The stop-on-change logic is meant to fire when the **user switches days**,
not when the clock rolls over while they're still on the same day.

## Scope
- In scope: stop auto-stopping / un-focusing a running stopwatch purely because `today` rolled over
  while the user is still viewing the same `selectedDate`.
- Out of scope / non-goals: the cross-day cleanup of stopwatches left running on *past* days is spec
  0008; switching days intentionally should still stop the running stopwatch.

## Affected files
- `frontend/src/Pages/stopwatchpage.jsx` — separate the "selected date changed" behavior from the
  "today rolled over" behavior so the stop+refetch only runs on an actual `selectedDate` change.

## Approach
1. Drive the stop-running-then-refetch effect off `selectedDate` changes only (e.g. track the previous
   `selectedDate` via a ref and bail out of `stopRunning()` when it hasn't changed), rather than
   re-running the whole effect when `today` changes.
2. Let `today` still update for `isFuture`/UI purposes without tearing down a running stopwatch.
3. Verify the running stopwatch keeps `end_time === null` and `runningId` stays set across the
   rollover, preserving the focused highlight.

## Acceptance criteria
- A stopwatch running at 23:59 is still running and still focused at 00:01, with time continuous.
- Manually switching `selectedDate` to another day still stops the running stopwatch (unchanged).

## Testing / verification
- Set the system clock near midnight (or temporarily shorten the midnight timeout) with a stopwatch
  running; confirm it does not stop or lose focus at rollover.
- Switch dates via the date picker and confirm the running stopwatch still stops.

## Risk
- **Involvement:** Minimal — restructure one effect's dependencies (+ two one-line `getDay`→`getDate` fixes).
- **Review attention:** Medium — subtle React effect/timing behavior around midnight; must not weaken 0008's stale-stopwatch cleanup.

## Risks & notes
- Related minor bug to fix while here: `homepage.jsx:26` and `habitpage.jsx:60` compute
  `msUntilMidnight` with `now.getDay()` (day-of-week) instead of `getDate()` (day-of-month), so their
  midnight rollover fires at the wrong time. `stopwatchpage.jsx:72` already uses `getDate()`
  correctly. Worth correcting the two pages in this PR or a tiny follow-up.
- Be careful not to weaken spec 0008's handling of genuinely stale running stopwatches.
