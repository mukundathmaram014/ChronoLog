# 0022 — Installable PWA (Progressive Web App)

## Problem / Goal
Make ChronoLog installable to the home screen (iPhone) and to a standalone window (desktop Chrome/Edge)
so it launches like an app — full-screen, own icon — instead of living in a browser tab. This is a
**packaging/frontend-only** change: same site, same login, same data. No backend changes.

## Scope
- **In scope:**
  - A real web app **manifest** (name, icons, colors, `display: standalone`) replacing the CRA template.
  - App **icons** (192/512 + maskable) and iOS `apple-touch-icon` / meta tags for a proper home-screen
    launch (full-screen, status-bar style, notch-safe).
  - A **service worker** that caches the app shell so the app opens instantly / offline-shell, with a
    **safe update strategy** so a new deploy doesn't get stuck behind a stale cache.
  - An in-app **install hint**: a real "Install" button where the browser supports it (desktop
    Chrome/Edge, Android) and an **iOS instruction** ("tap Share → Add to Home Screen"), dismissible and
    remembered.
  - A **responsive / touch pass** so the existing pages are usable on a phone (tap targets, widths, and
    **drag-and-drop via touch** — the `Sortable*` reorder UI uses dnd-kit and needs a touch sensor).
  - **Desktop install-to-window** is an explicit deliverable of the same manifest/SW work (no separate
    project) — the PWA install in Chrome/Edge gives a standalone window + taskbar/Start-menu icon.
- **Out of scope / non-goals:**
  - Native wrappers (Capacitor/Electron/Tauri) and the App Store — separate, larger, and they’d break
    the same-origin cookie flow (see Risks). A follow-up if ever wanted.
  - **Web push notifications** — deferred (iOS requires the app be installed first; own design). Note as
    a future spec.
  - **Offline data / write queue** — the shell caches, but data still needs the backend online. No
    offline CRUD, no local DB.
  - Any visual redesign — the responsive pass makes pages *usable* on a phone, not restyled.

## Context — current state
- Create React App **5.0.1**, React 19 (`frontend/package.json`). Served by Netlify; SPA fallback + the
  `/api` → backend proxy live in `frontend/public/_redirects` (per CLAUDE.md; the backend IP is baked in
  there).
- `frontend/public/manifest.json` is the **stock CRA template** (`"short_name": "React App"`, CRA logo
  icons, `theme_color #000000`). `index.html` already has `<link rel="manifest">`, an
  `apple-touch-icon` (logo192), a `theme-color` meta, and `<title>ChronoLog</title>`.
- **No service worker is registered.** `frontend/src/index.js` renders the app but never registers a SW,
  and the `cra-template-pwa` files (`service-worker.js`, `serviceWorkerRegistration.js`) are **not**
  present — so this must be added. CRA 5 without eject does **not** run Workbox over a `public/`
  service worker, so a small **hand-written** SW in `public/` (copied verbatim into the build) that we
  register manually is the lowest-config path (Workbox alternative noted in Decision 2).
- Auth: JWT access token in memory + an **httpOnly refresh cookie**; all authed calls go through the
  `useFetch` hook (`frontend/src/hooks/useFetch.js`), which retries once on 401 via the refresh flow
  (`frontend/src/context/AuthProvider.js`, backend `routes/users.py`). Because the installed PWA runs at
  the **same origin** in a real browser engine, the cookie/refresh flow is **unchanged** — nothing to
  do here. (This is the property a native wrapper would lose — see Risks.)
- Reorder UI uses dnd-kit (`frontend/src/Components/Sortable*`); on touch it needs a `TouchSensor` /
  `PointerSensor` configured or drag won't work on a phone.

## ⚠️ Decisions needed
1. **App icon + brand colors (the main input needed).** The current icons are the placeholder CRA React
   logo and colors are black/white. Options:
   - **(Recommended) Provide/approve a simple ChronoLog icon** (a plain wordmark/clock glyph is fine) and
     a `theme_color` / `background_color`. I can generate the required sizes (192, 512, and a **maskable**
     variant with safe padding) from one source image. Need: the source art (or "generate a simple one")
     and the two colors.
   - Ship with a quick generated placeholder now, replace art later. Works, but the icon is what you’ll
     stare at on your home screen — worth getting right.
