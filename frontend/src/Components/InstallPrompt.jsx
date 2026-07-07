import { useState, useEffect } from "react";
import { IoMdClose } from "react-icons/io";
import "./InstallPrompt.css";

const DISMISSED_KEY = "chronolog-install-dismissed";

// True when already running as an installed app (Chrome/Edge/Android set the
// display-mode media query; iOS Safari sets navigator.standalone).
const isStandalone = () =>
    window.matchMedia("(display-mode: standalone)").matches ||
    window.navigator.standalone === true;

const isIOS = () =>
    /iphone|ipad|ipod/i.test(window.navigator.userAgent) ||
    // iPadOS reports itself as a Mac but is still touch-driven
    (/macintosh/i.test(window.navigator.userAgent) && navigator.maxTouchPoints > 1);

export function InstallPrompt() {
    const [dismissed, setDismissed] = useState(
        () => localStorage.getItem(DISMISSED_KEY) === "true"
    );
    const [installEvent, setInstallEvent] = useState(null);
    const [showIOSHint] = useState(() => isIOS() && !isStandalone());

    useEffect(() => {
        const onBeforeInstallPrompt = (event) => {
            // Chrome/Edge/Android: stash the event so our own button can trigger it
            event.preventDefault();
            setInstallEvent(event);
        };
        const onAppInstalled = () => setInstallEvent(null);

        window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
        window.addEventListener("appinstalled", onAppInstalled);
        return () => {
            window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
            window.removeEventListener("appinstalled", onAppInstalled);
        };
    }, []);

    const dismiss = () => {
        localStorage.setItem(DISMISSED_KEY, "true");
        setDismissed(true);
    };

    const handleInstall = async () => {
        installEvent.prompt();
        await installEvent.userChoice;
        // Whether accepted or declined, don't keep nagging
        setInstallEvent(null);
        dismiss();
    };

    if (dismissed || isStandalone() || (!installEvent && !showIOSHint)) {
        return null;
    }

    return (
        <div className="install-prompt">
            {installEvent ? (
                <>
                    <span className="install-prompt-text">
                        Install ChronoLog as an app — it opens in its own window with its own icon.
                    </span>
                    <button className="install-prompt-button" onClick={handleInstall}>
                        Install
                    </button>
                </>
            ) : (
                <span className="install-prompt-text">
                    Install ChronoLog on your home screen: tap <strong>Share</strong> →{" "}
                    <strong>Add to Home Screen</strong>.
                </span>
            )}
            <button
                className="install-prompt-close"
                onClick={dismiss}
                aria-label="Dismiss install hint"
            >
                <IoMdClose />
            </button>
        </div>
    );
}
