# 0007 — Running stopwatch rolls over to the next day at midnight

## Problem / Goal
A stopwatch running across midnight currently **auto-stops and loses its "focused" highlight**. The
desired behavior is a clean **rollover**: the timer keeps running across midnight without the user
touching it, but the time **splits at the day boundary** — the portion before 00:00 stays recorded on
the current day, and at midnight the stopwatch **restarts from 0:00 under the new day** and keeps
running. (This supersedes the earlier plan of simply keeping it running on the *same* day; the author
now wants the post-midnight time counted under the next day, starting from 0.)

## Current behavior / root cause
`stopwatchpage.jsx` schedules a timeout to update `today` at midnight
(`frontend/src/Pages/stopwatchpage.jsx:71-79`). The main data effect depends on
`[selectedDate, today, isFuture]` (line 116), so when `today` flips at midnight that effect re-runs,
calls `stopRunning()` and refetches — which resets `runningId` to `null`, dropping the focused styling
(`focused-stopwatch` vs `not-focused-stopwatch` in `StopwatchItem.jsx:18`). So today the rollover both
stops the run and loses focus. We're replacing that accidental teardown with an **intentional
day-boundary hand-off**. (Line numbers re-verified after spec **0022** (installable PWA) landed — it
touched `stopwatchpage.jsx` and `habitpage.jsx`, shifting references slightly, but the rollover logic
itself is unchanged.)

## Desired behavior
At the midnight boundary (D → D+1), for the running (non-Total) stopwatch:
- **Finalize day D:** credit its time up to 00:00 and stop it, so day D keeps exactly the time it ran
  that day (unchanged after this point).
- **Restart on day D+1:** the matching stopwatch on the new day starts from `0` at 00:00 and is left
  **running**, so the session continues seamlessly, now attributed to D+1.
- **Focus follows:** the new day's running stopwatch is the focused one.
- Net effect: no user action, no lost time; D holds the pre-midnight portion, D+1 counts up from 0.

## Scope
- In scope: live rollover of a running stopwatch at midnight (tab open) — finalize on the old day,
  restart from 0 on the new day, keep it running and focused, and keep the Total consistent.
