import {useState, useEffect} from "react";
import { Link } from "react-router-dom";
import './homepage.css';

export function Home() {

    const DatetoISOString = (Date) => {
        const year = Date.getFullYear();
        const month = String(Date.getMonth() + 1).padStart(2, '0');
        const day = String(Date.getDate()).padStart(2,'0');
        const isoString = year + "-" + month + "-" + day;
        return isoString;
    }

    const [habitsData, setHabitsData] = useState(null);
    const [stopwatchesData, setStopwatchesData] = useState(null);
    const [today, setToday] = useState(() => (DatetoISOString(new Date())));
    const [quote, setQuote] = useState(() => localStorage.getItem("dailyQuote") || "Daily Quote");

    // updates state variable today
    useEffect(() => {
        const now = new Date();
        const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDay() + 1, 0, 0, 0, 0) //midnight next day

        const timeout = setTimeout(() => {
        setToday((DatetoISOString(new Date())));
        }, msUntilMidnight);

        return () => clearTimeout(timeout);
    },[today]);

    // fetches habit data for today
    useEffect(() => {

                fetch(`http://localhost:5000/stats/habits/${today}/day/`, {
                    method: "GET",
                    })
                .then(response => response.json())
                .then(data => {
                    setHabitsData(data);
                })
                .catch(error => console.error(error))
    
        }, [today])

    // fetches stopwatch data for today
    useEffect(() => {

                fetch(`http://localhost:5000/stats/stopwatches/${today}/day/`, {
                    method: "GET",
                    })
                .then(response => response.json())
                .then(data => {
                    setStopwatchesData(data);
                })
                .catch(error => console.error(error))
    
        }, [today])

    // gets saved quote from local storage
    useEffect(() => {
        const savedQuote = localStorage.getItem("dailyQuote");
        if (savedQuote) setQuote(savedQuote);
    }, []);

    // stores saved quote in local storage
    useEffect(() => {
        localStorage.setItem("dailyQuote", quote);
    }, [quote]);


    const formatTimeString = (totalMilliSeconds) => {
        if (totalMilliSeconds < 0) totalMilliSeconds = 0;
        const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
        const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
        const centiseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0');
        return [hours, minutes, seconds, centiseconds];
            
          
    };

    function CircularProgressTotal({time, goal_time, size = 280, strokeWidth = 40, bgColor = "#444" }) {
        const percentage = (time / goal_time) * 100 ?? 0 
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - ((percentage % 100) / 100) * circumference;
        const r = 0
        const g = 230
        const b = 122
        const colorOffset = Math.floor(percentage / 100)
        const color = `rgb(${r}, ${g - (50 * colorOffset)}, ${b - (50 * colorOffset) })`
        const color2 = (colorOffset >= 1 ? `rgb(${r}, ${g - (50 * (colorOffset - 1) )}, ${b - (50 * (colorOffset-1)) })` : bgColor)


        return (
            <svg width={size} height={size}>
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={color2}
                    strokeWidth={strokeWidth}
                    fill="none"
                />
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={color}
                    strokeWidth={strokeWidth}
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="butt"
                    style={{ transition: "stroke-dashoffset 0.5s" }}
                />
                <text
                    x="50%"
                    y="50%"
                    textAnchor="middle"
                    dy=".3em"
                    fontSize="1.7rem"                
                    fontWeight="bold"              
                    fontFamily="'Roboto Mono', monospace"
                    fill="white"                  
                    letterSpacing="2px"
                    style={{ marginBottom: "18px" }}
                >
                    {
                        (() => {
                            const [ hours, minutes, seconds, centiseconds ] = formatTimeString(time);
                            return (
                                <>
                                    {hours}:{minutes}:{seconds}
                                    <tspan fontSize="0.7em" opacity="0.7">:{centiseconds}</tspan>
                                </>
                            );
                        })()
                    }
                </text>
            </svg>
        );
    }


    function CircularProgress({percentage, completed_habits, total_habits, size = 280, strokeWidth = 40, color = "rgb(0,230,122)", bgColor = "#444"}) {
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - (percentage / 100) * circumference;

        return (
            <svg width={size} height={size}>
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={bgColor}
                    strokeWidth={strokeWidth}
                    fill="none"
                />
                <circle
                    cx={size / 2}
                    cy={size / 2}
                    r={radius}
                    stroke={color}
                    strokeWidth={strokeWidth}
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="butt"
                    style={{ transition: "stroke-dashoffset 0.5s" }}
                />
                <text
                    x="50%"
                    y="50%"
                    textAnchor="middle"
                    dy=".3em"
                    fontSize="2rem"
                    fill="#fff"
                    letterSpacing="2px"
                    style={{ marginBottom: "18px" }}
                >
                    {completed_habits} / {total_habits}
                </text>
            </svg>
        );
    }


    return (
        <div className = "App">
            <div className = "homepage-header">
                <h1>Welcome back</h1>
                <h2>Here's how you're doing today</h2>
            </div>
            <div className = "homepage-cards-grid">
                <div className = "homepage-habitcard">
                    <h3>Habits</h3>
                    <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px", marginBottom: "28px"}}>
                        <CircularProgress percentage={habitsData?.percentage ?? 0} completed_habits={habitsData?.completed_habits ?? 0} total_habits={habitsData?.total_habits ?? 0} />
                    </div>
                    <Link to="/habitpage">
                        <button>Go to Habits</button>
                    </Link>
                </div>
                <div className = "homepage-stopwatchcard">
                    <h3>Stopwatches</h3>
                        <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px", marginBottom: "28px" }}>
                                <CircularProgressTotal time ={stopwatchesData?.total_time_worked ?? 0} goal_time = {stopwatchesData?.total_goal_time ?? 0}/> 
                        </div>
                    <Link to="/stopwatchpage">
                        <button>Go to Stopwatches</button>
                    </Link>
                </div>
                <div className = "homepage-quotesection">
                    <textarea
                        value={quote}
                        onChange={e => setQuote(e.target.value)}
                        rows={2}
                        className="homepage-quote-input"              
                    />
                </div>

            </div>
        </div>
    )
}