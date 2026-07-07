import {useState, useEffect} from "react";
import { Link } from "react-router-dom";
import './homepage.css';
import useFetch from "../hooks/useFetch";

export function Home() {

    const fetchWithAuth = useFetch();

    const DatetoISOString = (Date) => {
        const year = Date.getFullYear();
        const month = String(Date.getMonth() + 1).padStart(2, '0');
        const day = String(Date.getDate()).padStart(2,'0');
        const isoString = year + "-" + month + "-" + day;
        return isoString;
    }

    const [habitsData, setHabitsData] = useState(null);
    const [stopwatchesData, setStopwatchesData] = useState(null);
    const [tasksData, setTasksData] = useState({ overdue: [], today: [] });
    const [levelData, setLevelData] = useState(null);
    const [today, setToday] = useState(() => (DatetoISOString(new Date())));
    const [quote, setQuote] = useState("");

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

                fetchWithAuth(`/stats/habits/${today}/day/`, {
                    method: "GET"
                    })
                .then(response => response.json())
                .then(data => {
                    setHabitsData(data);
                })
                .catch(error => console.error(error))
                
        // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [today])

    
    // fetches stopwatch data for today
    useEffect(() => {

                fetchWithAuth(`/stats/stopwatches/${today}/day/`, {
                    method: "GET"
                    })
                .then(response => response.json())
                .then(data => {
                    setStopwatchesData(data);
                })
                .catch(error => console.error(error))
        // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [today])

    // fetches overdue + today's tasks
    useEffect(() => {

                fetchWithAuth(`/tasks/${today}/`, {
                    method: "GET"
                    })
                .then(response => response.json())
                .then(data => {
                    setTasksData({ overdue: data.overdue ?? [], today: data.today ?? [] });
                })
                .catch(error => console.error(error))
        // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [today])

    // fetches the user's XP / level readout
    useEffect(() => {

                fetchWithAuth(`/level/${today}/`, {
                    method: "GET"
                    })
                .then(response => response.json())
                .then(data => {
                    setLevelData(data);
                })
                .catch(error => console.error(error))
        // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [today])

    // fetches the user's saved homepage note
    useEffect(() => {

                fetchWithAuth(`/note`, {
                    method: "GET"
                    })
                .then(response => response.json())
                .then(data => {
                    setQuote(data?.homepage_note ?? "");
                })
                .catch(error => console.error(error))
        // eslint-disable-next-line react-hooks/exhaustive-deps
        }, [])

    // saves the user's homepage note
    const saveQuote = () => {
        fetchWithAuth(`/note`, {
            method: "PUT",
            body: JSON.stringify({ homepage_note: quote })
        })
        .catch(error => console.error(error))
    }


    const formatTimeString = (totalMilliSeconds) => {
        if (totalMilliSeconds < 0) totalMilliSeconds = 0;
        const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
        const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
        const centiseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0');
        return [hours, minutes, seconds, centiseconds];
            
          
    };

    function CircularProgressTotal({time, goal_time, size = 280, strokeWidth = 40, bgColor = "#444" }) {
        const percentage = goal_time > 0 ? (time / goal_time) * 100 : 100 // 0 goal = no goal, render full
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
                <div className = "homepage-levelcard">
                    <div className = "homepage-level-header">
                        <h3>
                            Level {levelData?.level ?? 1}
                            <span className="homepage-level-rank">{levelData?.rank ?? "E"}-Rank</span>
                        </h3>
                        {(levelData?.streak ?? 0) > 0 && (
                            <span className="homepage-level-streak">
                                🔥 {levelData.streak}-day streak · ×{levelData.multiplier.toFixed(1)} XP
                            </span>
                        )}
                    </div>
                    <div className={`homepage-xp-bar ${(levelData?.streak ?? 0) > 0 ? 'streak-active' : ''}`}>
                        <div className="homepage-xp-bar-fill"
                            style={{ width: `${levelData?.xp_to_next ? Math.min((levelData.xp_into_level / levelData.xp_to_next) * 100, 100) : 0}%` }}>
                        </div>
                    </div>
                    <div className="homepage-xp-footer">
                        <span className="homepage-xp-today">+{levelData?.day_xp ?? 0} XP today</span>
                        <span className="homepage-xp-label">
                            {levelData?.xp_into_level ?? 0} / {levelData?.xp_to_next ?? 0} XP to level {(levelData?.level ?? 1) + 1}
                        </span>
                    </div>
                </div>
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
                <div className = "homepage-taskcard">
                    <h3>Tasks</h3>
                    <div className="homepage-task-summary">
                        {tasksData.overdue.length > 0 && (
                            <span className="homepage-task-overdue-count">{tasksData.overdue.length} overdue</span>
                        )}
                        <span>{tasksData.today.filter(task => task.done).length} / {tasksData.today.length} done today</span>
                    </div>
                    <div className="homepage-task-list">
                        {[...tasksData.overdue, ...tasksData.today].length === 0 && (
                            <p className="homepage-task-empty">Nothing due today</p>
                        )}
                        {[...tasksData.overdue, ...tasksData.today].slice(0, 6).map(task => (
                            <div key={task.id} className={`homepage-task-item ${task.done ? 'done' : ''}`}>
                                <span className={`homepage-task-dot ${tasksData.overdue.some(overdueTask => overdueTask.id === task.id) ? 'overdue' : ''}`}></span>
                                <span className="homepage-task-description">{task.description}</span>
                            </div>
                        ))}
                    </div>
                    <Link to="/taskpage">
                        <button>Go to Tasks</button>
                    </Link>
                </div>
                <div className = "homepage-quotesection">
                    <textarea
                        value={quote}
                        onChange={e => setQuote(e.target.value)}
                        onBlur={saveQuote}
                        placeholder="Write a note..."
                        rows={2}
                        className="homepage-quote-input"
                    />
                </div>

            </div>
        </div>
    )
}