## Table of Contents
- [High level overview of stopwatch logic](#high-level-overview-of-stopwatch-logic)
- [Architectural Change: Stopwatch Time Calculation Logic](#architectural-change-stopwatch-time-calculation-logic)
- [Architectural change: Stopwatch Response Standardization](#architectural-change-stopwatch-response-standardization)
- [Architectural change: Function Calls Standardized to be Async](#architectural-change-function-calls-standardized-to-be-async)
- [Architectural change: Datetime and Timezone Handling](#architectural-change-datetime-and-timezone-handling)

## High level overview of stopwatch logic -


In the backend, there exists a database of stopwatches, and each stopwatch stores the following parameters: id, title, start_time, interval_start, end_time, curr_duration, date, is_total, goal_time, and user_id. The title represents the title of the stopwatch, start_time represents the time the stopwatch was created (and is never changed after), interval_start represents the last time the stopwatch was started, and end_time represents the last time the stopwatch was stopped. curr_duration represents the current duration of the stopwatch. If a stopwatch is running, its end_time is null, and if it is stopped, the end_time is not null, so the value of end_time is used to determine whether a stopwatch is running or not. date is the day the stopwatch belongs to, is_total determines whether it is the total stopwatch or a regular stopwatch, and user_id denotes the user this stopwatch belongs to. 

Since on the frontend time is calculated on the fly, curr_duration is not updated while the stopwatch is running and is only updated when the stopwatch is stopped. Regular routes exist such as create stopwatch and edit stopwatch, however, three extra routes were added: start stopwatch, stop stopwatch, and reset stopwatch. The start stopwatch route sets end_time to null and updates interval_start to the current time. The stop stopwatch route updates end_time to the current time, and the reset stopwatch route resets the current duration and, if the stopwatch is running, stops it by setting end_time to the current time.

In order to make sure the page is reloaded every 10 milliseconds, setInterval() was used. setInterval calls a function repeatedly every x number of milliseconds and returns a unique ID. You can stop this repetitive function calling (or interval) by using clearInterval(id). The setInterval syntax is simply:

`setInterval(() => { function }, x);`

The way I stored this ID so I could clear it when the stopwatch was stopped was by using useRef, which is similar to useState but provides a persistent, mutable reference that doesn’t trigger re-renders when it changes — essentially, a variable that holds its value between renders. I made the interval ID a useRef by doing:

`const intervalRef = useRef(null);`

I then stored the interval ID using:

`intervalRef.current = setInterval(() => {}, x);`

Therefore, whenever I needed to stop the stopwatch, I would clear the interval by doing:

`clearInterval(intervalRef.current);`


## Architectural Change: Stopwatch Time Calculation Logic:

Currently: I am storing seconds elapsed as a state array and displaying this on the frontend. This array is updated using the interval timer.

Problem with this: It doesn’t persist after closing and reopening the app. It also causes a rerender of all stopwatches, leading to many unnecessary state updates.

A more efficient approach is to calculate the time on the fly and rerender without changing state every second.

Solution: Instead of storing and displaying secondsElapsed on the frontend, calculate the time for each stopwatch dynamically using its interval_start and curr_duration. This way, the displayed time is derived directly from data, not state. A rerender can still be triggered periodically (e.g., every few milliseconds) to visually update the display.

On the backend, I changed the logic so that it now returns only the current duration without performing any live calculations using datetime.now(). Since the frontend handles real-time calculation, the backend just keeps curr_duration updated when the stopwatch is stopped. This design works for both scenarios when fetching data from the backend:

If the stopwatch is paused: The duration returned from the backend remains static, and the frontend displays it accurately as-is.

If the stopwatch is running: The duration from the backend represents the time accumulated up until the last stop, and the frontend adds (now - interval_start) on top of that to display the current running time.

Overall, by keeping backend durations static and handling live calculations in the frontend, the app avoids redundant state updates. 




## Architectural change: Stopwatch Response Standardization

The communication protocol I followed before when connecting the frontend and backend was that, when creating a stopwatch, I would return a list like [total_stopwatch, created_stopwatch]. If the creation of a stopwatch didn’t result in the creation of a total_stopwatch, then the total_stopwatch portion would be null. I did this because we only need to create the total stopwatch once, upon the first creation of a stopwatch for a given date, so I thought the frontend could just check if the first entry was null.

However, when implementing the goal time functionality, this needed to change. I realized I had to update the total stopwatch’s goal time even if a user created a stopwatch that wasn’t the first one for that day. To handle this, I changed it so the backend always returns [total_stopwatch, created_stopwatch].

One problem that arised from this change was that some parts of the application on the frontend side (and in the GET method that handles creating stopwatches from a previous day) relied on this format for checking if this is the first stopwatch creation for the day, as they need to know if they should create the total stopwatch (GET method), or update it. This was fixed by simply changing the check to seeing if the list of existing stopwatches for the current day is empty. Additionally, I updated the update stopwatch route to go from just returning the updated stopwatch to returning a list like [total_stopwatch, updated_stopwatch], since the total stopwatch also needs to be updated when a stopwatch is modified. Now, almost all backend routes for stopwatches are standardized to return data in this format.


## Architectural change: Function Calls Standardized to be Async

The change I made is that now all functions that call the backend are asynchronous, such as add stopwatch, delete stopwatch, start stopwatch, etc. This was done to implement the functionality where, if the user clicked edit stopwatch while the stopwatch was still running, the stopwatch would first stop, the local state variables containing data about the stopwatches would be updated from the backend, and only then would the edit stopwatch screen appear. This is important because on the edit stopwatch screen we show the current time of the stopwatch, and if the stop action doesn’t happen before the screen appears, it will display the wrong (not updated) time.

The way to do this was to make the handleStop function async, and then when calling it, use await before it like:

`await handleStop(item.id, item.end_time);`

The reason I made all functions async is that even if a function is asynchronous, calling it without await still executes it like any other function. Therefore, by making all functions async, I retain their original behavior while gaining the ability to run them sequentially using await when needed.



## Architectural change: Datetime and Timezone Handling

Before, I would just store dates directly in the database and use SQLAlchemy’s [db.DateTime](https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.DateTime) to store the datetime objects. But if you refer to the docs, you’ll see that it doesn’t support timezones in SQLite. I had to make the change to store all times in UTC instead of local time because when running on Docker, it would use UTC time and not local time.

When storing datetime objects on the backend, however, because SQLAlchemy doesn’t support timezones for SQLite, it would remove the +00:00 offset at the end. This was a problem because calculations on the frontend would then interpret the times as local time instead of UTC. To fix this, I made an ensure_utc function that adds the UTC timezone offset to the datetime object, and then wrapped the time with this when serializing.

Additionally, I used this function whenever doing any datetime math on the backend since, when fetching time directly from the database, we’re not calling what is serialized, so it’s not in UTC. This fixed the issue, as now the frontend relies on the serialized data, which correctly includes the UTC offset thanks to the ensure_utc function.