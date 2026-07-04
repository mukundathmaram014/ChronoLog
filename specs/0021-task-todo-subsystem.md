# 0021 — Task / to-do subsystem (MVP)

## Problem / Goal
Add a lightweight to-do/assignment tracker alongside habits and stopwatches: create tasks, create them
for future days, quickly see what's due, and tick them off. This is the **minimal** first slice of the
larger "assignment tracker" idea — deliberately scoped to add / future-date / access / complete.

**Explicitly deferred to later specs (NOT in this one):** sub-tasks/sub-todos, dependency graph +
tree visualization, scheduling algorithms (EDF etc.), and periodic/auto-recreating tasks. This spec
builds the foundation those would layer onto.

## Context — how this fits the codebase
- Tasks are close cousins of **habits** (`backend/src/db.py:27-59`, `backend/src/routes/habits.py`): a
  per-user item with a `description`, a `done` flag, a `date`, ticked off in a list. Mirror that CRUD
  shape and conventions.
- **Key difference from habits:** habits auto **carry forward** every day (with `DeletedDay` markers and
  backfill — `habits.py:44-78`). Tasks do **not** carry forward that way — a task is created for one
  target day. So the model is *simpler* than Habit: **no carry-forward, no DeletedDay machinery.**
- Backend wiring pattern: a new blueprint registered under `/api` in `backend/src/app.py:63-66`,
  `@jwt_required()` + `int(get_jwt_identity())`, all queries scoped by `user_id`,
  `success_response`/`failure_response`, bodies via `json.loads(request.data)`.
- Frontend wiring pattern: a new page under the protected `RequireAuth` + `Layout` routes
  (`frontend/src/App.js:22-28`), a Navbar link (`frontend/src/Components/Navbar.jsx:39-47`), all calls
  through `useFetch`.

## ⚠️ Decisions needed
1. **What happens to an incomplete task after its day passes?** (biggest design call)
   - **(Recommended) Roll forward / stay visible as "overdue"** until completed or deleted — an
     unfinished task shouldn't disappear into a past day you never look at. Implement by surfacing
     undone tasks with `date <= today` in the "due" view (the task keeps its original `date`; it's just
     always shown until done).
   - Alternative: **pinned to its assigned date** — a task only appears on its day (simplest, but a
     forgotten task is easy to lose).
2. **How you view / "quickly access" tasks.**
   - **(Recommended) A dedicated Tasks page** showing **Overdue + Today + Upcoming**, grouped by date,
     so future-dated tasks are all visible in one place (best matches "add for future days, quickly
     access them").
   - Alternative: **per-day date slider** exactly like habits/stopwatches (consistent with the rest of
     the app, but you'd slide day-by-day to find future tasks).
3. **Homepage card?** Habits and stopwatches each have a homepage card. Recommended: add a small "Tasks"
   card (today + overdue) — optional, could be a fast follow-up. Confirm in or out of this spec.
4. **Fields.** Recommended MVP: `title/description`, target `date`, `done`, `user_id` — nothing else
   (no priority/notes/sub-tasks yet). Confirm.

## Affected files
- `backend/src/db.py` — new `Task` model: `id`, `description` (String), `done` (Boolean), `date`
  (Date, the target day), `user_id` (FK). `__init__` + `serialize`, mirroring `Habit`.
- `backend/src/routes/tasks.py` — **new** blueprint `task_routes`: list, create, get-one, update
  (toggle done / edit / reschedule date), delete — all `@jwt_required()`, `user_id`-scoped,
  `success_response`/`failure_response`. List shape follows Decision 2 (e.g. `GET /tasks/` returns
  overdue+today+upcoming, or `GET /tasks/<date>/` per day).
- `backend/src/app.py` — register `task_routes` under `/api` (`app.py:63-66`).
- `frontend/src/Pages/taskpage.jsx` + `taskpage.css` — **new** page: add-task form (with a date picker
  for future days), grouped/day list, checkbox to complete, edit/delete.
- `frontend/src/App.js` — add the protected route (`/taskpage`) under `RequireAuth` + `Layout`.
- `frontend/src/Components/Navbar.jsx` — add a "Tasks" nav link.
- (Maybe, Decision 3) `frontend/src/Pages/homepage.jsx` — a Tasks card; and a `TaskItem` component
  mirroring `HabitItem` if it keeps the page tidy.

## Approach
1. Add the `Task` model (mirror `Habit`, minus carry-forward). `db.create_all()` **auto-creates the new
   table** on startup — see Risks (no manual migration needed for a brand-new table).
2. Build `tasks.py` CRUD following the habits route conventions; the list endpoint returns tasks per the
   chosen view model (Decision 2) with the overdue rule (Decision 1).
3. Register the blueprint; verify all routes are `user_id`-scoped.
4. Frontend: new Tasks page + nav link + route; add-task form with a date field for future days; a list
   grouped by day (Overdue / Today / Upcoming) with checkbox-to-complete and edit/delete via `useFetch`.
5. (Optional) homepage Tasks card.

## Acceptance criteria
- Can create a task for today or any future date; it persists and is scoped to the user.
- Tasks are quickly viewable (per Decision 2), with future-dated ones visible ahead of time.
- Can tick a task complete/incomplete, edit its text/date, and delete it.
- (Per Decision 1) an incomplete past task is still surfaced (recommended) or pinned to its day.
- No cross-user leakage; no interaction with the habit/stopwatch carry-forward logic.

## Testing / verification
- Create tasks dated today, tomorrow, and next week; confirm they appear correctly and persist across
  reload.
- Complete/uncomplete and delete a task; edit a task's date and confirm it moves.
- Leave a task undone past its date and confirm the chosen overdue behavior.
- Confirm a second user can't see the first user's tasks.

## Risk
- **Involvement:** Involved — a whole new pillar: new model, a full CRUD blueprint, a page + route + nav link (and maybe a homepage card).
- **Review attention:** High — but this is *volume, not danger*: it's additive and isolated (new table auto-created, no carry-forward entanglement, mirrors habits), so there's a lot to review yet low regression risk; confirm the overdue/view decisions.

## Risks & notes
- **No migration headache here:** unlike the column-adding specs (0012–0014, 0019, 0020), this adds a
  **new table**, which `db.create_all()` creates automatically on boot — no `ALTER TABLE` needed.
- Keep tasks fully separate from the habit carry-forward / `DeletedDay` system — don't entangle them.
- Resist scope creep: this MVP is add / future-date / access / complete. Sub-todos, dependencies,
  scheduling, and periodic tasks are separate follow-up specs by design.
- This is a new app pillar (new nav entry + page); mention it in the PR and, once shipped, it's worth a
  line in the README feature list.
