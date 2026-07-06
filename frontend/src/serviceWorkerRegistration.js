// Registers the hand-written service worker in public/service-worker.js
// (spec 0022). Production only: in development a service worker would just
// get in the way of live reload. The update flow is handled inside the
// service worker itself (silent skipWaiting/claim; navigations are
// network-first, so a new deploy shows up on the next online launch).

export function register() {
  if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register(`${process.env.PUBLIC_URL}/service-worker.js`)
      .catch((error) => {
        console.error("Service worker registration failed:", error);
      });
  });
}

export function unregister() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => registration.unregister())
      .catch((error) => {
        console.error(error.message);
      });
  }
}
