## Table of Contents
- [How the "Total Time Stopwatch" Was Implemented](#how-the-total-time-stopwatch-was-implemented)
- [How Creating Stopwatches/Habits and Having Them Show Up on Future Days Was Implemented](#how-creating-stopwatcheshabits-and-having-them-show-up-on-future-days-was-implemented)
- [How the Goal Time Feature Was Implemented for Stopwatches](#how-the-goal-time-feature-was-implemented-for-stopwatches)

# How the "total time stopwatch" was implemented - 

Initially, I debated implementing the total time stopwatch logic on the frontend. I thought I could do this by creating a useEffect which, on mount, would send a POST request to create a stopwatch labeled "Total Time." However, I realized that if I did this, then for every start, stop, or reset API call, the frontend would have to send two requests, one for the total time stopwatch and one for the stopwatch being modified. I thought this would create too much traffic to the backend and make the app slow, so I decided to move the logic to the backend instead.

Now, upon database creation, a stopwatch with an ID of 1 labeled "Total Time" is automatically created. In the delete, start, stop, and reset routes, this total stopwatch is updated accordingly. Each stopwatch also has a parameter called is_total that is true only for the total time stopwatch, which makes filtering for it on the backend much easier. On the frontend, there is still some logic using nested ternary operators to ensure that when an API call returns updated stopwatch data, it updates not only the respective stopwatch but also the total stopwatch.

In hindsight, I might have been better off creating a separate table for total stopwatches, as it was tedious having to write many if and ternary statements dealing with the total stopwatch specifically when performing operations on the stopwatches.




# How Creating Stopwatches/Habits and Having Them Show Up on Future Days Was Implemented

On frontend a variable called isFuture was created that determines if its the future. If it was, the useEffect fetch just fetch todays date, and all buttons were disabled if isFuture were true. Aditionally all functions with api calls just had if (isFuture) return;

On backend to ensure that when it became the next day your stopwatches/habits carried over with everything reset, the "get all stopwatches" method was changed in that it checked that if todays stopwatches/habits were empty and it is today, then copy over yesterdays habits/stopwatches. For stowpatches some extra care had to be taken to not copy over total stopwatch from yesterday and to create a total stopwatch upon first creation. This means that if the user accesses previous days no stopwatches in the past are created which is good. I thought I would face a glitch where if I deleted all stopwatches for today, now that it was empty and since it was today, if I refreshed it would refetch yesterdays stopwatches. However, this was actually unintentionally fixed by the implementation of total stopwatch, because even if you delete all stopwatches you are not able to delete the total stopwatch so the stopwatch list for that day dosen't become empty and it dosent refetch which is the behaviour we want.

Change:

While this feature was unintentionally fixed for stopwatches, it was not for habits, since there is no equivalent to the total stopwatch in habit data. To get around this, I created another database called DeletedDay, which stores all days where the user intentionally deleted everything. Each entry in this table has a type field that is either stopwatch or habit. While I technically didn’t need this for stopwatches, I added the deleted day logic to that model as well for consistency. The logic is simple — only fetch data from the previous day if the current day is not marked as deleted.

Initially, it was fetching only from the day immediately before, but this caused an issue where, if the user didn’t open the app for a few days, it wouldn’t fetch the most recent day with data. To fix this, I changed the implementation so that instead of just checking the previous day, it keeps going back until it finds the most recent non-empty day and fetches from that.

Potential Change:

Now, I think the DeletedDay logic might not really be needed, since I could replace it by fetching data only if it’s the first time accessing that day. It’s currently working fine with the DeletedDay approach, but I may switch to the first-time-access logic later since it’s simpler and more intuitive. The only challenge would be determining when a day is being accessed for the first time.


# How the Goal Time Feature was Implemented for Stopwatches:

goal_time was added as a column for each stopwatch. In the backend, it’s stored as a float representing time in milliseconds. This choice was made because it’s easier to perform calculations with the goal time in this format. For example, calculating the total stopwatch’s goal time based on the goal times of individual stopwatches.

This calculation occurs whenever a stopwatch is added or deleted: the individual stopwatch’s goal time is either added to or subtracted from the total stopwatch’s goal time. Additionally, when a stopwatch’s goal time is edited, the total stopwatch’s goal time must also reflect this change, so the difference between the old and new goal times is calculated and applied to the total stopwatch’s goal time.

On the frontend, users set the goal time using two number inputs — one for hours and one for minutes. The frontend combines these values into a string formatted as HH:MM and sends it to the backend, where it’s converted into milliseconds for storage and calculation.