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
    const isFuture = (new Date(selectedDate)) > (new Date(today));
    const intervalRef = useRef(null);
    

    // goes to next day
    useEffect(() => {
        const now = new Date();
        const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0) - now//midnight next day
        const timeout = setTimeout(() => {
            setToday(new Date().toISOString().slice(0,10));
            setSelectedDate((new Date()).toISOString().slice(0,10))
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
        const newStopwatch = {
            title : stopwatchTitle,
            date : selectedDate
        }
        setIsAdding(true);
        fetch(`http://localhost:5000/stopwatches/`, {
            method: "POST",
            body: JSON.stringify(newStopwatch)
        })
        .then(response => response.json())
        .then(data => {
            console.log(data.stopwatches[0]);
            if (data.stopwatches[0] === null){
                setStopwatches(allStopwatches => [...allStopwatches, data.stopwatches[1]]);
            } else {
                setStopwatches(allStopwatches => [data.stopwatches[0], data.stopwatches[1]])
                console.log(allStopwatches)
            }
            setStopwatchTitle("");
            setAddingStopwatch(false);
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

        if (editingStopwatchID === null) return;

        const newStopwatch = {
            title: stopwatchTitle
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
                        <div className = "total-time-display">
                            {formatTime(getElapsed(item))}
                        </div>
                    </div>
                )
            } else {
                return (
                <div className = {`stopwatch-item ${isFuture ? "disabled-stopwatch" : ""} ${((runningId !== null) ? ((runningId !== item.id) ? "not-focused-stopwatch" : "focused-stopwatch")  : "")}`}
                     onClick={() => {setEditStopwatch(true); setStopwatchTitle(item.title);
                            setEditingStopwatchID(item.id);
                        }} disabled = {isFuture} key = {item.id}>
                    <div className = "stopwatch-title">
                        <p>{item.title}</p>
                    </div>
                    <div className="time-display">
                        {formatTime(getElapsed(item))}
                    </div>
                    <div className="controls">
                        <button onClick={(e) => {e.stopPropagation(); handleStart(item.id, item.end_time)}} disabled = {isFuture}>Start</button>
                        <button onClick={(e) => {e.stopPropagation(); handleStop(item.id, item.end_time)}} disabled = {isFuture}>Pause</button>
                        <button onClick={(e) => {e.stopPropagation(); handleReset(item.id, item.end_time)}} disabled = {isFuture}>Reset</button>
                        <MdEdit className = "edit-icon"
                            onClick={() => {if (isFuture) return; setEditStopwatch(true); setStopwatchTitle(item.title);
                            setEditingStopwatchID(item.id);
                        }}/>
                        <MdDelete className = "delete-icon"
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