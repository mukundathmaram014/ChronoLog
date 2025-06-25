import { useState, useRef, useEffect} from 'react';
import './stopwatchpage.css';
import { MdDelete } from "react-icons/md";
import { IoMdClose } from "react-icons/io";

export function Stopwatch() {
    const [allStopwatches, setStopwatches] = useState([]);
    const [secondsElapsed, setSecondsElapsed] = useState({});
    const [stopwatchTitle, setStopwatchTitle] = useState("Test");
    const [addingStopwatch, setAddingStopwatch] = useState(false);
    const [isAdding, setIsAdding] = useState(false);
    const intervalRefs = useRef([]);

    useEffect(() => {
    fetch("http://localhost:5000/stopwatches/", {
      method: "GET"
    })
    .then( response => response.json())
    .then(data => setStopwatches(data.stopwatches))
    .catch(error => console.error(error))
    }, []); 

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
            setSecondsElapsed(secondsElapsed => ({
                ...secondsElapsed, [data.id] : 0
            }));
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
            clearInterval(intervalRefs.current[index]);
            setStopwatches(allStopwatches => allStopwatches.filter(stopwatch => (stopwatch.id !== data.id)));
            if (intervalRefs.current[index]) {
                clearInterval(intervalRefs.current[index]);
                delete intervalRefs.current[index];
            }
            setSecondsElapsed(prev => {
                const updated = { ...prev };
                delete updated[index];
                return updated;
            }
            )
        }
        )
        .catch(error => console.error(error));
    }

    const handleStart = (index, end_time) => {
      
        if (end_time !== null){
            // setStartTime(Date.now());
            // setNow(Date.now());
            clearInterval(intervalRefs.current[index]);
            intervalRefs.current[index] = setInterval(() => {
                setSecondsElapsed(secondsElapsed => ({
                ...secondsElapsed, [index] : secondsElapsed[index] + 1
            })
                );
            }, 10)
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
             clearInterval(intervalRefs.current[index]);
             fetch(`http://localhost:5000/stopwatches/stop/${index}/`, {
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

    const handleReset = (index, end_time) =>{
        const update = {
            state : end_time
        }
        clearInterval(intervalRefs.current[index]);
        setSecondsElapsed(secondsElapsed => ({
                ...secondsElapsed, [index] : 0
            }));
        fetch(`http://localhost:5000/stopwatches/reset/${index}/`, {
            method: "PATCH",
            body: JSON.stringify(update)
        })
        .then(response => response.json())
        .then(data => {
                setStopwatches(allStopwatches => 
                allStopwatches.map(stopwatch => 
                (stopwatch.id === data.id) ? data : stopwatch));
            })
        .catch(error => console.error(error))
    }

    const formatTime = (totalSeconds) => {
        const hours = String(Math.floor(totalSeconds / 3600)).padStart(2, '0');
        const minutes = String(Math.floor((totalSeconds % 3600) / 60)).padStart(2, '0');
        const seconds = String(totalSeconds % 60).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    };

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
        {allStopwatches.map((item, index) => {
            return (
                <div className = "stopwatch-item" key = {index}>
                    <p>{item.title}</p>
                    <div className="time-display">
                        {formatTime(secondsElapsed[index])}
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