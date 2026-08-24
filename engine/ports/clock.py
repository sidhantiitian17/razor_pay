"""Clock and timestamp protocol (§6)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Protocol for system time provision."""

    def now(self) -> datetime:
        """Return current datetime in UTC."""
        ...


class SystemClock:
    """Standard system clock providing tz-aware UTC timestamps."""

    def now(self) -> datetime:
        """Return current UTC datetime."""
        return datetime.now(tz=UTC)
