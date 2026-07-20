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
    // null on all four data states means "not fetched yet" — the cards render a
    // muted placeholder for that case instead of zeros that read as real data
    const [tasksData, setTasksData] = useState(null);
    const [levelData, setLevelData] = useState(null);
    const [today, setToday] = useState(() => (DatetoISOString(new Date())));
    const [quote, setQuote] = useState("");

    // updates state variable today
    useEffect(() => {
        const now = new Date();
        const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0) - now //midnight next day

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

    function CircularProgressTotal({time, goal_time, loading = false, size = 280, strokeWidth = 40, bgColor = "#444" }) {
        // while loading, a 0% ring draws the background circle only
        const percentage = loading ? 0 : (time / (goal_time > 0 ? goal_time : 3600000)) * 100 // no goal: circle on a 1h visual cycle
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
                    fill={loading ? "#888" : "white"}
                    letterSpacing="2px"
                    style={{ marginBottom: "18px" }}
                >
                    {
                        loading ? "—" : (() => {
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


    function CircularProgress({percentage, completed_habits, total_habits, loading = false, size = 280, strokeWidth = 40, color = "rgb(0,230,122)", bgColor = "#444"}) {
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        // while loading, a 0% ring draws the background circle only
        const offset = circumference - ((loading ? 0 : percentage) / 100) * circumference;

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
                    fill={loading ? "#888" : "#fff"}
                    letterSpacing="2px"
                    style={{ marginBottom: "18px" }}
                >
                    {loading ? "—" : <>{completed_habits} / {total_habits}</>}
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
                            {levelData === null ? (
                                <span className="homepage-placeholder">Level —</span>
                            ) : (
                                <>
                                    Level {levelData.level}
                                    <span className="homepage-level-rank">{levelData.rank}-Rank</span>
                                </>
                            )}
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
                        {levelData === null ? (
                            <span className="homepage-placeholder">—</span>
                        ) : (
                            <>
                                <span className="homepage-xp-today">+{levelData.day_xp} XP today</span>
                                <span className="homepage-xp-label">
                                    {levelData.xp_into_level} / {levelData.xp_to_next} XP to level {levelData.level + 1}
                                </span>
                            </>
                        )}
                    </div>
                    {levelData?.streak_possible && (
                        levelData.streak_qualified ? (
                            <span className="homepage-streak-goal done">🔥 Streak secured for today</span>
                        ) : (
                            <span className="homepage-streak-goal">
                                🔥 {levelData.streak_remaining} XP to secure your streak today
                            </span>
                        )
                    )}
                </div>
                <div className = "homepage-habitcard">
                    <h3>Habits</h3>
                    <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px", marginBottom: "28px"}}>
                        <CircularProgress loading={habitsData === null} percentage={habitsData?.percentage ?? 0} completed_habits={habitsData?.completed_habits ?? 0} total_habits={habitsData?.total_habits ?? 0} />
                    </div>
                    <Link to="/habitpage">
                        <button>Go to Habits</button>
                    </Link>
                </div>
                <div className = "homepage-stopwatchcard">
                    <h3>Stopwatches</h3>
                        <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px", marginBottom: "28px" }}>
                                <CircularProgressTotal loading={stopwatchesData === null} time ={stopwatchesData?.total_time_worked ?? 0} goal_time = {stopwatchesData?.total_goal_time ?? 0}/>
                        </div>
                    <Link to="/stopwatchpage">
                        <button>Go to Stopwatches</button>
                    </Link>
                </div>
                <div className = "homepage-taskcard">
                    <h3>Tasks</h3>
                    <div className="homepage-task-summary">
                        {tasksData === null ? (
                            <span className="homepage-placeholder">—</span>
                        ) : (
                            <>
                                {tasksData.overdue.length > 0 && (
                                    <span className="homepage-task-overdue-count">{tasksData.overdue.length} overdue</span>
                                )}
                                <span>{tasksData.today.filter(task => task.done).length} / {tasksData.today.length} done today</span>
                            </>
                        )}
                    </div>
                    <div className="homepage-task-list">
                        {/* the empty state must wait for the fetch — otherwise it flashes "Nothing due today" */}
                        {tasksData !== null && (
                            <>
                                {[...tasksData.overdue, ...tasksData.today].length === 0 && (
                                    <p className="homepage-task-empty">Nothing due today</p>
                                )}
                                {[...tasksData.overdue, ...tasksData.today].slice(0, 6).map(task => (
                                    <div key={task.id} className={`homepage-task-item ${task.done ? 'done' : ''}`}>
                                        <span className={`homepage-task-dot ${tasksData.overdue.some(overdueTask => overdueTask.id === task.id) ? 'overdue' : ''}`}></span>
                                        <span className="homepage-task-description">{task.description}</span>
                                    </div>
                                ))}
                            </>
                        )}
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