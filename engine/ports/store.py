"""Storage protocol for report and closure persistence (§6)."""

from __future__ import annotations

from typing import Protocol


class StoragePort(Protocol):
    """Storage adapter interface."""

    def save_report(self, run_id: str, report_data: dict[str, object]) -> None:
        """Persist reconciliation report."""
        ...

    def load_report(self, run_id: str) -> dict[str, object] | None:
        """Retrieve reconciliation report by run_id."""
        ...
