import { useContext } from 'react'
import AuthContext from '../context/AuthProvider';
import useAuth from './useAuth';
import {useLocation, useNavigate} from "react-router-dom";

let useFetch = () => {

    const {auth} = useContext(AuthContext);
    const {setAuth} = useAuth();
    const location = useLocation();
    const navigate = useNavigate();

    let baseURL = 'http://localhost:5000';

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

    let refreshToken = async () => {
        try {
            let response = await fetch(`${baseURL}/refresh`, {
            method:'POST',
            credentials: "include",
            headers: {
                'X-CSRF-TOKEN': getCookie('csrf_refresh_token'),
                }
            })
            if (response.status === 401){
                throw new Error('Refresh token expired')
            }
            let data = await response.json()
            const new_access_token = data.access_token
            setAuth((prev) => ({ ...prev, access_token: new_access_token }))
            return new_access_token
        } catch (error) {
            // refresh token expired
            setAuth({});
            navigate("/loginpage", { state: { from: location }, replace: true });
            console.error(error);
        }
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
            console.log(response)
            let new_access_token = await refreshToken()
            console.log("refreshed access token")

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