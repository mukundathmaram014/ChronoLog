from datetime import datetime, timedelta, timezone, date
from utils import ensure_utc, process_date, validate_weekday_goal_times, effective_goal_time


def test_ensure_utc_none():
    assert ensure_utc(None) is None


def test_ensure_utc_naive():
    naive = datetime(2026, 1, 15, 12, 0, 0)
    result = ensure_utc(naive)
    assert result.tzinfo == timezone.utc
    assert result.replace(tzinfo=None) == naive


def test_ensure_utc_aware():
    aware = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert ensure_utc(aware) is aware


def test_process_date_explicit():
    class FakeRequest:
        data = b'{"date": "2026-01-15"}'

    assert process_date(FakeRequest()) == date(2026, 1, 15)


def test_process_date_default():
    class FakeRequest:
        data = b'{}'

    assert process_date(FakeRequest()) == date.today()


# ---- per-weekday stopwatch goals (spec 0036) ----

def test_validate_weekday_goal_times_accepts_none_and_a_full_week():
    # None = "one uniform goal", the pre-feature behavior
    assert validate_weekday_goal_times(None) is True
    assert validate_weekday_goal_times(["02:00"] * 7) is True
    # a null slot and "00:00" both mean "no goal that weekday"
    assert validate_weekday_goal_times([None, "00:00", "23:59", "00:01", None, "08:30", "12:00"]) is True
    # all-zero is legal: "no goal any day"
    assert validate_weekday_goal_times(["00:00"] * 7) is True


def test_validate_weekday_goal_times_rejects_malformed_schedules():
    assert validate_weekday_goal_times(["01:00"] * 6) is False   # too short
    assert validate_weekday_goal_times(["01:00"] * 8) is False   # too long
    assert validate_weekday_goal_times("01:00") is False         # not a list
    assert validate_weekday_goal_times({"Mo": "01:00"}) is False
    assert validate_weekday_goal_times([3600000] * 7) is False   # milliseconds, not "HH:MM"
    assert validate_weekday_goal_times([True] * 7) is False      # bools aren't strings
    assert validate_weekday_goal_times(["24:00"] * 7) is False   # hours out of range
    assert validate_weekday_goal_times(["01:60"] * 7) is False   # minutes out of range
    assert validate_weekday_goal_times(["1:00"] * 7) is False    # unpadded
    assert validate_weekday_goal_times(["01-00"] * 7) is False   # wrong separator
    assert validate_weekday_goal_times(["ab:cd"] * 7) is False


def test_effective_goal_time_falls_back_without_a_schedule():
    assert effective_goal_time(None, 3600000, date(2026, 1, 5)) == 3600000


def test_effective_goal_time_indexes_by_python_weekday():
    # index i = date.weekday() i (0 = Mon ... 6 = Sun); 2026-01-05 is a Monday
    schedule = [i * 1000 for i in range(7)]
    for offset in range(7):
        target = date(2026, 1, 5) + timedelta(days=offset)
        assert effective_goal_time(schedule, 999999, target) == offset * 1000
    # a zero slot means "no goal that weekday", not "fall back to the base goal"
    assert effective_goal_time([0] * 7, 3600000, date(2026, 1, 5)) == 0
