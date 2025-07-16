import { useState, useRef, useEffect} from 'react';
import './stopwatchpage.css';
import { MdDelete } from "react-icons/md";
import { MdEdit } from "react-icons/md";
import { IoMdClose } from "react-icons/io";
import { FaPlus } from "react-icons/fa";

export function Stopwatch() {
    const [allStopwatches, setStopwatches] = useState([]);
    const allStopwatchesRef = useRef(allStopwatches); // so we dont need to pass allStopwatches as dependency to second useEffect
    const [stopwatchTitle, setStopwatchTitle] = useState("");
    const [addingStopwatch, setAddingStopwatch] = useState(false);
    const [isAdding, setIsAdding] = useState(false);
    const [runningId, setRunningId] = useState(null);
    const [tick, setTick] = useState(0);
    const [editStopwatch, setEditStopwatch] = useState(false);
    const [editingStopwatchID, setEditingStopwatchID] = useState(null);
    const [today, setToday] = useState(() => (new Date()).toISOString().slice(0,10));
    const [selectedDate, setSelectedDate] = useState(today);
    const [inputHours, setInputHours] = useState(1);
    const [inputMinutes, setInputMinutes] = useState(0);
    const isFuture = (new Date(selectedDate)) > (new Date(today));
    const intervalRef = useRef(null);
    

    // goes to next day
    useEffect(() => {
        const now = new Date();
        const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0) - now//midnight next day
        const timeout = setTimeout(() => {
            setToday(new Date().toISOString().slice(0,10));
        }, msUntilMidnight);

        return () => clearTimeout(timeout);
    },[today]);

    useEffect(() => {
        // stops any running stopwatches when selected date changes
        const stopRunning = async () => {
            const running = allStopwatchesRef.current.find(
                sw => sw.end_time === null && !sw.isTotal
            );
            if (running) {
                await fetch(`http://localhost:5000/stopwatches/stop/${running.id}/`, {
                method: "PATCH",
            });
            setRunningId(null);
            }
        };

        stopRunning().then(() => {
            // gets current stopwatches if future date
            let dateToFetch = selectedDate;
            if (isFuture){
                dateToFetch = today;
            }
            fetch(`http://localhost:5000/stopwatches/${dateToFetch}/`, {
                method: "GET",
                })
            .then(response => response.json())
            .then(data => {
                setRunningId(null);
                setStopwatches((data.stopwatches));
            })
            .catch(error => console.error(error));
            });

        return () => {
            clearInterval(intervalRef.current);
        }
    }, [selectedDate, today, isFuture]); 

    // updates reference whenever allStopwatch updated.
    useEffect ( () => {
        allStopwatchesRef.current = allStopwatches;
    }, [allStopwatches]);
    

    // stops running stopwatches when website closed
    useEffect ( () => {
        const handleUnload = () => {
            allStopwatchesRef.current.forEach(stopwatch => {
                if ((stopwatch.end_time === null) && !stopwatch.isTotal){
                    navigator.sendBeacon(`http://localhost:5000/stopwatches/stop/${stopwatch.id}/`
                    );
                };
                setRunningId(null);
            });
        }
        window.addEventListener('pagehide', handleUnload)
        return () => window.removeEventListener('pagehide', handleUnload);
    }, [])

    const addStopwatch = () => {
        if (isFuture){
            return;
        }

        // Clamp values
        const safeHours = Math.max(0, Math.min(23, Number(inputHours)));
        const safeMinutes = Math.max(0, Math.min(59, Number(inputMinutes)));

        const inputTimeString = `${String(safeHours).padStart(2, '0')}:${String(safeMinutes).padStart(2, '0')}`
        const newStopwatch = {
            title : stopwatchTitle,
            date : selectedDate,
            goal_time : inputTimeString
        }
        setIsAdding(true);
        fetch(`http://localhost:5000/stopwatches/`, {
            method: "POST",
            body: JSON.stringify(newStopwatch)
        })
        .then(response => response.json())
        .then(data => {
            if (data.stopwatches[0] === null){
                setStopwatches(allStopwatches => [...allStopwatches, data.stopwatches[1]]);
            } else {
                setStopwatches(allStopwatches => [data.stopwatches[0], data.stopwatches[1]])
            }
            setStopwatchTitle("");
            setAddingStopwatch(false);
            setInputHours(1);
            setInputMinutes(0);
        })
        .catch(error => console.error(error))
        .finally(() => setIsAdding(false));
    }

    const deleteStopwatch = (index) => {
        if (isFuture) {
            return;
        }
        fetch(`http://localhost:5000/stopwatches/${index}/`, {
            method: "DELETE"
        })
        .then(response => response.json())
        .then(data =>{
            setStopwatches(allStopwatches => 
                allStopwatches.filter(stopwatch => (stopwatch.id !== data.stopwatches[1].id)) // remove deleted stopwatch
            );
            setStopwatches(allStopwatches =>
                allStopwatches.map(stopwatch => stopwatch.isTotal ? data.stopwatches[0] : stopwatch)); // update total stopwatch)
            if (runningId === index) {
                clearInterval(intervalRef.current);
                setRunningId(null);
            }
        }
        )
        .catch(error => console.error(error));
    }

    const handleStart = (index, end_time) => {

        if (isFuture) {
            return;
        }
      
        if (runningId === null && end_time !== null){
            setRunningId(index);
            clearInterval(intervalRef.current);
            intervalRef.current = setInterval(() => {
                setTick(tick => tick + 1);
            }, 10);  
            
            fetch(`http://localhost:5000/stopwatches/start/${index}/`, {
                method: "PATCH",
            })
            .then(response => response.json())
            .then(data => {
                setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that started
            })
            .catch(error => console.error(error))
        }
    }

    const handleStop = (index, end_time) => {

        if (isFuture) {
            return;
        }
      
        if (end_time === null){
             setRunningId(null);
             fetch(`http://localhost:5000/stopwatches/stop/${index}/`, {
                method: "PATCH",
            })
            .then(response => response.json())
            .then(data => {
                setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that stopped
                clearInterval(intervalRef.current);
                if (tick === 0){}; // just to avoid compiled with warnings. remove later
                
            })
            .catch(error => console.error(error))
        }
    }

    const handleReset = (index, end_time) =>{

        if (isFuture) {
            return;
        }

        const update = {
            state : end_time // if stopwatch is currently running or not
        }
        fetch(`http://localhost:5000/stopwatches/reset/${index}/`, {
            method: "PATCH",
            body: JSON.stringify(update)
        })
        .then(response => response.json())
        .then(data => {
                setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that reset
                if (runningId === index){
                    clearInterval(intervalRef.current);
                    setRunningId(null);
                }
            })
        .catch(error => console.error(error))
    }

    const handleEditStopwatch = () => {

        if (isFuture) {
            return;
        }

        // Clamp values
        const safeHours = Math.max(0, Math.min(23, Number(inputHours)));
        const safeMinutes = Math.max(0, Math.min(59, Number(inputMinutes)));

        if (editingStopwatchID === null) return;

        const inputTimeString = `${String(safeHours).padStart(2, '0')}:${String(safeMinutes).padStart(2, '0')}`

        const newStopwatch = {
            title: stopwatchTitle,
            goal_time: inputTimeString
        }

        setIsAdding(true);
        fetch(`http://localhost:5000/stopwatches/${editingStopwatchID}/`, {
            method: 'PUT',
            body: JSON.stringify(newStopwatch)
        })
        .then(response => response.json())
        .then(data => {
            setStopwatches(allStopwatches =>
                allStopwatches.map(stopwatch =>
                    (stopwatch.id === data.id) ? data : stopwatch
            ));
            setStopwatchTitle("");
            setInputHours(1);
            setInputMinutes(0);
            setEditStopwatch(false);
            setEditingStopwatchID(null);
        })
        .catch(error => console.log(error))
        .finally(() => setIsAdding(false))
    }

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
        const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
        const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
        const milliseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0');
        return {hours, minutes, seconds, milliseconds};
            
          
    };

    const getElapsed = (stopwatch) => {
        if (isFuture) {
            return 0;
        }
        if (stopwatch.end_time != null){
            return stopwatch.curr_duration;
        } else {
            return stopwatch.curr_duration + (Date.now() - new Date(stopwatch.interval_start));
        }
    }

    const convertMillisecondsToHoursAndMinutes = (milliseconds) => {
        const hours = Math.floor(milliseconds / 3600000)
        const remainingMs = milliseconds % 3600000
        const minutes = Math.floor(remainingMs / 60000)
        return [hours, minutes]
    }

    function CircularProgress({time, goal_time, size = 330, strokeWidth = 50, bgColor = "#444" }) {
        const percentage = (time / goal_time) * 100 ?? 0 
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - ((percentage % 100) / 100) * circumference;
        const r = 0
        const g = 230
        const b = 122
        const colorOffset = Math.floor(percentage / 100)
        console.log(colorOffset)
        const color = `rgb(${r}, ${g - (50 * colorOffset)}, ${b - (50 * colorOffset) })`
        const color2 = (colorOffset >= 1 ? `rgb(${r}, ${g - (50 * (colorOffset - 1) )}, ${b - (50 * (colorOffset-1)) })` : bgColor)
        console.log(color)
        console.log(color2)

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
                    fontSize="2.2rem"
                    fontFamily="'Roboto Mono', monospace"
                    fill="rgb(0,230,122)"
                    letterSpacing="2px"
                >
                    {
                        (() => {
                            const { hours, minutes, seconds, milliseconds } = formatTimeString(time);
                            return (
                                <>
                                    {hours}:{minutes}:{seconds}
                                    <tspan fontSize="0.7em" opacity="0.7">:{milliseconds}</tspan>
                                </>
                            );
                        })()
                    }
                </text>
            </svg>
        );
    }

    function CircularProgressTotal({time, goal_time, size = 600, strokeWidth = 50, bgColor = "#444" }) {
        const percentage = (time / goal_time) * 100 ?? 0 
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        const offset = circumference - ((percentage % 100) / 100) * circumference;
        const r = 0
        const g = 230
        const b = 122
        const colorOffset = Math.floor(percentage / 100)
        console.log(colorOffset)
        const color = `rgb(${r}, ${g - (50 * colorOffset)}, ${b - (50 * colorOffset) })`
        const color2 = (colorOffset >= 1 ? `rgb(${r}, ${g - (50 * (colorOffset - 1) )}, ${b - (50 * (colorOffset-1)) })` : bgColor)
        console.log(color)
        console.log(color2)

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
                    fontSize="5rem"                // Match .total-time-display font-size
                    fontWeight="bold"              // Match .total-time-display font-weight
                    fontFamily="'Roboto Mono', monospace"
                    fill="white"                   // Match .total-time-display color
                    letterSpacing="2px"
                    style={{ marginBottom: "8px" }}
                >
                    {
                        (() => {
                            const { hours, minutes, seconds, milliseconds } = formatTimeString(time);
                            return (
                                <>
                                    {hours}:{minutes}:{seconds}
                                    <tspan fontSize="0.7em" opacity="0.7">:{milliseconds}</tspan>
                                </>
                            );
                        })()
                    }
                </text>
            </svg>
        );
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
        <h1>Stopwatches</h1>
        <div className="stopwatches">
        <div className = "header">
            <button className = "primaryBtn" onClick = {() => setAddingStopwatch(true)} disabled = {isFuture}>
            <FaPlus className = "plus-icon" />
        </button>
        </div>
        {editStopwatch && (
                  <div className = "stopwatch-input">
                    <div className = "stopwatch-edit-item">
                      <IoMdClose className = "close-icon"
                        onClick={() => {setEditStopwatch(false); setStopwatchTitle("")}}/>
                      <h3>Edit Stopwatch</h3>
                      <label>Title: </label>
                      <input type= "text" value = {stopwatchTitle} 
                      onChange={(e) => setStopwatchTitle(e.target.value) }
                      onKeyDown={(e) => {
                        if (e.key === "Enter"){
                          handleEditStopwatch();
                        }
                      }}
                      placeholder="What's the stopwatch for"/>
                      <label>Goal Time:</label>
                      <label htmlFor="goal-hours">Goal Hours:</label>
                      <input
                        type="number"
                        id = "goal-hours"
                        min = "0"
                        max = "23"
                        value={inputHours}
                        onChange={e => setInputHours(e.target.value)}
                        onKeyDown={(e) => {
                        if (e.key === "Enter"){
                          handleEditStopwatch();
                        }
                        }}
                      />
                      <label htmlFor="goal-minutes">Goal Minutes:</label>
                        <input
                        type="number"
                        id="goal-minutes"
                        min="0"
                        max="59"
                        value={inputMinutes}
                        onChange={e => setInputMinutes(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === "Enter") handleEditStopwatch();
                        }}
                      />
                      <button type = 'button' className = 'editStopwatchButton'
                        onClick={handleEditStopwatch}
                        disabled = {isAdding}
                        > {isAdding ? "Editing..." : "Done"}</button>
                    </div>
                  </div>
                )}
        {addingStopwatch && (
                  <div className = "stopwatch-input">
                    <div className = "stopwatch-input-item">
                      <IoMdClose className = "close-icon"
                        onClick={() => setAddingStopwatch(false)}/>
                      <h3>Add a New Stopwatch</h3>
                      <label>Title: </label>
                      <input type= "text" value = {stopwatchTitle} 
                      onChange={(e) => setStopwatchTitle(e.target.value) }
                      onKeyDown={(e) => {
                        if (e.key === "Enter"){
                          addStopwatch();
                        }
                      }}
                      placeholder="What's the stopwatch for"/>
                      <label>Goal Time:</label>
                      <label htmlFor="goal-hours">Goal Hours:</label>
                      <input
                        type="number"
                        id = "goal-hours"
                        min = "0"
                        max = "23"
                        value={inputHours}
                        onChange={e => setInputHours(e.target.value)}
                        onKeyDown={(e) => {
                        if (e.key === "Enter"){
                          addStopwatch();
                        }
                        }}
                      />
                      <label htmlFor="goal-minutes">Goal Minutes:</label>
                        <input
                        type="number"
                        id="goal-minutes"
                        min="0"
                        max="59"
                        value={inputMinutes}
                        onChange={e => setInputMinutes(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === "Enter"){
                                addStopwatch();
                            } 
                        }}
                      />
                      <button type = 'button' className = 'addStopwatchButton'
                        onClick={addStopwatch}
                        disabled = {isAdding}
                        > {isAdding ? "Adding..." : "Add Stopwatch"}</button>
                    </div>
                  </div>
                )}
        {allStopwatches.map((item) => {
            if (item.isTotal === true){
                return (
                    <div className = "total-stopwatch-item" key = {item.id}>
                        <p>Total Time Worked: </p>
                        <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px" }}>
                                <CircularProgressTotal time ={getElapsed(item)} goal_time = {item.goal_time}/> 
                        </div>  
                    </div>
                )
            } else {
                return (
                <div className = {`stopwatch-item ${isFuture ? "disabled-stopwatch" : ""} ${((runningId !== null) ? ((runningId !== item.id) ? "not-focused-stopwatch" : "focused-stopwatch")  : "")}`}
                     onClick={() => {setEditStopwatch(true); setStopwatchTitle(item.title);
                            setEditingStopwatchID(item.id); const [hours, minutes] = convertMillisecondsToHoursAndMinutes(item.goal_time);
                            setInputHours(hours);
                            setInputMinutes(minutes);
                        }} disabled = {isFuture} key = {item.id}>
                    <div className = "stopwatch-title">
                        <p>{item.title}</p>
                    </div>
                    <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px" }}>
                                <CircularProgress time ={getElapsed(item)} goal_time = {item.goal_time}/> 
                    </div>  
                    <div className="goal-time">
                        {(() => {
                            const [goalHours, goalMinutes] = convertMillisecondsToHoursAndMinutes(item.goal_time);
                            return <>Goal: {goalHours}h {goalMinutes}m</>;
                        })()}
                    </div>
                    <div className="controls">
                        <button onClick={(e) => {e.stopPropagation(); handleStart(item.id, item.end_time)}} disabled = {isFuture}>Start</button>
                        <button onClick={(e) => {e.stopPropagation(); handleStop(item.id, item.end_time)}} disabled = {isFuture}>Pause</button>
                        <button onClick={(e) => {e.stopPropagation(); handleReset(item.id, item.end_time)}} disabled = {isFuture}>Reset</button>
                        <MdEdit className = "stopwatch-edit-icon"
                            onClick={() => {if (isFuture) return; setEditStopwatch(true); setStopwatchTitle(item.title);
                            setEditingStopwatchID(item.id); const [hours, minutes] = convertMillisecondsToHoursAndMinutes(item.goal_time);
                            setInputHours(hours);
                            setInputMinutes(minutes);;
                        }}/>
                        <MdDelete className = "stopwatch-delete-icon"
                         onClick = {(e) => {e.stopPropagation(); if (isFuture) return; deleteStopwatch(item.id)}}/>
                    </div>
                </div>
            )
            }
        })}
    </div>

    </div>
    );
}