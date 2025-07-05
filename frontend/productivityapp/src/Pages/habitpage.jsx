import { MdDelete } from "react-icons/md";
import { FaCheck } from "react-icons/fa";
import { FaPlus } from "react-icons/fa";
import { IoMdClose } from "react-icons/io";
import { MdEdit } from "react-icons/md";
import { useState, useEffect } from 'react';
import './habitpage.css';


export function Habit() {
  const [addHabit, setaddHabit] = useState(false);
  const [editHabit, setEditHabit] = useState(false);
  const [allHabits, setHabits] = useState([]);
  const [newDescription, setNewDescription] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [editingHabitID, setEditingHabitID] = useState(null);
  const [today, setToday] = useState(() => (new Date()).toISOString().slice(0,10));
  const [selectedDate, setSelectedDate] = useState(today);
  const isFuture = (new Date(selectedDate)) > (new Date(today))

  useEffect(() => {
    const now = new Date();
    const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDay() + 1, 0, 0, 0, 0) //midnight next day

    const timeout = setTimeout(() => {
      setToday((new Date()).toISOString().slice(0,10))
    }, msUntilMidnight);

    return () => clearTimeout(timeout);
  },[today]);

  useEffect(() => {
    let dateToFetch = selectedDate;
            if (isFuture){
                dateToFetch = today;
            }
    fetch(`http://localhost:5000/habits/${dateToFetch}/`, {
      method: "GET"
    })
    .then( response => response.json())
    .then(data => setHabits(data.habits))
    .catch(error => console.error(error))
  }, [today, selectedDate, isFuture]);

  const handleAddHabit = () => {
    if (isFuture){return;}
    const newHabit = {
      description: newDescription,
      done: false,
      date: selectedDate
    }
    setIsAdding(true);
    fetch("http://localhost:5000/habits/", {
      method: "POST",
      body: JSON.stringify(newHabit)
    })
    .then(response => response.json())
    .then( data => {
      setHabits(allHabits => [...allHabits, data]);
      setNewDescription("");
      setaddHabit(false);
    }
    )
    .catch(error => console.error(error))
    .finally(() => setIsAdding(false))
  };

  const handleDeleteHabit = (index) => {
    if (isFuture){return;}
    fetch(`http://localhost:5000/habits/${index}/`, {
      method: "DELETE"
    })
    .then(response => response.json())
    .then(data =>
      setHabits(allHabits => allHabits.filter(habit => (habit.id !== data.id)))
    )
    .catch(error => console.error(error))
  }

  const handleEditHabit = () => {
    if (isFuture){return;}
    if (editingHabitID === null) return;

    const newHabit = {
      description: newDescription
    }

    setIsAdding(true);
    fetch(`http://localhost:5000/habits/${editingHabitID}/`,{
      method: 'PUT',
      body: JSON.stringify(newHabit)
    })
    .then(response => response.json())
    .then(data => {
      setHabits(allHabits =>
        allHabits.map(habit =>
          (habit.id === data.id) ? data : habit 
        ));
      setNewDescription("");
      setEditHabit(false);
      setEditingHabitID(null);
    }
    )
    .catch(error => console.error(error))
    .finally(() => setIsAdding(false))
  }

  const handleToggleHabit = (index, currStatus) => {
    if (isFuture){return;}
    const newHabit = {
      done: !currStatus
    }
    fetch(`http://localhost:5000/habits/${index}/`,{
      method: "PUT",
      body: JSON.stringify(newHabit)
    })
    .then(response => response.json())
    .then(data => {
      setHabits(allHabits => 
        allHabits.map(habit =>
          (habit.id === data.id) ? data : habit
        ))
    }
    )
    .catch(error => console.error(error))
  }


  return (
    <div className="App">
      <div className="date-slider-container">
            <label htmlFor="date-slider">Select Date: </label>
            <input
                type="date"
                id="date-slider"
                value={selectedDate}
                onChange={e => setSelectedDate(e.target.value)}
            />
        </div>
      <h1>My Habits</h1>
      <div className="habit-wrapper">
        <button type = 'button' className = 'primaryBtn'
            onClick={() => setaddHabit(true)} disabled = {isFuture}>
            <FaPlus className = "plus-icon" />
        </button>
        {addHabit && (
          <div className = "habit-input">
            <div className = "habit-input-item">
              <IoMdClose className = "close-icon"
                onClick={() => setaddHabit(false)}/>
              <h3>Add a New Habit</h3>
              <label>Description</label>
              <input type= "text" value = {newDescription} 
              onChange={(e) => setNewDescription(e.target.value) }
              onKeyDown={(e) => {
                if (e.key === "Enter"){
                  handleAddHabit();
                }
              }}
              placeholder="What's the habit"/>
              <button type = 'button' className = 'addHabitButton'
                onClick={handleAddHabit}
                disabled = {isAdding}
                > {isAdding ? "Adding..." : "Add Habit"}</button>
            </div>
          </div>
        )}
        {editHabit && (
          <div className = "habit-input">
            <div className = "habit-edit-item">
              <IoMdClose className = "close-icon"
                onClick={() => {setEditHabit(false); setNewDescription("")}}/>
              <h3>Edit habit</h3>
              <label>Description</label>
              <input type= "text" value = {newDescription} 
              onChange={(e) => setNewDescription(e.target.value) }
              onKeyDown={(e) => {
                if (e.key === "Enter"){
                  handleEditHabit();
                }
              }}
              placeholder="What's the habit"/>
              <button type = 'button' className = 'editHabitButton'
                onClick={handleEditHabit}
                disabled = {isAdding}
                > {isAdding ? "Editing..." : "Done"}</button>
            </div>
          </div>
         )}
        <div className = "habit-list">
          {allHabits.map((item) =>{
             return (
              <div className = {`habit-list-item ${isFuture ? 'disabled-habit' : ''} ${item.done ? 'completed' : ''}`} 
                  onClick={() => {setEditHabit(true); setNewDescription(item.description);
                  setEditingHabitID(item.id);
                  }}key = {item.id}>
                <div className = "left-section">
                  <div
                    className={`custom-checkbox ${item.done ? 'checked' : ''}`}
                    onClick={(e) => {e.stopPropagation(); if (isFuture) return; handleToggleHabit(item.id, item.done)}}
                  >
                    {item.done && <FaCheck className="check-icon" />}
                  </div>
                  <div className = "habit-text">
                    <p>{item.description}</p>
                  </div>
                </div>
                <div className = "icon-bar">
                  <MdEdit className = "edit-icon"
                   onClick={() => {if (isFuture) return;setEditHabit(true); setNewDescription(item.description);
                    setEditingHabitID(item.id);
                   }}/>
                  <MdDelete className = "delete-icon"
                   onClick={(e) => {e.stopPropagation();if (isFuture) return;handleDeleteHabit(item.id)}}/>
                </div>
              </div>
             )
            })}
        
        </div>
      </div>
    </div>
  );
}