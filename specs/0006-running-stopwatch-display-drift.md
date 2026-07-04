# 0006 — Running stopwatch shows ~2s more than the stopped value

## Problem / Goal
While a stopwatch runs, the displayed elapsed time is a couple of seconds ahead of the value that
gets persisted when it stops, so the time visibly "jumps back" on stop. Make the running display
agree with the recorded duration.

## Likely cause (investigate first)
- Live display: `getElapsed` computes `curr_duration + (Date.now() - new Date(interval_start))`
  (`frontend/src/Pages/stopwatchpage.jsx:407-416`), i.e. **client clock** minus the server-provided
  `interval_start`.
- On stop: the backend computes `increment = ensure_utc(end_time) - ensure_utc(interval_start)` using
  the **server clock** (`backend/src/routes/stopwatch.py:236-239`).
- If the client clock differs from the server clock (skew) or there's request latency between
  `interval_start` being set server-side and the client starting to tick, the running display and the
  stopped value diverge — consistent with a steady ~2s offset.

First step in `/build` is to confirm this (log `Date.now()` vs server `interval_start` at start) before
committing to a fix.

## Scope
- In scope: make the running elapsed calc consistent with what the backend records on stop.
- Out of scope / non-goals: do NOT move the elapsed calc to the backend (CLAUDE.md: stopwatch elapsed
  is computed on the fly in the frontend from `interval_start` + `curr_duration`); no schema change.

## Affected files
- `frontend/src/Pages/stopwatchpage.jsx` — `getElapsed`, and `handleStart` where the started
  stopwatch state (incl. `interval_start`) comes back from the server.

## Approach (pending confirmation)
Preferred: anchor the live delta to a **client-side** timestamp captured when the start response
arrives, instead of mixing client `Date.now()` with the server's `interval_start`. e.g. record
`startedAtClient = Date.now()` when `handleStart` resolves, and compute
`elapsed = curr_duration + (Date.now() - startedAtClient)`. This removes client/server skew from the
running display while the persisted value still derives from server timestamps.
Alternative: have `start` return the server "now" and compute a one-time client/server offset to
subtract. Choose based on what the investigation shows.

## Acceptance criteria
- When a stopwatch is stopped, the displayed time does not visibly jump; the running display matches
  (within ~tens of ms) the persisted `curr_duration`.
- No regression to total-stopwatch accumulation or to the persisted duration.

## Testing / verification
- Start a stopwatch, let it run ~30s, stop it; the number should not snap backward by ~2s.
- Optionally skew the client clock by a few seconds and confirm the display still matches on stop.

## Risk
- **Involvement:** Minimal — a surgical edit to `getElapsed`/`handleStart` in one file.
- **Review attention:** Medium — small code, but the root cause is unconfirmed (investigation-first) and it touches the core on-the-fly elapsed calc the app depends on, so it's easy to regress timing.

## Risks & notes
- Uncertain root cause — investigation-first. If the offset is NOT clock skew (e.g. it's the 10ms
  interval accumulating, or latency in setting `interval_start`), revise the approach and note it in
  the PR.
- Touches the on-the-fly elapsed calc the rest of the app depends on; keep the change surgical.
