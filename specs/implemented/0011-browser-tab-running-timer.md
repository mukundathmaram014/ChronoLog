---
status: built
---

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
- In scope: while a non-Total stopwatch is running and the user is on the stopwatch page, set
  `document.title` to its live elapsed time (`00:12:34`); restore the original title when it stops, when
  navigating away, and on unmount.
- Out of scope / non-goals: no backend change; no change to the elapsed-time calc (stays frontend per
  CLAUDE.md); no notifications/favicon work.

## Decisions (made)
1. **Title format:** the **most minimal** — just the elapsed time, `00:12:34` (no glyph, no stopwatch
   title). Format isn't important here, so keep it as small as possible.
2. **Where it applies:** only **while on the stopwatch page** (simplest, reuses the existing per-second
   tick). App-wide was the considered alternative but isn't needed.

## Affected files
- `frontend/src/Pages/stopwatchpage.jsx` — add an effect that, when `runningId !== null`, updates
  `document.title` each tick using the existing `getElapsed` + `formatTimeString`; cleanup restores the
  prior title.

## Approach
1. Capture the default title once (e.g. `"ChronoLog"` or the current `document.title`).
2. In an effect keyed on the running stopwatch and the per-second tick, if a stopwatch is running, set
   `document.title` to the formatted elapsed (`00:12:34` via `formatTimeString`); else restore the
   default.
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
- **Review attention:** Low — additive, no backend, easily verified; title format and scope are settled (minimal time-only title, stopwatch page only).

## Risks & notes
- Keep the update on the existing render tick — don't add a second interval.
- Make sure the Total stopwatch isn't what drives the title; use the actually-running item.
