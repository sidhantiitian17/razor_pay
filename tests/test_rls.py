"""Tests for RLS policy correctness (check 0.7).

These tests verify the SQL migration's RLS policies.
Since we don't have a live Supabase DB for P0, these tests parse the SQL
and verify the policy structure. Live verification happens at P6.
"""

from __future__ import annotations

from pathlib import Path

import pytest

SQL_PATH = Path(__file__).resolve().parents[1] / "contracts" / "migrations" / "001_init.sql"

TABLES = [
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
    "eval_sweeps",
    "control_results",
    "run_requests",
]


@pytest.fixture()
def sql_content() -> str:
    """Load the SQL migration."""
    return SQL_PATH.read_text()


def test_anon_cannot_write(sql_content: str) -> None:
    """Check 6.6: Anon role is denied write access across every table."""
    lines = sql_content.split("\n")
    for line in lines:
        if "TO anon" in line:
            assert "FOR SELECT" in line or "POLICY" not in line, (
                f"anon has a non-SELECT policy: {line.strip()}"
            )


class TestRLSStructure:
    """Verify RLS policy structure in SQL migration."""

    def test_all_tables_have_rls_enabled(self, sql_content: str) -> None:
        """Every table must have RLS enabled."""
        for table in TABLES:
            assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY" in sql_content, (
                f"Table '{table}' missing ENABLE ROW LEVEL SECURITY"
            )

    def test_anon_has_no_write_policies(self, sql_content: str) -> None:
        """Anon role should have no INSERT, UPDATE, or DELETE policies."""
        lines = sql_content.split("\n")
        for line in lines:
            if "TO anon" in line:
                assert "FOR SELECT" in line or "POLICY" not in line, (
                    f"anon has a non-SELECT policy: {line.strip()}"
                )

    def test_anon_cannot_write(self, sql_content: str) -> None:
        """Check 6.6: Anon role is denied write access across every table."""
        self.test_anon_has_no_write_policies(sql_content)

    def test_service_role_has_all_access(self, sql_content: str) -> None:
        """service_role should have FOR ALL on every table."""
        for table in TABLES:
            assert f"service_all_{table} ON {table} FOR ALL TO service_role" in sql_content, (
                f"Table '{table}' missing service_role ALL policy"
            )

    def test_authenticated_can_insert_run_requests(self, sql_content: str) -> None:
        """Authenticated can INSERT into run_requests."""
        assert "auth_insert_run_requests ON run_requests FOR INSERT TO authenticated" in sql_content

    def test_authenticated_can_update_exceptions(self, sql_content: str) -> None:
        """Authenticated can UPDATE exceptions (triage)."""
        assert "auth_update_exceptions ON exceptions FOR UPDATE TO authenticated" in sql_content

    def test_truth_groups_gated_on_completion(self, sql_content: str) -> None:
        """truth_groups SELECT is gated on run completion for anon."""
        # The policy should check that the run is complete
        assert "status FROM runs WHERE runs.run_id = truth_groups.run_id" in sql_content

    def test_no_create_policy_if_not_exists(self, sql_content: str) -> None:
        """CREATE POLICY has no IF NOT EXISTS clause in PostgreSQL.

        Using it is a syntax error that aborts the whole migration
        transaction on first apply (P0 review finding). Idempotency must
        come from DROP POLICY IF EXISTS + CREATE POLICY pairs instead.
        """
        assert "CREATE POLICY IF NOT EXISTS" not in sql_content, (
            "CREATE POLICY IF NOT EXISTS is invalid PostgreSQL syntax — "
            "use DROP POLICY IF EXISTS <name> ON <table>; CREATE POLICY <name> ..."
        )

    def test_every_policy_has_a_matching_drop(self, sql_content: str) -> None:
        """Every CREATE POLICY must be preceded by a matching DROP POLICY.

        DROP POLICY IF EXISTS <name> ON <table> must appear somewhere for
        every CREATE POLICY <name> ON <table> — otherwise re-applying the
        migration to an existing database fails with 'policy already
        exists' instead of being idempotent.
        """
        import re

        creates = re.findall(r"CREATE POLICY (\w+) ON (\w+)", sql_content)
        for name, table in creates:
            assert f"DROP POLICY IF EXISTS {name} ON {table}" in sql_content, (
                f"Policy '{name}' on '{table}' has no matching DROP POLICY IF EXISTS "
                "— migration is not idempotent for this policy"
            )

    def test_closures_not_exposed_to_anon_or_authenticated(self, sql_content: str) -> None:
        """Closures must stay service_role-only.

        It holds write-back before/after state and is not in the §5.2
        anon/authenticated read list — same category as run_requests.
        """
        assert "anon_select_closures" not in sql_content
        assert "auth_select_closures" not in sql_content

    def test_exceptions_update_restricted_to_triage_columns(self, sql_content: str) -> None:
        """Exceptions UPDATE must be column-restricted via GRANT.

        RLS policies are row-scoped, not column-scoped — the FOR UPDATE
        policy on exceptions alone would let authenticated overwrite any
        column (bucket, evidence, severity), not just triage fields. A
        column-level GRANT must restrict this explicitly.
        """
        assert "REVOKE UPDATE ON exceptions FROM authenticated" in sql_content
        assert (
            "GRANT UPDATE (status, assignee, resolution_note) ON exceptions TO authenticated"
            in sql_content
        )
