import json
import math
import os
from datetime import date, timezone


# generalized response formats
def success_response(data, code=200):
    return json.dumps(data), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code


def validate_repeat_days(repeat_days):
    """
    Returns True iff repeat_days is a valid 7-bit weekday bitmask with at least one day set.
    Shared by habits and stopwatches — bit i = date.weekday() i (0 = Mon ... 6 = Sun).
    """
    return isinstance(repeat_days, int) and not isinstance(repeat_days, bool) and 1 <= repeat_days <= 127


def validate_weekday_goal_times(value):
    """
    Returns True iff value is a valid per-weekday stopwatch goal schedule (spec
    0036): None (one uniform goal), or a dense list of exactly 7 entries, each
    None ("no goal that weekday") or an "HH:MM" string with hours 0-23 and
    minutes 0-59. Index i = date.weekday() i (0 = Mon ... 6 = Sun), the same
    convention as validate_repeat_days.
    """
    if value is None:
        return True
    if not isinstance(value, list) or len(value) != 7:
        return False
    for entry in value:
        if entry is None:
            continue
        # bools/ints/etc. fail here, same spirit as validate_repeat_days' guard
        if not isinstance(entry, str) or len(entry) != 5 or entry[2] != ":":
            return False
        hours, minutes = entry[0:2], entry[3:5]
        if not (hours.isdigit() and minutes.isdigit()):
            return False
        if int(hours) > 23 or int(minutes) > 59:
            return False
    return True


def effective_goal_time(schedule, base_goal_time, target_date):
    """
    The goal time (ms) a stopwatch row lands with on `target_date`: its weekday's
    slot when the stopwatch carries a per-weekday schedule, else the uniform
    base goal. The single derivation point — nothing else indexes the schedule.
    Derivation is by weekday alone: a row sitting on a weekday its own
    repeat_days excludes still reads that weekday's slot.
    """
    if schedule is None:
        return base_goal_time
    return schedule[target_date.weekday()]


def process_date(request):
    body = json.loads(request.data)
    date_string = body.get("date", date.today().isoformat())
    requested_date = date.fromisoformat(date_string)
    return requested_date

