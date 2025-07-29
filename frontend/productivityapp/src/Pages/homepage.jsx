import {useState, useEffect} from "react";

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

    function CircularProgress({percentage, completed_habits, total_habits, size = 180, strokeWidth = 30, color = "rgb(0,230,122)", bgColor = "#444"}) {
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
                    fontSize="1.2em"
                    fill="#fff"
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
            <div className = "homepage-habitcard">
                <h3>Habits</h3>
                <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px" }}>
                    <CircularProgress percentage={habitsData?.percentage ?? 0} completed_habits={habitsData?.completed_habits ?? 0} total_habits={habitsData?.total_habits ?? 0} />
                    <div style={{ marginTop: "8px", color: "#aaa" }}>Completion</div>
                </div>
            </div>
            <div className = "homepage-stopwatchcard">
            </div>
        </div>
    )
}