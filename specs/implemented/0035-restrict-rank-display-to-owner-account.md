---
title: Restrict the letter-rank display to an env-configured account
status: decided
---

# Restrict the letter-rank display to an env-configured account

## Summary

The letter-rank layer (E → D → C → B → A → S) is a personal flourish, but it currently renders for
**every** account — registered users and guests alike. `GET /api/level/<date>/` returns `rank` for
anyone, the homepage level card shows an `X-Rank` chip next to the level, and the profile popup's
XP-rules section carries a "Ranks" table plus the wording "How XP & **ranks** work".

Gate the whole layer behind an **allowlist of usernames supplied by an environment variable**. When
the current account isn't on the list, the backend omits `rank` from its responses and the frontend
renders no rank chip, no Ranks table, and no "ranks" wording — the level, XP bar, and streak all
stay exactly as they are for everyone. There is **no in-app toggle**: other users can't enable it,
and can't discover that it exists.

Guests are excluded unconditionally, independent of the allowlist.

**The allowlisted username is never committed.** It lives only in the gitignored backend env file
(`backend/.env` locally, `~/.env` on the VM). The repo ships the variable *unset*, which means
"nobody" — a fresh clone shows no ranks to anyone. Do not write a real username into any tracked
file, including this spec, tests, or `.env.example` templates.

## Affected files

- `backend/src/utils.py` — new `rank_visible(user)` helper: parses the allowlist env var and answers
  whether this account may see ranks. `RANKS` / `rank_from_level` themselves are unchanged.
- `backend/src/db.py` — `User.serialize()` gains `show_rank` (computed via `rank_visible(self)`, not
  a stored column), so login/guest responses carry the flag to the client.
- `backend/src/routes/level.py` — include `"rank"` in the `/level/<date>/` payload only when
  `rank_visible(user)`; omit the key entirely otherwise.
- `backend/src/routes/users.py` — `/refresh` response gains `show_rank` alongside `username` /
  `email` / `is_guest` (it hand-builds its payload rather than using `serialize()`).
- `backend/tests/test_xp.py` — replace `test_level_readout_includes_rank` with the gated behaviour
  (absent by default; present when the env allowlist names the test user); add `rank_visible` unit
  coverage. `test_rank_from_level` stays as-is.
- `backend/tests/test_stopwatch_carryforward.py` — drop `"rank"` from the two invariant field tuples
  (lines ~435 and ~450); the key is no longer present by default.
- `backend/tests/test_guest.py` — add: a guest never receives `rank`, even when its username is on
  the allowlist.
- `frontend/src/context/AuthProvider.js` — carry `show_rank` from `/refresh` into `auth.showRank`.
- `frontend/src/Pages/loginpage.jsx` — carry `data.user.show_rank` into `auth.showRank` on both the
  login and the guest paths.
- `frontend/src/Pages/signuppage.jsx` — same, on the guest path.
- `frontend/src/Components/Navbar.jsx` — gate the "Ranks" heading + list on `auth.showRank`, and
  drop "& ranks" from the toggle label when it's off.
- `frontend/src/Pages/homepage.jsx` — render the `X-Rank` chip only when `levelData.rank` is present.
- `docs/deployment.md` — document the new backend env var (name and semantics only, no value).

Conditionally affected — **only if spec 0034 lands first** (it is `decided` but unbuilt, and adds a
`rank` field to the statistics XP section):

- `backend/src/routes/statistics.py` — apply the same `rank_visible` gate to the XP section's
  `level` object.
- `frontend/src/Pages/statisticspage.jsx` — render the rank in the XP section only when present.

No CSS changes: `.homepage-level-rank` and the `.xp-rank-letter.rank-*` colour rules stay; the
markup that uses them simply isn't rendered.

## Decisions needed

- [x] Per-account **setting with a toggle**, or **hard-locked to one account**? → Hard-locked. Other
      users must not see the feature or be able to enable it, so there is no UI and no DB column.
- [x] How is the account identified? → A **username allowlist read from an env var**, so the
      identity stays out of this public repo (see Summary). Not a hardcoded username, not a user id.
