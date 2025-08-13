import {useState, useEffect, useRef, useContext} from "react";
import { Link } from "react-router-dom";
import AuthContext from "../context/AuthProvider";

export function LoginPage(){

    const {setAuth} = useContext(AuthContext);
    const userRef = useRef();
    const errRef = useRef();

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [errMsg, setErrMsg] = useState('');
    const [success, setSuccess] = useState(false);

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
        if (access_token){
            setAuth({username, password, access_token})
            setUsername('');
            setPassword('');
            setSuccess(true);
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
      <>
        {success ? (
            <section>
                <h1>You are logged in!</h1>
                <br />
                <p>
                    <a href="#">Go to Home</a>
                </p>
            </section>
        ) : (
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
      )}
    </>
    );
  }
