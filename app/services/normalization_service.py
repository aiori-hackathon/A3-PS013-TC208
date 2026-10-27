from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Optional, Tuple

def normalize_to_utc(
    dt: Optional[datetime],
    uncertainty_margin_seconds: float = 1.0,
    timezone_assumption: str = "UTC"
) -> Tuple[Optional[datetime], Optional[datetime], Optional[datetime]]:
    """
    Normalizes a datetime object to timezone-aware UTC datetime and computes the
    uncertainty bounds [earliest_utc, latest_utc].
    Returns (normalized_utc, earliest_utc, latest_utc).
    """
    if dt is None:
        return None, None, None

    # If datetime is naive, apply the documented timezone assumption
    if dt.tzinfo is None:
        try:
            tz = ZoneInfo(timezone_assumption)
            aware_dt = dt.replace(tzinfo=tz)
        except Exception:
            aware_dt = dt.replace(tzinfo=timezone.utc)
    else:
        aware_dt = dt

    # Convert to UTC
    utc_dt = aware_dt.astimezone(timezone.utc)

    # Calculate uncertainty bounds
    delta = timedelta(seconds=max(0.0, uncertainty_margin_seconds))
    earliest_utc = utc_dt - delta
    latest_utc = utc_dt + delta

    return utc_dt, earliest_utc, latest_utc

def intervals_overlap(
    start_a: datetime,
    end_a: datetime,
    start_b: datetime,
    end_b: datetime
) -> bool:
    """Check if two time intervals [start_a, end_a] and [start_b, end_b] overlap."""
    if not start_a or not end_a or not start_b or not end_b:
        return False
    return max(start_a, start_b) <= min(end_a, end_b)
