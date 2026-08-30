"""Tests for golden report regression and replay stability (§4.4, check 5.10)."""

import json
import os

from engine.app.reporter import ReportGenerator
from engine.core.generator.build import generate_dataset


def test_golden_report_replay() -> None:
    """Check 5.10: Golden report byte-identical under deterministic replay (seed=42)."""
    dataset1 = generate_dataset(n=60, seed=42)
    gen1 = ReportGenerator()
    report1 = gen1.generate_report(
        dataset=dataset1,
        measurement_mode="replay",
        mode="rules_only",
        seed_set="dev",
        seeds=[42],
        dry_run=False,
    )

    dataset2 = generate_dataset(n=60, seed=42)
    gen2 = ReportGenerator()
    report2 = gen2.generate_report(
        dataset=dataset2,
        measurement_mode="replay",
        mode="rules_only",
        seed_set="dev",
        seeds=[42],
        dry_run=False,
    )

    # Normalize dynamic UUIDs and wall-clock timings before comparing byte identity
    for r in [report1, report2]:
        r["run_id"] = "00000000-0000-0000-0000-000000000000"
        tp = r["throughput"]
        assert isinstance(tp, dict)
        tp["wall_clock_seconds_median"] = 1.0
        stage_sec = tp["stage_seconds"]
        assert isinstance(stage_sec, dict)
        tp["stage_seconds"] = {k: 0.1 for k in stage_sec}
        tp["rows_per_second_end_to_end"] = {"value": 100.0, "numerator": 100, "denominator": 1.0}
        tp["residuals_per_second_agent_path"] = {
            "value": 10.0,
            "numerator": 10,
            "denominator": 1.0,
        }

    s1 = json.dumps(report1, sort_keys=True, indent=2)
    s2 = json.dumps(report2, sort_keys=True, indent=2)
    assert s1 == s2


