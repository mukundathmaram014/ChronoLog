import {useState, useEffect, useRef} from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import useAuth from "../hooks/useAuth";

export function LoginPage(){

    const {setAuth} = useAuth();

    const navigate = useNavigate();
    const location = useLocation();
    const from = location.state?.from?.pathname || "/";


    const userRef = useRef();
    const errRef = useRef();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [errMsg, setErrMsg] = useState('');

    useEffect(() => {
        userRef.current.focus();
    }, [])

    useEffect(() => {
        setErrMsg('');
    }, [username, password])

  
  const handleSubmit = async (e) => {
    e.preventDefault();

    const User = {
        username: username,
        password: password
    }

    try{
        const response = await fetch(`http://127.0.0.1:5000/login`, {
            method: "POST",
            body: JSON.stringify(User)
        });

        const data = await response.json();
        console.log(data);
        const access_token = data.access_token
        console.log(access_token);
        if (access_token){
            setAuth({username, password, access_token})
            setUsername('');
            setPassword('');
            if (from === "/"){
                navigate("/homepage", {replace : true});
            } else {
                navigate(from, {replace : true});
            }
        }
        else {
            setErrMsg(data.error);
            throw new Error("Login Failed")
        }
    } catch(error){
        errRef.current.focus();
        console.error(error);
    };
  }


    
    return (
            <div className="Login-box">
                <p ref={errRef} className={errMsg ? "errmsg" : "offscreen"} aria-live="assertive">{errMsg}</p>
                <h1>Login</h1>
                <form onSubmit={handleSubmit} className="Login-form">
                <label htmlFor="username">Username:</label>
                <input
                    type="text"
                    id="username"
                    className="Login-username"
                    ref={userRef}
                    autoComplete="off"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                />

                <label htmlFor="password">Password:</label>
                <input
                    type="password"
                    id="inputPassword"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="Login-password"
                    required
                />

                <button>Log In</button>
               
                </form>
                <p>
                    Need an Account?<br />
                    <span className="line">
                        <Link to="/">Sign Up</Link>
                    </span>
                </p>
            </div>
    );
  }
