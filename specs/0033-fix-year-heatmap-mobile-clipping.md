---
title: Fix year heatmap clipping earlier months on phone viewports
status: decided
---

# Fix year heatmap clipping earlier months on phone viewports

## Summary
On a phone, the year heatmap loses its leading months — they are simply gone, with no way to
reach them. The cause is not just that ~53 week-columns are wider than a phone; it is that the
heatmap's intended horizontal scroll **never engages**, and the overflow is centered.

Chain of causes:

1. `.cal-year-wrap` (`HabitCalendar.jsx`) has no width constraint and is a flex item of
   `.habit-calendar`, which is `display: flex; align-items: center`. So the wrap shrink-to-fits to
   its own ~800px max-content width. The `overflow-x: auto` declared on `.cal-year`
   (`HabitCalendar.css`) is therefore dead code — a scroll container sized by its own content never
   scrolls.
2. Because the wrap is *centered* inside a narrower card, the overflow spills equally left and
   right. `.per-habit-calendar-card` is `overflow-x: auto`, so the right-hand overflow is
   reachable by scrolling — but `scrollLeft` cannot go negative, so the left-hand overflow (the
   earliest months) is permanently unreachable. That is the reported symptom exactly.
3. The combined all-habits year heatmap has no scrolling ancestor at all, so there both ends are
   silently chopped by the global `overflow-x: clip` on `html, body` (spec 0024, `index.css`).

The fix keeps the heatmap legible and makes the scroll real:

- **Move the scroll container up to `.cal-year-wrap`** and give it `max-width: 100%; min-width: 0`.
  Scrolling the wrap moves the month-label row and the grid together, so labels can never drift out
  of alignment with the columns they annotate. Remove the now-dead `overflow-x` from `.cal-year`.
- **Stop centering it**: `align-self: stretch` on the wrap, and no `justify-content: center` on the
  inner grid. Content wider than a scroll container must be left-aligned — any centering
  re-creates the unreachable-left-overflow bug. Consequence: when the year *does* fit (desktop),
  the heatmap sits left-aligned in its card rather than centered. This is intended, and matches
  GitHub's own contribution graph.
- **Shrink modestly on phones**: under 600px, set `--cal-year-col: 9px` and `--cal-year-gap: 2px`
  on `.habit-calendar`. Both the grid and the month-label row already derive their track sizing
  from these vars, so they stay in lockstep. ~53 columns then span ~580px rather than ~800px —
  about 1.5 phone screens of scroll instead of 2+. Shrinking far enough to fit a 375px viewport
  would mean ~4px cells, which is unreadable, so scroll stays part of the answer.
- **Start scrolled to the most recent weeks** (right end), the useful end of the range and the
  behaviour GitHub uses on mobile. The month labels orient the user, and swiping toward older
  months is the natural gesture. On desktop, where the content fits, setting `scrollLeft` is a
  no-op.

Applies to every year-period heatmap, since they all render through the same component: the
combined all-habits view, the per-habit grid, and the stopwatch time heatmap.

CSS-plus-one-small-component-extraction; frontend only, no backend changes, no behaviour change to
the month/week/day layouts.

## Affected files
- `frontend/src/Components/HabitCalendar.css` — move `overflow-x: auto` from `.cal-year` to
  `.cal-year-wrap`; add `max-width: 100%`, `min-width: 0`, `align-self: stretch`,
  `overscroll-behavior-x: contain` to the wrap; add a `@media (max-width: 600px)` block overriding
  `--cal-year-col` / `--cal-year-gap` on `.habit-calendar`.
- `frontend/src/Components/HabitCalendar.jsx` — extract the `period === "year"` branch into a
  small `YearHeatmap` subcomponent in the same file, which owns a ref on `.cal-year-wrap` and a
  layout effect that scrolls it to the right end.
- `frontend/src/Pages/statisticspage.css` — verify/clean up `.per-habit-calendar-card`'s
  `overflow-x: auto` once the wrap scrolls itself (it becomes redundant; leaving it is harmless,
  but it should not double as the scroll container). `.per-habit-calendar-grid-year` (one card per
  row at year period) stays as is.

No test files: the repo has backend tests only, and this is presentation-layer CSS.

## Decisions needed
_None._

- Scroll vs. shrink-to-fit → **both, weighted to scroll**: 12px cells on desktop, 9px under 600px,
  horizontal scroll for the remainder.
- Initial scroll position → **right end (most recent)**.
- Scope → **all year heatmaps**, since they share one component.
- Synchronising scroll across the stacked per-habit cards → **out of scope**. Every card renders
  the same date range and starts at the same end position, so they agree on load; lifting scroll
  state across N sibling cards is a larger change than this bug warrants.
- Edge fade / "more to the left" affordance → **out of scope**. The month-label row already shows
  a mid-year label at the left edge when scrolled, which reads as "the range continues".

## Risk
- **Involvement:** Minimal — a handful of CSS declarations plus extracting an existing JSX branch
  into a subcomponent in the same file. No API, data, or state changes.
- **Review attention:** Medium — the centering/overflow interaction is the whole bug, so it is
  worth confirming on a real device that (a) the earliest month is reachable, (b) the month labels
  still sit over their own columns at both cell sizes, and (c) the desktop layout only changes by
  becoming left-aligned.

## Implementation notes
- **Hook order.** `HabitCalendar` early-returns for empty `days` *before* any hook runs, so a
  `useRef`/`useLayoutEffect` cannot be added to the top-level component without a conditional-hook
  violation. Hence the `YearHeatmap` extraction — it is only rendered on the year branch, and owns
  its own hooks cleanly.
- **Scroll-to-end effect.** `useLayoutEffect` (not `useEffect`) so the initial position is set
  before paint and the user never sees it jump. Set `el.scrollLeft = el.scrollWidth`; the browser
  clamps to the maximum, so no measurement math is needed. Re-run when `days` changes (period or
  date switches re-render with a new array). Do not set `scroll-behavior: smooth` on the wrap, or
  the initial positioning animates on every load.
- **Sizing the scroll content.** Give `.cal-month-labels` and `.cal-grid.cal-year` `width:
  max-content` inside the wrap. As stretch-aligned flex children they would otherwise be pinned to
  the container width and rely on implicit grid tracks spilling out; `max-content` makes both rows
  size to their real content and stay exactly the same width as each other.
- `overflow-x: auto` computes `overflow-y` to `auto`, but there is no vertical overflow here, so no
  vertical scrollbar appears. `.cal-month-label` keeps `overflow: visible` and may extend slightly
  past the last column into the scrollable area — harmless.
- Verify on a real phone **and** in the installed PWA (standalone mode), per spec 0024's
  verification convention — not DevTools alone.
