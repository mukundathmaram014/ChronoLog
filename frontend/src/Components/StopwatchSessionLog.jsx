// Chronological list of a day's recorded stopwatch segments (spec 0030). Purely
// presentational: the page owns fetching and the expanded/collapsed state.
export function StopwatchSessionLog({ intervals, loading, runningSegment }) {

    const formatClock = (isoString) =>
        new Date(isoString).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

    // "48m" / "1h 12m" — the segment's own length, not the stopwatch's running total
    const formatLength = (startIso, endIso) => {
        const minutes = Math.max(0, Math.round((new Date(endIso) - new Date(startIso)) / 60000));
        const hours = Math.floor(minutes / 60);
        return hours > 0 ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
    };

    if (loading) {
        return <div className="session-log-empty">Loading…</div>;
    }

    if (intervals.length === 0 && !runningSegment) {
        return <div className="session-log-empty">No sessions recorded.</div>;
    }

    return (
        <ul className="session-log-list">
            {intervals.map(interval => (
                <li className="session-log-row" key={interval.id}>
                    <span className="session-log-time">
                        {formatClock(interval.start_time)}–{formatClock(interval.end_time)}
                    </span>
                    <span className="session-log-title">{interval.title}</span>
                    <span className="session-log-length">
                        {formatLength(interval.start_time, interval.end_time)}
                    </span>
                </li>
            ))}
            {/* the in-flight segment isn't a row in the table yet */}
            {runningSegment && (
                <li className="session-log-row session-log-running">
                    <span className="session-log-time">
                        started {formatClock(runningSegment.interval_start)}
                    </span>
                    <span className="session-log-title">{runningSegment.title}</span>
                    <span className="session-log-length">running</span>
                </li>
            )}
        </ul>
    );
}
