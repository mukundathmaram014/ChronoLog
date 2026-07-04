# 0001 — Fix incorrect frontend path in README

## Problem / Goal
The README documents the frontend as living at `frontend/productivityapp/`, but the real
directory is `frontend/` (with `package.json` and `src/` directly inside). The phantom
`productivityapp` level misleads anyone following the setup steps. Make the README match reality.

## Scope
- In scope: correct the two `productivityapp` references in `README.md`.
- Out of scope / non-goals: no restructuring, no renaming the actual directory, no other README
  edits (the npm package `name` in `package.json` is legitimately `productivityapp` and stays).

## Affected files
- `README.md` — Project Structure tree (lines ~51–56) and the frontend "Running Locally" step (line ~93).

## Approach
1. In the Project Structure tree, collapse the `frontend/productivityapp/` level so `package.json`
   and `src/` sit directly under `frontend/`:
   ```
   ├── frontend/
   │   ├── package.json
   │   └── src/
   │       ├── App.js
   │       └── ... (components, pages, hooks)
   ```
2. In "Running Locally → Frontend", change `Navigate to `frontend/productivityapp`.` to
   `Navigate to `frontend`.`

## Acceptance criteria
- `grep -n productivityapp README.md` returns no matches.
- The Project Structure tree shows `frontend/` containing `package.json` and `src/` directly.
- The frontend run instructions tell the reader to `cd frontend`.

## Testing / verification
- Run `grep -n productivityapp README.md` → expect no output.
- Eyeball the rendered tree to confirm it's still well-formed.

## Risks & notes
- Trivial docs-only change; no code or runtime impact. Good first end-to-end test of the
  /spec → /build → PR loop.