- [x] Guests? → Never, regardless of the allowlist.
- [x] Gate server-side or client-side? → **Both.** The backend omits `rank` (so it isn't merely
      CSS-hidden and can't be read off the API), and the frontend hides the rank UI.

## Risk

- **Involvement:** Moderate — one small backend helper threaded through three response payloads,
  plus conditional rendering in four frontend files. No schema change, no migration, no data
  backfill. The breadth comes from the auth payload touching login/signup/refresh, not from depth.
- **Review attention:** Medium — the failure mode is quiet, not loud. Miss one of the three payloads
  (`serialize` / `/refresh` / `/level`) and the flag silently disagrees with itself: the homepage
  chip appears while the Ranks table doesn't, or vice versa. The env var is also easy to forget at
  deploy time (see below), and the existing `rank` assertions in two test files will fail loudly if
  not updated.

## Implementation notes

### Backend

- **`rank_visible(user)` in `utils.py`**, next to `RANKS` / `rank_from_level`:
  - `False` when `user` is `None` or `user.is_guest` is truthy — the guest check comes first and is
    not overridable.
  - Otherwise `True` iff `user.username`, stripped and lowercased, is in the allowlist parsed from
    `RANK_USERNAMES`: comma-separated, each entry stripped and lowercased, blanks dropped.
  - **Read the env var inside the helper** via `os.environ.get("RANK_USERNAMES", "")`, not as a
    module-level constant. This deliberately differs from `GUEST_TTL_DAYS` in `users.py`: reading at
    call time lets tests use `monkeypatch.setenv` and lets the VM change the value with a container
    restart instead of a code deploy. Note the deviation in a comment.
  - Unset / empty → nobody. That is the committed default.
- **`level.py`**: build the response dict, then add `"rank": rank_from_level(progress["level"])`
  only when `rank_visible(user)`. Omit the key rather than sending `null` — the frontend keys off
  presence, and an omitted key can't be mistaken for "rank not computed yet".
- **`db.py`**: `User.serialize()` adds `"show_rank": rank_visible(self)`. `db.py` already imports
  `ensure_utc` from `utils`, so the import direction is established.
- **`users.py`**: `/refresh` hand-builds `{access_token, username, email, is_guest}` — add
  `"show_rank": rank_visible(user)` there too. `/login` and `/guest` already return
  `user.serialize()` and need no change.
- No new route, no `User` column, no `ALTER TABLE`, nothing added to `app.py`'s migration block.

### Frontend

- `AuthProvider.js` sets `showRank: data.show_rank === true` alongside the existing `isGuest` line;
  `loginpage.jsx` / `signuppage.jsx` read it off `data.user`. Use the same explicit `=== true`
  coercion the `isGuest` lines use, so a missing field (backend not yet redeployed) reads as `false`
  rather than `undefined`.
- `Navbar.jsx`: wrap the `<h3>Ranks</h3>` + its `<ul>` in `{auth.showRank && (...)}`, and make the
  toggle label conditional — `"How XP & ranks work"` / `"Hide how XP & ranks work"` when on,
  `"How XP works"` / `"Hide how XP works"` when off.
- `homepage.jsx`: the chip becomes `{levelData.rank && <span className="homepage-level-rank">...}`.
  The `Level {levelData.level}` text and the `Level —` placeholder branch are untouched, so the
  card's loading behaviour from spec 0026 is unaffected.

### Deploying

`RANK_USERNAMES` must be added to the **VM's `~/.env`** (the file the VM's compose loads via
`env_file: .env`) before or with the backend deploy — and to `backend/.env` for local dev.
Ship the code without it and the rank simply vanishes for everyone, including the owner account:
a silent, easily-missed regression. Call this out in the PR description.

### Verifying

- With `RANK_USERNAMES` unset: `/level` has no `rank` key; `/refresh`, `/login`, `/guest` report
  `show_rank: false`; homepage shows `Level N` with no chip; the popup button reads "How XP works"
  and the expanded panel has Earning XP + Streak but no Ranks table.
- With the env var naming a registered user: that account sees the chip and the Ranks table; a
  second registered account, logged in simultaneously, sees neither.
- A guest whose username is placed on the allowlist still sees neither — the guest check wins.
