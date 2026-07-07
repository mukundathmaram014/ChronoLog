import {useState, useEffect} from "react";
import './statisticspage.css';
import useFetch from "../hooks/useFetch";
import HabitCalendar from "../Components/HabitCalendar";

// Slice colors for the stopwatch pie: starts from the app's green accent, then
// hues spaced for distinguishability on the dark background. Cycles if exceeded.
const PIE_COLORS = [
    "rgb(0, 230, 122)",
    "rgb(77, 163, 255)",
    "rgb(255, 184, 77)",
    "rgb(179, 139, 255)",
    "rgb(255, 107, 129)",
    "rgb(77, 215, 230)",
    "rgb(255, 225, 77)",
    "rgb(230, 120, 220)",
];

export function Statistics() {

    const fetchWithAuth = useFetch();

    const DatetoISOString = (Date) => {
        const year = Date.getFullYear();
        const month = String(Date.getMonth() + 1).padStart(2, '0');
        const day = String(Date.getDate()).padStart(2,'0');
        const isoString = year + "-" + month + "-" + day;
        return isoString;
    }

    const [selectedStatistics, setSelectedStatistics] = useState("habits")
    const [selectedTimePeriod, setSelectedTimePeriod] = useState("day");
    const [selectedDate, setSelectedDate] = useState(() => (DatetoISOString(new Date())));
    const [statsData, setStatsData] = useState(null);
    const [habits, setHabits] = useState([]);
    const [stopwatches, setStopwatches] = useState([]);
    const [selectedHabit, setSelectedHabit] = useState("");
    const [selectedStopwatch, setSelectedStopwatch] = useState("");
    const [breakdownData, setBreakdownData] = useState([]);
    const [combinedData, setCombinedData] = useState(null);
    const [calendarData, setCalendarData] = useState(null);


    // fetches the habits and stopwatches for the selector. For "day" these are the
    // day's own items; for longer periods, the distinct items that existed on any
    // day within the period. If the previously selected item isn't in the new list,
    // the selection falls back to the all/total view.
    useEffect(() => {
        if (selectedTimePeriod === "day") {
            fetchWithAuth(`/habits/${selectedDate}/`, {
            method: "GET"
            })
            .then( response => response.json())
            .then(data => {
                setHabits(data.habits);
                setSelectedHabit(prev => data.habits.some(habit => habit.description === prev) ? prev : "");
            })
            .catch(error => console.error(error))

            fetchWithAuth(`/stopwatches/${selectedDate}/`, {
                    method: "GET"
                    })
            .then(response => response.json())
            .then(data => {
                    setStopwatches((data.stopwatches));
                    setSelectedStopwatch(prev => data.stopwatches.some(stopwatch => stopwatch.title === prev) ? prev : "");
                })
            .catch(error => console.error(error));
        } else {
            fetchWithAuth(`/stats/items/${selectedDate}/${selectedTimePeriod}/`, {
                method: "GET"
                })
            .then(response => response.json())
            .then(data => {
                setHabits(data.habits.map(description => ({ id: description, description })));
                setStopwatches(data.stopwatches.map(title => ({ id: title, title })));
                setSelectedHabit(prev => data.habits.includes(prev) ? prev : "");
                setSelectedStopwatch(prev => data.stopwatches.includes(prev) ? prev : "");
            })
            .catch(error => console.error(error));
        }

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedDate, selectedTimePeriod]);

    useEffect(() => {
            
            let query = "";
            if (selectedStatistics === "habits" && selectedHabit) {
                query = `?description=${encodeURIComponent(selectedHabit)}`;
            } else if (selectedStatistics === "stopwatches" && selectedStopwatch) {
                query = `?title=${encodeURIComponent(selectedStopwatch)}`;
            }

            fetchWithAuth(`/stats/${selectedStatistics}/${selectedDate}/${selectedTimePeriod}/${query}`, {
                method: "GET"
                })
            .then(response => response.json())
            .then(data => {
                setStatsData(data);
            })
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedTimePeriod, selectedStatistics, selectedDate, selectedHabit, selectedStopwatch])

    // fetches the aggregate Total + per-item stats for the combined view (spec 0016)
    useEffect(() => {
            fetchWithAuth(`/stats/${selectedStatistics}/all/${selectedDate}/${selectedTimePeriod}/`, {
                method: "GET"
                })
            .then(response => response.json())
            .then(data => setCombinedData(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod])

    // fetches the per-day habit calendar, driven by the current habit selection:
    // a single habit -> status calendar; "All Habits" -> Total intensity heatmap (spec 0016)
    useEffect(() => {
            if (selectedStatistics !== "habits") { setCalendarData(null); return; }
            const query = selectedHabit ? `?description=${encodeURIComponent(selectedHabit)}` : "";
            fetchWithAuth(`/stats/habits/calendar/${selectedDate}/${selectedTimePeriod}/${query}`, {
                method: "GET"
                })
            .then(response => response.json())
            .then(data => setCalendarData(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod, selectedHabit])

    // fetches the per-stopwatch time breakdown for the pie chart
    useEffect(() => {

            if (selectedStatistics !== "stopwatches") return;

            fetchWithAuth(`/stats/stopwatches/breakdown/${selectedDate}/${selectedTimePeriod}/`, {
                method: "GET"
                })
            .then(response => response.json())
            .then(data => {
                setBreakdownData(data.breakdown ?? []);
            })
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod])

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

    const formatTimeString = (totalMilliSeconds) => {
        if (totalMilliSeconds < 0) totalMilliSeconds = 0;
        const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
        const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
        const centiseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0');
        return [hours, minutes, seconds, centiseconds];
            
          
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

    function CircularProgressTotal({time, goal_time, size = 550, strokeWidth = 80, bgColor = "#444" }) {
        const percentage = (time / (goal_time > 0 ? goal_time : 3600000)) * 100 // no goal: circle on a 1h visual cycle
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
                    fontSize="3.7rem"                
                    fontWeight="bold"              
                    fontFamily="'Roboto Mono', monospace"
                    fill="white"                  
                    letterSpacing="2px"
                    style={{ marginBottom: "8px" }}
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

    function StopwatchPie({ breakdown, size = 300 }) {
        const slices = [...breakdown]
            .filter(item => item.duration > 0)
            .sort((a, b) => b.duration - a.duration);
        const total = slices.reduce((sum, item) => sum + item.duration, 0);

        if (total === 0) {
            return (
                <div className="pie-empty">No time logged for this period</div>
            );
        }

        const cx = size / 2;
        const cy = size / 2;
        const radius = size / 2 - 2;
        // angle measured clockwise from 12 o'clock
        const point = (angle) => [
            cx + radius * Math.sin(angle),
            cy - radius * Math.cos(angle),
        ];

        let startAngle = 0;
        const pieSlices = slices.map((item, index) => {
            const sweep = (item.duration / total) * 2 * Math.PI;
            const [x0, y0] = point(startAngle);
            const [x1, y1] = point(startAngle + sweep);
            const largeArc = sweep > Math.PI ? 1 : 0;
            const d = `M ${cx} ${cy} L ${x0} ${y0} A ${radius} ${radius} 0 ${largeArc} 1 ${x1} ${y1} Z`;
            startAngle += sweep;
            return { ...item, d, color: PIE_COLORS[index % PIE_COLORS.length] };
        });

        return (
            <div className="stopwatch-pie">
                <svg width={size} height={size}>
                    {pieSlices.length === 1 ? (
                        // a 100% arc degenerates (start point == end point), so draw a full circle
                        <circle cx={cx} cy={cy} r={radius} fill={pieSlices[0].color} />
                    ) : (
                        pieSlices.map(slice => (
                            <path key={slice.title} d={slice.d} fill={slice.color} stroke="#232323" strokeWidth="2" />
                        ))
                    )}
                </svg>
                <div className="pie-legend">
                    {pieSlices.map(slice => {
                        const [hours, minutes] = formatTimeString(slice.duration);
                        const percent = ((slice.duration / total) * 100).toFixed(1);
                        return (
                            <div key={slice.title} className="pie-legend-item">
                                <span className="pie-legend-swatch" style={{ backgroundColor: slice.color }}></span>
                                <span className="pie-legend-title">{slice.title}</span>
                                <span className="pie-legend-value">{hours}h {minutes}m ({percent}%)</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    const renderStats = () => {
        switch(selectedStatistics){
            case "habits": 
                return (
                    <div className = "habitstatistics">
                        {statsData && (
                            <>
                                <div className = "total-habits-statistics">
                                    Total Habits: {statsData.total_habits}
                                </div>
                                <div className = "completed-habits-statistics">
                                    Completed Habits: {statsData.completed_habits}
                                </div>
                                <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px" }}>
                                    <CircularProgress percentage={statsData.percentage ?? 0} />
                                    <div style={{ marginTop: "8px", color: "#aaa" }}>Completion</div>
                                </div>
                            </>
                        )}

                        {calendarData && (
                            <div className="habit-calendar-section">
                                <p>{selectedHabit
                                    ? `Consistency — ${selectedHabit}`
                                    : "Consistency heatmap — all habits"}</p>
                                <HabitCalendar mode={calendarData.mode} days={calendarData.days} period={selectedTimePeriod} />
                            </div>
                        )}

                        {!selectedHabit && combinedData?.items?.length > 0 && (
                            <div className="per-item-list">
                                <p>Per-habit breakdown</p>
                                {combinedData.items.map(item => (
                                    <div key={item.description} className="per-item-card">
                                        <span className="per-item-name">{item.description}</span>
                                        <span className="per-item-stat">{item.completed_habits}/{item.total_habits}</span>
                                        <span className="per-item-pct">{item.percentage.toFixed(0)}%</span>
                                    </div>
                                ))}
                            </div>
                        )}

                    </div>
                );
            case "stopwatches": 
                return (
                    <div className = "stopwatchstatistics">
                        {statsData && (
                            <>
                                <div className = "total-time-worked">
                                    <p>Total Time Worked: </p>
                                    <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px", marginBottom: "50px" }}>
                                            <CircularProgressTotal time ={statsData.total_time_worked} goal_time = {statsData.total_goal_time}/> 
                                    </div>
                                    <div className="statistics-goal-time">
                                        {(() => {
                                            const [goalHours, goalMinutes] = formatTimeString(statsData.total_goal_time);
                                            return <>Total Goal Time: {goalHours}h {goalMinutes}m</>;
                                        })()}
                                    </div>  
                                </div>
                                <div className = "average-time-worked">
                                    Average Time Worked Per Day: {formatTime(statsData.average_time_worked_per_day)}
                                </div>
                                <div className = "stopwatch-pie-section">
                                    <p>Time by Stopwatch: </p>
                                    <StopwatchPie breakdown={breakdownData} />
                                </div>
                            </>
                        )}

                        {!selectedStopwatch && combinedData?.items?.length > 0 && (
                            <div className="per-item-list">
                                <p>Per-stopwatch breakdown</p>
                                {combinedData.items.map(item => {
                                    const [hrs, mins] = formatTimeString(item.total_time_worked);
                                    return (
                                        <div key={item.title} className="per-item-card">
                                            <span className="per-item-name">{item.title}</span>
                                            <span className="per-item-stat">{hrs}h {mins}m</span>
                                        </div>
                                    );
                                })}
                            </div>
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