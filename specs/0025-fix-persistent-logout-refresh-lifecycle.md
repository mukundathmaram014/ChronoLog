---
title: Fix users getting persistently logged out (refresh-cookie lifetime + refresh failure handling)
status: decided
---

# Fix users getting persistently logged out (refresh-cookie lifetime + refresh failure handling)

## Summary
Users are logged out far more often than the intended 30-day session. Three
token-lifecycle defects compound, spanning the backend cookie config and the
frontend refresh flow:

1. **Refresh cookies are browser session cookies.** `create_app()` in
   `backend/src/app.py` sets `JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)`
   but never sets `JWT_SESSION_COOKIE`, which defaults to `True` in
   flask-jwt-extended. So `set_refresh_cookies(...)` (login/guest in
   `backend/src/routes/users.py`) writes the `refresh_token_cookie` *and* the
   `csrf_refresh_token` cookie with no `Max-Age`/`Expires`. Closing the browser
   (or a mobile OS evicting the tab) deletes both, and the next visit's
   `/api/refresh` in `AuthProvider` gets a 401 → login page. This is the main
   "persistently logged out" cause: the 30-day refresh token effectively lives
   only as long as the browser process.
2. **No sliding session.** `/refresh` only mints a new access token; the
   refresh cookie itself is never re-issued. Even a daily-active user is
   hard-logged-out exactly 30 days after their last login. **Decided: adopt
   refresh-token rotation** — every successful `/refresh` also mints and sets
   a new 30-day refresh cookie, so any visit resets the clock; only 30+ days
   of inactivity logs the user out. The old refresh token is *not* revoked on
   rotation (revoking would break concurrent tabs/devices racing to refresh);
   logout continues to revoke via the `refresh_jti` claim. Guests get the
   same behavior — the server-side 7-day guest purge caps their lifetime
   regardless.
3. **Frontend treats any refresh hiccup as an expired session.** In
   `frontend/src/hooks/useFetch.js`, `refreshToken()`'s catch block runs
   `setAuth({})` + redirect-to-login on *any* error — a network blip, a 5xx
   during a backend redeploy, etc. Worse, a non-200/non-401 status (e.g. 500)
   falls through to `response.json()` and writes `access_token: undefined`
   into auth state. Only a 401/422 from `/api/refresh` actually means the
   session is dead. There is also no dedup of concurrent refreshes: N parallel
   401s fire N `/refresh` calls (harmless today, but a correctness requirement
   if rotation from item 2 is adopted).

## Affected files
- `backend/src/app.py` — set `JWT_SESSION_COOKIE = False` so refresh/CSRF
  cookies persist with the refresh token's 30-day expiry.
- `backend/src/routes/users.py` — `/refresh` mints a new refresh token and
  calls `set_refresh_cookies` on a `make_response(...)` (same pattern as
  `login`), embedding the new `refresh_jti`/`refresh_exp` claims in the new
  access token exactly as `login`/`guest` do. The old refresh token is not
  revoked (see Implementation notes).
- `frontend/src/hooks/useFetch.js` — only clear auth + redirect on 401/422
  from `/refresh`; on other failures return null and let the caller surface
  the original 401 without destroying the session; dedupe concurrent
  refreshes via a module-scope in-flight promise (the hook body re-runs per
  component, so the shared state cannot live inside the hook).
- `frontend/src/context/AuthProvider.js` — on mount, distinguish 401/422
  ("not logged in" → login page as today) from transient failures (network
  error, 5xx): on a transient failure, retry the `/api/refresh` once after a
  short delay (~2s); if the retry also fails, fall through to the login page.
  No new UI surface — the existing loading state covers the retry window.
- `backend/tests/test_auth.py` — tests: refresh cookie carries `Max-Age`
  (~30d) after login; `/refresh` succeeds with cookie + CSRF header;
  `/refresh` sets a new refresh cookie (rotation) and the old refresh token
  still works until its own expiry; logout after a refresh revokes the
  *current* (rotated) refresh token.

## Decisions needed
_None — all resolved:_
- **Sliding session via rotation: yes.** Security posture changes from "hard
  30-day max" to "sliding 30-day inactivity window", accepted for this app.
  Old tokens are not revoked on rotation; logout still revokes via the
  `refresh_jti` claim carried in the access token.
- **Mount-time transient refresh failure: one silent retry** after a short
  delay, then fall back to the login page (no new error UI).
- **Guests slide too** — same code path; the 7-day server-side guest purge
  bounds their lifetime independently.

## Risk
- **Involvement:** Moderate — four small, targeted edits across backend config,
  one route, and two frontend auth files; no schema or data migration.
- **Review attention:** High — this is the auth path for every user in prod;
  a mistake here locks everyone out or silently extends sessions. Cookie
  attribute changes are also easy to get wrong per-environment (Secure/SameSite
  interact with the Netlify `/api` proxy) and hard to test locally.

## Implementation notes
- `JWT_SESSION_COOKIE = False` makes flask-jwt-extended derive cookie
  `Max-Age` from `JWT_REFRESH_TOKEN_EXPIRES`; add it next to the other JWT
  config in `create_app()` (backend/src/app.py:126-133). Verify both
  `refresh_token_cookie` and `csrf_refresh_token` get the max-age in the test
  client (`resp.headers.getlist("Set-Cookie")`).
- `/refresh` currently returns a `success_response` tuple; setting cookies
  requires `make_response(success_response(...))` — CLAUDE.md explicitly
  allows raw responses when setting cookies, and `login` at
  backend/src/routes/users.py:91-93 is the pattern to copy. Keep returning
  `access_token`, `username`, `email`, `is_guest` in the body — the frontend
  (`AuthProvider`) reads all four.
- Rotation: the new access token must carry the *new* refresh token's
  `jti`/`exp` as `refresh_jti`/`refresh_exp` claims, or logout will revoke
  the wrong (old) refresh token. Follow the `decode_token(refresh_token)`
  pattern from `login` (backend/src/routes/users.py:86-90).
- In `useFetch.js`, distinguish statuses explicitly: `response.status === 401
  || response.status === 422` → session dead (clear auth, redirect); anything
  else non-200 → `return null` without touching auth. Wrap the `fetch` itself
  in try/catch for network errors → also `return null` without clearing auth.
  The existing caller already handles a falsy return by passing the original
  401 through.
- Concurrent-refresh dedupe: a module-level `let refreshPromise = null;` —
  first 401 assigns it, others `await` the same promise, clear it in a
  `finally`. Do not store it in component state.
- Unrelated but adjacent (do **not** fix here, just don't break it):
  `fetchWithAuth` drops `options.headers` when building `config` — callers'
  `Content-Type` never reaches the server today. Preserve current behavior;
  fixing it is a separate spec if wanted.
- Frontend has no test harness in use; backend tests in
  `backend/tests/test_auth.py` follow the `register`/`login` helper +
  `client` fixture pattern from `conftest.py`.
