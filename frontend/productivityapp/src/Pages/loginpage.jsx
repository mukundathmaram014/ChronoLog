import {useState, useEffect} from "react";
import { Link } from "react-router-dom";

export function LoginPage({onLogin}){

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  
  const handleSubmit = async e => {
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
        if (data.access_token){
            localStorage.setItem("token", data.access_token);
            onLogin();
        }
        else {
            setMessage(data.error);
            throw new Error("Login Failed")
        }
    } catch(error){
        console.error(error);
    };
  }


    
    return (
      <div className="Login-box">
        <form onSubmit={handleSubmit} className="Login-form">
          <h3>Login</h3>
          <input
            type="text"
            id="inputName"
            className="Login-username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Username"
            required
          />
          <input
            type="password"
            id="inputPassword"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="Login-password"
            placeholder="Password"
            required
          />

          <div className="Login-submit-grid">
            <button type="submit" className="Login-submit-button">
              Login
            </button>
          </div>
        {message && <div>{message}</div>}
        </form>
      </div>
    );
  }
