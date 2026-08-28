"""Background queue worker claiming and executing reconciliation runs.

Satisfies §5.2, §7 P6, checks 6.4, 6.5.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from engine.adapters.store_memory import MemoryStorageAdapter
from engine.app.publisher import ReportPublisher
from engine.app.reporter import ReportGenerator
from engine.core.generator.build import generate_dataset

if TYPE_CHECKING:
    from collections.abc import Callable

    from engine.ports.store import StoragePort


class ReconciliationWorker:
    """Worker polling and executing run requests with row-level locking."""

    def __init__(
        self,
        worker_id: str = "worker-default",
        store: StoragePort | None = None,
    ) -> None:
        self.worker_id = worker_id
        self.store = store or MemoryStorageAdapter()
        self.publisher = ReportPublisher(store=self.store)
        self.generator = ReportGenerator()

    def claim_next_request(self) -> dict[str, Any] | None:
        """Atomically claim the next pending run request."""
        return self.store.claim_run_request(worker_id=self.worker_id)

    def process_claimed_request(
        self,
        req: dict[str, Any],
        runner_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Execute reconciliation for claimed request and publish results."""
        req_id = int(req["id"])
        config = req.get("config", {})

        try:
            if runner_fn is not None:
                res = runner_fn(config)
                run_id = str(res.get("run_id", "00000000-0000-0000-0000-000000000000"))
                self.store.update_run_request(
                    req_id=req_id,
                    status="complete",
                    result_run_id=run_id,
                )
                return res

            n = int(config.get("n", 100))
            seed = int(config.get("seed", 42))
            mode = str(config.get("mode", "rules_only"))
            # Mirror CLI._classify_seed_set: regression=42, holdout=101-120, dev=1-10.
            seed_set = "regression" if seed == 42 else "holdout" if 101 <= seed <= 120 else "dev"

            dataset = generate_dataset(n=n, seed=seed)
            report = self.generator.generate_report(
                dataset=dataset,
                mode=mode,  # type: ignore[arg-type]
                seed=seed,
                seed_set=seed_set,  # type: ignore[arg-type]
            )

            self.publisher.publish(
                dataset=dataset,
                report=report,
                match_groups=self.generator.last_match_groups,
                link_decisions=self.generator.last_link_decisions,
                agent_calls=self.generator.last_agent_calls,
                closures=self.generator.last_closures,
            )
            run_id = str(report["run_id"])

            self.store.update_run_request(
                req_id=req_id,
                status="complete",
                result_run_id=run_id,
            )
            return report

        except Exception as e:
            self.store.update_run_request(
                req_id=req_id,
                status="failed",
                error_message=str(e),
            )
            return None

    def run_once(self) -> bool:
        """Claim and process a single pending run request. Returns True if a task was processed."""
        req = self.claim_next_request()
        if req is None:
            return False
        self.process_claimed_request(req)
        return True

    def run_loop(self, poll_interval: float = 1.0, max_iterations: int | None = None) -> None:
        """Continuously poll and execute run requests until stopped."""
        iterations = 0
        while max_iterations is None or iterations < max_iterations:
            processed = self.run_once()
            if not processed:
                time.sleep(poll_interval)
            iterations += 1
