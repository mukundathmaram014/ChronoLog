import { useRef, useState } from "react";
import "./StatsOverview.css";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const ACCENT = "rgb(0, 230, 122)";
const MS_PER_HOUR = 3600000;
const TOP = 16;
const BOTTOM = 34;
const LEFT = 46;

const isoToTime = (iso) => {
    const [year, month, day] = iso.split("-").map(Number);
    return Date.UTC(year, month - 1, day);
};

const shortDate = (iso) => {
    const date = new Date(isoToTime(iso));
    return `${MONTHS[date.getUTCMonth()]} ${date.getUTCDate()}`;
};

const formatHours = (milliseconds) => {
    const minutes = Math.round(milliseconds / 60000);
    return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, "0")}m`;
};

const percentage = (week) => (week.total_habits > 0 ? (week.completed_habits / week.total_habits) * 100 : 0);

const linePath = (points) => points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join("");

// Monotone cubic interpolation: the curve stays between neighbouring points, so
// smoothing a total that only rises can't make it look like it fell.
const monotonePath = (points) => {
    const n = points.length;
    if (n < 3) return linePath(points);
    const dx = [];
    const slope = [];
    for (let i = 0; i < n - 1; i++) {
        dx[i] = points[i + 1][0] - points[i][0];
        slope[i] = (points[i + 1][1] - points[i][1]) / dx[i];
    }
    const tangent = [slope[0]];
    for (let i = 1; i < n - 1; i++) {
        tangent[i] = slope[i - 1] * slope[i] <= 0 ? 0
            : (3 * (dx[i - 1] + dx[i])) / ((2 * dx[i] + dx[i - 1]) / slope[i - 1] + (dx[i] + 2 * dx[i - 1]) / slope[i]);
    }
    tangent[n - 1] = slope[n - 2];
    let path = `M${points[0][0].toFixed(1)},${points[0][1].toFixed(1)}`;
    for (let i = 0; i < n - 1; i++) {
        const h = dx[i] / 3;
        path += `C${(points[i][0] + h).toFixed(1)},${(points[i][1] + h * tangent[i]).toFixed(1)} `
            + `${(points[i + 1][0] - h).toFixed(1)},${(points[i + 1][1] - h * tangent[i + 1]).toFixed(1)} `
            + `${points[i + 1][0].toFixed(1)},${points[i + 1][1].toFixed(1)}`;
    }
    return path;
};

const niceStep = (span) => {
    const rough = (span || 1) / 4;
    const power = Math.pow(10, Math.floor(Math.log10(rough)));
    const factor = [1, 2, 2.5, 5, 10].find(candidate => candidate * power >= rough);
    return factor * power;
};

// Canvas size and x scale shared by the three charts, so their months line up
const chartFrame = (data) => {
    const narrow = window.innerWidth < 640;
    const width = narrow ? 460 : 900;
    const height = narrow ? 240 : 280;
    const right = narrow ? 14 : 22;
    const start = isoToTime(data.axis_start);
    const end = isoToTime(data.axis_end);
    const scaleX = (iso) => LEFT + ((isoToTime(iso) - start) / (end - start)) * (width - LEFT - right);

    const months = [];
    MONTHS.forEach((label, month) => {
        if (narrow && month % 2 !== 0) return;
        const mid = Date.UTC(data.year, month, 15);
        months.push({ label, x: LEFT + ((mid - start) / (end - start)) * (width - LEFT - right) });
    });
    return { width, height, right, scaleX, months };
};

// Chart shell: the month labels, plus a crosshair and tooltip for the nearest point
const ChartFrame = ({ frame, points, ariaLabel, tooltip, children }) => {
    const svgRef = useRef(null);
    const [active, setActive] = useState(null);

    const track = (event) => {
        const rect = svgRef.current.getBoundingClientRect();
        const x = ((event.clientX - rect.left) * frame.width) / rect.width;
        let nearest = 0;
        points.forEach(([px], i) => {
            if (Math.abs(px - x) < Math.abs(points[nearest][0] - x)) nearest = i;
        });
        setActive({ index: nearest, scale: rect.width / frame.width, chartWidth: rect.width });
    };

    let tooltipStyle = null;
    if (active && points[active.index]) {
        const left = points[active.index][0] * active.scale;
        const top = points[active.index][1] * active.scale;
        tooltipStyle = {
            ...(left + 260 > active.chartWidth ? { right: active.chartWidth - left + 12 } : { left: left + 12 }),
            ...(top < 100 ? { top: top + 12 } : { top: top - 12, transform: "translateY(-100%)" }),
        };
    }

    return (
        <div className="ov-chart">
            <svg
                ref={svgRef}
                viewBox={`0 0 ${frame.width} ${frame.height}`}
                role="img"
                aria-label={ariaLabel}
                onPointerMove={track}
                onPointerDown={track}
                onPointerLeave={() => setActive(null)}
            >
                {frame.months.map(month => (
                    <text key={month.label} x={month.x} y={frame.height - 10} textAnchor="middle">{month.label}</text>
                ))}
                {children}
                {tooltipStyle && (
                    <>
                        <line
                            x1={points[active.index][0]} x2={points[active.index][0]}
                            y1={TOP} y2={frame.height - BOTTOM}
                            stroke="#777"
                        />
                        <circle
                            cx={points[active.index][0]} cy={points[active.index][1]}
                            r="8" fill="none" stroke="#fff" strokeWidth="2"
                        />
                    </>
                )}
            </svg>
            {tooltipStyle && <div className="ov-tooltip" style={tooltipStyle}>{tooltip(active.index)}</div>}
        </div>
    );
};

const WeeklyChart = ({ data, value, maxValue, step, tick, ariaLabel, tooltip }) => {
    const frame = chartFrame(data);
    const scaleY = (v) => TOP + (1 - v / maxValue) * (frame.height - TOP - BOTTOM);
    const points = data.weeks.map(week => [frame.scaleX(week.week_start), scaleY(value(week))]);
    const inProgress = data.weeks[data.weeks.length - 1].in_progress;
    const settled = inProgress ? points.slice(0, -1) : points;

    const ticks = [];
    for (let v = 0; v <= maxValue + 1e-9; v += step) ticks.push(v);

    return (
        <ChartFrame frame={frame} points={points} ariaLabel={ariaLabel} tooltip={tooltip}>
            {ticks.map(v => (
                <g key={v}>
                    <line x1={LEFT} x2={frame.width - frame.right} y1={scaleY(v)} y2={scaleY(v)} stroke="#333" />
                    <text x={LEFT - 8} y={scaleY(v) + 4} textAnchor="end">{tick(v)}</text>
                </g>
            ))}
            <path d={linePath(settled)} fill="none" stroke={ACCENT} strokeWidth="2" />
            {inProgress && points.length > 1 && (
                <path d={linePath(points.slice(-2))} fill="none" stroke={ACCENT} strokeWidth="2" strokeDasharray="4 4" />
            )}
            {data.weeks.map((week, i) => (week.note
                ? <circle key={week.week_start} cx={points[i][0]} cy={points[i][1]} r="6.5" fill="#fff" stroke={ACCENT} strokeWidth="3" />
                : <circle key={week.week_start} cx={points[i][0]} cy={points[i][1]} r="3.5" fill={ACCENT} stroke="#232323" strokeWidth="1.5" />
            ))}
        </ChartFrame>
    );
};

const XpCurve = ({ data, mode }) => {
    const frame = chartFrame(data);
    const showLevel = mode === "level";
    const days = data.xp_days;
    const value = (day) => (showLevel ? day.level + day.xp_into_level / day.xp_to_next : day.total_xp);
    const values = days.map(value);
    const low = Math.min(...values);
    const high = Math.max(...values);
    const span = high - low || 1;
    const step = showLevel ? Math.max(1, Math.ceil(niceStep(span))) : niceStep(span);
    const minValue = Math.floor(low / step) * step;
    const maxValue = Math.max(Math.ceil(high / step) * step, minValue + step);
    const scaleY = (v) => TOP + (1 - (v - minValue) / (maxValue - minValue)) * (frame.height - TOP - BOTTOM);
    const points = days.map((day, i) => [frame.scaleX(day.date), scaleY(values[i])]);

    const ticks = [];
    for (let v = minValue; v <= maxValue + 1e-9; v += step) ticks.push(v);

    const curve = monotonePath(points);
    const last = points[points.length - 1];
    const lastDay = days[days.length - 1];
    const endLabel = showLevel ? `Level ${lastDay.level}` : `${lastDay.total_xp.toLocaleString()} XP`;
    const labelOnLeft = last[0] > frame.width - 130;

    return (
        <ChartFrame
            frame={frame}
            points={points}
            ariaLabel={`${showLevel ? "Level" : "Total XP"} over the year, ending at ${endLabel}.`}
            tooltip={(i) => (
                <>
                    <strong>{shortDate(days[i].date)}</strong>
                    <div>Level {days[i].level} <span className="ov-muted">({days[i].xp_into_level.toLocaleString()} / {days[i].xp_to_next.toLocaleString()})</span></div>
                    <div>{days[i].total_xp.toLocaleString()} XP total</div>
                    <div className="ov-muted">+{days[i].xp_earned.toLocaleString()} that day</div>
                </>
            )}
        >
            <defs>
                <linearGradient id="ov-xp-fill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0" stopColor={ACCENT} stopOpacity="0.22" />
                    <stop offset="1" stopColor={ACCENT} stopOpacity="0" />
                </linearGradient>
            </defs>
            {ticks.map(v => (
                <g key={v}>
                    <line x1={LEFT} x2={frame.width - frame.right} y1={scaleY(v)} y2={scaleY(v)} stroke="#333" />
                    <text x={LEFT - 8} y={scaleY(v) + 4} textAnchor="end">{Math.round(v).toLocaleString()}</text>
                </g>
            ))}
            <path d={`${curve}L${last[0]},${frame.height - BOTTOM}L${points[0][0]},${frame.height - BOTTOM}Z`} fill="url(#ov-xp-fill)" />
            <path d={curve} fill="none" stroke={ACCENT} strokeWidth="2.5" />
            <circle cx={last[0]} cy={last[1]} r="5" fill={ACCENT} stroke="#232323" strokeWidth="2" />
            <text
                className="ov-end-label"
                x={labelOnLeft ? last[0] - 10 : last[0] + 10}
                y={Math.max(TOP + 12, last[1] - 12)}
                textAnchor={labelOnLeft ? "end" : "start"}
            >
                {endLabel}
            </text>
        </ChartFrame>
    );
};

const NoteCell = ({ week, fetchWithAuth, onSaved, onError }) => {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState("");
    // Enter removes the input, which fires blur: only the first of the two may save
    const closedRef = useRef(false);

    const open = () => {
        closedRef.current = false;
        setDraft(week.note ?? "");
        setEditing(true);
    };

    const close = (save) => {
        if (closedRef.current) return;
        closedRef.current = true;
        setEditing(false);
        if (!save || draft.trim() === (week.note ?? "")) return;
        fetchWithAuth(`/stats/overview/notes/${week.week_start}/`, {
            method: "PUT",
            body: JSON.stringify({ note: draft }),
        })
            .then(response => {
                if (!response.ok) throw new Error(`status ${response.status}`);
                return response.json();
            })
            .then(data => onSaved(week.week_start, data.note))
            .catch(error => {
                console.error(error);
                onError(`Couldn't save the note for ${shortDate(week.week_start)}. Please try again.`);
            });
    };

    if (editing) {
        return (
            <input
                className="ov-note-input"
                autoFocus
                maxLength={500}
                value={draft}
                aria-label={`Note for the week of ${shortDate(week.week_start)}`}
                onChange={event => setDraft(event.target.value)}
                onBlur={() => close(true)}
                onKeyDown={event => {
                    if (event.key === "Enter") close(true);
                    if (event.key === "Escape") close(false);
                }}
            />
        );
    }
    return (
        <button className={`ov-note-button${week.note ? "" : " ov-note-empty"}`} onClick={open}>
            {week.note || "+ add note"}
        </button>
    );
};

