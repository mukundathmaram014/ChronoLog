# 0021 — Task / to-do subsystem

## Problem / Goal
Add a to-do / assignment tracker alongside habits and stopwatches: create tasks (for today or any future
day), see what's due, tick them off, break them into **sub-tasks**, and let some tasks **repeat
automatically**. Undone tasks **roll forward** and stay visible until done. It lives on its own **Tasks
page** with a small **homepage card**.

Scope now includes (expanded from the original MVP): **sub-tasks** and **periodic / auto-recreating
tasks**. **Parked in `specs/ideas.md` for a later spec:** a task dependency graph + tree visualization
and scheduling algorithms (EDF etc.).

## Design decisions (locked)
1. **Overdue roll-forward.** An incomplete task with `date <= today` stays visible as **overdue** until
   completed or deleted (it keeps its original `date`; the "due" view always surfaces it).
2. **Dedicated Tasks page** showing **Overdue / Today / Upcoming**, grouped by date (a nav tab + route).
3. **Homepage Tasks card** — a small card (today + overdue) alongside the habits/stopwatch cards.
4. **Core fields:** `description`, target `date`, `done`, `user_id` — plus the sub-task and recurrence
   fields below.
5. **Future-dating:** the add-task form has a date picker, so a task can be created for any future day.

## Sub-tasks
- A task may have **sub-tasks** (one level of nesting for v1). Model this as a self-referential
  `parent_id` (FK to `tasks.id`, nullable): top-level tasks have `parent_id = NULL`; a sub-task points to
  its parent. A sub-task carries the same fields (its own `done`; it can share/inherit the parent's `date`).
- **Completion:** sub-tasks are checked independently; the parent shows progress (e.g. "2/3 done").
  *Confirm at build:* whether completing all sub-tasks auto-completes the parent (recommended: **yes**,
  auto-complete when every sub-task is done; the parent can still be toggled manually).
- **UI:** on the Tasks page, a task row expands to show its sub-tasks with an "add sub-task" control.
- Deleting a parent deletes its sub-tasks (cascade).

## Periodic / auto-recreating tasks
- A task may be **periodic**: a `recurrence` field on the top-level task — `none` (default) / `daily` /
  `weekly` / `monthly` for v1. *Confirm at build:* whether `weekly` should pick specific weekdays (like
  spec 0014's bitmask) or just "+7 days".
- **Auto-recreation (spawn-on-complete):** completing a periodic instance **spawns the next occurrence** —
  a fresh, undone `Task` dated at the next date per `recurrence`, carrying the same `description`,
  `recurrence`, and a fresh copy of its sub-task template. (Alternative considered: pre-generate the next
  instance when the due date passes — rejected as it litters future rows; spawn-on-complete is simpler.)
- A missed periodic instance stays **overdue** (roll-forward) until done, then spawns the next occurrence.
- *Confirm at build:* editing a periodic task affects **future occurrences only** (recommended) vs. all
  instances.

## Context — how this fits the codebase
- Tasks mirror **habits** (`backend/src/db.py:27-59`, `backend/src/routes/habits.py`): a per-user item
  with `description` / `done` / `date`, ticked off in a list. Follow that CRUD shape + conventions.
- **Unlike habits**, tasks don't use the day-by-day carry-forward / `DeletedDay` machinery. Roll-forward
  is just "show undone tasks with `date <= today`"; recurrence is the spawn-on-complete chain above —
  keep both **separate** from the habit carry-forward system.
- Backend: a new blueprint under `/api` (`app.py:63-66`), `@jwt_required()` + `int(get_jwt_identity())`,
  `user_id`-scoped, `success_response`/`failure_response`, bodies via `json.loads(request.data)`.
- Frontend: a new page under `RequireAuth` + `Layout` (`App.js:22-28`), a Navbar link
  (`Navbar.jsx:39-47`), all calls via `useFetch`.

## Affected files
- `backend/src/db.py` — new **`Task`** model: `id`, `description` (String), `done` (Boolean), `date`
  (Date), `user_id` (FK), `parent_id` (FK `tasks.id`, nullable — sub-tasks), `recurrence` (String enum,
  default `none`). `__init__` + `serialize`. **New table** — `create_all` auto-creates it, no migration.
- `backend/src/routes/tasks.py` — **new** blueprint `task_routes`: list (Overdue/Today/Upcoming, sub-tasks
  nested under parents), create (optional `parent_id`, `recurrence`, future `date`), get-one, update
  (toggle done / edit / reschedule / change recurrence), delete (cascade sub-tasks). On completing a
  periodic top-level task, **spawn the next occurrence**. All `@jwt_required()`, `user_id`-scoped.
- `backend/src/app.py` — register `task_routes` under `/api`.
- `frontend/src/Pages/taskpage.jsx` + `taskpage.css` — **new** page: add-task form (date picker,
  recurrence selector, optional parent), grouped Overdue/Today/Upcoming list with expandable sub-tasks,
  add-sub-task, complete/edit/delete.
- `frontend/src/App.js` — protected `/taskpage` route; `frontend/src/Components/Navbar.jsx` — "Tasks" link.
- `frontend/src/Pages/homepage.jsx` — a small **Tasks card** (today + overdue); optionally a `TaskItem`
  component mirroring `HabitItem`.

## Approach
1. Add the `Task` model (self-referential `parent_id`, `recurrence`); `create_all` auto-creates the table.
2. Build `tasks.py` CRUD (habits conventions): the list endpoint returns Overdue/Today/Upcoming with
   sub-tasks nested under parents; create accepts `parent_id`, `recurrence`, and a future `date`.
3. **Sub-tasks:** parent shows progress; (recommended) auto-complete a parent when all its sub-tasks are
   done; delete cascades to sub-tasks.
4. **Periodic:** on completing a periodic top-level task, spawn the next occurrence (fresh, undone, next
   date, fresh sub-task copies).
5. Register the blueprint; verify `user_id` scoping everywhere.
6. Frontend: Tasks page + nav link + route; add/edit form with date + recurrence + sub-tasks; homepage card.

## Acceptance criteria
- Create a task for today or any future date; it persists and is `user_id`-scoped.
- Undone tasks past their date stay visible as **overdue** until done/deleted.
- A task can have **sub-tasks**; they toggle independently, the parent shows progress, and (recommended)
  completing all sub-tasks completes the parent; deleting a parent removes its sub-tasks.
- A **periodic** task auto-creates its next occurrence on completion per its `recurrence`; a missed one
  stays overdue, then spawns the next when done.
- The Tasks page shows Overdue/Today/Upcoming; the homepage shows a small Tasks card.
- No cross-user leakage; no entanglement with the habit/stopwatch carry-forward logic.

## Testing / verification
- Create tasks dated today / tomorrow / next week; confirm grouping + persistence across reload.
- Leave a task undone past its date → it shows as overdue.
- Add sub-tasks; toggle them; confirm parent progress + auto-complete; delete parent → sub-tasks gone.
- Complete a daily/weekly periodic task → the next occurrence appears at the right date, undone; miss one
  → overdue, then it spawns on completion.
- Confirm a second user can't see the first's tasks.

## Risk
- **Involvement:** Involved (larger than the original MVP) — a new pillar **plus** two non-trivial
  behaviors: self-referential sub-tasks (nested list, cascade delete, parent progress/auto-complete) and
  periodic spawn-on-complete recurrence, on top of the CRUD + page + nav + homepage card.
- **Review attention:** High — still additive/isolated (a brand-new table, no migration, no carry-forward
  entanglement), so low regression risk, but there's a lot of new surface **and** two behaviors with real
  edge cases (recurrence spawning, sub-task cascade/auto-complete, overdue interplay). Consider building in
  stages within the PR — CRUD + roll-forward, then sub-tasks, then periodic — and reviewing each stage.

## Risks & notes
- **No migration:** `Task` is a brand-new table (`create_all` makes it); `parent_id` / `recurrence` ship
  with it — no `ALTER TABLE`.
- Keep tasks **separate** from habit carry-forward / `DeletedDay` — roll-forward and recurrence are
  task-local (a `date <= today` filter + a spawn-on-complete chain), not the habit backfill machinery.
- **Recurrence + sub-tasks interaction:** spawning the next occurrence copies the sub-task template fresh
  (all undone). Confirm this and the "edit affects future occurrences only" rule at build time.
- New app pillar — mention it in the PR and add a README feature-list line once shipped.
- The dependency graph + tree visualization and scheduling algorithms (EDF etc.) are parked in
  `specs/ideas.md` for a future spec.
