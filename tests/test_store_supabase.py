"""Unit and mock tests for SupabaseStorageAdapter (§5.2, §6, P12)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from engine.adapters.store_supabase import SupabaseStorageAdapter, _chunk_list
from engine.app.worker import ReconciliationWorker


class MockSupabaseTable:
    def __init__(self, name: str, data_store: dict[str, list[dict[str, Any]]]) -> None:
        self.name = name
        self.data_store = data_store
        self._filter_col: str | None = None
        self._filter_val: Any = None
        self._select_count: str | None = None
        self._pending_data: list[dict[str, Any]] = []

    def upsert(self, records: list[dict[str, Any]] | dict[str, Any]) -> MockSupabaseTable:
        if isinstance(records, dict):
            records = [records]
        if self.name not in self.data_store:
            self.data_store[self.name] = []
        for r in records:
            # Simple key-based replace or append
            self.data_store[self.name].append(dict(r))
        return self

    def insert(self, records: list[dict[str, Any]] | dict[str, Any]) -> MockSupabaseTable:
        if isinstance(records, dict):
            records = [records]
        if self.name not in self.data_store:
            self.data_store[self.name] = []
        for _i, r in enumerate(records):
            new_r = dict(r)
            if "id" not in new_r:
                new_r["id"] = len(self.data_store[self.name]) + 1
            self.data_store[self.name].append(new_r)
            self._pending_data.append(new_r)
        return self

    def select(self, cols: str = "*", count: str | None = None) -> MockSupabaseTable:
        self._select_count = count
        return self

    def eq(self, column: str, value: Any) -> MockSupabaseTable:
        self._filter_col = column
        self._filter_val = value
        return self

    def order(self, column: str, ascending: bool = True) -> MockSupabaseTable:
        return self

    def limit(self, count: int) -> MockSupabaseTable:
        return self

    def update(self, payload: dict[str, Any]) -> MockSupabaseTable:
        rows = self.data_store.get(self.name, [])
        updated: list[dict[str, Any]] = []
        for r in rows:
            if self._filter_col is None or r.get(self._filter_col) == self._filter_val:
                r.update(payload)
                updated.append(r)
        self._pending_data = updated
        return self

    def execute(self) -> Any:
        rows = self.data_store.get(self.name, [])
        if self._filter_col is not None:
            rows = [r for r in rows if r.get(self._filter_col) == self._filter_val]

        res = MagicMock()
        res.data = self._pending_data if self._pending_data else rows
        if self._select_count == "exact":
            res.count = len(rows)
        else:
            res.count = None
        self._pending_data = []
        self._filter_col = None
        self._filter_val = None
        return res


class MockSupabaseClient:
    def __init__(self) -> None:
        self.data_store: dict[str, list[dict[str, Any]]] = {}

    def table(self, table_name: str) -> MockSupabaseTable:
        return MockSupabaseTable(table_name, self.data_store)


def test_chunk_list() -> None:
    items = [{"i": i} for i in range(550)]
    chunks = _chunk_list(items, chunk_size=200)
    assert len(chunks) == 3
    assert len(chunks[0]) == 200
    assert len(chunks[1]) == 200
    assert len(chunks[2]) == 150


def test_supabase_adapter_missing_key() -> None:
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY"):
        SupabaseStorageAdapter(url="https://example.supabase.co", key="")


def test_supabase_adapter_save_and_load_run() -> None:
    mock_client = MockSupabaseClient()
    adapter = SupabaseStorageAdapter(client=mock_client)  # type: ignore[arg-type]

    run_id = "test-run-123"
    report_data = {
        "run_id": run_id,
        "engine_version": "0.1.0",
        "schema_version": "1.0.0",
        "accuracy": {"match_rate": {"value": 0.85}},
    }

    adapter.save_run(run_id, report_data)
    loaded = adapter.load_run(run_id)
    assert loaded is not None
    assert loaded["accuracy"]["match_rate"]["value"] == 0.85


def test_supabase_adapter_save_all_entities() -> None:
    mock_client = MockSupabaseClient()
    adapter = SupabaseStorageAdapter(client=mock_client)  # type: ignore[arg-type]

    run_id = "test-run-all"
    adapter.save_sources(
        run_id=run_id,
        bank_txns=[{"bank_id": "b1", "amount_paise": 1000}],
        payouts=[{"payout_id": "p1", "amount_paise": 1000}],
        ledger_entries=[{"ledger_id": "l1", "amount_paise": 1000}],
    )
    adapter.save_truth_groups(run_id, [{"group_id": "tg1"}])
    adapter.save_match_groups(run_id, [{"group_id": "mg1"}])
    adapter.save_link_decisions(run_id, [{"id": 1, "link_type": "bank_payout"}])
    adapter.save_exceptions(run_id, [{"exception_id": "e1"}])
    adapter.save_agent_calls(run_id, [{"call_id": "c1", "seq": 1}])
    adapter.save_closures(run_id, [{"closure_id": "cl1"}])
    adapter.save_eval_sweeps(run_id, [{"seed": 101, "seed_set": "holdout", "report": {}}])
    adapter.save_control_results(run_id, [{"control_name": "null_agent", "passed": True}])

    sweeps = adapter.get_eval_sweeps(run_id)
    assert len(sweeps) == 1
    assert sweeps[0]["seed"] == 101

    controls = adapter.get_control_results(run_id)
    assert len(controls) == 1
    assert controls[0]["control_name"] == "null_agent"

    counts = adapter.count_rows_for_run(run_id)
    assert counts["source_bank"] == 1
    assert counts["source_payout"] == 1
    assert counts["source_ledger"] == 1
    assert counts["truth_groups"] == 1
    assert counts["match_groups"] == 1
    assert counts["link_decisions"] == 1
    assert counts["exceptions"] == 1
    assert counts["agent_calls"] == 1
    assert counts["closures"] == 1
    assert counts["control_results"] == 1


def test_supabase_adapter_run_requests_lifecycle() -> None:
    mock_client = MockSupabaseClient()
    adapter = SupabaseStorageAdapter(client=mock_client)  # type: ignore[arg-type]

    req_id = adapter.create_run_request({"seed": 42, "n": 50, "mode": "rules_only"})
    assert req_id > 0

    req = adapter.get_run_request(req_id)
    assert req is not None
    assert req["status"] == "pending"

    claimed = adapter.claim_run_request("worker-1")
    assert claimed is not None
    assert claimed["id"] == req_id

    adapter.update_run_request(req_id, status="completed", result_run_id="run-xyz")
    updated = adapter.get_run_request(req_id)
    assert updated is not None
    assert updated["status"] == "completed"
    assert updated["result_run_id"] == "run-xyz"


def test_supabase_publisher_and_worker_end_to_end() -> None:
    mock_client = MockSupabaseClient()
    adapter = SupabaseStorageAdapter(client=mock_client)  # type: ignore[arg-type]

    # Create request and process via worker
    req_id = adapter.create_run_request({"seed": 42, "n": 50, "mode": "rules_only"})
    worker = ReconciliationWorker(store=adapter, worker_id="test-worker")
    processed = worker.run_once()
    assert processed is True

    req = adapter.get_run_request(req_id)
    assert req is not None
    assert req["status"] == "complete"
    assert req["result_run_id"] is not None

    run_id = req["result_run_id"]
    loaded = adapter.load_run(run_id)
    assert loaded is not None
    assert "accuracy" in loaded
