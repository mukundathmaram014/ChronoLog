# 0011 — Show the running stopwatch timer in the browser tab

## Problem / Goal
When a stopwatch is running, there's no indication in the browser tab — you have to be on the page to
see elapsed time. Show the live elapsed time of the running stopwatch in the document title (browser
tab) so it's visible while you work in another tab, and restore the normal title when nothing runs.

## Context
- `frontend/src/Pages/stopwatchpage.jsx` already tracks the running stopwatch via `runningId` and
  computes live elapsed in `getElapsed(item)` (`stopwatchpage.jsx:407-416`), and already re-renders on a
  per-second tick while a stopwatch runs.
- There is no existing use of `document.title` for live state, so this is additive.

## Scope
- In scope: while a non-Total stopwatch is running, set `document.title` to its live elapsed time (and
  title); restore the original title when it stops, when navigating away, and on unmount.
- Out of scope / non-goals: no backend change; no change to the elapsed-time calc (stays frontend per
  CLAUDE.md); no notifications/favicon work.

## ⚠️ Decision needed
1. **Title format.** Recommended: `▶ 00:12:34 · <stopwatch title>` (so it reads at a glance in a narrow
   tab). Alternative: just `00:12:34`. Pick one.
2. **Where it applies.** Recommended: only while on the stopwatch page (simplest, uses the existing
   tick). Alternative: app-wide (would need the running-timer logic lifted above the page, larger).

## Affected files
- `frontend/src/Pages/stopwatchpage.jsx` — add an effect that, when `runningId !== null`, updates
  `document.title` each tick using the existing `getElapsed` + `formatTimeString`; cleanup restores the
  prior title.

## Approach
1. Capture the default title once (e.g. `"ChronoLog"` or the current `document.title`).
2. In an effect keyed on the running stopwatch and the per-second tick, if a stopwatch is running, set
   `document.title` to the formatted elapsed (per the chosen format); else restore the default.
3. Return a cleanup that restores the default title on unmount / when running stops.

## Acceptance criteria
- Starting a stopwatch updates the tab title to its live time; the value ticks ~once per second.
- Pausing/resetting/finishing, navigating away, or closing the page restores the normal title.
- No regression to the on-page timer or the existing tick.

## Testing / verification
- Start a stopwatch, switch to another tab, confirm the tab title counts up; pause and confirm it
  reverts.
- Navigate to another page mid-run and confirm the title is restored.

## Risk
- **Involvement:** Minimal — one additive effect writing `document.title` on the existing render tick.
- **Review attention:** Low — additive, no backend, easily verified; just confirm the title format/scope decision.

## Risks & notes
- Keep the update on the existing render tick — don't add a second interval.
- Make sure the Total stopwatch isn't what drives the title; use the actually-running item.
