---
title: Fix mobile layout — page wider than phone viewport and overlapping blocks
status: decided
---

# Fix mobile layout — page wider than phone viewport and overlapping blocks

## Summary
Despite spec 0022's responsive pass (per-page `@media` blocks, viewport meta, single-column
homepage collapse), pages on a real phone still render **wider than the screen** — the user has to
pan/zoom around — and **blocks overlap** each other. Because one element wider than the viewport
expands the whole layout viewport, a single unconstrained element per page is enough to produce
exactly this "everything is too big and misplaced" symptom.

This is a **CSS-only, frontend-only** fix pass:
1. Walk every page at phone width (375px) and find each element that exceeds the viewport or
   overlaps a sibling; fix the root cause (fixed px widths, `%`-width + padding without
   `box-sizing`, grid/flex min-content blowout, absolutely-positioned elements that don't shrink).
2. Add a **global backstop** so one missed element can never again blow up the whole layout:
   `overflow-x: clip` on `html, body` (clip, not hidden — doesn't create a scroll container) plus
   `max-width: 100%` guards where appropriate.
3. Verify on a real phone **and** in the installed PWA (standalone mode), not just DevTools.

No component restructuring, no visual redesign, no backend changes.

## Affected files
- `frontend/src/index.css` — global backstop: `overflow-x` guard on `html`/`body`, base
  `box-sizing` guards where safe.
- `frontend/src/Pages/homepage.css` — cards grid: `1fr` → `minmax(0, 1fr)` (grid children's
  min-content width can exceed the track and overflow), flex children `min-width: 0`, XP-bar/level
  header at narrow widths.
- `frontend/src/Pages/habitpage.css` — `.habit-wrapper` (60% width + fixed-px children), popup
  widths, absolutely-positioned element at `:276`, date-slider row.
- `frontend/src/Pages/stopwatchpage.css` — fixed `width: 266px` total block (`:404`), absolutely
  positioned elements (`:144`, `:158`, `:443`) that overlap at narrow widths, popup widths.
- `frontend/src/Pages/taskpage.css` — fixed `width: 266px` (`:77`), popup widths.
- `frontend/src/Pages/goalpage.css` — popup widths (300px/250px), input sizing.
- `frontend/src/Pages/statisticspage.css` — chart containers below 600px (only 900px breakpoint
  reflows the layout; charts/legends can still exceed 375px).
- `frontend/src/Pages/loginpage.css` / `frontend/src/Pages/signuppage.css` — form width +
  padding vs. viewport at ≤400px.
- `frontend/src/Components/Navbar.css` — `.user-dropdown` (fixed 200px anchored `right: 0`),
  navbar wrap behavior, profile popup at phone width.
- `frontend/src/Components/HabitCalendar.css` — calendar grid at phone width (month grid is a
  common min-content offender).
- `frontend/src/Components/InstallPrompt.css` — banner `max-width` vs. small screens (verify).
- `frontend/src/App.css` — only if a shared container guard belongs there (verify; may be
  no-change).

No `.jsx` changes expected — if a fix truly requires a markup change (e.g. a wrapper div for a
scrollable chart), keep it minimal and note it in the PR.

## Decisions needed
_None — both prior questions are answered:_
- **Reproduces in both the phone browser and the installed app** → this is a genuine CSS problem,
  not a stale service-worker shell. The SW-investigation branch is off the table; the SW only
  reappears in verification (confirm the installed app picks up the fixed build after deploy).
- **Worst page: stopwatch page.** The stopwatch cards' content is too big to fit inside them —
  the user has to pan around to see each one. Fix and verify this page first.

## Risk
- **Involvement:** Moderate — CSS-only and mechanical, but touches every page stylesheet; no
  logic, no backend, no data.
- **Review attention:** Medium — no correctness logic, but broad CSS edits can regress the
  **desktop** layout; each fix must be checked at both 375px and desktop width. The global
  `overflow-x` backstop must not hide a vertical-scroll or sticky-positioning behavior.

## Implementation notes
- **Primary target — stopwatch page (fix first, verify first).** `stopwatchpage.css` already has
  a `@media (max-width: 700px)` block (from spec 0022) that collapses the grid to one column and
  shrinks the *total* readout — but nothing inside the per-stopwatch cards is scaled down, so
  desktop-sized content overflows a ~345px card:
  - `.controls button` (`:255`): `font-size: 1.5rem` + `padding: 14px 28px` + `margin-right: 15px`
    stacked on the flex `gap: 10px` — start/stop/reset can't fit on one row and barely fit at all.
    Scale these down at phone width and drop the redundant `margin-right` (the gap already spaces
    them).
  - `.stopwatch-delete-icon` / `.stopwatch-edit-icon` (`:277`, `:286`): `font-size: 50px` — huge
    at phone width.
  - `.drag-handle-stopwatch` (`:442`): absolutely positioned `top: 16px; right: 16px` with a 40px
    icon — overlaps the title row when the card narrows.
  - `.time-display` (`:236`): `2.2rem` monospace with `letter-spacing: 2px` — check it fits;
    reduce at phone width if needed.
  - `.stopwatch-item` has `overflow: hidden` (`:225`), which currently *clips* the oversized
    content — that's why cards look cut off rather than scrolling. Once the content is scaled to
    fit, the clip becomes harmless, but don't rely on it as the fix.
  - `.stopwatch-title p` (`:343`): `30px` bold with no wrapping guard — long names need
    `overflow-wrap: anywhere` or ellipsis.
- **Method:** Chrome DevTools device toolbar at 375×812, walk every route (login, signup, home,
  habits, stopwatches, tasks, goals, stats) including popups/modals open. For each page, find the
  widest offending element (DevTools: `document.documentElement.scrollWidth > innerWidth`, then
  binary-search with element deletion or `outline` debugging). Fix the root cause; don't just
  clamp the symptom.
- **Known root-cause patterns to hunt (from reading the CSS):**
  - Fixed pixel widths that exceed ~340px of usable width, or that combine with padding without
    `box-sizing: border-box` (`padding: 25px` + `width: 300px` = 350px rendered box — already at
    the edge at 375px; several popups use exactly this).
  - CSS grid `repeat(2, 1fr)` / `1fr` tracks: `1fr` = `minmax(auto, 1fr)`, so a child's
    min-content width (long unbroken text, fixed-width child) expands the track past the
    viewport. Fix with `minmax(0, 1fr)` and/or `min-width: 0` on grid/flex children.
  - Absolutely-positioned elements sized for desktop (drag handles, badges, close icons,
    dropdowns anchored off a wider parent) — these are the prime suspects for the **overlap**
    symptom.
  - Long unbreakable strings (habit/stopwatch/task names, quotes) — `overflow-wrap: anywhere` or
    `text-overflow: ellipsis` on the name elements.
  - Recharts/statistics: no fixed widths found in JSX (good — ResponsiveContainer), but the
    stats page only reflows at 900px; check the 375px rendering of pie/bar charts + legends.
- **Backstop, applied last:** `html, body { overflow-x: clip; }` in `index.css`. Apply *after*
  root causes are fixed so it's a safety net, not a mask — a clipped page with a too-wide element
  still looks broken (content cut off), it just doesn't pan.
- **Verification:** stopwatch page first (every card fully visible, no panning, popups open);
  then every route at 375px with no horizontal scroll (`scrollWidth === innerWidth` check per
  page), popups open included; desktop width unchanged; then a real-phone pass in Safari **and**
  the installed PWA (safe-area/notch, standalone status bar). If the installed app still shows
  the old layout after the frontend deploy, the service-worker cache
  (`frontend/public/service-worker.js`) isn't delivering the new build — flag it, but that's a
  separate fix.
- Follows the same "usable, not redesigned" bar as spec 0022 Decision 4 — this closes the gap
  that pass left, it doesn't restyle anything.
