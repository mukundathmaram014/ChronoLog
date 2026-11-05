import {useState, useEffect, useRef} from "react";
import './statisticspage.css';
import useFetch from "../hooks/useFetch";
import HabitCalendar from "../Components/HabitCalendar";
import StatsOverview from "../Components/StatsOverview";

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

    const [selectedStatistics, setSelectedStatistics] = useState("overview")
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
    // spec 0029: "combined" = the existing all-habits heatmap, "per-habit" = a grid
    // of one mini status calendar per habit. Only applies when no habit is selected.
    const [calendarView, setCalendarView] = useState("combined");
    const [perHabitCalendars, setPerHabitCalendars] = useState(null);
    const [timeCalendarData, setTimeCalendarData] = useState(null);
    const [xpData, setXpData] = useState(null);
    // a week counts towards the year holding its Thursday (see overview_year_of in the backend)
    const [overviewYear, setOverviewYear] = useState(() => {
        const thursday = new Date();
        thursday.setDate(thursday.getDate() - ((thursday.getDay() + 6) % 7) + 3);
        return thursday.getFullYear();
    });
    const [overviewData, setOverviewData] = useState(null);
    const [overviewVersion, setOverviewVersion] = useState(0);


    // Rows for days the app wasn't opened only get created when a day page reads a
    // later date, so do that once for today before anything reads stats. Everything
    // below waits on it, including the selector fetch of the same day: two carry-forwards
    // running at once would create duplicate rows. Must stay the first effect on the page.
    const syncRef = useRef(null);
    useEffect(() => {
        if (syncRef.current) return;
        const today = DatetoISOString(new Date());
        syncRef.current = Promise.all([
            fetchWithAuth(`/habits/${today}/`, { method: "GET" }),
            fetchWithAuth(`/stopwatches/${today}/`, { method: "GET" }),
        ]).catch(error => console.error(error));
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const fetchAfterSync = (path) => syncRef.current.then(() => fetchWithAuth(path, { method: "GET" }));

    // fetches the habits and stopwatches for the selector. For "day" these are the
    // day's own items; for longer periods, the distinct items that existed on any
    // day within the period. If the previously selected item isn't in the new list,
    // the selection falls back to the all/total view.
    useEffect(() => {
        if (selectedTimePeriod === "day") {
            fetchAfterSync(`/habits/${selectedDate}/`)
            .then( response => response.json())
            .then(data => {
                setHabits(data.habits);
                setSelectedHabit(prev => data.habits.some(habit => habit.description === prev) ? prev : "");
            })
            .catch(error => console.error(error))

            fetchAfterSync(`/stopwatches/${selectedDate}/`)
            .then(response => response.json())
            .then(data => {
                    setStopwatches((data.stopwatches));
                    setSelectedStopwatch(prev => data.stopwatches.some(stopwatch => stopwatch.title === prev) ? prev : "");
                })
            .catch(error => console.error(error));
        } else {
            fetchAfterSync(`/stats/items/${selectedDate}/${selectedTimePeriod}/`)
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
            if (selectedStatistics === "xp" || selectedStatistics === "overview") return; // fetched by their own effects below

            // the server's clock is UTC; the average needs to know what day it is for the user
            let query = `?today=${DatetoISOString(new Date())}`;
            if (selectedStatistics === "habits" && selectedHabit) {
                query += `&description=${encodeURIComponent(selectedHabit)}`;
            } else if (selectedStatistics === "stopwatches" && selectedStopwatch) {
                query += `&title=${encodeURIComponent(selectedStopwatch)}`;
            }

            fetchAfterSync(`/stats/${selectedStatistics}/${selectedDate}/${selectedTimePeriod}/${query}`)
            .then(response => response.json())
            .then(data => {
                setStatsData(data);
            })
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedTimePeriod, selectedStatistics, selectedDate, selectedHabit, selectedStopwatch])

    // fetches the aggregate Total + per-item stats for the combined view (spec 0016)
    useEffect(() => {
            if (selectedStatistics === "xp" || selectedStatistics === "overview") return; // no "all" variant for these

            fetchAfterSync(`/stats/${selectedStatistics}/all/${selectedDate}/${selectedTimePeriod}/?today=${DatetoISOString(new Date())}`)
            .then(response => response.json())
            .then(data => setCombinedData(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod])

    // fetches one year of weekly rows and the XP curve for the Overview section (spec 0039)
    useEffect(() => {
            if (selectedStatistics !== "overview") return;

            fetchAfterSync(`/stats/overview/${overviewYear}/?today=${DatetoISOString(new Date())}`)
            .then(response => response.json())
            .then(data => setOverviewData(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, overviewYear, overviewVersion])

    // fetches the period-aware XP readout (spec 0034)
    useEffect(() => {
            if (selectedStatistics !== "xp") { setXpData(null); return; }

            fetchAfterSync(`/stats/xp/${selectedDate}/${selectedTimePeriod}/`)
            .then(response => response.json())
            .then(data => setXpData(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod])

    // fetches the per-day habit calendar, driven by the current habit selection:
    // a single habit -> status calendar; "All Habits" -> Total intensity heatmap (spec 0016)
    useEffect(() => {
            if (selectedStatistics !== "habits") { setCalendarData(null); return; }
            // the per-habit view renders from its own batch fetch below
            if (!selectedHabit && calendarView === "per-habit") { setCalendarData(null); return; }
            const query = selectedHabit ? `?description=${encodeURIComponent(selectedHabit)}` : "";
            fetchAfterSync(`/stats/habits/calendar/${selectedDate}/${selectedTimePeriod}/${query}`)
            .then(response => response.json())
            .then(data => setCalendarData(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod, selectedHabit, calendarView])

    // fetches every habit's status calendar in one request for the per-habit view (spec 0029)
    useEffect(() => {
            if (selectedStatistics !== "habits" || selectedHabit || calendarView !== "per-habit") {
                setPerHabitCalendars(null);
                return;
            }
            fetchAfterSync(`/stats/habits/calendar/all/${selectedDate}/${selectedTimePeriod}/`)
            .then(response => response.json())
            .then(data => setPerHabitCalendars(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod, selectedHabit, calendarView])

    // fetches the per-day Total time series for the stopwatch time calendar (spec 0029)
    useEffect(() => {
            if (selectedStatistics !== "stopwatches" || selectedStopwatch) {
                setTimeCalendarData(null);
                return;
            }
            fetchAfterSync(`/stats/stopwatches/calendar/${selectedDate}/${selectedTimePeriod}/`)
            .then(response => response.json())
            .then(data => setTimeCalendarData(data))
            .catch(error => console.error(error))

    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedStatistics, selectedDate, selectedTimePeriod, selectedStopwatch])

    // fetches the per-stopwatch time breakdown for the pie chart
    useEffect(() => {

            if (selectedStatistics !== "stopwatches") return;

            fetchAfterSync(`/stats/stopwatches/breakdown/${selectedDate}/${selectedTimePeriod}/`)
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
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="fluid-svg">
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
            <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="fluid-svg">
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

    // Generic breakdown pie (spec 0034): takes {label, value} items plus a
    // formatValue callback for the legend, so both the stopwatch and XP
    // sections can share one pie instead of each hardcoding a value shape.
    function BreakdownPie({ items, formatValue, size = 300, emptyMessage = "No data for this period" }) {
        const slices = [...items]
            .filter(item => item.value > 0)
            .sort((a, b) => b.value - a.value);
        const total = slices.reduce((sum, item) => sum + item.value, 0);

        if (total === 0) {
            return (
                <div className="pie-empty">{emptyMessage}</div>
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
            const sweep = (item.value / total) * 2 * Math.PI;
            const [x0, y0] = point(startAngle);
            const [x1, y1] = point(startAngle + sweep);
            const largeArc = sweep > Math.PI ? 1 : 0;
            const d = `M ${cx} ${cy} L ${x0} ${y0} A ${radius} ${radius} 0 ${largeArc} 1 ${x1} ${y1} Z`;
            startAngle += sweep;
            return { ...item, d, color: PIE_COLORS[index % PIE_COLORS.length] };
        });

        return (
            <div className="stopwatch-pie">
                <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="fluid-svg">
                    {pieSlices.length === 1 ? (
                        // a 100% arc degenerates (start point == end point), so draw a full circle
                        <circle cx={cx} cy={cy} r={radius} fill={pieSlices[0].color} />
                    ) : (
                        pieSlices.map(slice => (
                            <path key={slice.label} d={slice.d} fill={slice.color} stroke="#232323" strokeWidth="2" />
                        ))
                    )}
                </svg>
                <div className="pie-legend">
                    {pieSlices.map(slice => {
                        const percent = ((slice.value / total) * 100).toFixed(1);
                        return (
                            <div key={slice.label} className="pie-legend-item">
                                <span className="pie-legend-swatch" style={{ backgroundColor: slice.color }}></span>
                                <span className="pie-legend-title">{slice.label}</span>
                                <span className="pie-legend-value">{formatValue(slice.value)} ({percent}%)</span>
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    const renderStats = () => {
        switch(selectedStatistics){
            case "overview":
                return (
                    <StatsOverview
                        data={overviewData}
                        fetchWithAuth={fetchWithAuth}
                        onOpenWeek={weekStart => {
                            setSelectedDate(weekStart);
                            setSelectedTimePeriod("week");
                            setSelectedStatistics("habits");
                            window.scrollTo(0, 0);
                        }}
                        onNoteSaved={(weekStart, note) => setOverviewData(previous => ({
                            ...previous,
                            weeks: previous.weeks.map(week => week.week_start === weekStart ? { ...week, note } : week),
                        }))}
                        onImported={() => setOverviewVersion(version => version + 1)}
                    />
                );
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

                        {perHabitCalendars?.habits && (
                            <div className="habit-calendar-section">
                                <p>Consistency — per habit</p>
                                {perHabitCalendars.habits.length === 0 ? (
                                    <div className="calendar-empty">No habits in this period.</div>
                                ) : (
                                    // year heatmaps are too wide to sit side by side: one per row instead
                                    <div className={`per-habit-calendar-grid${selectedTimePeriod === "year" ? " per-habit-calendar-grid-year" : ""}`}>
                                        {perHabitCalendars.habits.map(habit => (
                                            <div key={habit.description} className="per-habit-calendar-card">
                                                <span className="per-habit-calendar-title">{habit.description}</span>
                                                <HabitCalendar
                                                    mode="status"
                                                    days={habit.days}
                                                    period={selectedTimePeriod}
                                                    compact={selectedTimePeriod !== "year"}
                                                />
                                            </div>
                                        ))}
                                    </div>
                                )}
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
                                    <BreakdownPie
                                        items={breakdownData.map(item => ({ label: item.title, value: item.duration }))}
                                        formatValue={value => {
                                            const [hours, minutes] = formatTimeString(value);
                                            return `${hours}h ${minutes}m`;
                                        }}
                                        emptyMessage="No time logged for this period"
                                    />
                                </div>
                            </>
                        )}

                        {timeCalendarData?.days && (
                            <div className="habit-calendar-section">
                                <p>Time worked</p>
                                <HabitCalendar mode="time" days={timeCalendarData.days} period={selectedTimePeriod} />
                            </div>
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
            case "xp":
                return (
                    <div className = "xpstatistics">
                        {xpData && (
                            <>
                                <div className="xp-level-row">
                                    <div className="xp-level-badge">
                                        Level {xpData.level.level} <span className="xp-rank">({xpData.level.rank})</span>
                                    </div>
                                    <div className="xp-level-bar-wrap">
                                        <div className="xp-level-bar">
                                            <div
                                                className="xp-level-bar-fill"
                                                style={{
                                                    width: `${Math.min(100,
                                                        (xpData.level.xp_into_level /
                                                            (xpData.level.xp_into_level + xpData.level.xp_to_next || 1)) * 100
                                                    )}%`
                                                }}
                                            />
                                        </div>
                                        <div className="xp-level-bar-label">
                                            {xpData.level.xp_into_level} / {xpData.level.xp_into_level + xpData.level.xp_to_next} XP
                                        </div>
                                    </div>
                                </div>

                                <div className="xp-stat-row">
                                    <div className="xp-stat-card">
                                        <span className="xp-stat-label">Total XP</span>
                                        <span className="xp-stat-value">{xpData.total.xp}</span>
                                    </div>
                                    <div className="xp-stat-card">
                                        <span className="xp-stat-label">Average XP / Day</span>
                                        <span className="xp-stat-value">{xpData.total.average_per_day.toFixed(1)}</span>
                                    </div>
                                    <div className="xp-stat-card">
                                        <span className="xp-stat-label">Best Day</span>
                                        <span className="xp-stat-value">
                                            {xpData.best_day ? `${xpData.best_day.xp} XP (${xpData.best_day.date})` : "—"}
                                        </span>
                                    </div>
                                </div>

                                <div className="xp-stat-row">
                                    <div className="xp-stat-card">
                                        <span className="xp-stat-label">Current Streak</span>
                                        <span className="xp-stat-value">{xpData.streak.current}</span>
                                    </div>
                                    <div className="xp-stat-card">
                                        <span className="xp-stat-label">Longest Streak</span>
                                        <span className="xp-stat-value">{xpData.streak.longest}</span>
                                    </div>
                                    <div className="xp-stat-card">
                                        <span className="xp-stat-label">Qualifying Days</span>
                                        <span className="xp-stat-value">{xpData.streak.qualified_days}/{xpData.total.days_counted}</span>
                                    </div>
                                </div>

                                <div className="habit-calendar-section">
                                    <p>XP heatmap</p>
                                    <HabitCalendar mode="xp" days={xpData.days} period={selectedTimePeriod} />
                                </div>

                                <div className = "stopwatch-pie-section">
                                    <p>XP by Source: </p>
                                    <BreakdownPie
                                        items={xpData.breakdown.map(item => ({ label: item.source, value: item.xp }))}
                                        formatValue={value => `${value} XP`}
                                        emptyMessage="No XP earned this period"
                                    />
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
            {selectedStatistics !== "overview" && (
            <div className="date-slider-container">
            <label htmlFor="date-slider">Select Date: </label>
            <input
                type="date"
                id="date-slider"
                value={selectedDate}
                onChange={e => setSelectedDate(e.target.value)}
            />
            </div>
            )}
            <h1>Statistics</h1>
            <div className = "statistics-wrapper">
                <div className = "selection-bar">
                    <div className = "stats-select-bar">
                    <select value = {selectedStatistics} onChange = {e => setSelectedStatistics(e.target.value)}>
                    <option value = "overview">Overview</option>
                    <option value= "habits">Habits</option>
                    <option value = "stopwatches">Stopwatches</option>
                    <option value = "xp">XP</option>
                    </select>
                    </div>
                    {selectedStatistics === "overview" ? (
                        <div className = "year-select-bar">
                        <select aria-label="Year" value={overviewYear} onChange={e => setOverviewYear(Number(e.target.value))}>
                        {(overviewData?.years ?? [overviewYear]).map(year => (
                            <option key={year} value={year}>{year}</option>
                        ))}
                        </select>
                        </div>
                    ) : (
                        <div className = "time-period-select-bar">
                        <select value={selectedTimePeriod} onChange={e => setSelectedTimePeriod(e.target.value)}>
                        <option value="day">Day</option>
                        <option value="week">Week</option>
                        <option value="month">Month</option>
                        <option value="year">Year</option>
                        </select>
                        </div>
                    )}
                    {/* item selector: doesn't apply to the XP or Overview sections (spec 0034) */}
                    {selectedStatistics !== "xp" && selectedStatistics !== "overview" && (
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
                    )}
                    {/* calendar view toggle: only meaningful for the all-habits calendar (spec 0029) */}
                    {selectedStatistics === "habits" && !selectedHabit && (
                        <div className = "calendar-view-select-bar">
                        <select value={calendarView} onChange={e => setCalendarView(e.target.value)}>
                        <option value="combined">Combined</option>
                        <option value="per-habit">Per-habit</option>
                        </select>
                        </div>
                    )}
                </div>

            {renderStats()}
            </div>

        </div>
    )

}