import { Link, useNavigate } from "react-router-dom"
import './Navbar.css';
import { useState, useContext} from "react";
import AuthContext from "../context/AuthProvider";
import { IoMdClose } from "react-icons/io";
import useAuth from "../hooks/useAuth";

export function Navbar() {
    const {auth} = useContext(AuthContext);
    const {setAuth} = useAuth();
    const [showProfilePopup, setShowProfilePopup] = useState(false);
    const [showXpRules, setShowXpRules] = useState(false);
    const navigate = useNavigate();

    const handleLogout = async () => {
    try {
        // Call backend logout endpoint to invalidate refresh token
        await fetch('/api/logout', {
            method: 'POST',
            credentials: "include",
            headers: {
                'Authorization': `Bearer ${auth.access_token}`
            }
        });
    } catch (err) {
        console.error('Logout error:', err);
    } finally {
        // Clear frontend auth state regardless of backend success
        setAuth({});
        navigate("/loginpage");
    }
}

    return (
        <>
             <div className = "navbar">
                <Link to="/homepage">
                    <button>Home</button>
                </Link>
                <Link to="/habitpage">
                    <button>Habits</button>
                </Link>
                <Link to="/taskpage">
                    <button>Tasks</button>
                </Link>
                <Link to="/goalpage">
                    <button>Goals</button>
                </Link>
                <Link to="/stopwatchpage">
                    <button>Stopwatch</button>
                </Link>
                <Link to="/statisticspage">
                    <button>Statistics</button>
                </Link>

                <div className="user-section">
                    <button 
                        className="user-button"
                        onClick={() => setShowProfilePopup(!showProfilePopup)}
                    >
                        {"👤"}
                    </button>
                    
                </div>
            </div>

            {auth.isGuest && (
                <div className="guest-banner">
                    You're using ChronoLog as a guest — guest data is deleted after 7 days.{" "}
                    <Link to="/">Sign up</Link> to keep your data.
                </div>
            )}

        {/* Profile Popup Overlay */}
            {showProfilePopup && (
                <div className="profile-overlay">
                    <div className="profile-popup">
                        <IoMdClose 
                            className="close-icon"
                            onClick={() => setShowProfilePopup(false)}
                        />
                        <div className="profile-avatar">
                            {auth.username ? auth.username.charAt(0).toUpperCase() : "?"}
                        </div>
                        <h2>User Profile</h2>
                        
                        <div className="profile-details">
                            <div className="profile-detail-item">
                                <label>Username</label>
                                <p>{auth.username || "Not available"}</p>
                            </div>
                            <div className="profile-detail-item">
                                <label>Email</label>
                                <p>{auth.email || "Not available"}</p>
                            </div>
                        </div>

                        <button
                            className="xp-rules-toggle"
                            onClick={() => setShowXpRules(prev => !prev)}
                        >
                            {showXpRules ? "Hide how XP & ranks work" : "How XP & ranks work"}
                        </button>

                        {showXpRules && (
                            <div className="xp-rules">
                                <h3>Earning XP</h3>
                                <ul className="xp-rules-list">
                                    <li><span>Habit — Easy</span><span>+10</span></li>
                                    <li><span>Habit — Medium</span><span>+25</span></li>
                                    <li><span>Habit — Hard</span><span>+50</span></li>
                                    <li><span>All habits done (bonus)</span><span>+25</span></li>
                                    <li><span>Tracked time</span><span>+20 / hour</span></li>
                                    <li><span>Tracked time — past daily goal</span><span>+30 / hour</span></li>
                                    <li><span>Hit daily goal time (bonus)</span><span>+50</span></li>
                                    <li><span>Goal — Easy</span><span>+500</span></li>
                                    <li><span>Goal — Medium</span><span>+2,000</span></li>
                                    <li><span>Goal — Hard</span><span>+5,000</span></li>
                                    <li><span>Goal — Extreme</span><span>+20,000</span></li>
                                </ul>
                                <p className="xp-rules-note">
                                    Finish every habit for a day, or log at least your daily goal time, to
                                    earn those bonuses. Your daily goal is the sum of your stopwatch goal
                                    times — hours logged past it also earn the higher overtime rate.
                                </p>

                                <h3>Streak</h3>
                                <p className="xp-rules-note">
                                    Keep your streak by completing at least 85% of a day's possible XP —
                                    essentially all your habits plus your goal time (you can miss a habit
                                    or two, or about an hour of work). Worked time counts only up to your
                                    goal. Each streak day adds ×0.1 to your habit XP, up to ×2.0 — miss a
                                    day and it resets.
                                </p>

                                <h3>Ranks</h3>
                                <ul className="xp-rules-list">
                                    <li><span className="xp-rank-letter rank-e">E</span><span>Levels 1–9</span></li>
                                    <li><span className="xp-rank-letter rank-d">D</span><span>Levels 10–24</span></li>
                                    <li><span className="xp-rank-letter rank-c">C</span><span>Levels 25–49</span></li>
                                    <li><span className="xp-rank-letter rank-b">B</span><span>Levels 50–74</span></li>
                                    <li><span className="xp-rank-letter rank-a">A</span><span>Levels 75–99</span></li>
                                    <li><span className="xp-rank-letter rank-s">S</span><span>Level 100+ · ultimate</span></li>
                                </ul>
                            </div>
                        )}

                        <button
                            className="logout-btn"
                            onClick={handleLogout}
                        >
                            Logout
                        </button>
                    </div>
                </div>
            )}
        
        </>
       
        )
}