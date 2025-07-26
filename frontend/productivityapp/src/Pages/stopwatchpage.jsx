import { useState, useRef, useEffect} from 'react';
import './stopwatchpage.css';
import { IoMdClose } from "react-icons/io";
import { FaPlus } from "react-icons/fa";
import {
  DndContext, 
  closestCenter,
  KeyboardSensor,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
} from '@dnd-kit/sortable';
import { SortableStopwatchItem } from '../Components/SortableStopwatchItem.jsx';
import {StopwatchItem} from '../Components/StopwatchItem.jsx';

export function Stopwatch() {

    const DatetoISOString = (Date) => {
        const year = Date.getFullYear();
        const month = String(Date.getMonth() + 1).padStart(2, '0');
        const day = String(Date.getDate()).padStart(2,'0');
        const isoString = year + "-" + month + "-" + day;
        return isoString;
    }

    const [activeId, setActiveId] = useState(null);
    const [allStopwatches, setStopwatches] = useState([]);
    const allStopwatchesRef = useRef(allStopwatches); // so we dont need to pass allStopwatches as dependency to second useEffect
    const [stopwatchTitle, setStopwatchTitle] = useState("");
    const [addingStopwatch, setAddingStopwatch] = useState(false);
    const [isAdding, setIsAdding] = useState(false);
    const [runningId, setRunningId] = useState(null);
    const [tick, setTick] = useState(0);
    const [editStopwatch, setEditStopwatch] = useState(false);
    const [editingStopwatchID, setEditingStopwatchID] = useState(null);
    const [today, setToday] = useState(() => (DatetoISOString(new Date())));
    const [selectedDate, setSelectedDate] = useState(today);
    const [inputHours, setInputHours] = useState(1);
    const [inputMinutes, setInputMinutes] = useState(0);
    const [currentHours, setCurrentHours] = useState(0);
    const [currentMinutes, setCurrentMinutes] = useState(0);
    const [currentSeconds, setCurrentSeconds] = useState(0);
    const [currentCentiseconds, setCurrentCentiseconds] = useState(0);
    const isFuture = (new Date(selectedDate)) > (new Date(today));
    const intervalRef = useRef(null);
    const [stopwatchError, setStopwatchError] = useState("");

    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, {
        coordinateGetter: sortableKeyboardCoordinates,
        })
    );
    

    // updates state variable today but not selecteday
    useEffect(() => {
        const now = new Date();
        const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0) - now //midnight next day
        const timeout = setTimeout(() => {
            setToday(DatetoISOString(new Date()));
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

    // updates displayed time
    useEffect (() => {
        if (editingStopwatchID !== null){
            const updated = allStopwatches.find(stopwatch => stopwatch.id === editingStopwatchID);
            if (updated){
                const [currHours, currMinutes, currSeconds, currCentiseconds] = formatTimeString(updated.curr_duration);
                setCurrentHours(Number(currHours));
                setCurrentMinutes(Number(currMinutes));
                setCurrentSeconds(Number(currSeconds));
                setCurrentCentiseconds(Number(currCentiseconds));
            }
        }
    },[editingStopwatchID, allStopwatches])

    
    const addStopwatch = async () => {
        if (isFuture){
            return;
        }
        setStopwatchError(""); // clear previous errors

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

        try{
            const response = await fetch(`http://localhost:5000/stopwatches/`, {
                method: "POST",
                body: JSON.stringify(newStopwatch)
            });

            if (response.status === 409) {
                setStopwatchError("A stopwatch with this title already exists.");
                throw new Error("Duplicate stopwatch");
            }

            const data = await response.json();
            // adds total stopwatch if first creation for this day otherwise updates total stopwatch
            if (allStopwatches.length === 0){
                setStopwatches([data.stopwatches[0], data.stopwatches[1]])
            } else {
                // updates total stopwatch and adds new stopwatch
                setStopwatches(allStopwatches => {
                    const updated = allStopwatches.map(stopwatch => stopwatch.isTotal ? data.stopwatches[0] : stopwatch);
                    return ([...updated, data.stopwatches[1]]);
                });
            }
            setStopwatchTitle("");
            setAddingStopwatch(false);
            setInputHours(1);
            setInputMinutes(0);
        } catch (error) {
            console.error(error);
        }  finally {
            setIsAdding(false);
        }
    }

    const deleteStopwatch = async (index) => {
        if (isFuture) {
            return;
        }
        try{
            const response = await fetch(`http://localhost:5000/stopwatches/${index}/`, {
            method: "DELETE"
            })
            const data = await response.json();
            setStopwatches(allStopwatches => 
                allStopwatches.filter(stopwatch => (stopwatch.id !== data.stopwatches[1].id)) // remove deleted stopwatch
            );
            setStopwatches(allStopwatches =>
                allStopwatches.map(stopwatch => stopwatch.isTotal ? data.stopwatches[0] : stopwatch)); // update total stopwatch)
            if (runningId === index) {
                clearInterval(intervalRef.current);
                setRunningId(null);
            }
        } catch (error) {
            console.error(error);
        }
    }

    const handleStart = async (index, end_time) => {

        if (isFuture) {
            return;
        }
      
        if (runningId === null && end_time !== null){
            setRunningId(index);
            clearInterval(intervalRef.current);
            intervalRef.current = setInterval(() => {
                setTick(tick => tick + 1);
            }, 10);  
            
            try {
                const response = await fetch(`http://localhost:5000/stopwatches/start/${index}/`, {
                method: "PATCH",
                })
                const data = await response.json();
                setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that started

            } catch(error){
                console.error(error);
            }
        }
    }

    const handleStop = async (index, end_time) => {

        if (isFuture) {
            return;
        }
      
        if (end_time === null){
             setRunningId(null);
             try{
                const response = await fetch(`http://localhost:5000/stopwatches/stop/${index}/`, {
                method: "PATCH",
            })
                const data = await response.json();
                setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that stopped
                clearInterval(intervalRef.current);
                if (tick === 0){}; // just to avoid compiled with warnings. remove later

             } catch (error){
                console.error(error);
             }
           
                
        }
    }

    const handleReset = async (index, end_time) =>{

        if (isFuture) {
            return;
        }

        const update = {
            state : end_time // if stopwatch is currently running or not
        }
        try {
            const response = await fetch(`http://localhost:5000/stopwatches/reset/${index}/`, {
            method: "PATCH",
            body: JSON.stringify(update)
            })
            const data = await response.json();
            setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that reset
            if (runningId === index){
                    clearInterval(intervalRef.current);
                    setRunningId(null);
                }
        } catch (error){
            console.error(error)
        }
    }

    const handleEditStopwatch = async () => {

        if (isFuture) {
            return;
        }

        setStopwatchError(""); // Clear previous errors

        // Clamp values
        const safeGoalHours = Math.max(0, Math.min(23, Number(inputHours)));
        const safeGoalMinutes = Math.max(0, Math.min(59, Number(inputMinutes)));

        const safeCurrHours = Math.max(0, Math.min(23, currentHours ))
        const safeCurrMinutes= Math.max(0, Math.min(59, currentMinutes ))
        const safeCurrSeconds = Math.max(0, Math.min(59, currentSeconds ))
        const safeCurrCentiseconds = Math.max(0, Math.min(99, currentCentiseconds ))

        if (editingStopwatchID === null) return;

        const inputTimeString = `${String(safeGoalHours).padStart(2, '0')}:${String(safeGoalMinutes).padStart(2, '0')}`;
        const newDuration = (safeCurrHours * 3600000) + (safeCurrMinutes * 60000) + (safeCurrSeconds * 1000) + (safeCurrCentiseconds * 10)

        const newStopwatch = {
            title: stopwatchTitle,
            goal_time: inputTimeString,
            curr_duration: newDuration
        }

        setIsAdding(true);

        try {
            const response = await fetch(`http://localhost:5000/stopwatches/${editingStopwatchID}/`, {
                method: 'PUT',
                body: JSON.stringify(newStopwatch)
            })

            if (response.status === 409) {
                setStopwatchError("A stopwatch with this title already exists.");
                throw new Error("Duplicate stopwatch");
            }

            const data = await response.json();
            setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that was edited
            setStopwatchTitle("");
            setInputHours(1);
            setInputMinutes(0);
            setCurrentHours(0);
            setCurrentMinutes(0);
            setCurrentSeconds(0);
            setCurrentCentiseconds(0);
            setEditStopwatch(false);
            setEditingStopwatchID(null);
        } catch (error){
            console.error(error);
        } finally {
            setIsAdding(false);
        }
    }

    // const formatTime = (totalMilliSeconds) => {
    //     const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
    //     const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
    //     const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
    //     const centiseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0');
    //     return (
    //         <>
    //             {hours}:{minutes}:{seconds}:<span className = "centiseconds">{centiseconds}</span>
            
    //         </>);
    // };

    const formatTimeString = (totalMilliSeconds) => {
        if (totalMilliSeconds < 0) totalMilliSeconds = 0;
        const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
        const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
        const centiseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0');
        return [hours, minutes, seconds, centiseconds];
            
          
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

    function CircularProgress({time, goal_time, size = 330, strokeWidth = 50, bgColor = "#444" }) {
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
                    fontSize="2.2rem"
                    fontFamily="'Roboto Mono', monospace"
                    fill="rgb(0,230,122)"
                    letterSpacing="2px"
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

    function CircularProgressTotal({time, goal_time, size = 550, strokeWidth = 80, bgColor = "#444" }) {
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
                    fontSize="4rem"                
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

    function handleDragStart(event) {
        const {active} = event;
        
        setActiveId(active.id);
    }
  
    function handleDragEnd(event) {
        const {active, over} = event;
        
        if (active.id !== over.id) {
        setStopwatches((prevStopwatches) => {
            const oldIndex = prevStopwatches.findIndex(stopwatch => stopwatch.id === active.id);
            const newIndex = prevStopwatches.findIndex(stopwatch => stopwatch.id === over.id);
            
            return arrayMove(prevStopwatches, oldIndex, newIndex);
        });
        }
        
        setActiveId(null);
    }


    return (
    <DndContext sensors={sensors} collisionDetection={closestCenter}
                onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
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
                        onClick={() => {setEditStopwatch(false); setStopwatchTitle(""); setInputHours(1); setInputMinutes(0); setStopwatchError("");}}/>
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
                      <label style={{ marginTop: "18px", display: "block" }}>Goal Time:</label>
                      <div className = "goal-time-inputs">
                        <label htmlFor="goal-hours">Hours:</label>
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
                        <label htmlFor="goal-minutes">Minutes:</label>
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
                      </div>
                      <label style={{ marginTop: "18px", display: "block" }}>Current Time:</label>
                      <div className = "current-time-inputs">
                        <label htmlFor="current-hours">Hours:</label>
                        <input
                            type="number"
                            id = "current-hours"
                            min = "0"
                            max = "23"
                            value={currentHours}
                            onChange={e => setCurrentHours(e.target.value)}
                            onKeyDown={(e) => {
                            if (e.key === "Enter"){
                                handleEditStopwatch();
                            }
                            }}
                        />
                        <label htmlFor="current-minutes">Minutes:</label>
                            <input
                            type="number"
                            id="current-minutes"
                            min="0"
                            max="59"
                            value={currentMinutes}
                            onChange={e => setCurrentMinutes(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === "Enter") handleEditStopwatch();
                            }}
                        />
                        <label htmlFor="current-seconds">Seconds:</label>
                            <input
                            type="number"
                            id="current-seconds"
                            min="0"
                            max="59"
                            value={currentSeconds}
                            onChange={e => setCurrentMinutes(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === "Enter") handleEditStopwatch();
                            }}
                        />
                        <label htmlFor="current-centiseconds">Centiseconds:</label>
                            <input
                            type="number"
                            id="current-centiseconds"
                            min="0"
                            max="99"
                            value={currentCentiseconds}
                            onChange={e => setCurrentCentiseconds(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === "Enter") handleEditStopwatch();
                            }}
                        />
                      </div>
                      <button type = 'button' className = 'editStopwatchButton'
                        onClick={handleEditStopwatch}
                        disabled = {isAdding}
                        > {isAdding ? "Editing..." : "Done"}</button>
                      {stopwatchError && (
                        <div style={{ color: "red", marginBottom: "10px" }}>{stopwatchError}</div>
                        )}
                    </div>
                  </div>
                )}
        {addingStopwatch && (
                  <div className = "stopwatch-input">
                    <div className = "stopwatch-input-item">
                      <IoMdClose className = "close-icon"
                        onClick={() => {setAddingStopwatch(false); setStopwatchError("")}}/>
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
                      <label style={{ marginTop: "18px", display: "block" }}>Goal Time:</label>
                      <div className = "goal-time-inputs">
                        <label htmlFor="goal-hours">Hours:</label>
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
                        <label htmlFor="goal-minutes">Minutes:</label>
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
                      </div> 
                      <button type = 'button' className = 'addStopwatchButton'
                        onClick={addStopwatch}
                        disabled = {isAdding}
                        > {isAdding ? "Adding..." : "Add Stopwatch"}</button>
                        {stopwatchError && (
                        <div style={{ color: "red", marginBottom: "10px" }}>{stopwatchError}</div>
                        )}
                    </div>
                  </div>
                )}
        <SortableContext items={allStopwatches.map(stopwatch => stopwatch.id)} strategy={rectSortingStrategy}>
            {allStopwatches.map((item) => (
            <SortableStopwatchItem
                key={item.id}
                item={item}
                isFuture={isFuture}
                onEdit={async item => {if (item.end_time === null){
                                                await handleStop(item.id, item.end_time);
                                            }
                                        setEditStopwatch(true); setStopwatchTitle(item.title);
                                        setEditingStopwatchID(item.id); const [hours, minutes] = formatTimeString(item.goal_time);
                                        setInputHours(Number(hours));
                                        setInputMinutes(Number(minutes)); }}
                onStart = {handleStart}
                onStop = {handleStop}
                onReset = {handleReset}
                onDelete={deleteStopwatch}
                activeId= {activeId}
                runningId = {runningId}
                getElapsed = {getElapsed}
                formatTimeString = {formatTimeString}
                CircularProgress = {CircularProgress}
                CircularProgressTotal = {CircularProgressTotal}
            />
            ))}
        </SortableContext>
    </div>

    </div>
    <DragOverlay>
            {activeId ? <StopwatchItem 
                item={allStopwatches.find(s => s.id === activeId)}
                isFuture={isFuture}
                onEdit={async item => {if (item.end_time === null){
                                                await handleStop(item.id, item.end_time);
                                            }
                                        setEditStopwatch(true); setStopwatchTitle(item.title);
                                        setEditingStopwatchID(item.id); const [hours, minutes] = formatTimeString(item.goal_time);
                                        setInputHours(Number(hours));
                                        setInputMinutes(Number(minutes)); }}
                onStart = {handleStart}
                onStop = {handleStop}
                onReset = {handleReset}
                onDelete={deleteStopwatch} 
                runningId = {runningId}
                getElapsed = {getElapsed}
                formatTimeString = {formatTimeString}
                CircularProgress = {CircularProgress}
                CircularProgressTotal = {CircularProgressTotal}/> : null}
    </DragOverlay>
    </DndContext>
    
    );
}