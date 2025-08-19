import { createContext, useState } from "react";
import { useEffect } from "react";

const AuthContext = createContext({});

export const AuthProvider = ({ children}) => {
    const [auth, setAuth] = useState({});
    const [loading, setLoading] = useState(true);

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        console.log(value)
        const parts = value.split(`; ${name}=`);
        console.log(parts)
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

     useEffect(() => {
        // Try to refresh access token on mount
        const refresh = async () => {
            try {
                const response = await fetch("http://localhost:5000/refresh", {
                    method:'POST',
                    credentials: "include",
                    headers: {
                        'X-CSRF-TOKEN': getCookie('csrf_refresh_token'),
                        }
                });
                if (response.status === 200) {
                    const data = await response.json();
                    let access_token = data.access_token
                    let username = data.username
                    let email = data.email
                    setAuth({username, email,  access_token });
                } else {
                    setAuth({});
                }
            } catch {
                setAuth({});
            } finally {
                setLoading(false);
            }
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