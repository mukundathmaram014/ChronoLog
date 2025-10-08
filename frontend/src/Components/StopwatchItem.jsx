import { MdEdit, MdDelete } from "react-icons/md";
import {forwardRef} from 'react';
import { RxDragHandleDots2 } from "react-icons/rx";

export const StopwatchItem = forwardRef(({item, isFuture, onEdit, onStart, onStop, onReset, onDelete, runningId, getElapsed, formatTimeString, CircularProgress, CircularProgressTotal, listeners}, ref) => {
       
            if (item.isTotal === true){
                return (
                    <div className = "total-stopwatch-item" key = {item.id} ref = {ref}>
                        <p>Total Time Worked: </p>
                        <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px", marginBottom: "50px" }}>
                                <CircularProgressTotal time ={getElapsed(item)} goal_time = {item.goal_time}/> 
                        </div>  
                    </div>
                )
            } else {
                return (
                <div className = {`stopwatch-item ${isFuture ? "disabled-stopwatch" : ""} ${((runningId !== null) ? ((runningId !== item.id) ? "not-focused-stopwatch" : "focused-stopwatch")  : "")}`}
                        onClick={async () =>{if (isFuture) return; onEdit(item)}}  ref = {ref}>
                    <div className = "stopwatch-title">
                        <p>{item.title}</p>
                    </div>
                    <div className="drag-handle-stopwatch" {...listeners}>
                        <RxDragHandleDots2 className="drag-icon-stopwatch" />
                    </div>
                    <div className="Completion" style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "18px" }}>
                                <CircularProgress time ={getElapsed(item)} goal_time = {item.goal_time}/> 
                    </div>  
                    <div className="goal-time">
                        {(() => {
                            const [goalHours, goalMinutes] = formatTimeString(item.goal_time);
                            return <>Goal: {goalHours}h {goalMinutes}m</>;
                        })()}
                    </div>
                    <div className="controls">
                        <button onClick={(e) => {e.stopPropagation(); onStart(item.id, item.end_time)}} disabled = {isFuture}>Start</button>
                        <button onClick={(e) => {e.stopPropagation(); onStop(item.id, item.end_time)}} disabled = {isFuture}>Pause</button>
                        <button onClick={(e) => {e.stopPropagation(); onReset(item.id, item.end_time)}} disabled = {isFuture}>Reset</button>
                        <MdEdit className = "stopwatch-edit-icon"/>
                        <MdDelete className = "stopwatch-delete-icon"
                            onClick = {(e) => {e.stopPropagation(); if (isFuture) return; onDelete(item.id)}}/>
                    </div>
                </div>
            )
            }
});