# Helper to ensure UTC-aware datetimes
def ensure_utc(dt):
    """
    Ensure a datetime object is timezone-aware (UTC). If naive, attach UTC tzinfo.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# ---- XP / level system (spec 0020) ----
# All balancing constants are fixed in code — users only pick a per-item
# difficulty tier, never how fast they level. Tune these together via the
# calibration simulation in backend/tests/test_xp.py.

HABIT_XP = {"easy": 10, "medium": 25, "hard": 50}
# Goals are worth days-to-months of effort (a normal productive day is ~200 XP),
# so they dwarf a single habit. "extreme" is the rare, life-changing tier.
GOAL_XP = {"easy": 500, "medium": 2000, "hard": 5000, "extreme": 20000}
XP_PER_HOUR = 20
# hours worked beyond the day's total goal time earn this higher rate (spec 0012)
XP_PER_HOUR_OVERTIME = 30
# flat bonus for completing every one of the day's habits
ALL_HABITS_BONUS = 25
# flat bonus for working at least the day's total goal time (a hard habit's worth)
GOAL_TIME_BONUS = 50
# flat bonus per individual (non-Total) stopwatch whose own goal is hit that day,
# summed but capped per day so short-goal farming can't outgrow the total-goal bonus
INDIVIDUAL_GOAL_BONUS = 10
INDIVIDUAL_GOAL_BONUS_CAP = 40
STREAK_STEP = 0.1
STREAK_CAP = 2.0
# a day counts toward the streak when its "grind" XP (habits done + worked time,
# capped at the goal) reaches this fraction of the *most* it could be that day
# (every habit done + the goal time worked). Self-scaling per day; ~all your
# habits and goal time, allowing a small miss.
STREAK_THRESHOLD_PCT = 0.85
LEVEL_B = 25
LEVEL_P = 1.5

# Habits use the 3-tier scale; goals add the "extreme" tier on top.
VALID_DIFFICULTIES = set(HABIT_XP)
VALID_GOAL_DIFFICULTIES = set(GOAL_XP)

# Solo Leveling-style letter ranks by level, ascending. S is the ultimate,
# reached at level 100+. Each (threshold, letter) means "this letter from
# `threshold` up to the next threshold".
RANKS = [
    (1, "E"),
    (10, "D"),
    (25, "C"),
    (50, "B"),
    (75, "A"),
    (100, "S"),
]


def streak_multiplier(streak):
    """
    Habit-XP multiplier for a day whose streak count is `streak`.
    A broken streak (0) gets no boost.
    """
    if streak < 1:
        return 1.0
    return min(1 + STREAK_STEP * (streak - 1), STREAK_CAP)


def compute_day_xp(habit_difficulties, hours_worked, goal_difficulties, prev_streak, goal_hours=0, all_habits_done=False, max_habit_xp=0, individual_goals_hit=0):
    """
    Pure day-XP function: the difficulty tiers of a day's completed habits,
    hours worked, tiers of goals completed that day, the previous day's streak,
    the day's total goal hours, whether every habit that day was completed, the
    day's max possible habit XP (every habit done), and the count of individual
    (non-Total) stopwatch goals hit that day -> {"xp_earned", "streak",
    "multiplier", "habit_xp", "work_xp", "goal_xp", "bonus_xp"}. The streak
    multiplier applies to habit XP only; work, goal, and the flat bonuses are
    flat. Worked time earns XP_PER_HOUR up to the day's goal hours and the
    higher XP_PER_HOUR_OVERTIME beyond it (goal_hours = 0 -> no overtime).
    Completing all of the day's habits adds a flat ALL_HABITS_BONUS; working at
    least the day's goal time adds a flat GOAL_TIME_BONUS; each individual
    stopwatch goal hit adds a flat INDIVIDUAL_GOAL_BONUS, summed but capped at
    INDIVIDUAL_GOAL_BONUS_CAP (kept out of the streak calc, which stays habits +
    worked-time-to-goal only). A day counts toward the streak when its grind XP
    (habits done + worked time capped at the goal) reaches STREAK_THRESHOLD_PCT
    of the most it could be (every habit done + goal time worked).

    Each component is rounded individually and xp_earned is their sum, so the
    pie breakdown always reconciles to the displayed total (can differ from a
    single rounding of the combined total by +/-1 XP -- an accepted drift).
    """
    habit_base = sum(HABIT_XP[difficulty] for difficulty in habit_difficulties)
    # standard rate up to the day's total goal time, overtime rate beyond it
    if goal_hours and goal_hours > 0:
        normal_hours = min(hours_worked, goal_hours)
        overtime_hours = max(0.0, hours_worked - goal_hours)
    else:
        normal_hours = hours_worked
        overtime_hours = 0.0
    work_xp = normal_hours * XP_PER_HOUR + overtime_hours * XP_PER_HOUR_OVERTIME

    # Streak: the day's grind XP as a fraction of the most it could be. Worked
    # time counts only up to the goal (overtime can't cover skipped habits);
    # goals and the flat bonuses don't count. A day with nothing to do (max 0)
    # can't be "completed", so it doesn't qualify.
    goal_xp_target = (goal_hours * XP_PER_HOUR) if (goal_hours and goal_hours > 0) else 0.0
    streak_work_xp = (min(hours_worked, goal_hours) * XP_PER_HOUR) if (goal_hours and goal_hours > 0) else 0.0
    qualifying_xp = habit_base + streak_work_xp
    max_day_xp = max_habit_xp + goal_xp_target
    streak = prev_streak + 1 if (max_day_xp > 0 and qualifying_xp >= STREAK_THRESHOLD_PCT * max_day_xp) else 0
    multiplier = streak_multiplier(streak)
    goal_xp = sum(GOAL_XP[difficulty] for difficulty in goal_difficulties)
    bonus = ALL_HABITS_BONUS if all_habits_done else 0
    # reaching the day's total goal time (when one is set) earns a flat bonus
    if goal_hours and goal_hours > 0 and hours_worked >= goal_hours:
        bonus += GOAL_TIME_BONUS
    bonus += min(individual_goals_hit * INDIVIDUAL_GOAL_BONUS, INDIVIDUAL_GOAL_BONUS_CAP)

    habit_xp = round(habit_base * multiplier)
    work_xp = round(work_xp)
    goal_xp = round(goal_xp)  # already integral
    bonus_xp = round(bonus)  # already integral
    xp_earned = habit_xp + work_xp + goal_xp + bonus_xp
    return {
        "xp_earned": xp_earned,
        "streak": streak,
        "multiplier": multiplier,
        "habit_xp": habit_xp,
        "work_xp": work_xp,
        "goal_xp": goal_xp,
        "bonus_xp": bonus_xp,
    }


def streak_progress(habit_base, hours_worked, goal_hours, max_habit_xp):
    """
    Today's streak status, from the same inputs as compute_day_xp's streak rule:
    the qualifying XP so far, the target (STREAK_THRESHOLD_PCT of the day's max
    possible grind XP), the XP still needed to hit it, and whether the day
    already counts. `possible` is False when there's nothing to do (max 0).
    """
    goal_xp_target = (goal_hours * XP_PER_HOUR) if (goal_hours and goal_hours > 0) else 0.0
    streak_work_xp = (min(hours_worked, goal_hours) * XP_PER_HOUR) if (goal_hours and goal_hours > 0) else 0.0
    current = habit_base + streak_work_xp
    max_day_xp = max_habit_xp + goal_xp_target
    target = STREAK_THRESHOLD_PCT * max_day_xp
    possible = max_day_xp > 0
    qualified = possible and current >= target
    remaining = math.ceil(max(0.0, target - current)) if (possible and not qualified) else 0
    return {
        "target": round(target),
        "current": round(current),
        "remaining": remaining,
        "qualified": qualified,
        "possible": possible,
    }


def level_cost(level):
    """
    XP needed to go from `level` to `level + 1` on the fixed curve.
    """
    return round(LEVEL_B * level ** LEVEL_P)


def level_from_xp(total_xp):
    """
    Derive {"level", "xp_into_level", "xp_to_next"} from a running XP total.
    """
    remaining = max(0, total_xp)
    level = 1
    while remaining >= level_cost(level):
        remaining -= level_cost(level)
        level += 1
    return {"level": level, "xp_into_level": remaining, "xp_to_next": level_cost(level)}


def rank_from_level(level):
    """
    The letter rank (E..S) for a level; S is the ultimate, reached at 100+.
    """
    letter = RANKS[0][1]
    for threshold, name in RANKS:
        if level >= threshold:
            letter = name
        else:
            break
    return letter


def rank_visible(user):
    """
    Whether `user` may see the rank layer at all: never for guests (checked
    first, not overridable), otherwise only for usernames on the
    RANK_USERNAMES allowlist. Unlike GUEST_TTL_DAYS in users.py, the env var
    is read here at call time rather than cached as a module-level constant,
    so tests can monkeypatch it and the VM can change it with a container
    restart instead of a code deploy.
    """
    if user is None or user.is_guest:
        return False
    allowlist = {
        entry.strip().lower()
        for entry in os.environ.get("RANK_USERNAMES", "").split(",")
        if entry.strip()
    }
    return user.username.strip().lower() in allowlist