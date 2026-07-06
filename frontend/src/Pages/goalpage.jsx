import { FaPlus, FaCheck } from "react-icons/fa";
import { IoMdClose } from "react-icons/io";
import { MdEdit, MdDelete } from "react-icons/md";
import { useState, useEffect } from 'react';
import './goalpage.css';
import useFetch from "../hooks/useFetch";

const DIFFICULTY_OPTIONS = ["easy", "medium", "hard"];

export function Goals() {

  const fetchWithAuth = useFetch();

  const DatetoISOString = (Date) => {
        const year = Date.getFullYear();
        const month = String(Date.getMonth() + 1).padStart(2, '0');
        const day = String(Date.getDate()).padStart(2,'0');
        const isoString = year + "-" + month + "-" + day;
        return isoString;
    }

  const [goals, setGoals] = useState([]);
  const [addGoal, setAddGoal] = useState(false);
  const [editGoal, setEditGoal] = useState(false);
  const [editingGoalID, setEditingGoalID] = useState(null);
  const [newDescription, setNewDescription] = useState("");
  const [newDifficulty, setNewDifficulty] = useState("medium");
  const [isSaving, setIsSaving] = useState(false);
  const [goalError, setGoalError] = useState("");

  const fetchGoals = () => {
    fetchWithAuth(`/goals/`, {
      method: "GET"
    })
    .then(response => response.json())
    .then(data => setGoals(data.goals ?? []))
    .catch(error => console.error(error))
  }

  useEffect(() => {
    fetchGoals();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAddGoal = () => {
    if (!newDescription.trim()) {
      setGoalError("Enter a description.");
      return;
    }
    setGoalError("");
    const newGoal = {
      description: newDescription,
      difficulty: newDifficulty
    }
    setIsSaving(true);
    fetchWithAuth("/goals/", {
      method: "POST",
      body: JSON.stringify(newGoal)
    })
    .then(response => response.json())
    .then(() => {
      setNewDescription("");
      setNewDifficulty("medium");
      setAddGoal(false);
      fetchGoals();
    })
    .catch(error => console.error(error))
    .finally(() => setIsSaving(false))
  };

  // completing grants the goal's XP on today's (client-local) date;
  // un-completing takes it back out
  const handleToggleGoal = (goal) => {
    fetchWithAuth(`/goals/${goal.id}/`, {
      method: "PUT",
      body: JSON.stringify({ done: !goal.done, date: DatetoISOString(new Date()) })
    })
    .then(response => response.json())
    .then(() => fetchGoals())
    .catch(error => console.error(error))
  };

  const handleDeleteGoal = (goalId) => {
    fetchWithAuth(`/goals/${goalId}/`, {
      method: "DELETE"
    })
    .then(response => response.json())
    .then(() => fetchGoals())
    .catch(error => console.error(error))
  };

  const openEditGoal = (item) => {
    setEditGoal(true);
    setEditingGoalID(item.id);
    setNewDescription(item.description);
    setNewDifficulty(item.difficulty ?? "medium");
  };

  const handleEditGoal = () => {
    if (isSaving) return;
    if (editingGoalID === null) return;
    if (!newDescription.trim()) {
      setGoalError("Enter a description.");
      return;
    }
    setGoalError("");

    setIsSaving(true);
    fetchWithAuth(`/goals/${editingGoalID}/`, {
      method: "PUT",
      body: JSON.stringify({ description: newDescription, difficulty: newDifficulty })
    })
    .then(response => response.json())
    .then(() => {
      setNewDescription("");
      setNewDifficulty("medium");
      setEditGoal(false);
      setEditingGoalID(null);
      fetchGoals();
    })
    .catch(error => console.error(error))
    .finally(() => setIsSaving(false))
  };

  const closeEditGoal = () => {
    setEditGoal(false);
    setEditingGoalID(null);
    setNewDescription("");
    setNewDifficulty("medium");
    setGoalError("");
  };

  const formatCompletedDate = (dateString) => {
    return new Date(dateString + "T00:00:00").toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const renderDifficultyPicker = () => (
    <>
      <label>Difficulty</label>
      <div className="difficulty-picker">
        {DIFFICULTY_OPTIONS.map(option => (
          <button type="button" key={option}
            className={`difficulty-toggle ${option} ${newDifficulty === option ? 'selected' : ''}`}
            onClick={() => setNewDifficulty(option)}>
            {option.charAt(0).toUpperCase() + option.slice(1)}
          </button>
        ))}
      </div>
    </>
  );

  const renderGoalItem = (item) => (
    <div key={item.id} className={`goal-list-item ${item.done ? 'completed' : ''}`}
          onClick={() => openEditGoal(item)}>
      <div className="left-section">
        <div
          className={`custom-checkbox ${item.done ? 'checked' : ''}`}
          onClick={(e) => {e.stopPropagation(); handleToggleGoal(item)}}
        >
          {item.done && <FaCheck className="check-icon" />}
        </div>
        <div className="goal-text">
          <p>{item.description}</p>
          <span className="goal-meta">
            <span className={`goal-difficulty ${item.difficulty}`}>{item.difficulty}</span>
            {item.done && item.completed_date && ` · completed ${formatCompletedDate(item.completed_date)}`}
          </span>
        </div>
      </div>
      <div className="icon-bar">
        <MdEdit className="edit-icon"
          onClick={() => openEditGoal(item)}/>
        <MdDelete className="delete-icon"
          onClick={(e) => {e.stopPropagation(); handleDeleteGoal(item.id)}}/>
      </div>
    </div>
  );

  const activeGoals = goals.filter(goal => !goal.done);
  const completedGoals = goals.filter(goal => goal.done);

  return (
    <div className="App">
      <h1>My Goals</h1>
      <div className="goal-wrapper">
        <button type='button' className='primaryBtn'
            onClick={() => {setAddGoal(true); setNewDifficulty("medium");}}>
            <FaPlus className="plus-icon" />
        </button>
        {addGoal && (
          <div className="goal-input">
            <div className="goal-input-item">
              <IoMdClose className="close-icon"
                onClick={() => {setAddGoal(false); setGoalError("");}}/>
              <h3>Add a New Goal</h3>
              <label>Description</label>
              <input type="text" value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter"){
                  handleAddGoal();
                }
              }}
              placeholder="What's the goal"/>
              {renderDifficultyPicker()}
              <button type='button' className='addGoalButton'
                onClick={handleAddGoal}
                disabled={isSaving}
                > {isSaving ? "Adding..." : "Add Goal"}</button>
              {goalError && (
                <div style={{ color: "red", marginBottom: "10px" }}>{goalError}</div>
              )}
            </div>
          </div>
        )}
        {editGoal && (
          <div className="goal-input">
            <div className="goal-edit-item">
              <IoMdClose className="close-icon"
                onClick={closeEditGoal}/>
              <h3>Edit goal</h3>
              <label>Description</label>
              <input type="text" value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter"){
                  handleEditGoal();
                }
              }}
              placeholder="What's the goal"/>
              {renderDifficultyPicker()}
              <button type='button' className='editGoalButton'
                onClick={handleEditGoal}
                disabled={isSaving}
                > {isSaving ? "Saving..." : "Done"}</button>
              {goalError && (
                <div style={{ color: "red", marginBottom: "10px" }}>{goalError}</div>
              )}
            </div>
          </div>
        )}
        <div className="goal-list">
          <div className="goal-group">
            <h2 className="goal-group-title">Active</h2>
            {activeGoals.length === 0 && <p className="goal-group-empty">No active goals — add one.</p>}
            {activeGoals.map(renderGoalItem)}
          </div>
          <div className="goal-group">
            <h2 className="goal-group-title">Completed</h2>
            {completedGoals.length === 0 && <p className="goal-group-empty">Nothing completed yet.</p>}
            {completedGoals.map(renderGoalItem)}
          </div>
        </div>
      </div>
    </div>
  );
}
