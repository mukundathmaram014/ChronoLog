import { Link } from "react-router-dom"
import './Navbar.css';

export function Navbar() {
    return (
        <div className = "navbar">
            <Link to="/">
                <button>Home</button>
            </Link>
            <Link to="/habitpage">
                <button>Habits</button>
            </Link>
            <Link to="/stopwatchpage">
                <button>Stopwatch</button>
            </Link>
            </div>
        )
}