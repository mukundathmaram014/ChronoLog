# 0002 — Backend pytest suite + GitHub Actions CI (with `create_app` factory)

## Problem / Goal
The backend has **no real tests** (`backend/src/routes/test.py` is a 2-line scratch file) and
**no CI** (`.github/workflows/` does not exist). It handles auth + per-user data and is deployed to
production manually, so a silent regression in datetime handling, user-scoping, or habit
carry-forward could quietly corrupt data with nothing to catch it. Add a focused pytest suite over
the highest-risk areas plus a minimal GitHub Actions workflow that runs it on pull requests.

Making the app testable requires a small, contained change to `app.py` (introduce a `create_app()`
factory) — see Risks. This was confirmed with the author as the chosen approach.

## Scope
- **In scope:**
  - Refactor `backend/src/app.py` into a `create_app(test_config=None)` factory, keeping
    `app = create_app()` and the `if __name__ == "__main__"` block so production is unchanged.
  - pytest suite under `backend/tests/` with shared fixtures (`conftest.py`) for an isolated app +
    throwaway DB + auth helpers.
  - Tests covering: UTC handling (`ensure_utc`, `process_date`), per-user query scoping
    (cross-user isolation), habit previous-day carry-forward logic, and auth happy-path + 401.
  - A `backend/requirements-dev.txt` adding `pytest`, and pytest config (`backend/pytest.ini`).
  - `.github/workflows/ci.yml` that installs backend deps and runs the suite on PRs.
- **Out of scope / non-goals:**
  - Any frontend tests.
  - **Fixing bugs the tests may surface** — tests assert *current* behavior; if something looks
    wrong (see Risks), note it in the PR rather than fixing it here (one task = one PR).
  - Exhaustive route coverage (stopwatch/statistics get only a scoping smoke test, not full CRUD).
  - Coverage thresholds/gates, refresh-cookie + CSRF double-submit flow testing (header-based
    `Authorization: Bearer` auth is used throughout, which sidesteps cookie/CSRF entirely).
  - Any change to deploy scripts, Dockerfile, or route behavior.

## Affected files
- `backend/src/app.py` — wrap app construction in `create_app(test_config=None)`; move the two
  module-level `@app.route` handlers (`/api/deletedday`, `/api/tokenblocklist`) and the
  `@jwt.token_in_blocklist_loader` inside the factory (they reference `app`/`jwt`). Keep
  `app = create_app()` at module bottom and the unchanged `if __name__ == "__main__": app.run(...)`.
- `backend/requirements-dev.txt` — **new**; `pytest` (prod `requirements.txt` stays slim/untouched).
- `backend/pytest.ini` — **new**; `pythonpath = src`, `testpaths = tests` so `from app import …` /
  `from db import …` resolve the same way the app does when run from `src/`.
- `backend/tests/conftest.py` — **new**; fixtures: `app` (calls `create_app` with test config),
  `client`, and an auth helper that registers + logs in a user and returns a Bearer token.
- `backend/tests/test_utils.py` — **new**; `ensure_utc` + `process_date` unit tests.
- `backend/tests/test_auth.py` — **new**; register/login happy-path + 401 cases.
- `backend/tests/test_user_scoping.py` — **new**; cross-user isolation tests.
- `backend/tests/test_habits_carryforward.py` — **new**; carry-forward + deleted-day tests.
- `.github/workflows/ci.yml` — **new**; run the suite on pull requests.

## Approach

### 1. `create_app()` factory in `app.py` (smallest change that works)
- Define `def create_app(test_config=None):` containing the existing setup: `Flask(__name__)`,
  `CORS(...)`, all `app.config[...]` lines, `jwt = JWTManager(app)`, `db.init_app(app)`, the
  `with app.app_context(): db.create_all()`, and the four `register_blueprint(...)` calls.
- **JWT secret / fail-fast:** set `app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")`,
  then `if test_config: app.config.update(test_config)`, then raise a clear error if the secret is
  still falsy. This preserves today's "don't boot prod without a secret" behavior while letting tests
  inject their own. (Do **not** keep the bare `os.environ['JWT_SECRET_KEY']` — it would crash at
  import before the test override could apply.)
- Move `get_deleted_day`, `get_token_blocklist`, and the `token_revoked`
  (`@jwt.token_in_blocklist_loader`) function inside the factory so they bind to the local
  `app`/`jwt`. Behavior identical.
- After the function: `app = create_app()` then the existing
  `if __name__ == "__main__": app.run(host="0.0.0.0", port=5000, debug=True)`. This keeps the Docker
  `CMD python3 src/app.py` and any `app:app` import working byte-for-byte.

### 2. Test config + fixtures (`conftest.py`)
- At the **top of conftest, before importing the app**, do
  `os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")` — importing `app.py` runs the
  module-level `app = create_app()` (prod path), which needs the env var present.
- `app` fixture (function-scoped) calls `create_app({...})` with:
  - `TESTING = True`
  - `SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"` with
    `SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}`
    so the in-memory DB persists across requests within the test (StaticPool from `sqlalchemy.pool`).
  - `JWT_SECRET_KEY = "test-secret-key"`, `JWT_COOKIE_SECURE = False`.
  - Each test gets a fresh app → fresh empty schema (`create_all` runs in the factory), giving full
    isolation; nothing touches the real `ChronoLog.db`.
