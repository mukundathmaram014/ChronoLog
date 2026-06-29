# 0004 — Lock the Total stopwatch out of drag-reordering

## Problem / Goal
The Total stopwatch is part of the sortable list, so reordering can move it / shuffle it among the
regular stopwatches. It should stay fixed (rendered first) and never be draggable.

## Scope
- In scope: exclude the Total stopwatch from the DnD sortable list and pin it in place.
- Out of scope / non-goals: no change to how elapsed/total time is computed; no backend change.

## Affected files
- `frontend/src/Pages/stopwatchpage.jsx` — render the Total outside the `SortableContext`; only map
  non-Total stopwatches into the sortable list; guard `handleDragEnd`.
- `frontend/src/Components/SortableStopwatchItem.jsx` — only used for non-Total items after this; no
  drag wiring for the Total.

## Approach
1. In `stopwatchpage.jsx`, split `allStopwatches` into the Total (`isTotal === true`) and the rest.
   Render the Total once at the top using the plain `StopwatchItem` (its `isTotal` branch already
   has no drag handle — `StopwatchItem.jsx:7-15`).
2. Build `SortableContext items={...}` and the `.map(...)` from the **non-Total** stopwatches only,
   so `useSortable` is never created for the Total.
3. In `handleDragEnd`, keep the `arrayMove` over the non-Total array (the Total is no longer in it),
   so it can never be displaced.
4. Keep this consistent with spec 0003's reorder payload (Total id is never included).

## Acceptance criteria
- The Total stopwatch cannot be picked up or dragged.
- Dragging any regular stopwatch never moves or reorders the Total; the Total stays at the top.
- Regular stopwatches still reorder normally.

## Testing / verification
- Stopwatches page: try to drag the Total (should not move); drag regular stopwatches around and
  confirm the Total stays put.

## Risks & notes
- Small, frontend-only. Best done together with **0003** since both touch the sortable list and the
  Total's placement.
