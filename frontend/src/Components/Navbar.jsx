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