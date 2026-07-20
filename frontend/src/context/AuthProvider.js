import { createContext, useState } from "react";
import { useEffect } from "react";

const AuthContext = createContext({});

export const AuthProvider = ({ children}) => {
    const [auth, setAuth] = useState({});
    const [loading, setLoading] = useState(true);

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

     useEffect(() => {
        // One refresh attempt. Returns true if the session was resolved either
        // way (logged in, or definitively logged out); false if the attempt
        // failed transiently and is worth retrying.
        const attemptRefresh = async () => {
            let response;
            try {
                response = await fetch("/api/refresh", {
                    method:'POST',
                    credentials: "include",
                    headers: {
                        'X-CSRF-TOKEN': getCookie('csrf_refresh_token'),
                        }
                });
            } catch {
                return false; // network error
            }

            if (response.status === 200) {
                try {
                    const data = await response.json();
                    let access_token = data.access_token
                    let username = data.username
                    let email = data.email
                    let isGuest = data.is_guest === true
                    setAuth({username, email,  access_token, isGuest });
                    return true;
                } catch {
                    return false;
                }
            }

            // Only these mean "not logged in"; anything else (5xx during a
            // backend redeploy, proxy error) is transient and gets one retry.
            if (response.status === 401 || response.status === 422) {
                setAuth({});
                return true;
            }
            return false;
        };

        // Try to refresh access token on mount
        const refresh = async () => {
            let resolved = await attemptRefresh();
            if (!resolved) {
                await new Promise((r) => setTimeout(r, 2000));
                resolved = await attemptRefresh();
            }
            if (!resolved) setAuth({});
            setLoading(false);
        };
        refresh();
    }, []);

    if (loading) return <div>Loading...</div>;

    return (
        <AuthContext.Provider value = {{auth, setAuth}}>
            {children}
        </AuthContext.Provider>
    )
}

export default AuthContext;