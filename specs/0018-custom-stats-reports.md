# 0018 — Custom statistics reports

## Problem / Goal
Generate a **report** of statistics for a chosen period (week, month, etc.) — a consolidated summary of
habit completion and time worked the author can review (and possibly export).

## Context
- Stats today are live, on-screen, one selection at a time (`statisticspage.jsx`,
  `backend/src/routes/statistics.py`). There's no notion of a saved/exported/consolidated report.
- 0016 (individual + total together) and 0017 (period-driven items) produce most of the underlying data
  a report would summarize — this spec is best sequenced **after** those.

## ⚠️ Decision needed — define "report" before building (scope grows otherwise)
1. **Contents.** Recommended starting set: for a chosen period — habit completion (totals + %), time
   worked (total + average/day + per-stopwatch breakdown), and the top/most-consistent items. Confirm
   the exact fields.
2. **Format / delivery.** Pick one:
   - **(Recommended) On-page report view** — a formatted summary rendered in the app (lowest cost,
     reuses existing data).
   - **Downloadable** — CSV (easy) or PDF (heavier, likely a new lib). 
3. **Generation trigger.** On-demand for a selected period (recommended) vs saved/scheduled reports
   (much larger — defer).

## Affected files
- `backend/src/routes/statistics.py` — (likely) a report endpoint assembling the chosen fields for a
  period in one response, scoped by `user_id`, reusing existing aggregation (and 0016/0017 data).
- `frontend/src/Pages/statisticspage.jsx` (or a new report view/component) — request and render the
  report; export control if Decision 2 includes download.
- (If PDF/CSV export) `frontend/package.json` and/or a backend export helper.

## Approach
1. Lock the report definition (Decisions 1–3) — keep v1 minimal.
2. Backend: assemble the report payload for the period.
3. Frontend: a "generate report" action that renders (and optionally exports) it.

## Acceptance criteria
- Selecting a period and generating a report yields the agreed fields, correct for that period.
- (If export chosen) the report downloads in the chosen format.
- No regression to the live stats views.

## Testing / verification
- Generate reports for a week and a month with known data; verify totals/percentages/breakdowns match
  the live stats.
- (If export) open the exported file and confirm contents.

## Risks & notes
- **Scope risk:** "custom reports" is open-ended (medium–large). Ship a minimal, well-defined v1 and
  layer extras later — don't let it sprawl.
- Best built after **0016** and **0017**, whose data it consumes. Sequence accordingly in build planning.