const NotesImport = ({ fetchWithAuth, onImported }) => {
    const [open, setOpen] = useState(false);
    const [text, setText] = useState("");
    const [message, setMessage] = useState("");

    const runImport = () => {
        const notes = [];
        const unreadable = [];
        text.split(/\r?\n/).forEach(line => {
            if (!line.trim()) return;
            const match = line.trim().match(/^(\d{4}-\d{2}-\d{2})\s+(.+)$/);
            if (match) notes.push({ week_start: match[1], note: match[2] });
            else unreadable.push(line.trim());
        });
        fetchWithAuth("/stats/overview/notes/import/", {
            method: "POST",
            body: JSON.stringify({ notes }),
        })
            .then(response => {
                if (!response.ok) throw new Error(`status ${response.status}`);
                return response.json();
            })
            .then(data => {
                const problems = [...unreadable, ...data.errors];
                setMessage(`Imported ${data.imported}. Skipped ${data.skipped} that already had a note.`
                    + (problems.length ? ` Couldn't read: ${problems.join("; ")}` : ""));
                setText("");
                onImported();
            })
            .catch(error => {
                console.error(error);
                setMessage("The import failed, so nothing was saved. Please try again.");
            });
    };

    if (!open) {
        return <button className="ov-link-button" onClick={() => setOpen(true)}>Import notes</button>;
    }
    return (
        <div className="ov-import">
            <label htmlFor="ov-import-text">Paste one note per line: the week's Monday as YYYY-MM-DD, then the note.</label>
            <textarea
                id="ov-import-text"
                rows={6}
                value={text}
                onChange={event => setText(event.target.value)}
            />
            <div className="ov-import-actions">
                <button className="ov-import-submit" disabled={!text.trim()} onClick={runImport}>Import</button>
                <button className="ov-link-button" onClick={() => setOpen(false)}>Close</button>
            </div>
            {message && <p className="ov-message" role="status">{message}</p>}
        </div>
    );
};