2. **Service-worker strategy & how aggressively to cache.**
   - **(Recommended) Minimal hand-written SW in `public/`** + manual registration; **network-first for
     navigations** (always try the live app, fall back to cached shell offline) and cache-first only for
     hashed static assets. This makes a new deploy show up immediately and avoids the classic "stale PWA"
     trap. Simplest with CRA-no-eject.
   - Workbox via the `cra-template-pwa` files (`GenerateSW`): more machinery/precache manifest; more than
     this needs.
   - Confirm the **update UX**: silently activate the new SW and reload on next launch (recommended) vs.
     an in-app "Update available — refresh" prompt.
3. **Install-hint behavior.** Desktop Chrome/Edge & Android fire `beforeinstallprompt` (we can show a real
   **Install** button that triggers the native prompt). **iOS Safari has neither** — it needs a small
   **instructional** hint ("Share → Add to Home Screen"). Recommended: one component that branches by
   capability, shown once, **dismissible and remembered in `localStorage`**, and hidden entirely when
   already running installed (`display-mode: standalone`). Confirm where it appears (e.g. a dismissible
   banner on the homepage/login) and that it shouldn’t nag.
4. **How far the responsive/touch pass goes.** Recommended MVP: every page **usable** at phone widths
   (no horizontal scroll, tappable controls) and **drag reorder works by touch**; no visual redesign.
   Confirm that "usable, not redesigned" is the bar for v1.

## Affected files
- `frontend/public/manifest.json` — real `name`/`short_name` ("ChronoLog"), proper icons incl. a
  **maskable** entry, `theme_color`/`background_color`, `display: standalone`, `start_url`.
- `frontend/public/index.html` — iOS/install meta: `apple-mobile-web-app-capable`,
  `apple-mobile-web-app-status-bar-style`, `apple-mobile-web-app-title`, update `theme-color`, and
  `viewport-fit=cover` on the viewport meta (for notch-safe layout).
- `frontend/public/` — new icon assets (e.g. `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`,
  refreshed `apple-touch-icon`), plus **`service-worker.js`** (the hand-written SW, Decision 2).
- `frontend/src/serviceWorkerRegistration.js` — **new**: registers `/service-worker.js` in production,
  wires the update flow (Decision 2). Called from `index.js`.
- `frontend/src/index.js` — register the service worker (currently does not).
- `frontend/src/Components/InstallPrompt.jsx` (+ small CSS) — **new**: the capability-branched, dismissible
  install hint (Decision 3); mounted once (e.g. in `layout.jsx` or on the homepage/login page).
- `frontend/src/Components/Sortable*` (dnd-kit setup) — add a touch/pointer sensor so reorder works on
  touch (Decision 4).
- Page/component CSS across `frontend/src/Pages/*` and `Components/*` — targeted responsive fixes
  (widths, wrapping, tap-target sizes, safe-area padding). Scoped to "usable on a phone" per Decision 4.
- `frontend/public/_redirects` — **verify only** (no change expected): Netlify serves real static files
  before applying the `/*  /index.html` rewrite, so `/service-worker.js` and `/manifest.json` are served
  directly, not rewritten to `index.html`. Confirm the SW is served with a JS MIME type and **not**
  long-cached (so updates propagate). See Risks.
- `README.md` — a short "Install as an app (iPhone / desktop)" note once shipped.

## Approach
1. **Manifest + icons + iOS meta** (Decision 1). Replace the CRA manifest with real ChronoLog metadata
   and icons (incl. maskable). Add the iOS meta tags + `viewport-fit=cover`. This alone makes iOS
   "Add to Home Screen" and desktop "Install" produce a properly named, full-screen, icon’d app.
2. **Service worker** (Decision 2). Add `public/service-worker.js` (network-first navigations, cache the
   app shell, cache-first for hashed assets) + `src/serviceWorkerRegistration.js`, and register it from
   `index.js` in production only. Bump a cache version on each release; on activate, clean old caches.
   Wire the chosen update UX. **Guard against the stale-PWA trap** — this is the main correctness risk.