- `client` fixture: `app.test_client()`.
- `auth_token(client, username=...)` helper: POST `/api/register` then `/api/login`, return the
  `access_token` from the body. Tests pass it as `headers={"Authorization": f"Bearer {token}"}`.

### 3. The tests (assert current behavior; follow existing conventions)
- **`test_utils.py`** — `ensure_utc(None) is None`; naive datetime → tzinfo is UTC and clock value
  unchanged; already-aware datetime returned unchanged. `process_date` with a fake request object
  (`.data = b'{"date":"2026-01-15"}'`) → `date(2026, 1, 15)`; with `{}` → `date.today()`.
- **`test_auth.py`** — register new user → 201 and body has no `password_hash`; duplicate username
  → 409; duplicate email → 409; login with correct creds → 200 with `access_token`; wrong password
  → 401; a protected route (e.g. `GET /api/habits/<int:id>/`) with no token → 401, with a valid
  token → not 401.
- **`test_user_scoping.py`** — register users A and B. A creates a habit (`POST /api/habits/`).
  Assert B: `GET /api/habits/<A_habit_id>/` → 404; `PUT` same id → 404; `DELETE` same id → 404;
  `GET /api/habits/<A_habit_date>/` does not include A's habit. Add one stopwatch smoke check:
  A creates a stopwatch, B cannot fetch/modify it. (Confirms every query is `user_id`-scoped.)
- **`test_habits_carryforward.py`** — drive `get_habits` in `routes/habits.py`:
  - Carry-forward: A creates habits on day D; `GET /api/habits/<D+1>/` returns the same descriptions
    re-created with `done = False` and date D+1.
  - Gap fill: with habits only on D, `GET /api/habits/<D+3>/` repopulates intermediate days D+1, D+2
    as well as D+3 (the inner `create_habit_for_date` loop).
  - Deleted-day marker: delete all habits on a day → a `DeletedDay` row is created → re-`GET` that
    day does **not** repopulate; and carry-forward walking backwards stops at a deleted day.
- Use `success_response`/`failure_response` status codes as the contract; parse `json.loads(resp.data)`.

### 4. CI (`.github/workflows/ci.yml`)
- Trigger: `on: pull_request` (optionally also `push` to `main`).
- Single job, `ubuntu-latest`, `actions/setup-python` pinned to **3.10** to match the production
  Docker image (`python:3.10.5`) — not the local 3.13 venv.
- Steps: checkout → setup-python → `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`
  → run `pytest` with working directory `backend` and `env: JWT_SECRET_KEY: test-secret-key`.

## Acceptance criteria
- [ ] `cd backend && pip install -r requirements.txt -r requirements-dev.txt && pytest` runs and
      **all tests pass** locally.
- [ ] `python src/app.py` still boots the server, and `docker-compose up --build` still serves the
      backend (production path unchanged).
- [ ] Tests never read or write the real `backend/src/instance/ChronoLog.db` (each test uses an
      isolated in-memory DB).
- [ ] The suite includes at least: `ensure_utc`/`process_date` unit tests; register/login + 401
      auth tests; cross-user isolation tests for habits (+ a stopwatch smoke test); and carry-forward
      + deleted-day tests for `get_habits`.
- [ ] `.github/workflows/ci.yml` runs the suite on pull requests and is green on this PR.
- [ ] No production route behavior changed; any suspected bug found is **noted in the PR**, not fixed.

## Testing / verification
1. Local: `cd backend && pip install -r requirements.txt -r requirements-dev.txt && pytest -v` → green.
2. Sanity that prod is intact: `cd backend/src && python app.py` boots on :5000; optionally
   `docker-compose up --build` serves the API.
3. Push the branch, open the PR, and confirm the **CI** check runs and passes on GitHub.

## Risks & notes
- **`app.py` edit touches the production entrypoint.** Mitigated by keeping `app = create_app()` and
  the `__main__` block, so `CMD python3 src/app.py` and any `app:app` import are byte-for-byte
  equivalent. Verify locally (step 2) before merge.
- **Importing `app.py` still builds the prod app** (`app = create_app()` runs `create_all` against
  `ChronoLog.db`). `create_all` is idempotent and non-destructive, but it means importing the module
  touches the real DB file. conftest sets a dummy `JWT_SECRET_KEY` so import succeeds; CI runs on a
  clean checkout so it just creates an empty ephemeral file. Acceptable; noted for transparency.
- **In-memory SQLite needs `StaticPool`** or the per-request connections each get a separate empty
  DB and tests fail confusingly. (Temp-file SQLite via `tmp_path` is a fallback if StaticPool is
  awkward.)
- **Old dependency pins** (Flask 2.2.2 / SQLAlchemy 1.4.42) on the CI Python: pinning CI to 3.10
  matches the prod image and avoids surprises. If `pip install` ever fails, that's the first knob.
- **Tests may surface latent bugs** — e.g. `update_habit` does `habit.date = body.get("date", habit.date)`
  storing a raw string rather than a parsed `date`; carry-forward has nontrivial date-walking. Per
  the working agreement, the tests should pin *current* behavior and the PR should **flag** anything
  that looks wrong rather than fixing it in this PR.
