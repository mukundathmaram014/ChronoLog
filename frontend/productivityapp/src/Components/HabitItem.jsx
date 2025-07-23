import { MdEdit, MdDelete } from "react-icons/md";
import { FaCheck } from "react-icons/fa";

export function HabitItem({item, isFuture, onEdit, onDelete, onToggle}){
    return (

        <div className = {`habit-list-item ${isFuture ? 'disabled-habit' : ''} ${item.done ? 'completed' : ''}`} 
                  onClick={() => onEdit(item)}>
                <div className = "left-section">
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

    );
}