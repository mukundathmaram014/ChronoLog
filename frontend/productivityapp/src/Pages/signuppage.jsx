import {useState, useEffect, useRef} from "react";
import { Link } from "react-router-dom";
import {faCheck, faTimes, faInfoCircle} from "@fortawesome/free-solid-svg-icons";
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome";

const USER_REGEX = /^[A-z][A-z0-9-_]{3,23}$/;
const PWD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[!@#$%]).{8,24}$/;
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function SignupPage(){

  const userRef = useRef();
  const errRef = useRef();

  const [username, setUsername] = useState("");
  const [validName, setValidName] = useState(false);
  const [userFocus, setUserFocus] = useState(false);

  const [email, setEmail] = useState("");
  const [validEmail, setValidEmail] = useState(false);
  const [emailFocus, setEmailFocus] = useState(false);

  const [password, setPassword] = useState("");
  const [validPwd, setValidPwd] = useState(false);
  const [pwdFocus, setPwdFocus] = useState(false);

  const [matchPwd, setMatchPwd] = useState("");
  const [validMatch, setValidMatch] = useState(false);
  const [matchFocus, setMatchFocus] = useState(false);

  const [errMsg, setErrMsg] = useState("");
  const [Success, setSuccess] = useState(false);
  
  useEffect(() => {
        userRef.current.focus();
    }, [])

  useEffect(() => {
      setValidName(USER_REGEX.test(username));
  }, [username])

  useEffect(() => {
      setValidEmail(EMAIL_REGEX.test(email));
  }, [email])

  useEffect(() => {
      setValidPwd(PWD_REGEX.test(password));
      setValidMatch(password === matchPwd);
  }, [password, matchPwd])

  useEffect(() => {
      setErrMsg('');
  }, [username, email, password, matchPwd])

  const handleSubmit = async (e) => {
    e.preventDefault();

    // if button enabled with JS hack
    const v1 = USER_REGEX.test(username);
    const v2 = PWD_REGEX.test(password);
    if (!v1 || !v2) {
        setErrMsg("Invalid Entry");
        return;
    }

    const newUser = {
        username: username,
        email: email,
        password: password
    }

    try{
        const response = await fetch(`http://localhost:5000/register`, {
            method: "POST",
            body: JSON.stringify(newUser)
        });

        const data = await response.json();
        if (response.status === 409) {
              setErrMsg(data.error);
              throw new Error("username or email already exists");
            }
        else if (response.status === 201){
              setSuccess(true);
              setUsername("");
              setEmail("");
              setPassword("");
              setMatchPwd("");
        }
 
        
    } catch(error){
        errRef.current.focus();
        console.error(error);
    };
  }


    
    return (
        <>
            {Success ? (
                <section>
                    <h1>Success!</h1>
                    <p>
                        <Link to="/loginpage">Log In</Link>
                    </p>
                </section>
            ) : (
                <div className="Signup-box">
                  <p ref={errRef} className={errMsg ? "errmsg" : "offscreen"} aria-live="assertive">{errMsg}</p>
                  <h1>Register</h1>
                  <form onSubmit={handleSubmit} className="Signup-form">
                    <label htmlFor = "username">
                      Username:
                      {validName && <FontAwesomeIcon icon={faCheck} className= "signup-check" />}
                      {!validName && username && <FontAwesomeIcon icon={faTimes} className="signup-x" />}
                    </label>
                    <input
                      type="text"
                      id="username"
                      ref={userRef}
                      autoComplete="off"
                      onChange={(e) => setUsername(e.target.value)}
                      value={username}
                      required
                      aria-invalid={validName ? "false" : "true"}
                      aria-describedby="uidnote"
                      onFocus={() => setUserFocus(true)}
                      onBlur={() => setUserFocus(false)}
                    />
                    {userFocus && username && !validName && <p id="uidnote" className = "username-instructions">
                        <FontAwesomeIcon icon={faInfoCircle} />
                        4 to 24 characters.<br />
                        Must begin with a letter.<br />
                        Letters, numbers, underscores, hyphens allowed.
                    </p>}

                    <label htmlFor = "email">
                      Email:
                      {validEmail && <FontAwesomeIcon icon={faCheck} className="signup-check" />}
                      {!validEmail && email && <FontAwesomeIcon icon={faTimes} className= "signup-x" />}
                    </label>
                    <input
                      type="text"
                      id="email"
                      autoComplete="off"
                      onChange={(e) => setEmail(e.target.value)}
                      value={email}
                      required
                      aria-invalid={validEmail ? "false" : "true"}
                      aria-describedby="emailnote"
                      onFocus={() => setEmailFocus(true)}
                      onBlur={() => setEmailFocus(false)}
                    />
                    {emailFocus && email && !validEmail && <p id="emailnote" className="email-instructions">
                      <FontAwesomeIcon icon={faInfoCircle} />
                      Must be a valid email address.<br />
                      Example: user@example.com<br />
                      No spaces or special characters outside of <b>@</b> and <b>.</b>
                    </p>}

                    <label htmlFor="password">
                        Password:
                        {validPwd && <FontAwesomeIcon icon={faCheck} className= "signup-check" />}
                        {!validPwd && password && <FontAwesomeIcon icon={faTimes} className= "signup-x"/>}
                    </label>
                    <input
                      type="password"
                      id="password"
                      onChange={(e) => setPassword(e.target.value)}
                      value={password}
                      required
                      aria-invalid={validPwd ? "false" : "true"}
                      aria-describedby="pwdnote"
                      onFocus={() => setPwdFocus(true)}
                      onBlur={() => setPwdFocus(false)}
                    />
                    {pwdFocus && !validPwd && <p id="pwdnote" className="password-instructions">
                        <FontAwesomeIcon icon={faInfoCircle} />
                        8 to 24 characters.<br />
                        Must include uppercase and lowercase letters, a number and a special character.<br />
                        Allowed special characters: <span aria-label="exclamation mark">!</span> <span aria-label="at symbol">@</span> <span aria-label="hashtag">#</span> <span aria-label="dollar sign">$</span> <span aria-label="percent">%</span>
                    </p>}

                    <label htmlFor="confirm_pwd">
                        Confirm Password:
                        {validMatch && matchPwd && <FontAwesomeIcon icon={faCheck} className="signup-check" />}
                        {!validMatch && matchPwd && <FontAwesomeIcon icon={faTimes} className="signup-x "/>}
                    </label>
                    <input
                        type="password"
                        id="confirm_pwd"
                        onChange={(e) => setMatchPwd(e.target.value)}
                        value={matchPwd}
                        required
                        aria-invalid={validMatch ? "false" : "true"}
                        aria-describedby="confirmnote"
                        onFocus={() => setMatchFocus(true)}
                        onBlur={() => setMatchFocus(false)}
                    />
                    {matchFocus && !validMatch && <p id="confirmnote" className="confirm-password-instructions">
                        <FontAwesomeIcon icon={faInfoCircle} />
                        Must match the first password input field.
                    </p>}

                    <button disabled={!validName || !validEmail ||  !validPwd || !validMatch ? true : false}>Sign Up</button>

                  </form>
                  <p>
                      Already registered?<br />
                      <span className="line">
                          <Link to="/loginpage">Log In</Link>
                      </span>
                  </p>
                </div>
                )}
      </>
    );
  }
