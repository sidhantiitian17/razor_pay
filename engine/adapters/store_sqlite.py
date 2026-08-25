"""SQLite storage adapter implementing StoragePort for local persistence (§5.2, §6)."""

from __future__ import annotations

import json
import sqlite3
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class SQLiteStorageAdapter:
    """Thread-safe SQLite implementation of the persistence store."""

    def __init__(self, db_path: Path | str = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            from pathlib import Path

            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    engine_version TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    config TEXT NOT NULL,
                    report TEXT NOT NULL,
                    status TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_bank (
                    bank_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    posted_at TEXT NOT NULL,
                    value_date TEXT NOT NULL,
                    amount_paise INTEGER NOT NULL,
                    utr TEXT,
                    narration TEXT NOT NULL,
                    currency TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_payout (
                    payout_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    settled_at TEXT,
                    amount_paise INTEGER NOT NULL,
                    fee_paise INTEGER NOT NULL,
                    tax_paise INTEGER NOT NULL,
                    utr TEXT,
                    status TEXT NOT NULL,
                    currency TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS source_ledger (
                    ledger_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    journal_id TEXT NOT NULL,
                    entry_date TEXT NOT NULL,
                    amount_paise INTEGER NOT NULL,
                    account TEXT NOT NULL,
                    reference TEXT NOT NULL,
                    currency TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS truth_groups (
                    group_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    cohort TEXT NOT NULL,
                    bank_ids TEXT NOT NULL,
                    payout_ids TEXT NOT NULL,
                    ledger_ids TEXT NOT NULL,
                    expected_outcome TEXT NOT NULL,
                    expected_tag TEXT,
                    expected_bucket TEXT
                );

                CREATE TABLE IF NOT EXISTS match_groups (
                    group_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    bank_ids TEXT NOT NULL,
                    payout_ids TEXT NOT NULL,
                    ledger_ids TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT NOT NULL,
                    fields_matched TEXT NOT NULL,
                    tolerances_used TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    agent_turns INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS link_decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    link_type TEXT NOT NULL,
                    left_id TEXT NOT NULL,
                    right_id TEXT NOT NULL,
                    predicted INTEGER NOT NULL,
                    truth INTEGER NOT NULL,
                    outcome TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS exceptions (
                    exception_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    row_ids TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    proposed_action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    assignee TEXT,
                    resolution_note TEXT
                );

                CREATE TABLE IF NOT EXISTS agent_calls (
                    call_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    turns INTEGER NOT NULL,
                    tools_used TEXT NOT NULL,
                    tokens_in INTEGER NOT NULL,
                    tokens_out INTEGER NOT NULL,
                    cost_usd REAL NOT NULL,
                    latency_ms INTEGER NOT NULL,
                    prompt_redacted TEXT NOT NULL,
                    response TEXT NOT NULL,
                    guardrail_verdict TEXT NOT NULL,
                    guardrail_reasons TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS closures (
                    closure_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    action TEXT NOT NULL,
                    before_state TEXT NOT NULL,
                    after_state TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    reversed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS control_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    control_name TEXT NOT NULL,
                    passed INTEGER NOT NULL,
                    details TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS run_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    claimed_by TEXT,
                    claimed_at TEXT,
                    result_run_id TEXT,
                    error_message TEXT
                );
                """
            )

    def save_run(
        self,
        run_id: str,
        report_data: dict[str, Any],
        status: str = "complete",
    ) -> None:
        """Persist or update reconciliation run and report JSON."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                    run_id, engine_version, schema_version, config, report, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    str(report_data.get("engine_version", "0.1.0")),
                    str(report_data.get("schema_version", "1.0.0")),
                    json.dumps(report_data.get("config", {})),
                    json.dumps(report_data),
                    status,
                ),
            )

    def load_run(self, run_id: str) -> dict[str, Any] | None:
        """Retrieve reconciliation report by run_id."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("SELECT report FROM runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if row:
                return json.loads(row["report"])  # type: ignore[no-any-return]
            return None

    def save_sources(
        self,
        run_id: str,
        bank_txns: list[dict[str, Any]],
        payouts: list[dict[str, Any]],
        ledger_entries: list[dict[str, Any]],
    ) -> None:
        """Persist source records for a run."""
        with self._lock, self._conn:
            for b in bank_txns:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO source_bank (
                        bank_id, run_id, posted_at, value_date,
                        amount_paise, utr, narration, currency
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(b["bank_id"]),
                        run_id,
                        str(b.get("posted_at", "")),
                        str(b.get("value_date", "")),
                        int(b["amount_paise"]),
                        b.get("utr"),
                        str(b.get("narration", "")),
                        str(b.get("currency", "INR")),
                    ),
                )
            for p in payouts:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO source_payout (
                        payout_id, run_id, created_at, settled_at,
                        amount_paise, fee_paise, tax_paise, utr, status, currency
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(p["payout_id"]),
                        run_id,
                        str(p.get("created_at", "")),
                        str(p.get("settled_at")) if p.get("settled_at") else None,
                        int(p["amount_paise"]),
                        int(p.get("fee_paise", 0)),
                        int(p.get("tax_paise", 0)),
                        p.get("utr"),
                        str(p.get("status", "processed")),
                        str(p.get("currency", "INR")),
                    ),
                )
            for el in ledger_entries:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO source_ledger (
                        ledger_id, run_id, journal_id, entry_date,
                        amount_paise, account, reference, currency
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(el["ledger_id"]),
                        run_id,
                        str(el.get("journal_id", "")),
                        str(el.get("entry_date", "")),
                        int(el["amount_paise"]),
                        str(el.get("account", "bank")),
                        str(el.get("reference", "")),
                        str(el.get("currency", "INR")),
                    ),
                )

    def save_truth_groups(self, run_id: str, truth_groups: list[dict[str, Any]]) -> None:
        """Persist ground truth groups for a run."""
        with self._lock, self._conn:
            for tg in truth_groups:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO truth_groups (
                        group_id, run_id, kind, cohort, bank_ids,
                        payout_ids, ledger_ids, expected_outcome, expected_tag, expected_bucket
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(tg["group_id"]),
                        run_id,
                        str(tg.get("kind", "")),
                        str(tg.get("cohort", "")),
                        json.dumps(tg.get("bank_ids", [])),
                        json.dumps(tg.get("payout_ids", [])),
                        json.dumps(tg.get("ledger_ids", [])),
                        str(tg.get("expected_outcome", "resolved")),
                        tg.get("expected_tag"),
                        tg.get("expected_bucket"),
                    ),
                )

    def save_match_groups(self, run_id: str, match_groups: list[dict[str, Any]]) -> None:
        """Persist resolved match groups for a run."""
        with self._lock, self._conn:
            for mg in match_groups:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO match_groups (
                        group_id, run_id, kind, bank_ids, payout_ids, ledger_ids,
                        confidence, source, fields_matched, tolerances_used,
                        tag, reason, agent_turns
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(mg["group_id"]),
                        run_id,
                        str(mg.get("kind", "")),
                        json.dumps(mg.get("bank_ids", [])),
                        json.dumps(mg.get("payout_ids", [])),
                        json.dumps(mg.get("ledger_ids", [])),
                        float(mg.get("confidence", 1.0)),
                        str(mg.get("source", "deterministic")),
                        json.dumps(mg.get("fields_matched", [])),
                        json.dumps(mg.get("tolerances_used", [])),
                        str(mg.get("tag", "")),
                        str(mg.get("reason", "")),
                        int(mg.get("agent_turns", 0)),
                    ),
                )

    def save_link_decisions(self, run_id: str, link_decisions: list[dict[str, Any]]) -> None:
        """Persist link-level decisions for a run."""
        with self._lock, self._conn:
            for ld in link_decisions:
                self._conn.execute(
                    """
                    INSERT INTO link_decisions (
                        run_id, link_type, left_id, right_id, predicted, truth, outcome
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        str(ld["link_type"]),
                        str(ld["left_id"]),
                        str(ld["right_id"]),
                        1 if ld["predicted"] else 0,
                        1 if ld["truth"] else 0,
                        str(ld["outcome"]),
                    ),
                )

    def save_exceptions(self, run_id: str, exceptions: list[dict[str, Any]]) -> None:
        """Persist open exception records for a run."""
        with self._lock, self._conn:
            for exc in exceptions:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO exceptions (
                        exception_id, run_id, row_ids, bucket, severity,
                        evidence, proposed_action, status, assignee, resolution_note
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(exc["exception_id"]),
                        run_id,
                        json.dumps(exc.get("row_ids", [])),
                        str(exc.get("bucket", "")),
                        str(exc.get("severity", "medium")),
                        json.dumps(exc.get("evidence", [])),
                        str(exc.get("proposed_action", "")),
                        str(exc.get("status", "open")),
                        exc.get("assignee"),
                        exc.get("resolution_note"),
                    ),
                )

    def save_agent_calls(self, run_id: str, agent_calls: list[dict[str, Any]]) -> None:
        """Persist agent trace and telemetry records for a run."""
        with self._lock, self._conn:
            for call in agent_calls:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_calls (
                        call_id, run_id, seq, turns, tools_used, tokens_in, tokens_out,
                        cost_usd, latency_ms, prompt_redacted, response,
                        guardrail_verdict, guardrail_reasons
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(call["call_id"]),
                        run_id,
                        int(call.get("seq", 0)),
                        int(call.get("turns", 0)),
                        json.dumps(call.get("tools_used", [])),
                        int(call.get("tokens_in", 0)),
                        int(call.get("tokens_out", 0)),
                        float(call.get("cost_usd", 0.0)),
                        int(call.get("latency_ms", 0)),
                        json.dumps(call.get("prompt_redacted", {})),
                        json.dumps(call.get("response", {})),
                        str(call.get("guardrail_verdict", "accepted")),
                        json.dumps(call.get("guardrail_reasons", [])),
                    ),
                )

    def save_closures(self, run_id: str, closures: list[dict[str, Any]]) -> None:
        """Persist audit-grade closure journal entries for a run."""
        with self._lock, self._conn:
            for cl in closures:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO closures (
                        closure_id, run_id, target, action, before_state,
                        after_state, applied_at, reversed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(cl["closure_id"]),
                        run_id,
                        str(cl.get("target", "")),
                        str(cl.get("action", "")),
                        json.dumps(cl.get("before", {})),
                        json.dumps(cl.get("after", {})),
                        str(cl.get("applied_at", "")),
                        cl.get("reversed_at"),
                    ),
                )

    def save_control_results(self, run_id: str, control_results: list[dict[str, Any]]) -> None:
        """Persist negative control verification results for a run."""
        with self._lock, self._conn:
            for cr in control_results:
                self._conn.execute(
                    """
                    INSERT INTO control_results (run_id, control_name, passed, details)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        str(cr["control_name"]),
                        1 if cr["passed"] else 0,
                        json.dumps(cr.get("details", {})),
                    ),
                )

    def get_control_results(self, run_id: str) -> list[dict[str, Any]]:
        """Retrieve control results for a run."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "SELECT control_name, passed, details FROM control_results WHERE run_id = ?",
                (run_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "control_name": r["control_name"],
                    "passed": bool(r["passed"]),
                    "details": json.loads(r["details"]),
                }
                for r in rows
            ]

    def create_run_request(self, config: dict[str, Any]) -> int:
        """Create a new pending run request in the queue."""
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute(
                "INSERT INTO run_requests (config, status) VALUES (?, 'pending')",
                (json.dumps(config),),
            )
            last_id = cur.lastrowid
            return int(last_id) if last_id is not None else 0

    def claim_run_request(self, worker_id: str) -> dict[str, Any] | None:
        """Atomically claim the next pending run request in the queue."""
        with self._lock, self._conn:
            cur = self._conn.cursor()
            cur.execute("SELECT id, config FROM run_requests WHERE status = 'pending' LIMIT 1")
            row = cur.fetchone()
            if not row:
                return None
            req_id = row["id"]
            cur.execute(
                """
                UPDATE run_requests
                SET status = 'claimed', claimed_by = ?
                WHERE id = ? AND status = 'pending'
                """,
                (worker_id, req_id),
            )
            if cur.rowcount > 0:
                return {"id": req_id, "config": json.loads(row["config"])}
            return None

    def update_run_request(
        self,
        req_id: int,
        status: str,
        result_run_id: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Update status, result run ID, or error message of a run request."""
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE run_requests
                SET status = ?, result_run_id = coalesce(?, result_run_id), error_message = ?
                WHERE id = ?
                """,
                (status, result_run_id, error_message, req_id),
            )

    def get_run_request(self, req_id: int) -> dict[str, Any] | None:
        """Retrieve run request by request ID."""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                """
                SELECT id, config, status, claimed_by, result_run_id, error_message
                FROM run_requests WHERE id = ?
                """,
                (req_id,),
            )
            row = cur.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "config": json.loads(row["config"]),
                    "status": row["status"],
                    "claimed_by": row["claimed_by"],
                    "result_run_id": row["result_run_id"],
                    "error_message": row["error_message"],
                }
            return None

    def dump_all(self) -> dict[str, list[dict[str, Any]]]:
        """Dump all in-memory tables for verification and inspection."""
        with self._lock:
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
            result: dict[str, list[dict[str, Any]]] = {}
            for t in tables:
                cur = self._conn.cursor()
                cur.execute(f"SELECT * FROM {t}")
                result[t] = [dict(r) for r in cur.fetchall()]
            return result

    def count_rows_for_run(self, run_id: str) -> dict[str, int]:
        """Count stored rows across tables for a run."""
        with self._lock:
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
                cur = self._conn.cursor()
                cur.execute(f"SELECT count(*) as c FROM {t} WHERE run_id = ?", (run_id,))
                counts[t] = cur.fetchone()["c"]
            return counts
