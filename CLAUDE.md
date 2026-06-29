# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What ChronoLog is

A personal productivity tracker (habits + time tracking + stats) the author uses daily,
deployed at https://chronologtracker.com. Flask REST API backend + React 19 SPA frontend.

## Layout (note: the README's `frontend/productivityapp/src` path is outdated)

```
backend/src/
  app.py              # Flask app: CORS, JWT config, blueprint registration, blocklist loader
  db.py               # SQLAlchemy models: User, Habit, Stopwatch, DeletedDay, TokenBlocklist
  utils.py            # success_response / failure_response / process_date / ensure_utc
  routes/
    users.py          # register, login, refresh, logout (JWT + cookie auth)
    habits.py         # habit CRUD + previous-day carry-forward logic
    stopwatch.py      # stopwatch CRUD + start/stop/reset
    statistics.py     # analytics over habits + stopwatch time
  instance/ChronoLog.db   # SQLite database (gitignored data)
frontend/src/
  Pages/              # homepage, loginpage, signuppage, habitpage, stopwatchpage, statisticspage (.jsx + .css)
  Components/         # Navbar, HabitItem, StopwatchItem, Sortable* (DnD), RequireAuth
  context/AuthProvider.js, hooks/useAuth.js, hooks/useFetch.js
docs/                 # architecture, authentication, deployment, implementation_details
docker-compose.yml    # backend container
specs/                # implementation specs (see specs/README.md)
```

## Conventions — match these, don't introduce new patterns

### Backend
- Every route is a Flask blueprint registered under `/api` in `app.py`.
- Return values use `success_response(data, code)` / `failure_response(message, code)` from `utils.py`
  (these `json.dumps` + return a `(body, code)` tuple). Do not return raw Flask responses unless
  setting cookies (see `users.py`).
- Protected routes use `@jwt_required()` and read the user via `int(get_jwt_identity())`.
  **Always scope queries by `user_id`** — every model is per-user.
- Datetimes are stored and compared in **UTC**. Wrap any datetime read from the DB with
  `ensure_utc(...)` before math or serialization (SQLite drops tzinfo). See `docs/architecture.md`.
- Read request bodies with `json.loads(request.data)` and `.get("field", default)`.

### Frontend
- React 19, react-router-dom 7, Create React App (`react-scripts`). No TypeScript.
- All authenticated API calls go through the `useFetch` hook, which injects the bearer token and
  transparently retries once on 401 via the refresh-cookie flow. Use it; don't call `fetch` directly.
- Base API path is `/api` (proxied/served per environment).
- Stopwatch elapsed time is computed on the fly in the frontend from `interval_start` + `curr_duration`;
  the backend keeps `curr_duration` static and only updates it on stop. Don't move this calc to the backend.

## Running locally
- Backend: `cd backend/src && pip install -r ../requirements.txt && python app.py` (port 5000).
  Requires `backend/.env` with `JWT_SECRET_KEY="..."`.
- Frontend: `cd frontend && npm install && npm start` (port 3000).
- Full stack: `docker-compose up --build`.

## Working agreement (AI-assisted workflow)
- **No large refactors.** Implement the smallest change that satisfies the spec. If a task seems to
  require broad restructuring, stop and flag it rather than doing it.
- One task = one branch = one PR. Keep diffs small and reviewable.
- Follow the spec in `specs/` for the task; if reality diverges from the spec, note it in the PR.
- `main` is the deployed/stable branch. Never commit directly to it — always branch.