3. **Install hint** (Decision 3). `InstallPrompt.jsx`: capture `beforeinstallprompt` (desktop/Android) to
   drive a real Install button; on iOS Safari show the Share→Add instruction; hide when
   `display-mode: standalone`; remember dismissal in `localStorage`.
4. **Responsive / touch pass** (Decision 4). Add a dnd-kit touch/pointer sensor so reorder works on a
   phone; walk each page at ~375px width and fix overflow / tap targets / safe-area insets. Keep changes
   CSS-level; don't restructure components.
5. **Verify no auth impact.** Confirm `useFetch` + refresh-cookie login still works installed (same
   origin). Nothing to change — but test it (see Testing) because it's the thing people assume breaks.

## Acceptance criteria
- On **iPhone Safari**, Share → "Add to Home Screen" installs ChronoLog with the correct name + icon;
  launching it opens **full-screen** (no Safari chrome), with a correct status bar and no content under
  the notch.
- On **desktop Chrome/Edge**, an **Install** control appears and installs ChronoLog into its **own
  window** with a taskbar/Start-menu icon.
- The app **opens offline to its shell** (not a browser error); data actions still require connectivity.
- After a new deploy, the installed app **picks up the new version** (no permanent stale cache) per the
  chosen update UX.
- **Login and stay-logged-in work identically** in the installed app (refresh-cookie flow via `useFetch`
  unaffected).
- Every page is **usable on a phone** (no horizontal scrolling, controls tappable) and **drag-to-reorder
  works by touch**.
- The install hint shows appropriately, is **dismissible**, doesn’t reappear after dismissal, and is
  **hidden when already installed**.

## Testing / verification
- **Lighthouse → PWA / Installable** (Chrome DevTools) on the deployed site: installable, has manifest +
  SW, valid icons.
- **iPhone:** add to home screen; launch; confirm full-screen, icon, status bar, notch-safe; log in and
  navigate; toggle airplane mode and confirm the shell still opens.
- **Desktop Chrome/Edge:** install; confirm standalone window + icon; confirm login/session works.
- **Update:** deploy a change, reopen the installed app, confirm the new version appears (per Decision 2).
- **Touch reorder:** on a phone, drag a habit/stopwatch to reorder and confirm it persists.
- **Responsive:** DevTools device toolbar at 375px across all pages — no overflow, tappable controls.

## Risks & notes
- **Stale-cache trap (top risk).** A too-aggressive service worker can pin users to an old build. Use
  network-first for navigations, version + clean caches on activate, and ensure the SW file itself is
  served **un-cached** (short/no `Cache-Control`) so updates are seen. Netlify serves hashed CRA assets
  immutably (fine) but the SW and `index.html` must not be long-cached.
- **Netlify `_redirects` interaction.** The SPA rewrite `/*  /index.html 200` must not swallow
  `/service-worker.js` or `/manifest.json`. Netlify serves existing static files before rewrites, so
  real build files win — **verify** after deploy that `/service-worker.js` returns the JS file (not the
  HTML shell) and with a JS MIME type.
- **Same-origin is what makes auth "just work."** The installed PWA runs on the same origin as the site,
  so the httpOnly `SameSite` refresh cookie is sent normally and `useFetch`'s refresh retry is
  unaffected — **no auth changes needed.** ⚠️ A **future native wrapper (Capacitor/Electron/Tauri) would
  NOT** have this property: it runs on a custom app origin (e.g. `capacitor://localhost`), making the API
  cross-site, so the `SameSite=Lax` cookie wouldn’t send and token storage would have to be reworked.
  That’s a real reason to prefer the PWA and to treat any native wrapper as a separate, larger effort.
- **iOS limitations to set expectations:** no programmatic install (hence the manual hint), home-screen
  PWA storage can be evicted under pressure, and background execution is limited. Fine for this app; just
  don’t promise native-grade background behavior.
- **No backend/DB/migration impact** — this is frontend packaging only. Nothing in `backend/` changes.
- **Stopwatch timing is already mobile-safe:** elapsed is computed from `interval_start` + stored
  `curr_duration` (per CLAUDE.md), so backgrounding/locking the phone (which suspends JS) doesn’t drift —
  it reconstructs on foreground. No change needed, but it’s why this app suits a phone well.