- Out of scope / non-goals: the **closed-tab** case (if the page isn't open at midnight, the stopwatch
  is finalized on its day by spec **0008** — there's no auto-continue onto the next day); manually
  switching `selectedDate` should still stop the running stopwatch (unchanged).

## Decisions (made)
1. **The view follows to the new day:** advance `selectedDate` to the new `today` at rollover, so the
   user sees the freshly-running 0:00 timer (rather than leaving the view on the finalized old day).
2. **Frontend-orchestrated** at the existing midnight timeout — stop the running stopwatch, let D+1's
   carry-forward create the fresh row, then start the matching one. The timeout already fires at ~00:00,
   so the split is near-exact and **no backend change is needed** (a backend rollover/split endpoint is
   the fallback only if exact-midnight atomicity ever matters).
3. **Total stopwatch splits in tandem:** finalize D's Total and start D+1's Total alongside the child, so
   the aggregate rolls over the same way.

## Affected files
- `frontend/src/Pages/stopwatchpage.jsx` — the midnight timeout handler: instead of the data effect
  tearing down the running stopwatch, on rollover (a) **stop** the running stopwatch (persists D's time),
  (b) advance `selectedDate` to the new `today`, (c) after D+1's stopwatches load (carry-forward creates
  them fresh at 0), **auto-start** the one matching the previously-running stopwatch and set `runningId`
  (focus). Note this file was modified by spec **0022** (PWA polish); the midnight effect is now at
  lines 71–79 and the data effect at 81–116.
- `frontend/src/Pages/homepage.jsx`, `frontend/src/Pages/habitpage.jsx`,
  `frontend/src/Pages/taskpage.jsx` — fix their broken `msUntilMidnight` computations (see Risks &
  notes; `taskpage.jsx` is a page added since this spec was first written and inherits the same bug).
- `backend/src/routes/stopwatch.py` — **no change needed** for the chosen frontend approach (it reuses
  the existing stop / carry-forward / start). A small backend split/rollover endpoint is only a fallback
  if exact-midnight atomicity ever proves necessary.

## Approach
1. Keep the midnight timeout that advances `today`, but stop letting the `[selectedDate, today, ...]`
   effect call `stopRunning()` purely because `today` changed (that's the current teardown bug).
2. In the timeout handler, if a non-Total stopwatch is running: call `stop` on it (day D now holds its
   time up to ~midnight), then set `selectedDate` to the new `today`.
3. When D+1's list loads (carry-forward creates the matching stopwatch fresh at `curr_duration = 0`),
   find it by title and call `start`, and set `runningId` to it so it's focused and ticking from 0.
4. If nothing is running at midnight, just advance `today`/`selectedDate` as usual — no stop/start.
5. Keep the Total consistent across the hand-off (finalize D's Total, start D+1's Total in tandem).

## Acceptance criteria
- A stopwatch running at 23:59 is still running at 00:01 **without the user restarting it**; at 00:00 its
  displayed count restarts from 0 under the new day, and the pre-midnight time stays recorded on the
  previous day.
- The running stopwatch stays **focused** after the rollover (now the new day's row).
- Old-day time + new-day time ≈ total elapsed (no dropped or double-counted seconds at the boundary).
- The Total reflects the same split.
- Manually switching `selectedDate` still stops the running stopwatch (unchanged).
- With the tab closed at midnight, the stopwatch is finalized on its day per **0008** (no phantom
  overnight time) — no auto-continue.

## Testing / verification
- Near midnight with a stopwatch running (shorten the timeout or set the system clock): confirm at
  rollover the old day shows the time up to midnight, the new day shows a stopwatch running from 0:00,
  focus is preserved, and no user action was needed.
- Verify old-day + new-day durations sum to ≈ the total time run (no large gap/overlap).
- Switch dates via the picker and confirm the running stopwatch still stops.
- Since the app is now an installable PWA with a service worker (spec **0022**), verify the rollover in
  the installed/standalone app too — it's the same page code, but a long-lived installed window is the
  most likely place a tab sits open across midnight.

## Risk
- **Involvement:** Moderate — reworks the midnight handler into a finalize-then-restart hand-off across
  days (stop + carry-forward + start + focus + Total), not just the one-line effect guard the original
  spec proposed.
- **Review attention:** Medium–High — timing around midnight and the day-boundary split are easy to get
  subtly wrong (dropped or double-counted seconds); must keep the Total consistent and play well with
  **0008** (closed-tab finalize) and **0009** (carry-forward creating the next day's row). Watch focus
  and that a manual day switch still stops.

## Risks & notes
- Related minor bugs to fix while here — the other pages' midnight timeouts are broken in **two** ways
  (`stopwatchpage.jsx:73` is the only correct one):
  1. `homepage.jsx:28`, `habitpage.jsx:65`, and `taskpage.jsx:39` compute `msUntilMidnight` with
     `now.getDay()` (day-of-week) instead of `getDate()` (day-of-month).
  2. Those same three lines also **omit the `- now` subtraction**, so `msUntilMidnight` is a `Date`
     object (coerced to epoch milliseconds) rather than a delay — the timeout effectively never fires.
  Fix both in this PR or a tiny follow-up. (`goalpage.jsx`, also added since this spec was written, has
  no midnight timeout — nothing to fix there.)
- **No double counting at the boundary:** finalize D crediting up to 00:00 and start D+1 from 00:00, so
  the same second isn't counted twice (or dropped).
- Coordinate with **0008** (closed-tab stale finalize) and **0009** (carry-forward must create the new
  day's matching stopwatch so there's something to start).
- Keep the Total's `curr_duration` consistent if it was aggregating the rolled-over stopwatch.