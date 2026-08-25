"""In-memory storage adapter implementing StoragePort (§5.2, §6)."""

from __future__ import annotations

import copy
import threading
from typing import Any


class MemoryStorageAdapter:
    """Thread-safe in-memory implementation of the persistence store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tables: dict[str, dict[str, dict[str, Any]]] = {
            "runs": {},
            "source_bank": {},
            "source_payout": {},
            "source_ledger": {},
            "truth_groups": {},
            "match_groups": {},
            "link_decisions": {},
            "exceptions": {},
            "agent_calls": {},
            "closures": {},
            "eval_sweeps": {},
            "control_results": {},
        }
        self._run_requests: list[dict[str, Any]] = []
        self._request_id_seq: int = 1

    def save_run(
        self,
        run_id: str,
        report_data: dict[str, Any],
        status: str = "complete",
    ) -> None:
        """Persist or update run report."""
        with self._lock:
            self._tables["runs"][run_id] = {
                "run_id": run_id,
                "engine_version": report_data.get("engine_version", "0.1.0"),
                "schema_version": report_data.get("schema_version", "1.0.0"),
                "config": copy.deepcopy(report_data.get("config", {})),
                "report": copy.deepcopy(report_data),
                "status": status,
            }

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve run report by run_id."""
        with self._lock:
            row = self._tables["runs"].get(run_id)
            if row and "report" in row:
                return copy.deepcopy(row["report"])  # type: ignore[no-any-return]
            return None

    def save_sources(
        self,
        run_id: str,
        bank_txns: list[dict[str, Any]],
        payouts: list[dict[str, Any]],
        ledger_entries: list[dict[str, Any]],
    ) -> None:
        """Persist source records for a run."""
        with self._lock:
            for b in bank_txns:
                rec = copy.deepcopy(b)
                rec["run_id"] = run_id
                self._tables["source_bank"][str(rec["bank_id"])] = rec

            for p in payouts:
                rec = copy.deepcopy(p)
                rec["run_id"] = run_id
                self._tables["source_payout"][str(rec["payout_id"])] = rec

            for el in ledger_entries:
                rec = copy.deepcopy(el)
                rec["run_id"] = run_id
                self._tables["source_ledger"][str(rec["ledger_id"])] = rec

    def save_truth_groups(self, run_id: str, truth_groups: list[dict[str, Any]]) -> None:
        """Persist ground truth groups for a run."""
        with self._lock:
            for tg in truth_groups:
                rec = copy.deepcopy(tg)
                rec["run_id"] = run_id
                self._tables["truth_groups"][str(rec["group_id"])] = rec

    def save_match_groups(self, run_id: str, match_groups: list[dict[str, Any]]) -> None:
        """Persist match groups for a run."""
        with self._lock:
            for mg in match_groups:
                rec = copy.deepcopy(mg)
                rec["run_id"] = run_id
                self._tables["match_groups"][str(rec["group_id"])] = rec

    def save_link_decisions(self, run_id: str, link_decisions: list[dict[str, Any]]) -> None:
        """Persist link-level decisions for a run."""
        with self._lock:
            for idx, ld in enumerate(link_decisions):
                rec = copy.deepcopy(ld)
                rec["run_id"] = run_id
                key = f"{run_id}_{rec['link_type']}_{rec['left_id']}_{rec['right_id']}_{idx}"
                self._tables["link_decisions"][key] = rec

    def save_exceptions(self, run_id: str, exceptions: list[dict[str, Any]]) -> None:
        """Persist classified exception records for a run."""
        with self._lock:
            for exc in exceptions:
                rec = copy.deepcopy(exc)
                rec["run_id"] = run_id
                self._tables["exceptions"][str(rec["exception_id"])] = rec

    def save_agent_calls(self, run_id: str, agent_calls: list[dict[str, Any]]) -> None:
        """Persist agent call trace and telemetry."""
        with self._lock:
            for call in agent_calls:
                rec = copy.deepcopy(call)
                rec["run_id"] = run_id
                self._tables["agent_calls"][str(rec["call_id"])] = rec

    def save_closures(self, run_id: str, closures: list[dict[str, Any]]) -> None:
        """Persist closure records."""
        with self._lock:
            for cl in closures:
                rec = copy.deepcopy(cl)
                rec["run_id"] = run_id
                self._tables["closures"][str(rec["closure_id"])] = rec

    def save_eval_sweeps(self, run_id: str, sweeps: list[dict[str, Any]]) -> None:
        """Persist eval sweep rows."""
        with self._lock:
            for sw in sweeps:
                rec = copy.deepcopy(sw)
                rec["run_id"] = run_id
                key = f"{run_id}_{rec['seed']}"
                self._tables["eval_sweeps"][key] = rec

    def get_eval_sweeps(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve eval sweep rows for a run."""
        with self._lock:
            return sorted(
                [
                    copy.deepcopy(r)
                    for r in self._tables["eval_sweeps"].values()
                    if r.get("run_id") == run_id
                ],
                key=lambda x: int(x.get("seed", 0)),
            )

    def save_control_results(self, run_id: str, control_results: list[dict[str, Any]]) -> None:
        """Persist negative control results."""
        with self._lock:
            for cr in control_results:
                rec = copy.deepcopy(cr)
                rec["run_id"] = run_id
                key = f"{run_id}_{rec['control_name']}"
                self._tables["control_results"][key] = rec

    def get_control_results(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve negative control results for a run."""
        with self._lock:
            return [
                copy.deepcopy(r)
                for r in self._tables["control_results"].values()
                if r.get("run_id") == run_id
            ]

    def create_run_request(self, config: dict[str, Any]) -> int:
        """Create a new run request in pending state."""
        with self._lock:
            req_id = self._request_id_seq
            self._request_id_seq += 1
            self._run_requests.append(
                {
                    "id": req_id,
                    "config": copy.deepcopy(config),
                    "status": "pending",
                    "claimed_by": None,
                    "claimed_at": None,
                    "result_run_id": None,
                    "error_message": None,
                }
            )
            return req_id

    def claim_run_request(self, worker_id: str) -> dict[str, Any] | None:
        """Claim the next pending run request."""
        with self._lock:
            for req in self._run_requests:
                if req["status"] == "pending":
                    req["status"] = "claimed"
                    req["claimed_by"] = worker_id
                    return copy.deepcopy(req)
            return None

    def update_run_request(
        self,
        req_id: int,
        status: str,
        result_run_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update request status, result run ID, or error message."""
        with self._lock:
            for req in self._run_requests:
                if req["id"] == req_id:
                    req["status"] = status
                    if result_run_id is not None:
                        req["result_run_id"] = result_run_id
                    if error_message is not None:
                        req["error_message"] = error_message
                    return

    def get_run_request(self, req_id: int) -> dict[str, Any] | None:
        """Retrieve a run request by ID."""
        with self._lock:
            for req in self._run_requests:
                if req["id"] == req_id:
                    return copy.deepcopy(req)
            return None

    def dump_all(self) -> dict[str, list[dict[str, Any]]]:
        """Dump all records across in-memory tables."""
        with self._lock:
            return {tbl: list(rows.values()) for tbl, rows in self._tables.items()}

    def count_rows_for_run(self, run_id: str) -> dict[str, int]:
        """Count rows across tables for a run."""
        with self._lock:
            counts: dict[str, int] = {}
            for tbl, rows in self._tables.items():
                counts[tbl] = sum(1 for r in rows.values() if r.get("run_id") == run_id)
            return counts
