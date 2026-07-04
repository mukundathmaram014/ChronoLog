# 0005 — Motivational quote is shared / never rotates

## Problem / Goal
The homepage "quote" is an editable `<textarea>` whose value is stored in `localStorage` under a
single key `"dailyQuote"`, defaulting to the literal string `"Daily Quote"`
(`frontend/src/Pages/homepage.jsx:21, 66-74, 222-227`). Consequences:
- Every user sees the same default `"Daily Quote"`.
- It's keyed per-browser, not per-user — two accounts on the same browser share the text, and it
  doesn't follow a user across devices.
- It never changes on its own; it's just a free-text box.

The author's intent ("fix motivational quote being shown as same across every user's page") is that
each user should get an actual motivational quote, ideally rotating (per day), not one shared box.

## ⚠️ Needs an author decision before building
Where should quotes come from? Pick one:
- **A. Bundled rotating list (recommended, no backend, no network):** ship a small array of quotes in
  the frontend; pick deterministically by `(user id + date)` so each user gets a stable quote per day
  that rotates daily. Lowest cost, offline-safe.
- **B. External quote API:** fetch a daily quote from a public API, cache it in `localStorage` per
  date. Adds a network dependency / CORS + reliability concerns.
- **C. Backend per-user quote:** add a quote field/route so a user's chosen quote persists server-side
  across devices. Most work; only worth it if users should *edit and keep* their own quote.

The rest of this spec assumes **A**; adjust in `/build` if the author picks B or C.

## Scope (assuming A)
- In scope: replace the shared default with a per-user, per-day quote chosen from a bundled list;
  namespace any cached value by user id.
- Out of scope / non-goals: no backend route (unless option C is chosen); no quote-management UI.

## Affected files
- `frontend/src/Pages/homepage.jsx` — replace the `localStorage("dailyQuote")` default/seed with a
  deterministic pick from a quotes list keyed by user + `today`.
- (new) `frontend/src/data/quotes.js` (or inline) — the bundled quote array.
- `frontend/src/hooks/useAuth.js` / `context/AuthProvider.js` — source of the current user id for the
  per-user key (read existing auth context; don't add a new one).

## Approach (assuming A)
1. Add a `quotes` array (a dozen+ entries).
2. Compute today's quote deterministically: index = hash(`userId + today`) % quotes.length, so it's
   stable for the day and differs per user. `today` already exists in `homepage.jsx`.
3. Display it (read-only, or keep editable but persist under a per-user key like
   `dailyQuote:<userId>:<today>` if the author wants editing preserved).
4. Remove reliance on the single global `"dailyQuote"` key.

## Acceptance criteria
- A fresh user sees a real quote, not the literal `"Daily Quote"`.
- Two different accounts (even on the same browser) see independently-chosen quotes.
- The quote changes day-to-day and is stable within a day.

## Testing / verification
- Log in as two users on the same browser → different quotes.
- Confirm the quote stays the same on refresh within a day and changes after the date rolls over
  (can simulate by changing `today`).

## Risk
- **Involvement:** Minimal — frontend-only: a bundled quote list + a deterministic per-user/day pick (option A).
- **Review attention:** Low — isolated to the homepage, no schema; the thing to confirm is the A/B/C source decision (option C would make it backend-touching → Moderate).

## Risks & notes
- Confirm the current user id is available from the existing auth context before building.
- If option C is chosen this becomes a backend-touching spec (new column + route + `useFetch`).
