import './HabitCalendar.css';

// Presentational per-day calendar / heatmap (spec 0016). Takes the backend's
// per-day array and a mode, and lays it out to match the selected period:
//   month -> weeks x 7 aligned to weekday   week -> single 7-day row
//   year  -> GitHub-style heatmap (7 weekday rows, one column per week)
//   day   -> single cell
// A single habit renders by STATUS (4 distinct colors); Total renders by
// INTENSITY (a ramp of the "done" green). No per-cell requests — plain divs.

const DONE = "rgb(0, 230, 122)";
const MISSED = "rgb(255, 90, 90)";
const NOT_SCHEDULED = "#4a4a4a";
const NO_DATA = "transparent";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function statusColor(status) {
    switch (status) {
        case "done": return DONE;
        case "missed": return MISSED;
        case "not-scheduled": return NOT_SCHEDULED;
        default: return NO_DATA;
    }
}

// intensity day -> color. scheduled 0 = nothing scheduled -> neutral no-data look.
function intensityColor(day) {
    if (!day || !day.scheduled) return NO_DATA;
    const ratio = day.completed / day.scheduled;
    // ramp from faint to full "done" green
    const alpha = 0.18 + 0.82 * ratio;
    return `rgba(0, 230, 122, ${alpha.toFixed(3)})`;
}

function cellColor(day, mode) {
    if (!day) return NO_DATA;
    return mode === "status" ? statusColor(day.status) : intensityColor(day);
}

function cellTitle(day, mode) {
    if (!day) return "";
    if (mode === "status") return `${day.date} — ${day.status}`;
    const pct = day.scheduled ? Math.round((day.completed / day.scheduled) * 100) : null;
    return day.scheduled
        ? `${day.date} — ${day.completed}/${day.scheduled} done (${pct}%)`
        : `${day.date} — nothing scheduled`;
}

// weekday index matching Python date.weekday(): Mon = 0 ... Sun = 6
function weekdayIndex(isoDate) {
    const js = new Date(isoDate + "T00:00:00").getDay(); // 0 = Sun
    return (js + 6) % 7;
}

export default function HabitCalendar({ mode, days, period }) {
    if (!days || days.length === 0) {
        return <div className="calendar-empty">No history for this period.</div>;
    }

    const cell = (day, key) => (
        <div
            key={key}
            className={`cal-cell${day ? "" : " cal-cell-empty"}`}
            style={{ backgroundColor: cellColor(day, mode) }}
            title={cellTitle(day, mode)}
        />
    );

    let grid;
    if (period === "day") {
        grid = <div className="cal-grid cal-day">{cell(days[0], "d0")}</div>;
    } else if (period === "week") {
        grid = (
            <div className="cal-grid cal-week">
                {days.slice(0, 7).map((d, i) => cell(d, i))}
            </div>
        );
    } else if (period === "month") {
        const pad = weekdayIndex(days[0].date);
        const leading = Array.from({ length: pad }, (_, i) => cell(null, `p${i}`));
        grid = (
            <div className="cal-grid cal-month">
                {WEEKDAYS.map(w => <div key={w} className="cal-weekday-label">{w}</div>)}
                {leading}
                {days.map((d, i) => cell(d, i))}
            </div>
        );
    } else {
        // year: columns = weeks, 7 rows = weekdays (Mon..Sun), column-major flow
        const pad = weekdayIndex(days[0].date);
        const leading = Array.from({ length: pad }, (_, i) => cell(null, `p${i}`));
        grid = (
            <div className="cal-grid cal-year">
                {leading}
                {days.map((d, i) => cell(d, i))}
            </div>
        );
    }

    const legend = mode === "status" ? (
        <div className="cal-legend">
            <span><i style={{ backgroundColor: DONE }} /> Done</span>
            <span><i style={{ backgroundColor: MISSED }} /> Missed</span>
            <span><i style={{ backgroundColor: NOT_SCHEDULED }} /> Not scheduled</span>
            <span><i className="cal-legend-nodata" /> No data</span>
        </div>
    ) : (
        <div className="cal-legend">
            <span>Less</span>
            <i style={{ backgroundColor: "rgba(0,230,122,0.18)" }} />
            <i style={{ backgroundColor: "rgba(0,230,122,0.45)" }} />
            <i style={{ backgroundColor: "rgba(0,230,122,0.72)" }} />
            <i style={{ backgroundColor: "rgba(0,230,122,1)" }} />
            <span>More</span>
        </div>
    );

    return (
        <div className="habit-calendar">
            {grid}
            {legend}
        </div>
    );
}
