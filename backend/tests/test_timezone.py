import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import timezone as app_timezone


def test_bogota_time_uses_business_timezone_at_day_boundary(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 10, 22, 4, 30, tzinfo=timezone.utc)
            return value.astimezone(tz) if tz else value.replace(tzinfo=None)

    monkeypatch.setattr(app_timezone, 'datetime', FixedDateTime)

    assert app_timezone.BOGOTA_TIMEZONE.utcoffset(None) == timedelta(hours=-5)
    assert app_timezone.bogota_now() == datetime(2026, 10, 21, 23, 30)
    assert app_timezone.bogota_today() == date(2026, 10, 21)
