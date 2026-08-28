"""Supabase storage adapter implementing StoragePort for live cloud persistence (§5.2, §6).

Uses the Supabase Python client with service_role privileges to write directly
to the relational database schema defined in contracts/migrations/001_init.sql.
"""

from __future__ import annotations

import os
from typing import Any, cast

from postgrest.types import CountMethod

try:
    from supabase import Client, create_client
except ImportError:
    Client = Any  # type: ignore[misc,assignment]
    create_client = None  # type: ignore[assignment]


def _chunk_list(items: list[dict[str, Any]], chunk_size: int = 200) -> list[list[dict[str, Any]]]:
    """Split a list into chunks of at most chunk_size."""
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


class SupabaseStorageAdapter:
    """Live Supabase implementation of the StoragePort protocol."""

    def __init__(
        self,
        url: str | None = None,
        key: str | None = None,
        client: Client | None = None,
    ) -> None:
        if client is not None:
            self.client = client
            return

        self.url = (
            url
            or os.environ.get("SUPABASE_URL")
            or os.environ.get("VITE_SUPABASE_URL")
            or "https://dtgwbqcjblbcgclogvtv.supabase.co"
        )
        # Require a server-side service_role key.  The VITE_SUPABASE_PUBLISHABLE_KEY
        # is the browser anon key and must NEVER be used here — it bypasses RLS and
        # violates the adapter's stated service_role contract (CHANGELOG.md §68).
        self.key = key or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""

        if not self.key:
            raise ValueError(
                "SUPABASE_SERVICE_ROLE_KEY must be set for the Supabase adapter. "
                "The browser anon/publishable key (VITE_SUPABASE_PUBLISHABLE_KEY) "
                "is explicitly rejected — it does not have service_role privileges."
            )

        if create_client is None:
            raise ImportError(
                "supabase package not installed. Run 'uv pip install supabase' to enable."
            )

        self.client = create_client(self.url, self.key)

    def save_run(
        self,
        run_id: str,
        report_data: dict[str, Any],
        status: str = "complete",
    ) -> None:
        """Persist or update reconciliation run and report JSON."""
        row = {
            "run_id": run_id,
            "engine_version": report_data.get("engine_version", "0.1.0"),
            "schema_version": report_data.get("schema_version", "1.0.0"),
            "config": report_data.get("config", {}),
            "report": report_data,
            "status": status,
        }
        self.client.table("runs").upsert(row).execute()

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve reconciliation report by run_id."""
        res = self.client.table("runs").select("report").eq("run_id", run_id).execute()
        data = cast("list[dict[str, Any]]", res.data)
        if data and len(data) > 0:
            rep = data[0].get("report")
            if isinstance(rep, dict):
                return cast("dict[str, Any]", rep)
        return None

    def save_sources(
        self,
        run_id: str,
        bank_txns: list[dict[str, Any]],
        payouts: list[dict[str, Any]],
        ledger_entries: list[dict[str, Any]],
    ) -> None:
        """Persist source records for a run in chunks.

        on_conflict targets the compound PK (run_id, entity_id) added by migration
        20260828174500, so a re-published seed run updates its own rows only and
        never overwrites another run's data.
        """
        # 1. Bank txns
        bank_rows = [{**b, "run_id": run_id} for b in bank_txns]
        for chunk in _chunk_list(bank_rows):
            self.client.table("source_bank").upsert(chunk, on_conflict="run_id,bank_id").execute()

        # 2. Payouts
        payout_rows = [{**p, "run_id": run_id} for p in payouts]
        for chunk in _chunk_list(payout_rows):
            self.client.table("source_payout").upsert(
                chunk, on_conflict="run_id,payout_id"
            ).execute()

        # 3. Ledger entries
        ledger_rows = [{**el, "run_id": run_id} for el in ledger_entries]
        for chunk in _chunk_list(ledger_rows):
            self.client.table("source_ledger").upsert(
                chunk, on_conflict="run_id,ledger_id"
            ).execute()

    def save_truth_groups(self, run_id: str, truth_groups: list[dict[str, Any]]) -> None:
        """Persist ground truth groups for a run."""
        rows = [{**tg, "run_id": run_id} for tg in truth_groups]
        for chunk in _chunk_list(rows):
            self.client.table("truth_groups").upsert(chunk, on_conflict="run_id,group_id").execute()

    def save_match_groups(self, run_id: str, match_groups: list[dict[str, Any]]) -> None:
        """Persist resolved match groups for a run."""
        rows = [{**mg, "run_id": run_id} for mg in match_groups]
        for chunk in _chunk_list(rows):
            self.client.table("match_groups").upsert(chunk, on_conflict="run_id,group_id").execute()

    def save_link_decisions(self, run_id: str, link_decisions: list[dict[str, Any]]) -> None:
        """Persist link-level decisions (TP, FP, FN, TN) for a run.

        link_decisions uses a BIGINT IDENTITY PK — no compound entity key to conflict
        on, so we use plain insert (each call produces genuinely new rows).
        """
        rows = [{**ld, "run_id": run_id} for ld in link_decisions]
        for chunk in _chunk_list(rows):
            self.client.table("link_decisions").insert(chunk).execute()

    def save_exceptions(self, run_id: str, exceptions: list[dict[str, Any]]) -> None:
        """Persist open/classified exception records for a run."""
        rows = [{**e, "run_id": run_id} for e in exceptions]
        for chunk in _chunk_list(rows):
            self.client.table("exceptions").upsert(
                chunk, on_conflict="run_id,exception_id"
            ).execute()

    def save_agent_calls(self, run_id: str, agent_calls: list[dict[str, Any]]) -> None:
        """Persist agent trace and telemetry records for a run."""
        rows = [{**ac, "run_id": run_id} for ac in agent_calls]
        for chunk in _chunk_list(rows):
            self.client.table("agent_calls").upsert(chunk, on_conflict="run_id,call_id").execute()

    def save_closures(self, run_id: str, closures: list[dict[str, Any]]) -> None:
        """Persist audit-grade closure journal entries for a run."""
        rows = [{**cl, "run_id": run_id} for cl in closures]
        for chunk in _chunk_list(rows):
            self.client.table("closures").upsert(chunk, on_conflict="run_id,closure_id").execute()

    def save_eval_sweeps(self, run_id: str, sweeps: list[dict[str, Any]]) -> None:
        """Persist sweep distribution rows for a run."""
        rows = [{**sw, "run_id": run_id} for sw in sweeps]
        for chunk in _chunk_list(rows):
            self.client.table("eval_sweeps").upsert(chunk).execute()

    def get_eval_sweeps(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve eval sweep rows for a run."""
        res = (
            self.client.table("eval_sweeps")
            .select("id, run_id, sweep_type, seed, seed_set, report, created_at")
            .eq("run_id", run_id)
            .order("seed")
            .execute()
        )
        return [dict(r) for r in cast("list[dict[str, Any]]", res.data or [])]

    def save_control_results(self, run_id: str, control_results: list[dict[str, Any]]) -> None:
        """Persist negative control verification results for a run."""
        rows = [{**cr, "run_id": run_id} for cr in control_results]
        for chunk in _chunk_list(rows):
            self.client.table("control_results").upsert(chunk).execute()

    def get_control_results(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve control results for a run."""
        res = (
            self.client.table("control_results")
            .select("control_name, passed, details")
            .eq("run_id", run_id)
            .execute()
        )
        return [dict(r) for r in cast("list[dict[str, Any]]", res.data or [])]

    def create_run_request(self, config: dict[str, Any]) -> int:
        """Create a new pending run request in the queue."""
        res = (
            self.client.table("run_requests")
            .insert({"config": config, "status": "pending"})
            .execute()
        )
        data = cast("list[dict[str, Any]]", res.data)
        if data and len(data) > 0:
            return int(data[0]["id"])
        return 0

    def claim_run_request(self, worker_id: str) -> dict[str, Any] | None:
        """Atomically claim the next pending run request in the queue."""
        # Find oldest pending request
        res = (
            self.client.table("run_requests")
            .select("id, config")
            .eq("status", "pending")
            .order("created_at")
            .limit(1)
            .execute()
        )
        data = cast("list[dict[str, Any]]", res.data)
        if not data or len(data) == 0:
            return None

        req_id = int(data[0]["id"])
        config = cast("dict[str, Any]", data[0]["config"])

        # Attempt to claim with optimistic concurrency
        upd = (
            self.client.table("run_requests")
            .update({"status": "claimed", "claimed_by": worker_id})
            .eq("id", req_id)
            .eq("status", "pending")
            .execute()
        )
        upd_data = cast("list[dict[str, Any]]", upd.data)
        if upd_data and len(upd_data) > 0:
            return {"id": req_id, "config": config}
        return None

    def update_run_request(
        self,
        req_id: int,
        status: str,
        result_run_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update status, result run ID, or error message of a run request."""
        payload: dict[str, Any] = {"status": status}
        if result_run_id is not None:
            payload["result_run_id"] = result_run_id
        if error_message is not None:
            payload["error_message"] = error_message
        self.client.table("run_requests").update(payload).eq("id", req_id).execute()

    def get_run_request(self, req_id: int) -> dict[str, Any] | None:
        """Retrieve run request by request ID."""
        res = (
            self.client.table("run_requests")
            .select("id, config, status, claimed_by, result_run_id, error_message")
            .eq("id", req_id)
            .execute()
        )
        data = cast("list[dict[str, Any]]", res.data)
        if data and len(data) > 0:
            return dict(data[0])
        return None

    def count_rows_for_run(self, run_id: str) -> dict[str, int]:
        """Count stored rows across tables for a run.

        Use select("*", count=CountMethod.exact) — PostgREST returns the row
        count in the response metadata (res.count).  The earlier select("count",
        ...) asked for a physical column named 'count' that does not exist in any
        table, which would raise a 400 from the live API.
        """
        tables = [
            "runs",
            "source_bank",
            "source_payout",
            "source_ledger",
            "truth_groups",
            "match_groups",
            "link_decisions",
            "exceptions",
            "agent_calls",
            "closures",
            "control_results",
        ]
        counts: dict[str, int] = {}
        for t in tables:
            res = (
                self.client.table(t)
                .select("*", count=CountMethod.exact)
                .eq("run_id", run_id)
                .execute()
            )
            counts[t] = res.count or 0
        return counts

    def dump_all(self) -> dict[str, list[dict[str, Any]]]:
        """Dump all tables for inspection."""
        tables = [
            "runs",
            "source_bank",
            "source_payout",
            "source_ledger",
            "truth_groups",
            "match_groups",
            "link_decisions",
            "exceptions",
            "agent_calls",
            "closures",
            "control_results",
        ]
        dump: dict[str, list[dict[str, Any]]] = {}
        for t in tables:
            res = self.client.table(t).select("*").limit(100).execute()
            dump[t] = [dict(r) for r in cast("list[dict[str, Any]]", res.data or [])]
        return dump
