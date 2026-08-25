"""Storage protocol for report, sources, and worker persistence (§5.2, §6)."""

from __future__ import annotations

from typing import Any, Protocol


class StoragePort(Protocol):
    """Storage adapter interface for database operations."""

    def save_run(self, run_id: str, report_data: dict[str, Any], status: str = "complete") -> None:
        """Persist or update reconciliation run and report JSON."""
        ...

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve reconciliation report by run_id."""
        ...

    def save_sources(
        self,
        run_id: str,
        bank_txns: list[dict[str, Any]],
        payouts: list[dict[str, Any]],
        ledger_entries: list[dict[str, Any]],
    ) -> None:
        """Persist source records for a run."""
        ...

    def save_truth_groups(self, run_id: str, truth_groups: list[dict[str, Any]]) -> None:
        """Persist ground truth groups for a run."""
        ...

    def save_match_groups(self, run_id: str, match_groups: list[dict[str, Any]]) -> None:
        """Persist resolved match groups for a run."""
        ...

    def save_link_decisions(self, run_id: str, link_decisions: list[dict[str, Any]]) -> None:
        """Persist link-level decisions (TP, FP, FN, TN) for a run."""
        ...

    def save_exceptions(self, run_id: str, exceptions: list[dict[str, Any]]) -> None:
        """Persist open/classified exception records for a run."""
        ...

    def save_agent_calls(self, run_id: str, agent_calls: list[dict[str, Any]]) -> None:
        """Persist agent trace and telemetry records for a run."""
        ...

    def save_closures(self, run_id: str, closures: list[dict[str, Any]]) -> None:
        """Persist audit-grade closure journal entries for a run."""
        ...

    def save_eval_sweeps(self, run_id: str, sweeps: list[dict[str, Any]]) -> None:
        """Persist eval sweep distribution rows for a run."""
        ...

    def get_eval_sweeps(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve eval sweep rows for a run."""
        ...

    def save_control_results(self, run_id: str, control_results: list[dict[str, Any]]) -> None:
        """Persist negative control verification results for a run."""
        ...

    def get_control_results(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve control results for a run."""
        ...

    def create_run_request(self, config: dict[str, Any]) -> int:
        """Create a new pending run request in the queue."""
        ...

    def claim_run_request(self, worker_id: str) -> dict[str, Any] | None:
        """Atomically claim the next pending run request in the queue."""
        ...

    def update_run_request(
        self,
        req_id: int,
        status: str,
        result_run_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update status, result run ID, or error message of a run request."""
        ...

    def get_run_request(self, req_id: int) -> dict[str, Any] | None:
        """Retrieve run request by request ID."""
        ...

    def dump_all(self) -> dict[str, list[dict[str, Any]]]:
        """Dump all in-memory tables for verification and inspection."""
        ...

    def count_rows_for_run(self, run_id: str) -> dict[str, int]:
        """Count stored rows across tables for a run."""
        ...
