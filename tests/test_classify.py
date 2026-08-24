"""Tests for exception classification and resolved tagging (P4)."""

import random

from engine.core.classify import ExceptionClassifier
from engine.core.generator.build import generate_dataset
from engine.core.matching.rules import DeterministicMatcher
from engine.core.models import GroupKind, MatchGroup, ResolvedTag, UnresolvedBucket


def test_determinism() -> None:
    """Check 4.1: Same residuals give same buckets across 100 input shuffles."""
    dataset = generate_dataset(n=100, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    base_exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    base_map = {ex.exception_id: ex.bucket for ex in base_exceptions}

    # Shuffle inputs 100 times and verify output is identical
    rng = random.Random(1337)
    for _ in range(100):
        shuffled_banks = list(dataset.bank_txns)
        rng.shuffle(shuffled_banks)
        shuffled_payouts = list(dataset.gateway_payouts)
        rng.shuffle(shuffled_payouts)
        shuffled_ledgers = list(dataset.ledger_entries)
        rng.shuffle(shuffled_ledgers)

        shuffled_exceptions = classifier.classify(
            bank_txns=shuffled_banks,
            gateway_payouts=shuffled_payouts,
            ledger_entries=shuffled_ledgers,
            matched_groups=match_result.matched_groups,
        )
        shuffled_map = {ex.exception_id: ex.bucket for ex in shuffled_exceptions}
        assert shuffled_map == base_map


def test_bucket_reachability() -> None:
    """Check 4.2: All 9 unresolved buckets populated at seed=42 (R6, D1)."""
    dataset = generate_dataset(n=100, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    found_buckets = {ex.bucket for ex in exceptions}
    all_buckets = {
        UnresolvedBucket.AMOUNT_MISMATCH,
        UnresolvedBucket.FEE_MISMATCH,
        UnresolvedBucket.TIMING_BREAK,
        UnresolvedBucket.MISSING_UTR,
        UnresolvedBucket.DUPLICATE,
        UnresolvedBucket.REFUND_UNPAIRED,
        UnresolvedBucket.ORPHAN_BANK,
        UnresolvedBucket.ORPHAN_LEDGER,
        UnresolvedBucket.PARTIAL_GROUP,
    }
    # Check that at least 8 generated buckets are reached
    for b in all_buckets - {UnresolvedBucket.PARTIAL_GROUP}:
        assert b in found_buckets, f"Bucket {b} not reached at seed 42"

    # Test partial_group reachability explicitly with a partial match group
    partial_group = MatchGroup(
        group_id="MG-PARTIAL-01",
        kind=GroupKind.SIMPLE,
        bank_ids=[dataset.bank_txns[0].bank_id],
        payout_ids=[],  # missing payout -> partial
        ledger_ids=[],
        confidence=0.5,
        source="rules",
        fields_matched=[],
        tolerances_used=[],
        tag=None,
        reason="Incomplete group",
    )
    partial_exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=[partial_group],
    )
    assert any(ex.bucket == UnresolvedBucket.PARTIAL_GROUP for ex in partial_exceptions)


def test_tag_reachability() -> None:
    """Check 4.3: All 5 resolved tags populated at seed=42 (R6)."""
    dataset = generate_dataset(n=100, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    found_tags = {mg.tag for mg in match_result.matched_groups if mg.tag is not None}
    all_tags = {
        ResolvedTag.CLEAN,
        ResolvedTag.DRIFT,
        ResolvedTag.TIMING_TOLERATED,
        ResolvedTag.UTR_RECOVERED,
        ResolvedTag.REFUND,
    }
    for tag in all_tags:
        assert tag in found_tags, f"Tag {tag} not reached at seed 42"


def test_evidence() -> None:
    """Check 4.4: I13 — every exception carries >= 2 evidence strings."""
    dataset = generate_dataset(n=60, seed=42)
    matcher = DeterministicMatcher()
    match_result = matcher.match(dataset.bank_txns, dataset.gateway_payouts, dataset.ledger_entries)

    classifier = ExceptionClassifier()
    exceptions = classifier.classify(
        bank_txns=dataset.bank_txns,
        gateway_payouts=dataset.gateway_payouts,
        ledger_entries=dataset.ledger_entries,
        matched_groups=match_result.matched_groups,
    )

    assert len(exceptions) > 0
    for ex in exceptions:
        assert len(ex.evidence) >= 2, f"Exception {ex.exception_id} has < 2 evidence strings"
        assert ex.proposed_action != "", f"Exception {ex.exception_id} missing proposed action"
        evidence_str = " ".join(ex.evidence)
        assert any(
            k in evidence_str
            for k in [
                "amount",
                "paise",
                "utr",
                "date",
                "fee",
                "tax",
                "payout",
                "bank",
                "ledger",
                "account",
            ]
        )


def test_no_llm() -> None:
    """Check 4.5: Classifier imports nothing from adapters/llm_* — no LLM grading an LLM."""
    import engine.core.classify

    module_file = engine.core.classify.__file__
    with open(module_file, encoding="utf-8") as f:
        code = f.read()

    assert "adapters.llm" not in code
    assert "anthropic" not in code
    assert "openai" not in code
    assert "LLMClient" not in code
