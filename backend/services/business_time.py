from datetime import date, datetime, time, timedelta, timezone

from utils.timezone import MANILA_TZ, format_manila_datetime, to_manila_datetime


PHILIPPINE_TZ = MANILA_TZ


def business_now():
    return datetime.now(PHILIPPINE_TZ)


def _rollover_time(value: str | None) -> time:
    try:
        return datetime.strptime(value or "00:00", "%H:%M").time()
    except ValueError:
        return time.min


def business_today(rollover: str | None = None):
    now = business_now()
    return now.date() if now.time() >= _rollover_time(rollover) else now.date() - timedelta(days=1)


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def business_day_utc_bounds(day: date, rollover: str | None = None):
    start_local = datetime.combine(day, _rollover_time(rollover), tzinfo=PHILIPPINE_TZ)
    end_local = start_local + timedelta(days=1) - timedelta(microseconds=1)
    start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start_utc, end_utc


def local_interval_to_utc(start_local, end_local):
    if start_local.tzinfo is None:
        start_local = start_local.replace(tzinfo=PHILIPPINE_TZ)
    if end_local.tzinfo is None:
        end_local = end_local.replace(tzinfo=PHILIPPINE_TZ)
    return (
        start_local.astimezone(timezone.utc).replace(tzinfo=None),
        end_local.astimezone(timezone.utc).replace(tzinfo=None),
    )


def to_business_iso(value):
    return format_manila_datetime(value)


def to_business_datetime(value):
    return to_manila_datetime(value)
