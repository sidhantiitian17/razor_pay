"""Tests for worker claim concurrency and failure handling (§5.2, §7 P6, checks 6.4, 6.5)."""

from __future__ import annotations

import threading

from engine.adapters.store_memory import MemoryStorageAdapter
from engine.app.worker import ReconciliationWorker


def test_claim() -> None:
    """Check 6.4: Two concurrent workers never claim the same request (row lock)."""
    store = MemoryStorageAdapter()
    req_id = store.create_run_request(config={"n": 60, "seed": 42, "mode": "rules_only"})

    worker_a = ReconciliationWorker(worker_id="worker-A", store=store)
    worker_b = ReconciliationWorker(worker_id="worker-B", store=store)

    claimed_workers: list[str] = []

    def run_worker_claim(worker: ReconciliationWorker) -> None:
        claimed = worker.claim_next_request()
        if claimed is not None:
            claimed_workers.append(worker.worker_id)

    t1 = threading.Thread(target=run_worker_claim, args=(worker_a,))
    t2 = threading.Thread(target=run_worker_claim, args=(worker_b,))

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly 1 worker should have successfully claimed the request
    assert len(claimed_workers) == 1
    req = store.get_run_request(req_id)
    assert req is not None
    assert req["status"] == "claimed"
    assert req["claimed_by"] in ("worker-A", "worker-B")


def test_failure_path() -> None:
    """Check 6.5: A failing run marks failed with a message; never hangs in claimed."""
    store = MemoryStorageAdapter()
    req_id = store.create_run_request(config={"invalid_param": "crash"})

    worker = ReconciliationWorker(worker_id="worker-err", store=store)
    req = worker.claim_next_request()
    assert req is not None
    assert req["id"] == req_id

    # Process request where runner fails
    def faulty_runner(config: dict[str, object]) -> dict[str, object]:
        raise ValueError("Simulated pipeline crash for failure path test")

    worker.process_claimed_request(req=req, runner_fn=faulty_runner)

    # Must be marked failed with error message
    final_req = store.get_run_request(req_id)
    assert final_req is not None
    assert final_req["status"] == "failed"
    assert "Simulated pipeline crash" in str(final_req.get("error_message", ""))


def test_worker_seed_42_classified_as_regression() -> None:
    """Check seed=42 is persisted as seed_set='regression', not 'dev'.

    Runtime-confirmed bug: worker line previously said
    ``seed_set = 'holdout' if 101<=seed<=120 else 'dev'``
    which mislabelled seed 42 as 'dev', contradicting CLI._classify_seed_set.
    """
    store = MemoryStorageAdapter()
    req_id = store.create_run_request(config={"n": 50, "seed": 42, "mode": "rules_only"})

    worker = ReconciliationWorker(worker_id="worker-reg", store=store)
    result = worker.run_once()
    assert result is True

    req = store.get_run_request(req_id)
    assert req is not None
    assert req["status"] == "complete"

    run_id = req["result_run_id"]
    assert run_id is not None

    report = store.load_run(run_id)
    assert report is not None
    got = report.get("config", {}).get("seed_set")
    assert got == "regression", f"seed=42 seed_set should be 'regression', got {got!r}"
