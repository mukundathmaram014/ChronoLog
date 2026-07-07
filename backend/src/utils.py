import json
from datetime import date, timezone


# generalized response formats
def success_response(data, code=200):
    return json.dumps(data), code


def failure_response(message, code=404):
    return json.dumps({"error": message}), code


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
STREAK_STEP = 0.1
STREAK_CAP = 2.0
# a day's "grind" XP (habits + worked time, no goals) must reach this for the
# day to count toward the streak. Set near a strong day's output so keeping a
# streak is demanding, not a formality.
STREAK_THRESHOLD = 250
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


def compute_day_xp(habit_difficulties, hours_worked, goal_difficulties, prev_streak, goal_hours=0, all_habits_done=False):
    """
    Pure day-XP function: the difficulty tiers of a day's completed habits,
    hours worked, tiers of goals completed that day, the previous day's streak,
    the day's total goal hours, and whether every habit that day was completed
    -> {"xp_earned", "streak", "multiplier"}. The streak multiplier applies to
    habit XP only; work, goal, and the all-habits bonus are flat. Worked time
    earns XP_PER_HOUR up to the day's goal hours and the higher
    XP_PER_HOUR_OVERTIME beyond it (goal_hours = 0 -> no overtime). Completing
    all of the day's habits adds a flat ALL_HABITS_BONUS. A day qualifies for
    the streak on its habit + worked-time XP (goals excluded).
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
    # goals are rare one-off wins and don't carry a daily streak
    qualifying_xp = habit_base + work_xp
    streak = prev_streak + 1 if qualifying_xp >= STREAK_THRESHOLD else 0
    multiplier = streak_multiplier(streak)
    goal_xp = sum(GOAL_XP[difficulty] for difficulty in goal_difficulties)
    bonus = ALL_HABITS_BONUS if all_habits_done else 0
    xp_earned = round(habit_base * multiplier + work_xp + goal_xp + bonus)
    return {"xp_earned": xp_earned, "streak": streak, "multiplier": multiplier}


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