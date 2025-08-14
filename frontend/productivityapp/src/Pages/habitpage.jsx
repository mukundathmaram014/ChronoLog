import { FaPlus } from "react-icons/fa";
import { IoMdClose } from "react-icons/io";
import { useState, useEffect, useContext} from 'react';
import './habitpage.css';
import {SortableHabitItem} from "../Components/SortableHabitItem";
import {HabitItem} from "../Components/HabitItem"
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
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import AuthContext from "../context/AuthProvider";



export function Habit() {

  const { auth } = useContext(AuthContext);

  const DatetoISOString = (Date) => {
        const year = Date.getFullYear();
        const month = String(Date.getMonth() + 1).padStart(2, '0');
        const day = String(Date.getDate()).padStart(2,'0');
        const isoString = year + "-" + month + "-" + day;
        return isoString;
    }

  const [activeId, setActiveId] = useState(null);
  const [addHabit, setaddHabit] = useState(false);
  const [editHabit, setEditHabit] = useState(false);
  const [allHabits, setHabits] = useState([]);
  const [newDescription, setNewDescription] = useState("");
  const [isAdding, setIsAdding] = useState(false);
  const [editingHabitID, setEditingHabitID] = useState(null);
  const [today, setToday] = useState(() => (DatetoISOString(new Date())));
  const [selectedDate, setSelectedDate] = useState(today);
  const isFuture = (new Date(selectedDate)) > (new Date(today));
  const [habitError, setHabitError] = useState("");

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // updates state variable today but not selecteday
  useEffect(() => {
    const now = new Date();
    const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDay() + 1, 0, 0, 0, 0) //midnight next day

    const timeout = setTimeout(() => {
      setToday(DatetoISOString(new Date()));
    }, msUntilMidnight);

    return () => clearTimeout(timeout);
  },[today]);

  useEffect(() => {
    let dateToFetch = selectedDate;
            if (isFuture){
                dateToFetch = today;
            }
    fetch(`http://localhost:5000/habits/${dateToFetch}/`, {
      method: "GET",
      headers: {
        'Authorization': `Bearer ${auth.access_token}`
      }
    })
    .then( response => response.json())
    .then(data => setHabits(data.habits))
    .catch(error => console.error(error))
  }, [today, selectedDate, isFuture, auth.access_token]);

  const handleAddHabit = () => {
    if (isFuture){return;}
    setHabitError(""); // Clear previous errors
    const newHabit = {
      description: newDescription,
      done: false,
      date: selectedDate
    }
    setIsAdding(true);
    fetch("http://localhost:5000/habits/", {
      method: "POST",
      headers: {
        'Authorization': `Bearer ${auth.access_token}`
      },
      body: JSON.stringify(newHabit)
    })
    .then(async response => {
      if (response.status === 409) {
        setHabitError("A habit with this description already exists.");
        throw new Error("Duplicate habit");
      }
      return response.json();
    })
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
      method: "DELETE",
      headers: {
        'Authorization': `Bearer ${auth.access_token}`
      }
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
    setHabitError(""); // Clear previous errors

    const newHabit = {
      description: newDescription
    }

    setIsAdding(true);
    fetch(`http://localhost:5000/habits/${editingHabitID}/`,{
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${auth.access_token}`
      },
      body: JSON.stringify(newHabit)
    })
    .then(async response => {
      if (response.status === 409) {
        setHabitError("A habit with this description already exists.");
        throw new Error("Duplicate habit");
      }
      return response.json();
    })
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
      headers: {
        'Authorization': `Bearer ${auth.access_token}`
      },
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

  function handleDragStart(event) {
    const {active} = event;
    
    setActiveId(active.id);
  }
  
  function handleDragEnd(event) {
    const {active, over} = event;
    
    if (active.id !== over.id) {
      setHabits((prevHabits) => {
        const oldIndex = prevHabits.findIndex(habit => habit.id === active.id);
        const newIndex = prevHabits.findIndex(habit => habit.id === over.id);
        
        return arrayMove(prevHabits, oldIndex, newIndex);
      });
    }
    
    setActiveId(null);
  }


  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter}
                onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
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
                  onClick={() => {setaddHabit(false); setHabitError("");}}/>
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
                {habitError && (
                  <div style={{ color: "red", marginBottom: "10px" }}>{habitError}</div>
                )}
              </div>
            </div>
          )}
          {editHabit && (
            <div className = "habit-input">
              <div className = "habit-edit-item">
                <IoMdClose className = "close-icon"
                  onClick={() => {setEditHabit(false); setNewDescription(""); setHabitError("")}}/>
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
                {habitError && (
                <div style={{ color: "red", marginBottom: "10px" }}>{habitError}</div>
                )}
              </div>
            </div>
          )}
          <SortableContext items={allHabits.map(habit => habit.id)} strategy={verticalListSortingStrategy}>
            <div className = "habit-list">
            {allHabits.map((item) =>(
                <SortableHabitItem
                  key={item.id}
                  item={item}
                  isFuture={isFuture}
                  onEdit={item => { setEditHabit(true); setNewDescription(item.description); setEditingHabitID(item.id); }}
                  onDelete={handleDeleteHabit}
                  onToggle={handleToggleHabit}
                  activeId= {activeId}
                />
              ))}
            </div>
          </SortableContext>
        </div>
      </div>
      <DragOverlay>
        {activeId ? <HabitItem 
            item={allHabits.find(h => h.id === activeId)}
            isFuture={isFuture}
            onEdit={item => { setEditHabit(true); setNewDescription(item.description); setEditingHabitID(item.id); }}
            onDelete={handleDeleteHabit}
            onToggle={handleToggleHabit} /> : null}
      </DragOverlay>
    </DndContext>
   
  );
}