export default function StatsOverview({ data, failed, fetchWithAuth, onOpenWeek, onNoteSaved, onImported }) {
    const [xpMode, setXpMode] = useState("level");
    const [error, setError] = useState("");

    if (!data) {
        return (
            <div className="overviewstatistics">
                {failed && <p className="ov-message" role="alert">Couldn't load the overview. Please refresh the page to try again.</p>}
            </div>
        );
    }

    const importer = <NotesImport fetchWithAuth={fetchWithAuth} onImported={onImported} />;

    if (data.weeks.length === 0) {
        return (
            <div className="overviewstatistics">
                <p className="ov-title">Nothing tracked in this year yet.</p>
                {importer}
            </div>
        );
    }

    const maxAverage = Math.max(...data.weeks.map(week => week.average_time_worked_per_day)) / MS_PER_HOUR;
    const maxHours = Math.max(2, Math.ceil(maxAverage / 2) * 2);
    const anyInProgress = data.weeks[data.weeks.length - 1].in_progress;

    const weekTooltip = (i) => {
        const week = data.weeks[i];
        return (
            <>
                <strong>Week of {shortDate(week.week_start)}{week.in_progress ? " (so far)" : ""}</strong>
                <div>{percentage(week).toFixed(1)}% <span className="ov-muted">({week.completed_habits} of {week.total_habits})</span></div>
                <div>{formatHours(week.average_time_worked_per_day)} <span className="ov-muted">per day</span></div>
                <div>{week.xp.toLocaleString()} <span className="ov-muted">XP</span></div>
                {week.note && <div className="ov-tooltip-note">{week.note}</div>}
            </>
        );
    };

    return (
        <div className="overviewstatistics">
            <div className="ov-head">
                <p className="ov-title">Habit completion by week</p>
                <div className="ov-legend">
                    <span>
                        <svg width="16" height="16" aria-hidden="true"><circle cx="8" cy="8" r="5.5" fill="#fff" stroke={ACCENT} strokeWidth="3" /></svg>
                        Week has a note
                    </span>
                    {anyInProgress && (
                        <span>
                            <svg width="22" height="6" aria-hidden="true"><line x1="0" x2="22" y1="3" y2="3" stroke={ACCENT} strokeWidth="2" strokeDasharray="4 4" /></svg>
                            Week in progress
                        </span>
                    )}
                </div>
            </div>
            <WeeklyChart
                data={data}
                value={percentage}
                maxValue={100}
                step={20}
                tick={v => `${v}%`}
                ariaLabel={`Habit completion percentage for each week of ${data.year}. The table below has the same numbers.`}
                tooltip={weekTooltip}
            />

            <p className="ov-title">Time worked: average hours per day, by week</p>
            <WeeklyChart
                data={data}
                value={week => week.average_time_worked_per_day / MS_PER_HOUR}
                maxValue={maxHours}
                step={2}
                tick={v => `${v}h`}
                ariaLabel={`Average hours worked per day for each week of ${data.year}. The table below has the same numbers.`}
                tooltip={weekTooltip}
            />

            {data.xp_days.length > 0 && (
                <>
                    <div className="ov-head">
                        <p className="ov-title">{xpMode === "level" ? "Level" : "Total XP"} over the year</p>
                        <div className="ov-toggle" role="group" aria-label="Curve shows">
                            <button aria-pressed={xpMode === "level"} onClick={() => setXpMode("level")}>Level</button>
                            <button aria-pressed={xpMode === "xp"} onClick={() => setXpMode("xp")}>XP</button>
                        </div>
                    </div>
                    <XpCurve data={data} mode={xpMode} />
                </>
            )}

            <div className="ov-head">
                <p className="ov-title">Week by week</p>
                <div className="ov-legend">
                    <span>Click a date to open that week in Habits. Click a note to edit it.</span>
                    {importer}
                </div>
            </div>
            {error && <p className="ov-message" role="alert">{error}</p>}
            <div className="ov-table-wrap">
                <table className="ov-table">
                    <thead>
                        <tr>
                            <th>Week of</th>
                            <th className="ov-num">Done</th>
                            <th className="ov-num">Completion</th>
                            <th className="ov-num">Avg / day</th>
                            <th className="ov-num">XP</th>
                            <th>Note</th>
                        </tr>
                    </thead>
                    <tbody>
                        {[...data.weeks].reverse().map(week => (
                            <tr key={week.week_start}>
                                <td className="ov-week">
                                    <button className="ov-week-link" onClick={() => onOpenWeek(week.week_start)}>{shortDate(week.week_start)}</button>
                                    {week.in_progress && <span className="ov-so-far">so far</span>}
                                </td>
                                <td className="ov-num" data-label="Done">{week.completed_habits} / {week.total_habits}</td>
                                <td className="ov-num ov-pct" data-label="Completion">{percentage(week).toFixed(1)}%</td>
                                <td className="ov-num" data-label="Avg / day">{formatHours(week.average_time_worked_per_day)}</td>
                                <td className="ov-num" data-label="XP">{week.xp.toLocaleString()}</td>
                                <td className="ov-note">
                                    <NoteCell
                                        week={week}
                                        fetchWithAuth={fetchWithAuth}
                                        onSaved={(weekStart, note) => { setError(""); onNoteSaved(weekStart, note); }}
                                        onError={setError}
                                    />
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
