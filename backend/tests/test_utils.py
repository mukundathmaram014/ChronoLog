from datetime import datetime, timezone, date
from utils import ensure_utc, process_date


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