def test_heuristic_agent_derives_real_row_id_not_hardcoded_fallback() -> None:
    """Regression: HeuristicLLMClient must resolve the row it was actually asked about.

    Before this fix, the derivation loop looked for an `arguments` key
    directly on each transcript message (a key that never existed at that
    level, since `agent.py` never recorded the assistant's own tool_use
    turns), so it always fell through to a hardcoded
    "BNK-00000001"/"PO-00000001" fallback and every proposal was rejected as
    hallucinated_id — silently zeroing out the agent's contribution.
    """
    from engine.adapters.llm_heuristic import HeuristicLLMClient
    from engine.app.agent import AgentRunner
    from engine.core.generator.build import generate_dataset
    from engine.core.guardrail import GuardrailConfig
    from engine.core.matching.blocker import build_candidate_space
    from engine.core.matching.rules import DeterministicMatcher

    dataset = generate_dataset(n=100, seed=42)
    space = build_candidate_space(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    matched = DeterministicMatcher().match(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    matched_bank_ids = {bid for mg in matched.matched_groups for bid in mg.bank_ids}
    unmatched = [b for b in dataset.bank_txns if b.bank_id not in matched_bank_ids]
    assert unmatched, "fixture must have at least one residual to exercise the agent"

    runner = AgentRunner(
        llm_client=HeuristicLLMClient(),
        guardrail_config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        max_turns=6,
    )

    reject_reasons: set[str] = set()
    accepted_count = 0
    for b in unmatched:
        result = runner.resolve_residual(
            row_id=b.bank_id,
            bank_txns=dataset.bank_txns,
            gateway_payouts=dataset.gateway_payouts,
            ledger_entries=dataset.ledger_entries,
            candidate_space=space,
        )
        if result.accepted:
            accepted_count += 1
            assert result.proposed_group is not None
            # The proposal must reference the row actually being resolved,
            # never a hardcoded, unrelated literal id.
            assert b.bank_id in result.proposed_group.bank_ids
        else:
            reject_reasons.update(result.guardrail_reasons)

    # The old bug rejected 100% of proposals as hallucinated_id, every time,
    # regardless of the dataset. That specific total-failure signature must
    # not recur.
    assert not (reject_reasons == {"hallucinated_id"} and accepted_count == 0), (
        "heuristic agent rejected every residual as hallucinated_id — "
        "this is the pre-fix silent-failure signature"
    )


def test_heuristic_agent_proposes_verified_ledger_journal() -> None:
    """The agent must resolve the ledger side, not just bank<->payout.

    On any residual whose payout has a clean, balanced journal reachable in
    the candidate space, the accepted proposal must carry that journal's
    ledger ids (every entry keyed on `reference == payout_id`, netting to
    zero) — never an empty ledger list. This is what lets a residual the
    agent resolves register as an exact 3-way match rather than a
    bank<->payout-only link.
    """
    from engine.adapters.llm_heuristic import HeuristicLLMClient
    from engine.app.agent import AgentRunner
    from engine.core.generator.build import generate_dataset
    from engine.core.guardrail import GuardrailConfig
    from engine.core.matching.blocker import build_candidate_space
    from engine.core.matching.rules import DeterministicMatcher

    dataset = generate_dataset(n=100, seed=1)
    space = build_candidate_space(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    matched = DeterministicMatcher().match(
        dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries
    )
    matched_bank_ids = {bid for mg in matched.matched_groups for bid in mg.bank_ids}
    ledger_by_id = {e.ledger_id: e for e in dataset.ledger_entries}

    runner = AgentRunner(
        llm_client=HeuristicLLMClient(),
        guardrail_config=GuardrailConfig(min_confidence=0.70, min_fields=2),
        max_turns=6,
    )

    proposals_with_ledger = 0
    for b in dataset.bank_txns:
        if b.bank_id in matched_bank_ids:
            continue
        result = runner.resolve_residual(
            row_id=b.bank_id,
            bank_txns=dataset.bank_txns,
            gateway_payouts=dataset.gateway_payouts,
            ledger_entries=dataset.ledger_entries,
            candidate_space=space,
        )
        group = result.proposed_group
        if group is None or not group.ledger_ids:
            continue
        proposals_with_ledger += 1
        payout_id = group.payout_ids[0]
        entries = [ledger_by_id[lid] for lid in group.ledger_ids]
        # Genuine, truth-free invariants the proposal must satisfy.
        assert all(e.reference == payout_id for e in entries)
        assert sum(e.amount_paise for e in entries) == 0
        assert "ledger_journal" in group.fields_matched

    assert proposals_with_ledger > 0, (
        "agent never proposed any ledger ids — the ledger side is still unresolved"
    )


def test_ablation_arms_are_genuinely_recomputed_not_hardcoded() -> None:
    """Regression: every ablation arm must reflect this run's own dataset/seed.

    Before this fix, three of the four arms in `ablation` were hardcoded
    constants (0.70/0.98, 0.65/0.92, 0.01) regardless of the seed, while the
    UI caption claimed every arm "reruns the same seeded dataset with a
    different matcher configuration." This asserts the arm NOT matching the
    requested mode is not simply the old fixed constant for at least one of
    two differently-seeded runs — proving it was actually recomputed.
    """
    from engine.core.generator.build import generate_dataset

    old_hardcoded = {
        "rules_only": (0.70, 0.98),
        "agent_only": (0.65, 0.92),
        "rules_agent": (0.78, 0.96),
    }

    saw_a_genuine_recompute = False
    for seed in (7, 42, 101):
        dataset = generate_dataset(n=60, seed=seed)
        gen = ReportGenerator()
        report = gen.generate_report(
            dataset=dataset,
            mode="rules_only",
            seed=seed,
            seed_set="dev" if seed < 100 else "holdout",
            dry_run=True,
        )
        ablation = report["ablation"]
        assert isinstance(ablation, dict)
        for arm_name in ("agent_only", "rules_agent"):
            arm = ablation[arm_name]
            fixed_mr, fixed_p = old_hardcoded[arm_name]
            if arm["match_rate"] != fixed_mr or arm["precision"] != fixed_p:
                saw_a_genuine_recompute = True

    assert saw_a_genuine_recompute, (
        "every non-primary ablation arm exactly matched the old hardcoded "
        "constants across all seeds tried — ablation may be fabricated again"
    )


def test_agent_backend_disclosed_and_never_silently_swapped() -> None:
    """Regression: `config.agent_backend` must always say which backend ran.

    "none" when no agent was invoked, "heuristic" for the offline simulator
    (the default with no ANTHROPIC_API_KEY configured) — never omitted.
    """
    from engine.core.generator.build import generate_dataset

    dataset = generate_dataset(n=60, seed=42)

    rules_only_report = ReportGenerator().generate_report(
        dataset=dataset, mode="rules_only", seed=42, seed_set="dev", dry_run=True
    )
    config = rules_only_report["config"]
    assert isinstance(config, dict)
    assert config["agent_backend"] == "none"

    agent_report = ReportGenerator().generate_report(
        dataset=dataset, mode="rules_agent", seed=42, seed_set="dev", dry_run=True
    )
    config2 = agent_report["config"]
    assert isinstance(config2, dict)
    assert config2["agent_backend"] in ("live", "heuristic")


def test_agent_arm_is_deterministic_across_hash_seeds() -> None:
    """Regression: the agent path must give the same number on every process.

    `fetch_candidates` used to iterate `candidate_space` sets directly, whose
    order for string tuples depends on PYTHONHASHSEED (randomised per
    process). That made `agent_only` / `rules_agent` match_rate wander run to
    run. Run the same seed in fresh subprocesses with different explicit hash
    seeds and require an identical result.
    """
    import subprocess
    import sys

    snippet = (
        "from engine.core.generator.build import generate_dataset;"
        "from engine.app.reporter import ReportGenerator;"
        "r=ReportGenerator().generate_report("
        "dataset=generate_dataset(n=100,seed=114),mode='agent_only',seed=114,"
        "seed_set='holdout',seeds=[114],fast=True);"
        "print(r['accuracy']['match_rate']['value'])"
    )

    results = []
    for hashseed in ("0", "1", "random"):
        env = {**os.environ, "PYTHONHASHSEED": hashseed}
        out = subprocess.run(
            [sys.executable, "-c", snippet],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        results.append(out.stdout.strip())

    assert len(set(results)) == 1, (
        f"agent_only match_rate differs across PYTHONHASHSEED values: {results}"
    )
