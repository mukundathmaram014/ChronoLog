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

## Affected files
- `backend/src/routes/users.py` — a guest entry endpoint (e.g. `/guest`) that provisions a guest `User`
  and issues access/refresh tokens like `login`; mark guests (e.g. an `is_guest` flag on `User`).
- `backend/src/db.py` — (likely) `User.is_guest` + serialize. **Schema change** — see Risks.
- Guest cleanup — a purge path for expired guests (and their habits/stopwatches/deleted-days/tokens).
- `frontend/src/Pages/loginpage.jsx` (+ signup) — a "Use as guest" button calling the guest endpoint and
  populating `auth`.
- `frontend/src/context/AuthProvider.js` / `RequireAuth.js` — allow a guest session to satisfy the auth
  gate; surface guest state (e.g. a banner / "sign up to keep your data").

## Approach
1. Backend: a `/guest` endpoint provisions an ephemeral guest `User` (marked `is_guest`) + access/refresh
   tokens; everything else (habits/stopwatch/stats) works unchanged via normal `user_id` scoping.
2. Frontend: "Use as guest" enters an authed-but-guest session; show guest status and a sign-up nudge.
3. Add the TTL purge for guest accounts + their data (~7 days), covering habits, stopwatches,
   deleted-days, and tokens.

## Acceptance criteria
- A visitor can enter the app as a guest and use habits/stopwatches/stats without registering.
- Guest data is isolated per guest session (no clobbering between guests / real users).
- Guests are identifiable (`is_guest`) and their data is cleaned up per the TTL (~7 days).

## Testing / verification
- "Use as guest" → land in the app authed; create habits/stopwatches; confirm they persist for the
  session and are scoped to the guest.
- Confirm a guest can't see another user's data.
- Confirm the cleanup path removes an expired guest and its data.

## Risk
- **Involvement:** Involved — touches auth (`users.py`), a `User.is_guest` schema change, guest cleanup/TTL, and the frontend auth gate.
- **Review attention:** High — security-sensitive (keep token handling identical to the real flow), a prod migration, and guest-data isolation + mandatory cleanup; review closely.

## Risks & notes
- **SQLite migration** for `User.is_guest` (no Alembic; `create_all` won't alter `users`) — `ALTER
  TABLE` + backfill existing users to non-guest.
- Touches auth — keep token handling identical to the real flow (refresh cookie, blocklist on logout) so
  guest sessions don't weaken security.
- Without cleanup, guest accounts accumulate — the TTL/purge isn't optional.
