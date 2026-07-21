import { FaPlus, FaCheck, FaChevronDown, FaChevronRight } from "react-icons/fa";
import { IoMdClose } from "react-icons/io";
import { MdEdit, MdDelete } from "react-icons/md";
import { useState, useEffect } from 'react';
import './taskpage.css';
import useFetch from "../hooks/useFetch";
import { CompletedTaskLog } from "../Components/CompletedTaskLog.jsx";

const RECURRENCE_OPTIONS = ["none", "daily", "weekly", "monthly"];
const HISTORY_PAGE_SIZE = 50;

export function Tasks() {

  const fetchWithAuth = useFetch();

  const DatetoISOString = (Date) => {
        const year = Date.getFullYear();
        const month = String(Date.getMonth() + 1).padStart(2, '0');
        const day = String(Date.getDate()).padStart(2,'0');
        const isoString = year + "-" + month + "-" + day;
        return isoString;
    }

  const [taskGroups, setTaskGroups] = useState({ overdue: [], today: [], upcoming: [] });
  const [addTask, setAddTask] = useState(false);
  const [editTask, setEditTask] = useState(false);
  const [editingTaskID, setEditingTaskID] = useState(null);
  const [editingIsSubtask, setEditingIsSubtask] = useState(false);
  const [newDescription, setNewDescription] = useState("");
  const [newRecurrence, setNewRecurrence] = useState("none");
  const [isSaving, setIsSaving] = useState(false);
  const [taskError, setTaskError] = useState("");
  const [expandedTasks, setExpandedTasks] = useState({});
  const [subtaskInputs, setSubtaskInputs] = useState({});
  const [today, setToday] = useState(() => (DatetoISOString(new Date())));
  const [newDate, setNewDate] = useState(() => (DatetoISOString(new Date())));
  // completed-task history: collapsed on every visit, fetched on first expand.
  // null = never loaded, which is what gates that first fetch.
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyHasMore, setHistoryHasMore] = useState(false);
  const [historyOffset, setHistoryOffset] = useState(0);

  // updates state variable today
  useEffect(() => {
    const now = new Date();
    const msUntilMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 0, 0, 0, 0) - now //midnight next day

    const timeout = setTimeout(() => {
      setToday(DatetoISOString(new Date()));
    }, msUntilMidnight);

    return () => clearTimeout(timeout);
  },[today]);

  const fetchTasks = () => {
    fetchWithAuth(`/tasks/${today}/`, {
      method: "GET"
    })
    .then(response => response.json())
    .then(data => setTaskGroups({ overdue: data.overdue ?? [], today: data.today ?? [], upcoming: data.upcoming ?? [] }))
    .catch(error => console.error(error))
  }

  useEffect(() => {
    fetchTasks();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [today]);

  // offset 0 replaces the loaded history, any other offset appends the next page
  const loadHistory = (offset) => {
    setHistoryLoading(true);
    fetchWithAuth(`/tasks/completed/?limit=${HISTORY_PAGE_SIZE}&offset=${offset}`, {
      method: "GET"
    })
    .then(response => response.json())
    .then(data => {
      const page = data.completed ?? [];
      setHistory(prev => (offset === 0 ? page : [...(prev ?? []), ...page]));
      setHistoryHasMore(!!data.has_more);
      setHistoryOffset(offset + page.length);
    })
    .catch(error => console.error(error))
    .finally(() => setHistoryLoading(false))
  };

  // a task completed today sits in the Today group and the history at once, so
  // anything that changes one has to refresh the other. Resetting to the first
  // page (rather than re-fetching every loaded page) also keeps offset paging
  // honest after a delete shifts every later row up.
  const refreshHistory = () => {
    if (historyOpen) {
      loadHistory(0);
    }
  };

  const handleAddTask = () => {
    if (!newDescription.trim()) {
      setTaskError("Enter a description.");
      return;
    }
    setTaskError("");
    const newTask = {
      description: newDescription,
      done: false,
      date: newDate,
      recurrence: newRecurrence
    }
    setIsSaving(true);
    fetchWithAuth("/tasks/", {
      method: "POST",
      body: JSON.stringify(newTask)
    })
    .then(response => response.json())
    .then(() => {
      setNewDescription("");
      setNewRecurrence("none");
      setNewDate(today);
      setAddTask(false);
      fetchTasks();
    })
    .catch(error => console.error(error))
    .finally(() => setIsSaving(false))
  };

  const handleAddSubtask = (parentId) => {
    const description = (subtaskInputs[parentId] ?? "").trim();
    if (!description) return;
    fetchWithAuth("/tasks/", {
      method: "POST",
      body: JSON.stringify({ description: description, done: false, parent_id: parentId })
    })
    .then(response => response.json())
    .then(() => {
      setSubtaskInputs(prev => ({ ...prev, [parentId]: "" }));
      fetchTasks();
    })
    .catch(error => console.error(error))
  };

  // refetches after every change: completing a periodic task can spawn its
  // next occurrence and completing a sub-task can auto-complete the parent
  const handleToggleTask = (taskId, currStatus) => {
    fetchWithAuth(`/tasks/${taskId}/`, {
      method: "PUT",
      // the server may be in another timezone, so the completion day is ours to send
      body: JSON.stringify({ done: !currStatus, completed_date: today })
    })
    .then(response => response.json())
    .then(() => {
      fetchTasks();
      refreshHistory();
    })
    .catch(error => console.error(error))
  };

  // also used for history rows, which have no other affordance
  const handleDeleteTask = (taskId) => {
    fetchWithAuth(`/tasks/${taskId}/`, {
      method: "DELETE"
    })
    .then(response => response.json())
    .then(() => {
      fetchTasks();
      refreshHistory();
    })
    .catch(error => console.error(error))
  };

  const openEditTask = (item) => {
    setEditTask(true);
    setEditingTaskID(item.id);
    setEditingIsSubtask(item.parent_id !== null);
    setNewDescription(item.description);
    setNewDate(item.date);
    setNewRecurrence(item.recurrence);
  };

  const handleEditTask = () => {
    if (isSaving) return;
    if (editingTaskID === null) return;
    if (!newDescription.trim()) {
      setTaskError("Enter a description.");
      return;
    }
    setTaskError("");

    const updatedTask = editingIsSubtask
      ? { description: newDescription }
      : { description: newDescription, date: newDate, recurrence: newRecurrence };

    setIsSaving(true);
    fetchWithAuth(`/tasks/${editingTaskID}/`, {
      method: "PUT",
      body: JSON.stringify(updatedTask)
    })
    .then(response => response.json())
    .then(() => {
      setNewDescription("");
      setNewRecurrence("none");
      setNewDate(today);
      setEditTask(false);
      setEditingTaskID(null);
      fetchTasks();
    })
    .catch(error => console.error(error))
    .finally(() => setIsSaving(false))
  };

  const closeEditTask = () => {
    setEditTask(false);
    setEditingTaskID(null);
    setNewDescription("");
    setNewRecurrence("none");
    setNewDate(today);
    setTaskError("");
  };

  const toggleExpanded = (taskId) => {
    setExpandedTasks(prev => ({ ...prev, [taskId]: !prev[taskId] }));
  };

  const formatDateHeading = (dateString) => {
    return new Date(dateString + "T00:00:00").toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const renderTaskItem = (item) => {
    const subtasks = item.subtasks ?? [];
    const doneCount = subtasks.filter(subtask => subtask.done).length;
    const isExpanded = !!expandedTasks[item.id];
    return (
      <div key={item.id} className="task-block">
        <div className={`task-list-item ${item.done ? 'completed' : ''}`}
              onClick={() => openEditTask(item)}>
          <div className="left-section">
            <div
              className={`custom-checkbox ${item.done ? 'checked' : ''}`}
              onClick={(e) => {e.stopPropagation(); handleToggleTask(item.id, item.done)}}
            >
              {item.done && <FaCheck className="check-icon" />}
            </div>
            <div className="task-text">
              <p>{item.description}</p>
              {(subtasks.length > 0 || item.recurrence !== "none") && (
                <span className="task-meta">
                  {subtasks.length > 0 && `${doneCount}/${subtasks.length} done`}
                  {subtasks.length > 0 && item.recurrence !== "none" && " · "}
                  {item.recurrence !== "none" && `repeats ${item.recurrence}`}
                </span>
              )}
            </div>
          </div>
          <div className="icon-bar">
            <MdEdit className="edit-icon"
              onClick={() => openEditTask(item)}/>
            <MdDelete className="delete-icon"
              onClick={(e) => {e.stopPropagation(); handleDeleteTask(item.id)}}/>
            <div className="expand-toggle"
              onClick={(e) => {e.stopPropagation(); toggleExpanded(item.id)}}>
              {isExpanded ? <FaChevronDown /> : <FaChevronRight />}
            </div>
          </div>
        </div>
        {isExpanded && (
          <div className="subtask-list">
            {subtasks.map(subtask => (
              <div key={subtask.id} className={`task-list-item subtask ${subtask.done ? 'completed' : ''}`}
                    onClick={() => openEditTask(subtask)}>
                <div className="left-section">
                  <div
                    className={`custom-checkbox ${subtask.done ? 'checked' : ''}`}
                    onClick={(e) => {e.stopPropagation(); handleToggleTask(subtask.id, subtask.done)}}
                  >
                    {subtask.done && <FaCheck className="check-icon" />}
                  </div>
                  <div className="task-text">
                    <p>{subtask.description}</p>
                  </div>
                </div>
                <div className="icon-bar">
                  <MdEdit className="edit-icon"
                    onClick={() => openEditTask(subtask)}/>
                  <MdDelete className="delete-icon"
                    onClick={(e) => {e.stopPropagation(); handleDeleteTask(subtask.id)}}/>
                </div>
              </div>
            ))}
            <div className="subtask-add">
              <input type="text" value={subtaskInputs[item.id] ?? ""}
                onChange={(e) => setSubtaskInputs(prev => ({ ...prev, [item.id]: e.target.value }))}
                onKeyDown={(e) => {
                  if (e.key === "Enter"){
                    handleAddSubtask(item.id);
                  }
                }}
                placeholder="Add a sub-task"/>
              <button type='button' className='addSubtaskButton'
                onClick={() => handleAddSubtask(item.id)}>Add</button>
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderGroup = (title, tasks, showDateHeadings, emptyMessage) => {
    const byDate = {};
    tasks.forEach(task => { (byDate[task.date] = byDate[task.date] ?? []).push(task); });
    return (
      <div className="task-group">
        <h2 className={`task-group-title ${title === "Overdue" ? "overdue-title" : ""}`}>{title}</h2>
        {tasks.length === 0 && <p className="task-group-empty">{emptyMessage}</p>}
        {Object.keys(byDate).sort().map(dateKey => (
          <div key={dateKey}>
            {showDateHeadings && <h4 className="task-date-heading">{formatDateHeading(dateKey)}</h4>}
            {byDate[dateKey].map(renderTaskItem)}
          </div>
        ))}
      </div>
    );
  };

  const renderRecurrencePicker = () => (
    <>
      <label>Repeats</label>
      <select className="recurrence-select" value={newRecurrence}
        onChange={(e) => setNewRecurrence(e.target.value)}>
        {RECURRENCE_OPTIONS.map(option => (
          <option key={option} value={option}>{option === "none" ? "never" : option}</option>
        ))}
      </select>
    </>
  );

  return (
    <div className="App">
      <h1>My Tasks</h1>
      <div className="task-wrapper">
        <button type='button' className='primaryBtn'
            onClick={() => {setAddTask(true); setNewDate(today); setNewRecurrence("none");}}>
            <FaPlus className="plus-icon" />
        </button>
        {addTask && (
          <div className="task-input">
            <div className="task-input-item">
              <IoMdClose className="close-icon"
                onClick={() => {setAddTask(false); setTaskError("");}}/>
              <h3>Add a New Task</h3>
              <label>Description</label>
              <input type="text" value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter"){
                  handleAddTask();
                }
              }}
              placeholder="What's the task"/>
              <label>Due date</label>
              <input type="date" value={newDate} min={today}
                onChange={(e) => setNewDate(e.target.value)}/>
              {renderRecurrencePicker()}
              <button type='button' className='addTaskButton'
                onClick={handleAddTask}
                disabled={isSaving}
                > {isSaving ? "Adding..." : "Add Task"}</button>
              {taskError && (
                <div style={{ color: "red", marginBottom: "10px" }}>{taskError}</div>
              )}
            </div>
          </div>
        )}
        {editTask && (
          <div className="task-input">
            <div className="task-edit-item">
              <IoMdClose className="close-icon"
                onClick={closeEditTask}/>
              <h3>{editingIsSubtask ? "Edit sub-task" : "Edit task"}</h3>
              <label>Description</label>
              <input type="text" value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter"){
                  handleEditTask();
                }
              }}
              placeholder="What's the task"/>
              {!editingIsSubtask && (
                <>
                  <label>Due date</label>
                  <input type="date" value={newDate} min={today}
                    onChange={(e) => setNewDate(e.target.value)}/>
                  {renderRecurrencePicker()}
                </>
              )}
              <button type='button' className='editTaskButton'
                onClick={handleEditTask}
                disabled={isSaving}
                > {isSaving ? "Saving..." : "Done"}</button>
              {taskError && (
                <div style={{ color: "red", marginBottom: "10px" }}>{taskError}</div>
              )}
            </div>
          </div>
        )}
        <div className="task-list">
          {renderGroup("Overdue", taskGroups.overdue, true, "Nothing overdue.")}
          {renderGroup("Today", taskGroups.today, false, "Nothing due today.")}
          {renderGroup("Upcoming", taskGroups.upcoming, true, "Nothing coming up.")}
        </div>
        {/* opt-in look back at what's already been finished (spec 0031) */}
        <div className="completed-log-section">
          <button
            type="button"
            className="completed-log-toggle"
            aria-expanded={historyOpen}
            onClick={() => {
              const opening = !historyOpen;
              setHistoryOpen(opening);
              if (opening && history === null) {
                loadHistory(0);
              }
            }}
          >
            Completed {historyOpen ? "▾" : "▸"}
          </button>
          {historyOpen && (
            <>
              <CompletedTaskLog
                tasks={history ?? []}
                loading={historyLoading && history === null}
                onDelete={handleDeleteTask}
                formatDateHeading={formatDateHeading}
              />
              {historyHasMore && (
                <button type="button" className="completed-log-more"
                  onClick={() => loadHistory(historyOffset)}
                  disabled={historyLoading}>
                  {historyLoading ? "Loading…" : "Show more"}
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
