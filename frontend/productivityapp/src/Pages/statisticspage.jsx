import {useState, useEffect} from "react";
import './statisticspage.css';


export function Statistics() {

    const [selectedStatistics, setSelectedStatistics] = useState("habits")
    const [selectedTimePeriod, setSelectedTimePeriod] = useState("day");
    // const [today, setToday] = useState(() => (new Date()).toISOString().slice(0,10));
    const [selectedDate, setSelectedDate] = useState(() => (new Date()).toISOString().slice(0,10));
    const [statsData, setStatsData] = useState(null);
    const [habits, setHabits] = useState([]);
    const [stopwatches, setStopwatches] = useState([]);
    const [selectedHabit, setSelectedHabit] = useState("");
    const [selectedStopwatch, setSelectedStopwatch] = useState("");

    // fetches habits
    useEffect(() => {
        fetch(`http://localhost:5000/habits/${selectedDate}/`, {
        method: "GET"
        })
        .then( response => response.json())
        .then(data => setHabits(data.habits))
        .catch(error => console.error(error))
    }, [selectedDate]);

    //fetches stopwatches
    useEffect(() => {

        fetch(`http://localhost:5000/stopwatches/${selectedDate}/`, {
                method: "GET",
                })
        .then(response => response.json())
        .then(data => {
                setStopwatches((data.stopwatches));
            })
        .catch(error => console.error(error));

    }, [selectedDate]); 

    useEffect(() => {
            
            let query = "";
            if (selectedStatistics === "habits" && selectedHabit) {
                query = `?description=${encodeURIComponent(selectedHabit)}`;
            } else if (selectedStatistics === "stopwatches" && selectedStopwatch) {
                query = `?title=${encodeURIComponent(selectedStopwatch)}`;
            }

            fetch(`http://localhost:5000/stats/${selectedStatistics}/${selectedDate}/${selectedTimePeriod}/${query}`, {
                method: "GET",
                })
            .then(response => response.json())
            .then(data => {
                setStatsData(statsData => data);
            })
            .catch(error => console.error(error))

    }, [selectedTimePeriod, selectedStatistics, selectedDate, selectedHabit, selectedStopwatch])

    const formatTime = (totalMilliSeconds) => {
        const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
        const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
        const milliseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0');
        return (
            <>
                {hours}:{minutes}:{seconds}:<span className = "milliseconds">{milliseconds}</span>
            
            </>);
    };

    function CircularProgress({ percentage, size = 180, strokeWidth = 30, color = "rgb(0,230,122)", bgColor = "#444" }) {
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
                    {percentage?.toFixed(2)}%
                </text>
            </svg>
        );
    }

    const renderStats = () => {
        switch(selectedStatistics){
            case "habits": 
                return (
                    <div className = "habitstatistics">
                        {statsData && (
                            <>
                                <div className = "total-habits">
                                    Total Habits: {statsData.total_habits}
                                </div>
                                <div className = "completed-habits">
                                    Completed Habits: {statsData.completed_habits}
                                </div>
                                <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px" }}>
                                    <CircularProgress percentage={statsData.percentage ?? 0} />
                                    <div style={{ marginTop: "8px", color: "#aaa" }}>Completion</div>
                                </div>
                            </>
                        )}

                    </div>
                );
            case "stopwatches": 
                return (
                    <div className = "stopwatchstatistics">
                        {statsData && (
                            <>
                                <div className = "total-time-worked">
                                    Total Time Worked: {formatTime(statsData.total_time_worked)}
                                </div>
                                <div className = "average-time-worked">
                                    Average Time Worked Per Day: {formatTime(statsData.average_time_worked_per_day)}
                                </div>
                            </>
                        )}

                    </div>
                );
            default: 
                return (
                    <h2>default case</h2>
                );
        }
    }

    return (
        <div className = "App">
            <div className="date-slider-container">
            <label htmlFor="date-slider">Select Date: </label>
            <input
                type="date"
                id="date-slider"
                value={selectedDate}
                onChange={e => setSelectedDate(e.target.value)}
            />
            </div>
            <h1>Statistics</h1>
            <div className = "statistics-wrapper">
                <div className = "selection-bar">
                    <div className = "stats-select-bar">
                    <select value = {selectedStatistics} onChange = {e => setSelectedStatistics(e.target.value)}>
                    <option value= "habits">Habits</option>
                    <option value = "stopwatches">Stopwatches</option>
                    </select>
                    </div>
                    <div className = "time-period-select-bar">
                    <select value={selectedTimePeriod} onChange={e => setSelectedTimePeriod(e.target.value)}>
                    <option value="day">Day</option>
                    <option value="week">Week</option>
                    <option value="month">Month</option>
                    <option value="year">Year</option>
                    </select>
                    </div>
                    <div className = "habits-or-stopwatches-select-bar">
                    <select value = {selectedStatistics === "habits" ? selectedHabit : selectedStopwatch}
                     onChange = {e => {if (selectedStatistics === "habits"){ setSelectedHabit(e.target.value)}
                                       else {setSelectedStopwatch(e.target.value)}}}>
                    {selectedStatistics === "habits" && (
                        <option value="">All Habits</option>
                    )} 
                    {(selectedStatistics === "habits" ? habits : stopwatches).map(item => (
                        // For stopwatches, use the title as the value, but for the "Total Time" stopwatch, use an empty string ("").
                        // This ensures selecting "Total Time" or "All Habits" results in no query parameter being sent to the backend.
                        <option 
                            key={item.id} 
                            value={selectedStatistics === "habits" ? item.description : (item.title === "Total Time" ? "" : item.title)}> 
                            {selectedStatistics === "habits" ? item.description : item.title}
                        </option>
                    ))}   
                    </select>
                    </div>
                </div>

            {renderStats()}
            </div>

        </div>
    )

}