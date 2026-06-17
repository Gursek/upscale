from datetime import datetime, timezone
from zoneinfo import ZoneInfo


MANILA_TZ = ZoneInfo("Asia/Manila")


def get_manila_today():
    return datetime.now(MANILA_TZ).date()


def to_manila_datetime(utc_dt):
    if utc_dt is None:
        return None
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(MANILA_TZ)


def format_manila_datetime(utc_dt):
    manila_dt = to_manila_datetime(utc_dt)
    if manila_dt is None:
        return None
    return manila_dt.strftime("%Y-%m-%d %H:%M:%S")
