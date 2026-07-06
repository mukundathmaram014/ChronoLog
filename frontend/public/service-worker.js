/*
 * ChronoLog service worker (hand-written; CRA copies this file into the build
 * verbatim and serviceWorkerRegistration.js registers it in production).
 *
 * Strategy (spec 0022, Decision 2):
 *  - Navigations: network-first — always try the live app, fall back to the
 *    cached shell when offline. Every successful navigation refreshes the
 *    cached shell, so a new deploy is picked up on the next online launch.
 *  - /static/ build assets: cache-first — CRA content-hashes these filenames,
 *    so a cached entry can never be stale.
 *  - /api/ requests are never touched: data always requires the network.
 *
 * Bump CACHE_VERSION only when the caching logic here changes (deploys don't
 * need it: the shell refreshes on navigation and asset URLs are hashed).
 * Updates activate silently (skipWaiting + clients.claim) — no in-app prompt.
 */

const CACHE_VERSION = "chronolog-v1";
const SHELL_URL = "/index.html";
const PRECACHE_URLS = [SHELL_URL, "/manifest.json", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(CACHE_VERSION)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

async function cachePut(request, response) {
  const cache = await caches.open(CACHE_VERSION);
  await cache.put(request, response);
}

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      cachePut(SHELL_URL, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(SHELL_URL);
    if (cached) {
      return cached;
    }
    throw err;
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }
  const response = await fetch(request);
  if (response.ok) {
    cachePut(request, response.clone());
  }
  return response;
}

async function networkFallingBackToCache(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      cachePut(request, response.clone());
    }
    return response;
  } catch (err) {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith("/api/")) {
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(networkFirstNavigation(request));
  } else if (url.pathname.startsWith("/static/")) {
    event.respondWith(cacheFirst(request));
  } else {
    event.respondWith(networkFallingBackToCache(request));
  }
});
