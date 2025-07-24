import { MdEdit, MdDelete } from "react-icons/md";
import { FaCheck } from "react-icons/fa";
import {forwardRef} from 'react';
import { RxDragHandleDots2 } from "react-icons/rx";

export const HabitItem = forwardRef(({item, isFuture, onEdit, onDelete, onToggle, listeners}, ref) => {
    return (
            <div className = {`habit-list-item ${isFuture ? 'disabled-habit' : ''} ${item.done ? 'completed' : ''}`} 
                  onClick={() => {if (isFuture) return; onEdit(item)}} ref = {ref}>
                <div className = "left-section">
                    <div className="drag-handle-habit" {...listeners}>
                        <RxDragHandleDots2 className="drag-icon-habit" />
                    </div>
                  <div
                    className={`custom-checkbox ${item.done ? 'checked' : ''}`}
                    onClick={(e) => {e.stopPropagation(); if (isFuture) return; onToggle(item.id, item.done)}}
                  >
                    {item.done && <FaCheck className="check-icon" />}
                  </div>
                  <div className = "habit-text">
                    <p>{item.description}</p>
                  </div>
                </div>
                <div className = "icon-bar">
                  <MdEdit className = "edit-icon"
                   onClick={() => {if (isFuture) return; onEdit(item); // dont need to stop propogation as both are editing
                   }}/>
                  <MdDelete className = "delete-icon"
                   onClick={(e) => {e.stopPropagation();if (isFuture) return; onDelete(item.id); }}/>
                </div>
              </div>


    )
});