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

## ⚠️ Decision needed — this drives the whole design
1. **Where does guest data live?**
   - **(Recommended) Ephemeral backend guest user:** create a throwaway `User` + tokens on "use as
     guest", real backend behavior, and expire/clean it up later (TTL job or on logout). Most faithful;
     cost is user lifecycle + cleanup.
   - **Frontend-only/local:** guest data stays in `localStorage`, no backend writes. No server cost, but
     duplicates all data logic on the client and diverges from the real app — large and fragile. Not
     recommended.
   - **Single shared demo account:** simplest, but all guests share/clobber the same data — poor UX.
2. **Conversion.** If a guest later signs up, do we migrate their guest data to the new account?
   Recommended: not in v1 (note as a follow-up).
3. **Limits/expiry.** TTL for guest accounts/data (e.g. purge after N days), and any feature limits.

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
1. Decide the data model (Decision 1) — recommended ephemeral guest user.
2. Backend: `/guest` provisions a guest user + tokens; everything else (habits/stopwatch/stats) works
   unchanged via normal `user_id` scoping.
3. Frontend: "Use as guest" enters an authed-but-guest session; show guest status and a sign-up nudge.
4. Add cleanup/TTL for guest data (Decision 3).

## Acceptance criteria
- A visitor can enter the app as a guest and use habits/stopwatches/stats without registering.
- Guest data is isolated per guest session (no clobbering between guests / real users).
- Guests are identifiable and their data is cleaned up per the chosen TTL.

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
