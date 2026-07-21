import { MdDelete } from "react-icons/md";

// History of completed tasks, grouped by the day they were finished (spec 0031).
// Read-only apart from delete: the page owns fetching, paging and the
// expanded/collapsed state, and passes the delete callback down.
export function CompletedTaskLog({ tasks, loading, onDelete, formatDateHeading }) {

    if (loading) {
        return <p className="task-group-empty">Loading…</p>;
    }

    if (tasks.length === 0) {
        return <p className="task-group-empty">No completed tasks yet.</p>;
    }

    // rows completed before completed_date existed fall back to their due date,
    // matching the ordering the backend applied
    const dayOf = (task) => task.completed_date ?? task.date;

    // built by walking the list rather than keying an object, so the server's
    // most-recent-first order survives grouping
    const days = [];
    tasks.forEach(task => {
        const day = dayOf(task);
        const current = days[days.length - 1];
        if (current && current.day === day) {
            current.tasks.push(task);
        } else {
            days.push({ day: day, tasks: [task] });
        }
    });

    return (
        <div className="completed-log">
            {days.map(({ day, tasks: dayTasks }) => (
                <div key={day}>
                    <h4 className="task-date-heading">{formatDateHeading(day)}</h4>
                    {dayTasks.map(task => (
                        <div key={task.id} className="task-block">
                            <div className="task-list-item completed history-item">
                                <div className="left-section">
                                    <div className="task-text">
                                        <p>{task.description}</p>
                                        {task.recurrence !== "none" && (
                                            <span className="task-meta">{`repeats ${task.recurrence}`}</span>
                                        )}
                                    </div>
                                </div>
                                <div className="icon-bar">
                                    <MdDelete className="delete-icon"
                                        onClick={() => onDelete(task.id)}/>
                                </div>
                            </div>
                            {/* sub-tasks carry no date of their own: the parent is the unit
                                of history, even if a sub-task was finished on an earlier day */}
                            {(task.subtasks ?? []).length > 0 && (
                                <div className="subtask-list">
                                    {task.subtasks.map(subtask => (
                                        <div key={subtask.id}
                                            className={`task-list-item subtask history-item ${subtask.done ? 'completed' : ''}`}>
                                            <div className="left-section">
                                                <div className="task-text">
                                                    <p>{subtask.description}</p>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            ))}
        </div>
    );
}
