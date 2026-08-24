"""Timezone-aware time windows and calendar-day deltas."""

from __future__ import annotations

from datetime import UTC, date, datetime


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware UTC.

    Args:
        dt: A datetime to validate.

    Returns:
        The validated datetime.

    Raises:
        ValueError: If dt is naive (no timezone) or not UTC.
    """
    if dt.tzinfo is None:
        raise ValueError(f"Naive datetime not allowed: {dt!r}. Use tz-aware UTC.")
    if dt.utcoffset() != UTC.utcoffset(None):
        raise ValueError(f"Non-UTC datetime not allowed: {dt!r}")
    return dt


def calendar_day_delta(d1: date, d2: date) -> int:
    """Compute absolute calendar-day difference.

    Args:
        d1: First date.
        d2: Second date.

    Returns:
        Absolute number of calendar days between d1 and d2.
    """
    return abs((d1 - d2).days)


def date_within_window(d1: date, d2: date, max_days: int) -> bool:
    """Check if two dates are within a calendar-day window.

    Args:
        d1: First date.
        d2: Second date.
        max_days: Maximum allowed calendar-day difference (inclusive).

    Returns:
        True if |d1 - d2| <= max_days.
    """
    return calendar_day_delta(d1, d2) <= max_days
