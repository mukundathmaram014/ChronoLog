import {useState, useEffect} from "react";
import './statisticspage.css';


export function Statistics() {

    const [selectedStatistics, setSelectedStatistics] = useState("habits")
    const [selectedTimePeriod, setSelectedTimePeriod] = useState("day");
    // const [today, setToday] = useState(() => (new Date()).toISOString().slice(0,10));
    const [selectedDate, setSelectedDate] = useState(() => (new Date()).toISOString().slice(0,10));
    const [statsData, setStatsData] = useState(null);

    useEffect(() => {
            fetch(`http://localhost:5000/stats/${selectedStatistics}/${selectedDate}/${selectedTimePeriod}/`, {
                method: "GET",
                })
            .then(response => response.json())
            .then(data => {
                setStatsData(statsData => data);
            })
            .catch(error => console.error(error))

    }, [selectedTimePeriod, selectedStatistics, selectedDate])

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
                                <div className = "Completion">
                                    Completion: {statsData.percentage}
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
        <>
            <h1>Statistics</h1>
            <select value = {selectedStatistics} onChange = {e => setSelectedStatistics(e.target.value)}>
                <option value= "habits">Habits</option>
                <option value = "stopwatches">Stopwatches</option>
            </select>
            <select value={selectedTimePeriod} onChange={e => setSelectedTimePeriod(e.target.value)}>
                <option value="day">Day</option>
                <option value="week">Week</option>
                <option value="month">Month</option>
                <option value="year">Year</option>
            </select>
            <div className="date-slider-container">
            <label htmlFor="date-slider">Select Date: </label>
            <input
                type="date"
                id="date-slider"
                value={selectedDate}
                onChange={e => setSelectedDate(e.target.value)}
            />
            </div>

            {renderStats()}
        </>
    )

}