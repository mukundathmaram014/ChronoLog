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
  TouchSensor,
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
import { StopwatchSessionLog } from '../Components/StopwatchSessionLog.jsx';
import { useLocation } from "react-router-dom";
import useFetch from "../hooks/useFetch";

// bit i = weekday i (0 = Mon ... 6 = Sun), matching Python date.weekday(); 127 = every day
const WEEKDAY_LABELS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
const ALL_DAYS = 127;

export function Stopwatch() {

    const fetchWithAuth = useFetch();

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
    const [noGoal, setNoGoal] = useState(false);
    const [isRecurring, setIsRecurring] = useState(true);
    const [repeatDays, setRepeatDays] = useState(ALL_DAYS);
    const [previousTitles, setPreviousTitles] = useState([]);
    const [editingIsTotal, setEditingIsTotal] = useState(false);
    const [matchSum, setMatchSum] = useState(true);
    const [currentHours, setCurrentHours] = useState(0);
    const [currentMinutes, setCurrentMinutes] = useState(0);
    const [currentSeconds, setCurrentSeconds] = useState(0);
    const [currentCentiseconds, setCurrentCentiseconds] = useState(0);
    const isFuture = (new Date(selectedDate)) > (new Date(today));
    const intervalRef = useRef(null);
    // client-clock anchor for the running interval, captured when the start response
    // arrives; getElapsed uses it instead of the server's interval_start so the live
    // display doesn't drift by the client/server clock skew (spec 0006)
    const intervalStartClientRef = useRef(null);
    const defaultTitleRef = useRef(document.title);
    // title of the stopwatch that was running at midnight; the data effect starts
    // its fresh copy on the new day (midnight rollover hand-off)
    const rolloverTitleRef = useRef(null);
    const [stopwatchError, setStopwatchError] = useState("");
    // session log (spec 0030): collapsed by default and lazily fetched — expanding
    // is the only thing that loads it, and a date change collapses it back to unloaded
    const [sessionLogOpen, setSessionLogOpen] = useState(false);
    const [sessionIntervals, setSessionIntervals] = useState(null);
    const [sessionLogLoading, setSessionLogLoading] = useState(false);
    const location = useLocation();
    

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 5 },
        }),
        // touch devices without pointer events; a short hold distinguishes drag from scroll
        useSensor(TouchSensor, {
            activationConstraint: { delay: 200, tolerance: 8 },
        }),
        useSensor(KeyboardSensor, {
        coordinateGetter: sortableKeyboardCoordinates,
        })
    );
    

    // midnight rollover: remember which stopwatch was running (by title), then
    // advance today AND selectedDate. The data effect below finalizes the old
    // day (stop persists its time up to ~00:00), fetches the new day (carry-
    // forward creates fresh rows at 0), and restarts the remembered stopwatch
    // so it keeps running, focused, counting up from 0 under the new day.
    useEffect(() => {
        const now = new Date();
        const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0) - now //midnight next day
        const timeout = setTimeout(() => {
            const running = allStopwatchesRef.current.find(
                sw => sw.end_time === null && !sw.isTotal
            );
            rolloverTitleRef.current = running ? running.title : null;
            const newToday = DatetoISOString(new Date());
            setToday(newToday);
            setSelectedDate(newToday);
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
                await fetchWithAuth(`/stopwatches/stop/${running.id}/`, {
                method: "PATCH"
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
            fetchWithAuth(`/stopwatches/${dateToFetch}/`, {
                method: "GET"
                })
            .then(response => response.json())
            .then(data => {
                setRunningId(null);
                intervalStartClientRef.current = null;
                setStopwatches((data.stopwatches));
                // midnight hand-off: restart the stopwatch that was running when
                // the day rolled over — its fresh copy counts up from 0 on the new day
                const rolloverTitle = rolloverTitleRef.current;
                rolloverTitleRef.current = null;
                const match = (rolloverTitle === null || dateToFetch !== today) ? null :
                    data.stopwatches.find(sw => !sw.isTotal && sw.title === rolloverTitle);
                if (match) {
                    setRunningId(match.id);
                    clearInterval(intervalRef.current);
                    intervalRef.current = setInterval(() => {
                        setTick(tick => tick + 1);
                    }, 10);
                    fetchWithAuth(`/stopwatches/start/${match.id}/`, {
                        method: "PATCH"
                    })
                    .then(response => response.json())
                    .then(started => {
                        setStopwatches(allStopwatches =>
                            allStopwatches.map(stopwatch =>
                                (stopwatch.isTotal) ? started.stopwatches[0] :
                             (stopwatch.id === started.stopwatches[1].id) ? started.stopwatches[1] : stopwatch)); // updates total stopwatch and stopwatch that rolled over
                    })
                    .catch(error => console.error(error));
                } else {
                    setRunningId(null);
                }
            })
            .catch(error => console.error(error));
            });

        return () => {
            clearInterval(intervalRef.current);
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedDate, today, isFuture]); 

    // updates reference whenever allStopwatch updated.
    useEffect ( () => {
        allStopwatchesRef.current = allStopwatches;
    }, [allStopwatches]);

    // the session log never persists across days: changing the date collapses it,
    // so re-expanding refetches for the day now shown
    useEffect(() => {
        setSessionLogOpen(false);
        setSessionIntervals(null);
    }, [selectedDate]);
    

    // stops running stopwatches when website closed
    useEffect ( () => {
        const handleUnload = () => {
            allStopwatchesRef.current.forEach(stopwatch => {
                if ((stopwatch.end_time === null) && !stopwatch.isTotal){
                    fetchWithAuth(`/stopwatches/stop/${stopwatch.id}/`, {
                        keepalive : true,
                        method : "PATCH"
                    });
                };
                setRunningId(null);
            });
        }
        window.addEventListener('pagehide', handleUnload)
        return () => window.removeEventListener('pagehide', handleUnload);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    //stops running stopwatches when user navigates to different page
    useEffect(() => {
        return () => {
            allStopwatchesRef.current.forEach(stopwatch => {
            if ((stopwatch.end_time === null) && !stopwatch.isTotal){

                fetchWithAuth(`/stopwatches/stop/${stopwatch.id}/`, {
                    keepalive : true,
                    method : "PATCH"
                });
            }
            });
            setRunningId(null);
        };
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [location.pathname]);

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

    // shows the running stopwatch's live elapsed time in the browser tab
    useEffect(() => {
        const running = allStopwatches.find(stopwatch => (stopwatch.id === runningId) && !stopwatch.isTotal);
        let newTitle = defaultTitleRef.current;
        if (running) {
            const [hours, minutes, seconds] = formatTimeString(getElapsed(running));
            newTitle = `${hours}:${minutes}:${seconds}`;
        }
        if (document.title !== newTitle) {
            document.title = newTitle;
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [runningId, tick, allStopwatches]);

    // restores the default title on unmount (navigating to another page)
    useEffect(() => {
        const defaultTitle = defaultTitleRef.current;
        return () => {
            document.title = defaultTitle;
        };
    }, []);


    // loads the selected day's recorded segments; called on expand and after any
    // action that changes them while the log is open
    const loadSessionIntervals = async () => {
        if (isFuture) {
            return;
        }
        setSessionLogLoading(true);
        try {
            const response = await fetchWithAuth(`/stopwatches/intervals/${selectedDate}/`, {
                method: "GET"
            });
            const data = await response.json();
            setSessionIntervals(data.intervals);
        } catch (error) {
            console.error(error);
        } finally {
            setSessionLogLoading(false);
        }
    }

    const addStopwatch = async () => {
        if (isFuture){
            return;
        }
        if (isRecurring && repeatDays === 0) {
            setStopwatchError("Select at least one repeat day.");
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
            goal_time : noGoal ? null : inputTimeString,
            is_recurring : isRecurring,
            // a non-recurring stopwatch never carries, so its mask stays the every-day default
            repeat_days : isRecurring ? repeatDays : ALL_DAYS
        }
        setIsAdding(true);

        try{
            const response = await fetchWithAuth(`/stopwatches/`, {
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
            setNoGoal(false);
            setIsRecurring(true);
            setRepeatDays(ALL_DAYS);
        } catch (error) {
            console.error(error);
        }  finally {
            setIsAdding(false);
        }
    }

    // "reuse previous" dropdown: prefills the add form with a prior title, its goal
    // and its repeat days
    const prefillFromPrevious = (title) => {
        const previous = previousTitles.find(p => p.title === title);
        if (!previous) return;
        setStopwatchTitle(previous.title);
        setNoGoal(!previous.goal_time);
        setRepeatDays(previous.repeat_days ?? ALL_DAYS);
        const [hours, minutes] = formatTimeString(previous.goal_time || 3600000);
        setInputHours(Number(hours));
        setInputMinutes(Number(minutes));
    }

    const deleteStopwatch = async (index) => {
        if (isFuture) {
            return;
        }
        try{
            const response = await fetchWithAuth(`/stopwatches/${index}/`, {
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
                intervalStartClientRef.current = null;
                setRunningId(null);
            }
            // the cascade removed the deleted stopwatch's segments
            if (sessionLogOpen) {
                loadSessionIntervals();
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
                const response = await fetchWithAuth(`/stopwatches/start/${index}/`, {
                    method: "PATCH"
                })
                const data = await response.json();
                intervalStartClientRef.current = Date.now();
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
                const response = await fetchWithAuth(`/stopwatches/stop/${index}/`, {
                method: "PATCH"
            })
                const data = await response.json();
                setStopwatches(allStopwatches => 
                    allStopwatches.map(stopwatch => 
                        (stopwatch.isTotal) ? data.stopwatches[0] : 
                     (stopwatch.id === data.stopwatches[1].id) ? data.stopwatches[1] : stopwatch)); // updates total stopwatches and stopwatch that stopped
                clearInterval(intervalRef.current);
                intervalStartClientRef.current = null;
                if (tick === 0){}; // just to avoid compiled with warnings. remove later
                // the stop just recorded a segment
                if (sessionLogOpen) {
                    loadSessionIntervals();
                }

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
            const response = await fetchWithAuth(`/stopwatches/reset/${index}/`, {
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
                    intervalStartClientRef.current = null;
                    setRunningId(null);
                }
            // the reset dropped that stopwatch's segments for the day
            if (sessionLogOpen) {
                loadSessionIntervals();
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
        if (!editingIsTotal && isRecurring && repeatDays === 0) {
            setStopwatchError("Select at least one repeat day.");
            return;
        }

        const inputTimeString =`${String(safeGoalHours).padStart(2, '0')}:${String(safeGoalMinutes).padStart(2, '0')}`;
        const newDuration = (safeCurrHours * 3600000) + (safeCurrMinutes * 60000) + (safeCurrSeconds * 1000) + (safeCurrCentiseconds * 10)

        // Editing the Total sets the daily goal: "match sum" clears the override,
        // otherwise the entered time is a custom override. Its elapsed isn't edited.
        // Editing a child sends its own goal (null = no goal) and current time.
        const newStopwatch = editingIsTotal
            ? (matchSum
                ? { title: stopwatchTitle, match_sum: true }
                : { title: stopwatchTitle, goal_time: inputTimeString })
            : { title: stopwatchTitle, goal_time: noGoal ? null : inputTimeString, curr_duration: newDuration, is_recurring: isRecurring, repeat_days: isRecurring ? repeatDays : ALL_DAYS };

        setIsAdding(true);

        try {
            const response = await fetchWithAuth(`/stopwatches/${editingStopwatchID}/`, {
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
            setNoGoal(false);
            setIsRecurring(true);
            setRepeatDays(ALL_DAYS);
            setEditingIsTotal(false);
            setMatchSum(true);
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
        // only a stopwatch dated today may tick live; a past-day one with a null
        // end_time is stale (left running when the tab closed) and stays frozen
        if (stopwatch.end_time != null || stopwatch.date !== today){
            return stopwatch.curr_duration;
        } else if (intervalStartClientRef.current != null) {
            // both the running stopwatch and the Total share the same interval, so
            // one anchor covers both (only one stopwatch can run at a time)
            return stopwatch.curr_duration + (Date.now() - intervalStartClientRef.current);
        } else {
            // no anchor (e.g. a stopwatch left running by a previous session):
            // fall back to the server timestamp
            return stopwatch.curr_duration + (Date.now() - new Date(stopwatch.interval_start));
        }
    }

    // opens the edit form for a stopwatch (pausing it first if running), seeding the
    // goal inputs. For the Total row, seeds the "match sum of goals" toggle from
    // goal_overridden; for a child, seeds the "no goal" toggle from its goal_time.
    const openEditStopwatch = async (item) => {
        // pause a running child before editing its time; the Total's goal edit
        // doesn't touch its timer, so don't stop it (avoids desyncing a running child)
        if (!item.isTotal && item.end_time === null) {
            await handleStop(item.id, item.end_time);
        }
        setEditStopwatch(true);
        setStopwatchTitle(item.title);
        setEditingStopwatchID(item.id);
        setEditingIsTotal(item.isTotal);
        if (item.isTotal) {
            setMatchSum(!item.goal_overridden);
        } else {
            setNoGoal(!item.goal_time);
            setIsRecurring(item.is_recurring);
            setRepeatDays(item.repeat_days ?? ALL_DAYS);
        }
        const [hours, minutes] = formatTimeString(item.goal_time || 3600000);
        setInputHours(Number(hours));
        setInputMinutes(Number(minutes));
    }

    // only meaningful for a recurring stopwatch — repeat days gate which weekdays it carries to
    const renderWeekdayPicker = () => (
        <>
          <label style={{ marginTop: "18px", display: "block" }}>Repeat on</label>
          <div className="weekday-picker">
            {WEEKDAY_LABELS.map((label, i) => (
              <button type="button" key={label}
                className={`weekday-toggle ${(repeatDays & (1 << i)) ? 'selected' : ''}`}
                onClick={() => setRepeatDays(prev => prev ^ (1 << i))}>
                {label}
              </button>
            ))}
          </div>
          {repeatDays === 0 && (
            <div style={{ color: "red", marginBottom: "10px" }}>Select at least one day.</div>
          )}
        </>
    );

    function CircularProgress({time, goal_time, size = 330, strokeWidth = 50, bgColor = "#444" }) {
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

        if (over && active.id !== over.id) {
            const total = allStopwatches.find(stopwatch => stopwatch.isTotal);
            const rest = allStopwatches.filter(stopwatch => !stopwatch.isTotal);
            const oldIndex = rest.findIndex(stopwatch => stopwatch.id === active.id);
            const newIndex = rest.findIndex(stopwatch => stopwatch.id === over.id);
            const reordered = arrayMove(rest, oldIndex, newIndex);
            setStopwatches(total ? [total, ...reordered] : reordered);

            // the Total is never sent in the reorder payload
            if (!isFuture) {
                fetchWithAuth("/stopwatches/reorder/", {
                    method: "PATCH",
                    body: JSON.stringify({ date: selectedDate, order: reordered.map(stopwatch => stopwatch.id) })
                })
                .catch(error => console.error(error));
            }
        }

        setActiveId(null);
    }


    const totalStopwatch = allStopwatches.find(stopwatch => stopwatch.isTotal);
    const nonTotalStopwatches = allStopwatches.filter(stopwatch => !stopwatch.isTotal);
    // the open segment has no row in the table yet, so the log renders it live
    const runningStopwatch = nonTotalStopwatches.find(
        stopwatch => stopwatch.end_time === null && stopwatch.date === selectedDate
    );

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
            <button className = "primaryBtn" onClick = {() => {
                setAddingStopwatch(true); setNoGoal(false); setInputHours(1); setInputMinutes(0); setIsRecurring(true); setRepeatDays(ALL_DAYS);
                // feeds the "reuse previous" dropdown with the user's distinct prior titles
                fetchWithAuth(`/stopwatches/titles/`, { method: "GET" })
                    .then(response => response.json())
                    .then(data => setPreviousTitles(data.titles))
                    .catch(error => console.error(error));
            }} disabled = {isFuture}>
                <FaPlus className = "plus-icon" />
            </button>
        </div>
        {editStopwatch && (
                  <div className = "stopwatch-input">
                    <div className = "stopwatch-edit-item">
                      <IoMdClose className = "close-icon"
                        onClick={() => {setEditStopwatch(false); setStopwatchTitle(""); setInputHours(1); setInputMinutes(0); setNoGoal(false); setIsRecurring(true); setEditingIsTotal(false); setMatchSum(true); setStopwatchError("");}}/>
                      <h3>{editingIsTotal ? "Set Daily Goal" : "Edit Stopwatch"}</h3>
                      {!editingIsTotal && (
                        <>
                          <label>Title: </label>
                          <input type= "text" value = {stopwatchTitle}
                          onChange={(e) => setStopwatchTitle(e.target.value) }
                          onKeyDown={(e) => {
                            if (e.key === "Enter"){
                              handleEditStopwatch();
                            }
                          }}
                          placeholder="What's the stopwatch for"/>
                        </>
                      )}
                      <label style={{ marginTop: "18px", display: "block" }}>{editingIsTotal ? "Daily Goal:" : "Goal Time:"}</label>
                      {editingIsTotal ? (
                        <label className="no-goal-toggle">
                          <input type="checkbox" checked={matchSum} onChange={e => setMatchSum(e.target.checked)} />
                          Match sum of stopwatch goals
                        </label>
                      ) : (
                        <label className="no-goal-toggle">
                          <input type="checkbox" checked={noGoal} onChange={e => setNoGoal(e.target.checked)} />
                          No goal
                        </label>
                      )}
                      <div className = "goal-time-inputs">
                        <label htmlFor="goal-hours">Hours:</label>
                        <input
                            type="number"
                            id = "goal-hours"
                            min = "0"
                            max = "23"
                            value={inputHours}
                            disabled={editingIsTotal ? matchSum : noGoal}
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
                            disabled={editingIsTotal ? matchSum : noGoal}
                            onChange={e => setInputMinutes(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === "Enter") handleEditStopwatch();
                            }}
                        />
                      </div>
                      {!editingIsTotal && (
                        <>
                      <label className="no-goal-toggle">
                        <input type="checkbox" checked={isRecurring} onChange={e => setIsRecurring(e.target.checked)} />
                        Recurring (carries forward to future days)
                      </label>
                      {isRecurring && renderWeekdayPicker()}
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
                            onChange={e => setCurrentSeconds(e.target.value)}
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
                        </>
                      )}
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
                        onClick={() => {setAddingStopwatch(false); setNoGoal(false); setIsRecurring(true); setStopwatchError("")}}/>
                      <h3>Add a New Stopwatch</h3>
                      {previousTitles.length > 0 && (
                        <>
                          <label htmlFor="reuse-previous">Reuse previous: </label>
                          <select
                            id="reuse-previous"
                            className="reuse-previous-select"
                            value=""
                            onChange={e => prefillFromPrevious(e.target.value)}
                          >
                            <option value="" disabled>Select a previous stopwatch…</option>
                            {previousTitles.map(previous => (
                              <option key={previous.title} value={previous.title}>{previous.title}</option>
                            ))}
                          </select>
                        </>
                      )}
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
                      <label className="no-goal-toggle">
                        <input type="checkbox" checked={noGoal} onChange={e => setNoGoal(e.target.checked)} />
                        No goal
                      </label>
                      <div className = "goal-time-inputs">
                        <label htmlFor="goal-hours">Hours:</label>
                        <input
                            type="number"
                            id = "goal-hours"
                            min = "0"
                            max = "23"
                            value={inputHours}
                            disabled={noGoal}
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
                            disabled={noGoal}
                            onChange={e => setInputMinutes(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === "Enter"){
                                    addStopwatch();
                                }
                            }}
                        />
                      </div>
                      <label className="no-goal-toggle">
                        <input type="checkbox" checked={isRecurring} onChange={e => setIsRecurring(e.target.checked)} />
                        Recurring (carries forward to future days)
                      </label>
                      {isRecurring && renderWeekdayPicker()}
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
        {totalStopwatch && (
            <StopwatchItem
                item={totalStopwatch}
                isFuture={isFuture}
                onEdit={openEditStopwatch}
                onStart = {handleStart}
                onStop = {handleStop}
                onReset = {handleReset}
                onDelete={deleteStopwatch}
                runningId = {runningId}
                getElapsed = {getElapsed}
                formatTimeString = {formatTimeString}
                CircularProgress = {CircularProgress}
                CircularProgressTotal = {CircularProgressTotal}
            />
        )}
        <SortableContext items={nonTotalStopwatches.map(stopwatch => stopwatch.id)} strategy={rectSortingStrategy}>
            {nonTotalStopwatches.map((item) => (
            <SortableStopwatchItem
                key={item.id}
                item={item}
                isFuture={isFuture}
                onEdit={openEditStopwatch}
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

    {/* opt-in detail view of the day's real timed segments (spec 0030) */}
    {!isFuture && (
        <div className="session-log">
            <button
                type="button"
                className="session-log-toggle"
                aria-expanded={sessionLogOpen}
                onClick={() => {
                    const opening = !sessionLogOpen;
                    setSessionLogOpen(opening);
                    if (opening && sessionIntervals === null) {
                        loadSessionIntervals();
                    }
                }}
            >
                Session log {sessionLogOpen ? "▾" : "▸"}
            </button>
            {sessionLogOpen && (
                <StopwatchSessionLog
                    intervals={sessionIntervals || []}
                    loading={sessionLogLoading && sessionIntervals === null}
                    runningSegment={runningStopwatch}
                />
            )}
        </div>
    )}

    </div>
    <DragOverlay>
            {activeId ? <StopwatchItem 
                item={allStopwatches.find(s => s.id === activeId)}
                isFuture={isFuture}
                onEdit={openEditStopwatch}
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