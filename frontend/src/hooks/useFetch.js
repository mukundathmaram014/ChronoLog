import { useContext } from 'react'
import AuthContext from '../context/AuthProvider';
import useAuth from './useAuth';
import {useLocation, useNavigate} from "react-router-dom";

// Shared across every component using the hook: N parallel 401s must trigger
// exactly one /refresh, otherwise refresh-token rotation makes them race and
// the losers set a stale refresh cookie. Module scope, not component state.
let refreshPromise = null;

let useFetch = () => {

    const {auth} = useContext(AuthContext);
    const {setAuth} = useAuth();
    const location = useLocation();
    const navigate = useNavigate();

    let baseURL = '/api';

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    let originalRequest = async (url, config)=> {
        url = `${baseURL}${url}`
        let response = await fetch(url, config)
        return response
    }

    // Returns the new access token, or null if the refresh did not produce one.
    // Only a 401/422 means the session is actually dead; every other failure
    // (network blip, 5xx during a redeploy) leaves auth state untouched so the
    // caller can surface the original 401 without logging the user out.
    let doRefresh = async () => {
        let response;
        try {
            response = await fetch(`${baseURL}/refresh`, {
                method:'POST',
                credentials: "include",
                headers: {
                    'X-CSRF-TOKEN': getCookie('csrf_refresh_token'),
                }
            })
        } catch (error) {
            console.error("Refresh request failed", error);
            return null;
        }

        if (response.status === 401 || response.status === 422) {
            setAuth({});
            navigate("/loginpage", { state: { from: location }, replace: true });
            return null;
        }

        if (!response.ok) {
            console.error(`Refresh failed with status ${response.status}`);
            return null;
        }

        try {
            const data = await response.json()
            const new_access_token = data.access_token
            if (!new_access_token) return null;
            setAuth((prev) => ({ ...prev, access_token: new_access_token }))
            return new_access_token
        } catch (error) {
            console.error("Could not parse refresh response", error);
            return null;
        }
    }

    let refreshToken = async () => {
        if (!refreshPromise) {
            refreshPromise = doRefresh().finally(() => { refreshPromise = null; });
        }
        return refreshPromise;
    }

    let fetchWithAuth = async (url, options = {}) => {
        
        const headers = {
                'Authorization': `Bearer ${auth.access_token}`
            }

        const config = {
            ...options,
            headers: headers
        };

        let response = await originalRequest(url, config)
        

        if (response.status=== 401){
            let new_access_token = await refreshToken()

             if (!new_access_token) {
                // If refreshToken failed, do not retry, just return the original 401 response
                return response;
            }

            // Retry with new token
            const retryHeaders = {
                'Authorization': `Bearer ${new_access_token}`
            };
            const retryConfig = {
                ...options,
                headers: retryHeaders
            };

            response = await originalRequest(url, retryConfig);
        }
        return response
    }

    return fetchWithAuth;
}

export default useFetch;