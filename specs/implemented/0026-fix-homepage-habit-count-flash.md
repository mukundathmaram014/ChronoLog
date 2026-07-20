---
title: Fix pre-fetch data flash on all four homepage cards with a loading state
status: built
---

# Fix pre-fetch data flash on all four homepage cards with a loading state

## Summary

On first open of the homepage, every card renders hard fallback values for a
frame before its fetch resolves, then snaps to real data. In
`frontend/src/Pages/homepage.jsx` the data states are initialized to `null`
(or an empty shape) and the JSX renders immediately with `?? 0`-style
fallbacks, so the pre-fetch frame shows values that read as real data rather
than "still loading":

- **Habits** (the reported bug): `CircularProgress` gets
  `habitsData?.completed_habits ?? 0` / `?? 0` (line 281) → a hard "0 / 0"
  that reads as "you have no habits".
- **Stopwatches**: `CircularProgressTotal` gets `?? 0` (line 290) →
  "00:00:00".
- **Level**: header and XP bar fall back to "Level 1", "E-Rank", "0 / 0 XP"
  (lines 248–266) → reads as a fresh account for a frame.
- **Tasks**: `tasksData` starts as `{ overdue: [], today: [] }` (line 20) →
  "0 / 0 done today" plus the "Nothing due today" empty-state message
  (line 306) before the fetch resolves.

The fix: distinguish "not loaded yet" from "loaded, value is 0" and render a
**minimal loading treatment** (no skeleton/pulse animation) for the former.
`data === null` already encodes not-loaded for habits/stopwatches/level; the
tasks state changes its initial value to `null` to gain the same sentinel.
There is no existing per-card loading pattern in the app (the only precedent
is `AuthProvider`'s whole-app "Loading..." gate), so this introduces the
pattern — keep it minimal and local to the homepage.

## Affected files

- `frontend/src/Pages/homepage.jsx` — branch all four cards on
  data-not-yet-loaded instead of rendering fallbacks; change `tasksData`
  initial state to `null`.
- `frontend/src/Pages/homepage.css` — muted-placeholder styles if the chosen
  treatment needs any (likely just a muted text color class).

## Decisions needed

_None — decided in spec-chat (2026-07-19): cover all four cards; minimal
treatment (background-color ring + muted "—" placeholder), no skeleton or
pulse animation._

## Risk

- **Involvement:** Minimal — one page component plus its stylesheet; no
  backend, routing, or data-shape changes over the wire.
- **Review attention:** Low — purely presentational. Two things to check in
  review: (1) the loaded-but-empty case (a user with genuinely 0 habits /
  tasks) still renders real "0 / 0" values and isn't stuck on the loading
  treatment; (2) the tasks card's null-init doesn't break the
  `tasksData.overdue` / `tasksData.today` accesses at lines 299–313 while
  loading.

## Implementation notes

- Entry point: `Home` in `frontend/src/Pages/homepage.jsx`. All four fetches
  are `useEffect`s keyed on `today` hitting `/stats/habits/...`,
  `/stats/stopwatches/...`, `/tasks/...`, `/level/...` via `useFetch` (keep
  using that hook per CLAUDE.md).
- Use `data === null` as the loading flag for each card rather than adding
  separate `isLoading` state — each fetch's `.then` sets the state to the
  response object, and errors leave it null (acceptable: an errored card
  staying in the placeholder state is better than false zeros).
- **Habits card**: pass a `loading` prop to `CircularProgress` (line 194).
  When loading, render the ring with `percentage = 0` (background circle
  only) and replace the `{completed_habits} / {total_habits}` text with a
  muted "—". Keep the same `size` so the card doesn't jump when data lands.
- **Stopwatches card**: same `loading` prop on `CircularProgressTotal`
  (line 130) — background ring plus muted "—" in place of the time string.
- **Level card**: while `levelData === null`, render muted "—" placeholders
  in the header/XP-footer text and an empty XP bar; suppress the streak line
  (it's already conditional on loaded data).
- **Tasks card**: change the initial state from `{ overdue: [], today: [] }`
  to `null`. While null, show a muted "—" in the summary line and suppress
  the "Nothing due today" empty state (that message must only appear once
  data has loaded and both lists are empty). Guard the `.overdue`/`.today`
  accesses accordingly (e.g. branch the card body on `tasksData === null`).
- Do **not** prefetch/cache data at the router or auth layer — there's no
  existing prefetch infrastructure, and per-card loading state solves the
  flash without new architecture.
- The midnight-rollover effect resets `today`, which refires the fetches;
  each state keeps its old value during that refetch, so cards briefly show
  yesterday's numbers instead of flashing placeholders — that's fine, don't
  reset states to null on date change.
- Minimal visual treatment only: muted fill color (e.g. `#888`-ish via a CSS
  class or SVG `fill`), no pulse/skeleton animation, no layout shift.
- Tests: the only frontend test is the CRA default `App.test.js`; no test
  changes required. Verify manually by loading the homepage on a throttled
  network (DevTools → Slow 3G) and confirming no card shows fake zeros
  pre-load, and that a fresh account with zero habits/tasks still shows real
  "0 / 0" values after load.
