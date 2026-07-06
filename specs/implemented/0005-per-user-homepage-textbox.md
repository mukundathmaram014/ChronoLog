---
status: built
---

# 0005 — Per-user editable homepage text box

## Problem / Goal
The homepage has a free-text box (currently labeled a "quote") whose value is stored in `localStorage`
under one global key `"dailyQuote"`, defaulting to the literal string `"Daily Quote"`
(`frontend/src/Pages/homepage.jsx:21, 63-72, 222-227`). Because the key is global and per-browser:
- every user starts from the same `"Daily Quote"` placeholder,
- two accounts on the same browser share and overwrite each other's text, and
- the text doesn't follow a user across devices.

The author just wants a plain **configurable text box each user owns** — free-form text the user can
edit and keep. It is explicitly **not** a rotating/generated quote and need not be "motivational"; it's
just an editable note on the front page.

## Scope
- In scope: make the homepage text box per-user and persistent so each user edits and keeps their own
  text; drop the shared global `"dailyQuote"` key and the `"Daily Quote"` placeholder default.
- Out of scope / non-goals: no rotating/generated quotes, no bundled quote list, no external quote API;
  no rich-text/formatting; no change to the habit/stopwatch cards.

## Decisions (made)
The text persists in a **backend field on `User`** (a nullable `homepage_note` column) exposed via a
small `@jwt_required()` GET/PUT route and saved through `useFetch`. This keeps the note per-user and
device-independent, consistent with the rest of the app (every other piece of data is per-user,
server-side). The cost is a one-off SQLite `ALTER TABLE` (no Alembic — see Risk) plus one route.
The considered alternative — a `localStorage` key namespaced by user id (frontend-only, no migration)
— was **not** chosen because it stays per-browser and is lost on cache clear.

## Affected files
- `backend/src/db.py` — add `User.homepage_note` (String, nullable) and include it in `User.serialize()`
  (`db.py:7-22`). **Schema change** — see Risk.
- `backend/src/routes/users.py` — add a `@jwt_required()` GET + PUT (e.g. `/note`) that reads/updates the
  current user's note, scoped by `int(get_jwt_identity())`, reading the body with
  `json.loads(request.data)` and returning `success_response`/`failure_response` (mirror the existing
  route conventions). No `app.py` change — it rides on the already-registered `user_routes` under `/api`.
- `frontend/src/Pages/homepage.jsx` — replace the `localStorage("dailyQuote")` seed and the two
  `localStorage` effects (`:21, 63-72`) with: fetch the user's note on mount via `useFetch` and save
  edits back (on blur or debounced). Keep the existing `<textarea>` (`:222-227`); remove the
  `"Daily Quote"` default (empty box with a neutral placeholder instead).

## Approach
1. Add `homepage_note` (nullable String) to the `User` model and to `serialize()`.
2. Add the note route on `user_routes`: GET returns `{ homepage_note }` for the current user; PUT reads
   `body.get("homepage_note", "")` and persists it (`db.session.commit()`), everything scoped by
   `user_id` via `int(get_jwt_identity())`.
3. In `homepage.jsx`, drop the `localStorage` seed/effects; on mount, GET the note into the `quote`
   state; on edit, PUT it (debounced or on blur) through `fetchWithAuth`. Keep the `<textarea>` and its
   `value`/`onChange`; show an empty box (neutral placeholder) instead of `"Daily Quote"`.
4. Leave the rest of the homepage untouched.

## Acceptance criteria
- Each user has their own text box; editing it persists and reloads with their saved text.
- Two accounts (even on the same browser) have independent text; one never sees or overwrites the
  other's.
- The text follows the user across devices (it's stored server-side).
- A brand-new user sees an empty box (or neutral placeholder), not the literal `"Daily Quote"`.

## Testing / verification
- Log in, type into the box, reload → text persists. Log in as a second user → independent/empty box;
  editing it doesn't change the first user's text.
- Log in on another browser/device and confirm the saved text loads.
- Backend: GET/PUT the note route with a valid token and confirm it's scoped to the caller (a second
  user can't read or overwrite the first's note).

## Risk
- **Involvement:** Moderate — one `User` column + a small GET/PUT route + swapping the homepage's
  `localStorage` logic for `useFetch`.
- **Review attention:** Medium — needs a hand-applied prod `ALTER TABLE` on the live `users` table (no
  Alembic); confirm the note route is `user_id`-scoped so one user can't read or overwrite another's.

## Risks & notes
- **SQLite migration:** `db.create_all()` won't add a column to the existing `users` table and there's
  no Alembic — add `homepage_note` to the live `instance/ChronoLog.db` with a one-off
  `ALTER TABLE users ADD COLUMN homepage_note VARCHAR` (existing rows default to NULL). Call this out in
  the PR with the exact statement. Same migration concern as specs 0003/0012.
- The box's contents are free-form per-user data — treat it as in-app user data, nothing to hard-code.
