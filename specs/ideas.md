# Future ideas (parking lot)

Ideas that aren't active specs yet — parked here so they're not lost. These are **not** in the
review/build queue. Promote one to a numbered spec via `/spec` when it's worth building.

## Custom statistics reports
A consolidated, reviewable **report** of stats for a chosen period (week/month/…): habit completion
(totals + %), time worked (total + average/day + per-stopwatch breakdown), and the top / most-consistent
items. Delivery would start as an on-page report view, with optional CSV/PDF export as a later add-on.
Best built **after** the stats cluster (0015/0016/0017), whose period-aware data it would consume.

Deferred because "custom reports" is open-ended and prone to scope-sprawl — revisit once the stats
cluster lands and the exact fields/format/trigger are worth pinning down. (Was spec 0018.)

## Task dependency graph + scheduling
For the task subsystem (spec 0021): let tasks declare **dependencies** on other tasks, visualize the
resulting **tree / graph**, and apply **scheduling algorithms** (e.g. earliest-deadline-first) to suggest
an order to work through them. Layers on top of the task model once sub-tasks + recurrence (0021) are in
place. Deferred — it's a larger, more algorithmic feature and needs the base task subsystem shipped first.

