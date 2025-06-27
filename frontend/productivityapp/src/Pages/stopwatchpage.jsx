import { useState, useRef, useEffect} from 'react';
import './stopwatchpage.css';
import { MdDelete } from "react-icons/md";
import { IoMdClose } from "react-icons/io";

export function Stopwatch() {
    const [allStopwatches, setStopwatches] = useState([]);
    const allStopwatchesRef = useRef(allStopwatches); // so we dont need to pass allStopwatches as dependency to second useEffect
    const [stopwatchTitle, setStopwatchTitle] = useState("");
    const [addingStopwatch, setAddingStopwatch] = useState(false);
    const [isAdding, setIsAdding] = useState(false);
    const [runningId, setRunningId] = useState(null);
    const [tick, setTick] = useState(0);
    const intervalRef = useRef(null);

    useEffect(() => {
    fetch("http://localhost:5000/stopwatches/", {
      method: "GET"
    })
    .then( response => response.json())
    .then(data => {
        setRunningId(null);
        setStopwatches((data.stopwatches));
    })
    .catch(error => console.error(error));

    return () => {
        clearInterval(intervalRef.current);
    }

    }, []); 

    // updates reference whenever allStopwatch updated.
    useEffect ( () => {
        allStopwatchesRef.current = allStopwatches;
    }, [allStopwatches]);
    

    // stops running stopwatches when website closed
    useEffect ( () => {
        const handleUnload = () => {
            allStopwatchesRef.current.forEach(stopwatch => {
                if (stopwatch.end_time === null){
                    navigator.sendBeacon(`http://localhost:5000/stopwatches/stop/${stopwatch.id}/`
                    );
                }
            });
        }
        window.addEventListener('pagehide', handleUnload)
        return () => window.removeEventListener('pagehide', handleUnload);
    }, [])

    const addStopwatch = () => {
        const newStopwatch = {
            title : stopwatchTitle
        }
        setIsAdding(true);
        fetch("http://localhost:5000/stopwatches/", {
            method: "POST",
            body: JSON.stringify(newStopwatch)
        })
        .then(response => response.json())
        .then(data => {
            setStopwatches(allStopwatches => [...allStopwatches, data])
            setStopwatchTitle("")
            setAddingStopwatch(false);
        })
        .catch(error => console.error(error))
        .finally(() => setIsAdding(false));
    }

    const deleteStopwatch = (index) => {
        fetch(`http://localhost:5000/stopwatches/${index}/`, {
            method: "DELETE"
        })
        .then(response => response.json())
        .then(data =>{
            setStopwatches(allStopwatches => allStopwatches.filter(stopwatch => (stopwatch.id !== data.id)));
            if (runningId === index) {
                clearInterval(intervalRef.current);
                setRunningId(null);
            }
        }
        )
        .catch(error => console.error(error));
    }

    const handleStart = (index, end_time) => {
      
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
                        (stopwatch.id === data.id) ? data : stopwatch)); 
            })
            .catch(error => console.error(error))
        }
    }

    const handleStop = (index, end_time) => {
      
        if (end_time === null){
             setRunningId(null);
             fetch(`http://localhost:5000/stopwatches/stop/${index}/`, {
                method: "PATCH",
            })
            .then(response => response.json())
            .then(data => {
                setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.id === data.id) ? data : stopwatch));
                clearInterval(intervalRef.current);
                if (tick === 0){}; // just to avoid compiled with warnings. remove later
                
            })
            .catch(error => console.error(error))
        }
    }

    const handleReset = (index, end_time) =>{
        const update = {
            state : end_time
        }
        fetch(`http://localhost:5000/stopwatches/reset/${index}/`, {
            method: "PATCH",
            body: JSON.stringify(update)
        })
        .then(response => response.json())
        .then(data => {
                setStopwatches(allStopwatches => 
                allStopwatches.map(stopwatch => 
                (stopwatch.id === data.id) ? data : stopwatch));
                if (runningId === index){
                    clearInterval(intervalRef.current);
                    setRunningId(null);
                }
            })
        .catch(error => console.error(error))
    }

    const formatTime = (totalMilliSeconds) => {
        const hours = String(Math.floor(totalMilliSeconds / 3600000)).padStart(2, '0');
        const minutes = String(Math.floor((totalMilliSeconds % 3600000) / 60000)).padStart(2, '0');
        const seconds = String(Math.floor((totalMilliSeconds % 60000) / 1000)).padStart(2, '0');
        const milliseconds = String(Math.floor((totalMilliSeconds % 1000) / 10)).padStart(2,'0')
        return `${hours}:${minutes}:${seconds}:${milliseconds}`;
    };

    const getElapsed = (stopwatch) => {
        if (stopwatch.end_time != null){
            return stopwatch.curr_duration;
        } else {
            return stopwatch.curr_duration + (Date.now() - new Date(stopwatch.interval_start));
        }
    }

    return (
    <div className="stopwatches">
        <button onClick = {() => setAddingStopwatch(true)}>
            Add a Stopwatch
        </button>
        {addingStopwatch && (
                  <div className = "stopwatch-input">
                    <div className = "stopwatch-input-item">
                      <IoMdClose className = "close-icon"
                        onClick={() => setAddingStopwatch(false)}/>
                      <h3>Add a New Stopwatch</h3>
                      <label>Title</label>
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
        <h2>Stopwatches</h2>
        {allStopwatches.map((item) => {
            return (
                <div className = "stopwatch-item" key = {item.id}>
                    <p>{item.title}</p>
                    <div className="time-display">
                        {formatTime(getElapsed(item))}
                    </div>
                    <div className="controls">
                        <button onClick={() => handleStart(item.id, item.end_time)}>Start</button>
                        <button onClick={() => handleStop(item.id, item.end_time)}>Pause</button>
                        <button onClick={() => handleReset(item.id, item.end_time)}>Reset</button>
                        <MdDelete className = "delete-icon"
                         onClick = {() => deleteStopwatch(item.id, item.end_time)}/>
                    </div>
                </div>
            )
        })}
    </div>
    );
}