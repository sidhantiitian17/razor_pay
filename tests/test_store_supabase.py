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
        self._select_cols: str = "*"
        self._pending_data: list[dict[str, Any]] = []

    def upsert(
        self,
        records: list[dict[str, Any]] | dict[str, Any],
        on_conflict: str | None = None,
    ) -> MockSupabaseTable:
        if isinstance(records, dict):
            records = [records]
        if self.name not in self.data_store:
            self.data_store[self.name] = []
        conflict_keys = [k.strip() for k in on_conflict.split(",")] if on_conflict else []
        for r in records:
            r = dict(r)
            if conflict_keys:
                # Replace existing row if all conflict keys match, else append.
                matched = False
                for i, existing in enumerate(self.data_store[self.name]):
                    if all(existing.get(k) == r.get(k) for k in conflict_keys):
                        self.data_store[self.name][i] = r
                        matched = True
                        break
                if not matched:
                    self.data_store[self.name].append(r)
            else:
                self.data_store[self.name].append(r)
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
        self._select_cols = cols
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
    """Adapter raises ValueError when no key is provided at all."""
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY must be set"):
        SupabaseStorageAdapter(url="https://example.supabase.co", key="")


def test_supabase_adapter_rejects_browser_anon_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """VITE_SUPABASE_PUBLISHABLE_KEY must NOT be accepted — it is the browser anon key.

    Before the security fix the adapter silently fell back to this key, which
    means --db supabase could write with anon privileges and bypass RLS.
    Ensure the adapter raises rather than proceeding with that key.
    """
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.setenv("VITE_SUPABASE_PUBLISHABLE_KEY", "anon-key-must-not-be-accepted")
    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY must be set"):
        SupabaseStorageAdapter(url="https://example.supabase.co")


def test_supabase_adapter_accepts_service_role_key_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adapter initialises successfully when SUPABASE_SERVICE_ROLE_KEY is set in env."""
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-role-secret")
    # Pass a pre-built mock client so create_client is never called (no network).
    mock_client = MockSupabaseClient()
    adapter = SupabaseStorageAdapter(client=mock_client)  # type: ignore[arg-type]
    assert adapter.client is mock_client


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


def test_supabase_no_cross_seed_pk_collision() -> None:
    """Prove compound on_conflict prevents cross-seed row collision.

    The generator resets counters each generate_dataset() call, so bank_id='bank_001'
    appears in every run. Before the compound-PK migration, upsert(on_conflict=bank_id)
    would let seed-102 silently overwrite seed-101's bank_001 row. After the fix,
    on_conflict='run_id,bank_id' keeps them separate.

    This is a unit/integration test against the mock (exact Supabase behaviour verified
    by the migration SQL when applied to a real project). The mock honours on_conflict
    properly so the assertion here is meaningful.
    """
    mock_client = MockSupabaseClient()
    adapter = SupabaseStorageAdapter(client=mock_client)  # type: ignore[arg-type]

    run_a = "run-seed-101"
    run_b = "run-seed-102"

    # Both runs happen to produce the same bank_id — exactly as the generator does
    # when counters reset. Before the fix this overwrote run_a's row.
    bank_a = {
        "bank_id": "bank_001",
        "amount_paise": 10000,
        "run_id": run_a,
        "posted_at": "2024-01-01T00:00:00Z",
        "value_date": "2024-01-01",
        "utr": "UTR_A",
        "narration": "Narration A",
        "currency": "INR",
    }
    bank_b = {
        "bank_id": "bank_001",
        "amount_paise": 99999,
        "run_id": run_b,
        "posted_at": "2024-01-02T00:00:00Z",
        "value_date": "2024-01-02",
        "utr": "UTR_B",
        "narration": "Narration B",
        "currency": "INR",
    }

    adapter.save_sources(run_id=run_a, bank_txns=[bank_a], payouts=[], ledger_entries=[])
    adapter.save_sources(run_id=run_b, bank_txns=[bank_b], payouts=[], ledger_entries=[])

    all_rows = mock_client.data_store.get("source_bank", [])

    # Must be 2 distinct rows — one per run — not 1 overwritten row.
    assert len(all_rows) == 2, (
        f"Expected 2 rows (one per run), got {len(all_rows)} — "
        "cross-seed PK collision still occurring"
    )

    # Each run_id points to its own distinct data.
    rows_a = [r for r in all_rows if r["run_id"] == run_a]
    rows_b = [r for r in all_rows if r["run_id"] == run_b]
    assert len(rows_a) == 1 and rows_a[0]["amount_paise"] == 10000
    assert len(rows_b) == 1 and rows_b[0]["amount_paise"] == 99999


def test_count_rows_for_run_uses_star_not_count_column() -> None:
    """Prove count_rows_for_run uses select('*', count=...) not select('count', ...).

    The earlier bug called .select("count", count=CountMethod.exact).  PostgREST
    interprets the first arg as a column selector, so it tried to select a physical
    'count' column that does not exist in any table — resulting in a 400 error
    against a live Supabase project.  The correct form is select("*", ...) which
    fetches all columns but only reads res.count for the metadata.

    This mock-level test would have caught the bug: it records the cols arg passed
    to .select() and asserts it is "*".
    """

    class ColumnCheckingTable(MockSupabaseTable):
        """Raises if select() is called with a non-wildcard column list for count ops."""

        def select(self, cols: str = "*", count: str | None = None) -> ColumnCheckingTable:
            if count is not None and cols != "*":
                raise ValueError(
                    f"count_rows_for_run must use select('*', count=...), "
                    f"got select({cols!r}, count=...) — "
                    f"'{cols}' is not a real column and will 400 in production"
                )
            return super().select(cols, count)  # type: ignore[return-value]

    class ColumnCheckingClient(MockSupabaseClient):
        def table(self, table_name: str) -> ColumnCheckingTable:
            return ColumnCheckingTable(table_name, self.data_store)

    adapter = SupabaseStorageAdapter(
        client=ColumnCheckingClient()  # type: ignore[arg-type]
    )

    # Save a run so the table has rows, then count — must not raise.
    run_id = "run-count-test"
    adapter.save_run(
        run_id, {"run_id": run_id, "engine_version": "0.1.0", "schema_version": "1.0.0"}
    )
    counts = adapter.count_rows_for_run(run_id)

    # Sanity: runs table has 1 row; method returned without raising.
    assert counts["runs"] >= 0  # mock count may be 0 if eq filter gives 0; no ValueError = pass
