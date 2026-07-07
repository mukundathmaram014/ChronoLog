---
status: built
---

# 0019 — "Use as guest" mode

## Problem / Goal
Let someone try ChronoLog without creating an account — a "use as guest" entry point that lets them use
habits/stopwatches/stats, so the app is explorable before sign-up.

## Context
- Auth is JWT-based and pervasive: every data route is `@jwt_required()` and scoped by
  `int(get_jwt_identity())` (`backend/src/routes/*.py`); every model has a `user_id` FK
  (`backend/src/db.py`).
- The frontend gates routes behind `RequireAuth` (`frontend/src/Components/RequireAuth.js`), which checks
  `auth?.username`; `AuthProvider` (`frontend/src/context/AuthProvider.js`) hydrates auth from the
  refresh-cookie flow on mount.
- Because everything is per-user and server-persisted, "guest" needs a clear data story.
- **Spec 0005 (built)** added `User.homepage_note` (nullable String, included in `User.serialize()`),
  `@jwt_required()` GET/PUT `/note` routes in `users.py`, and a `useFetch`-based note load/save in
  `homepage.jsx`. A guest is a real `User`, so the note feature works for guests unchanged; but this
  spec's `db.py`/`users.py` edits land on top of 0005's — branch from a base that includes it.

## Decisions (made)
1. **Ephemeral backend guest user.** "Use as guest" provisions a throwaway `User` (+ access/refresh
   tokens) so guests get the real backend behavior via normal `user_id` scoping; the account and its
   data are cleaned up later. (The frontend-only/localStorage and single-shared-demo options were
   rejected — the former duplicates all data logic and diverges from the real app; the latter lets
   guests clobber each other.)
2. **No conversion in v1.** If a guest later signs up, their guest data is **not** migrated to the new
   account (noted as a possible follow-up).
3. **Expiry/cleanup:** guests and all their data are **purged on a TTL** — default ~7 days (adjustable);
   no special feature limits beyond that. Cleanup is mandatory (see Risks), not optional.

## Affected files (as built)
- `backend/src/routes/users.py` — `POST /guest` provisions a guest `User` (`guest-<hex>` username,
  `@guest.invalid` email, random never-disclosed password) and issues access/refresh tokens exactly like
  `login`; `purge_expired_guests()` (TTL via `GUEST_TTL_DAYS` env, default 7 days) runs at startup and on
  each guest provisioning; `/refresh` now also returns `is_guest` so the frontend can re-hydrate guest
  state. `/note` unchanged — it's `user_id`-scoped and works for guests as-is.
- `backend/src/db.py` — `User.is_guest` **and `User.created_at`** (the TTL purge needs a creation
  timestamp, which `User` lacked — a deviation from the original spec); `is_guest` added to
  `User.serialize()`. **Schema change** — two `ALTER TABLE`s on `users`; see Risks.
- `backend/src/app.py` — `ensure_user_is_guest_column()` / `ensure_user_created_at_column()` startup
  migrations (same PRAGMA pattern as earlier specs) + startup call to `purge_expired_guests()`.
- Guest purge covers **all** per-user tables — the repo grew since this spec was written, so that's
  habits, tasks, goals, daily_xp, stopwatches, deleted-days, and token_blocklist. The homepage note
  lives on the `User` row itself, so deleting the guest `User` covers it.
- `frontend/src/Pages/loginpage.jsx` / `signuppage.jsx` (+ their `.css`) — a "Use as guest" link calling
  `/guest` and populating `auth` (with `isGuest: true`).
- `frontend/src/context/AuthProvider.js` — hydrates `isGuest` from the `/refresh` response.
- `frontend/src/Components/RequireAuth.js` — **no change needed**: guests have a `username`, so the
  existing gate passes.
- `frontend/src/Components/Navbar.jsx` / `Navbar.css` — guest banner on every protected page
  ("guest data is deleted after 7 days — sign up to keep your data").
- `frontend/src/Pages/homepage.jsx` — no change, as predicted.
- `backend/tests/test_guest.py` — new: guest entry, credential uniqueness, habit use, isolation from
  registered users, homepage note, TTL purge (expired guest + data removed; regular users and fresh
  guests spared).

## Approach
1. Backend: a `/guest` endpoint provisions an ephemeral guest `User` (marked `is_guest`) + access/refresh
   tokens; everything else (habits/stopwatch/stats, homepage note) works unchanged via normal `user_id`
   scoping.
2. Frontend: "Use as guest" enters an authed-but-guest session; show guest status and a sign-up nudge.
3. Add the TTL purge for guest accounts + their data (~7 days), covering habits, stopwatches,
   deleted-days, and tokens (the guest's `User` row, including its homepage note, goes with it).

## Acceptance criteria
- A visitor can enter the app as a guest and use habits/stopwatches/stats without registering.
- Guest data is isolated per guest session (no clobbering between guests / real users).
- Guests are identifiable (`is_guest`) and their data is cleaned up per the TTL (~7 days).

## Testing / verification
- "Use as guest" → land in the app authed; create habits/stopwatches; confirm they persist for the
  session and are scoped to the guest.
- Confirm a guest can't see another user's data.
- Confirm the guest homepage (including the 0005 note box) loads and saves without errors.
- Confirm the cleanup path removes an expired guest and its data.

## Risk
- **Involvement:** Involved — touches auth (`users.py`), a `User.is_guest` schema change, guest cleanup/TTL, and the frontend auth gate.
- **Review attention:** High — security-sensitive (keep token handling identical to the real flow), a prod migration, and guest-data isolation + mandatory cleanup; review closely.

## Risks & notes
- **SQLite migration** for `User.is_guest` and `User.created_at` (no Alembic; `create_all` won't alter
  `users`). As built, these are self-applied at startup via the repo's `ensure_*_column()` PRAGMA
  pattern in `app.py`: `ALTER TABLE users ADD COLUMN is_guest BOOLEAN NOT NULL DEFAULT 0` (backfills
  existing users to non-guest) and `ALTER TABLE users ADD COLUMN created_at TIMESTAMP` (NULL for
  pre-existing rows — the purge skips guests without a timestamp, and non-guests are never purged).
- Touches auth — keep token handling identical to the real flow (refresh cookie, blocklist on logout) so
  guest sessions don't weaken security.
- Without cleanup, guest accounts accumulate — the TTL/purge isn't optional.
- Coordinate with spec 0005's branch: this spec edits the same regions of `db.py` (`User` model /
  `serialize()`) and `users.py`; branching from a base without 0005 merged will conflict.