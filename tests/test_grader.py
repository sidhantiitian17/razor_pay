"""Tests for truth link grader and isolation (§4.1, §6, R8, D6, checks 5.2, 5.16)."""

import pytest
from engine.core.grader import LinkGrader
from engine.core.models import (
    GroupKind,
    MatchGroup,
    ResolvedTag,
    TruthLink,
)


def test_hand_computed() -> None:
    """Check 5.2: 12-row hand fixture with confusion matrix matches grader (R8, D6)."""
    # 3 bank txns, 3 payouts, 6 ledger entries = 12 source rows
    # Hand-crafted truth links:
    # (BNK-01, POUT-01): TRUE
    # (BNK-02, POUT-02): TRUE
    # (BNK-03, POUT-03): TRUE
    truth_links = [
        TruthLink(link_type="bank_payout", left_id="BNK-01", right_id="POUT-01", is_match=True),
        TruthLink(link_type="bank_payout", left_id="BNK-02", right_id="POUT-02", is_match=True),
        TruthLink(link_type="bank_payout", left_id="BNK-03", right_id="POUT-03", is_match=True),
        TruthLink(link_type="bank_payout", left_id="BNK-01", right_id="POUT-02", is_match=False),
        TruthLink(link_type="bank_payout", left_id="BNK-02", right_id="POUT-01", is_match=False),
        TruthLink(link_type="bank_payout", left_id="BNK-03", right_id="POUT-02", is_match=False),
    ]

    # Candidate space pairs
    candidate_pairs = [
        ("BNK-01", "POUT-01"),  # TP
        ("BNK-02", "POUT-01"),  # FP (predicted match, truth false)
        ("BNK-03", "POUT-03"),  # FN (not predicted, truth true)
        ("BNK-01", "POUT-02"),  # TN (not predicted, truth false)
    ]

    # Predicted match groups:
    # 1. Matches BNK-01 with POUT-01 (TP)
    # 2. Matches BNK-02 with POUT-01 (FP)
    # BNK-03 is not predicted (FN)
    predicted_groups = [
        MatchGroup(
            group_id="MG-01",
            kind=GroupKind.SIMPLE,
            bank_ids=["BNK-01"],
            payout_ids=["POUT-01"],
            ledger_ids=["LED-01", "LED-02"],
            confidence=1.0,
            source="deterministic",
            fields_matched=["utr"],
            tolerances_used=[],
            tag=ResolvedTag.CLEAN,
            reason="Exact UTR match",
            agent_turns=0,
        ),
        MatchGroup(
            group_id="MG-02",
            kind=GroupKind.SIMPLE,
            bank_ids=["BNK-02"],
            payout_ids=["POUT-01"],
            ledger_ids=["LED-01", "LED-02"],
            confidence=0.8,
            source="deterministic",
            fields_matched=[],
            tolerances_used=[],
            tag=ResolvedTag.CLEAN,
            reason="Incorrect match",
            agent_turns=0,
        ),
    ]

    grader = LinkGrader()
    decisions = grader.grade(
        link_type="bank_payout",
        candidate_pairs=candidate_pairs,
        predicted_groups=predicted_groups,
        truth_links=truth_links,
    )

    outcomes = {f"{d.left_id}->{d.right_id}": d.outcome for d in decisions}
    assert outcomes["BNK-01->POUT-01"] == "TP"
    assert outcomes["BNK-02->POUT-01"] == "FP"
    assert outcomes["BNK-03->POUT-03"] == "FN"
    assert outcomes["BNK-01->POUT-02"] == "TN"

    matrix = grader.confusion_matrix(decisions)
    assert matrix["tp"] == 1
    assert matrix["fp"] == 1
    assert matrix["fn"] == 1
    assert matrix["tn"] == 1


def test_isolation() -> None:
    """Check 5.16: grader.py shares no import with matching/ or agent.py."""
    import engine.core.grader

    module_file = engine.core.grader.__file__
    with open(module_file, encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip().startswith(("import", "from"))]

    for line in lines:
        assert "matching" not in line
        assert "rules" not in line
        assert "blocker" not in line
        assert "agent" not in line


def test_payout_ledger_grading() -> None:
    """Grader correctly grades payout_ledger links with TP, FP, FN, TN."""
    truth_links = [
        TruthLink(link_type="payout_ledger", left_id="POUT-01", right_id="LED-01", is_match=True),
        TruthLink(link_type="payout_ledger", left_id="POUT-02", right_id="LED-02", is_match=True),
        TruthLink(link_type="payout_ledger", left_id="POUT-01", right_id="LED-02", is_match=False),
        TruthLink(link_type="payout_ledger", left_id="POUT-02", right_id="LED-01", is_match=False),
    ]

    candidate_pairs = [
        ("POUT-01", "LED-01"),  # TP
        ("POUT-01", "LED-02"),  # FP (predicted in MG-01)
        ("POUT-02", "LED-02"),  # FN (not predicted)
        ("POUT-02", "LED-01"),  # TN (not predicted)
    ]

    predicted_groups = [
        MatchGroup(
            group_id="MG-01",
            kind=GroupKind.SIMPLE,
            bank_ids=["BNK-01"],
            payout_ids=["POUT-01"],
            ledger_ids=["LED-01", "LED-02"],
            confidence=1.0,
            source="deterministic",
            fields_matched=["utr"],
            tolerances_used=[],
            tag=ResolvedTag.CLEAN,
            reason="Test group",
            agent_turns=0,
        ),
    ]

    grader = LinkGrader()
    decisions = grader.grade(
        link_type="payout_ledger",
        candidate_pairs=candidate_pairs,
        predicted_groups=predicted_groups,
        truth_links=truth_links,
    )

    outcomes = {f"{d.left_id}->{d.right_id}": d.outcome for d in decisions}
    assert outcomes["POUT-01->LED-01"] == "TP"
    assert outcomes["POUT-01->LED-02"] == "FP"
    assert outcomes["POUT-02->LED-02"] == "FN"
    assert outcomes["POUT-02->LED-01"] == "TN"

    matrix = grader.confusion_matrix(decisions)
    assert matrix == {"tp": 1, "fp": 1, "fn": 1, "tn": 1}


def test_compute_link_metrics_values_and_denominators() -> None:
    """compute_link_metrics calculates exact precision, recall, F1 with I11 numerators."""
    grader = LinkGrader()

    # Normal case: tp=8, fp=2, fn=2, tn=88
    # precision = 8 / (8 + 2) = 0.8, num=8, den=10
    # recall = 8 / (8 + 2) = 0.8, num=8, den=10
    # f1 = 2 * 0.8 * 0.8 / (0.8 + 0.8) = 0.8, num=16, den=20
    m = grader.compute_link_metrics({"tp": 8, "fp": 2, "fn": 2, "tn": 88})
    assert m["precision"]["value"] == 0.8
    assert m["precision"]["numerator"] == 8
    assert m["precision"]["denominator"] == 10

    assert m["recall"]["value"] == 0.8
    assert m["recall"]["numerator"] == 8
    assert m["recall"]["denominator"] == 10

    assert m["f1"]["value"] == pytest.approx(0.8)
    assert m["f1"]["numerator"] == 16
    assert m["f1"]["denominator"] == 20


def test_compute_link_metrics_edge_cases_zero_divisions() -> None:
    """compute_link_metrics handles zero counts without ZeroDivisionError."""
    grader = LinkGrader()

    # All zeros
    m0 = grader.compute_link_metrics({"tp": 0, "fp": 0, "fn": 0, "tn": 10})
    assert m0["precision"] == {"value": 0.0, "numerator": 0, "denominator": 0}
    assert m0["recall"] == {"value": 0.0, "numerator": 0, "denominator": 0}
    assert m0["f1"] == {"value": 0.0, "numerator": 0, "denominator": 0}

    # Only FP (no TP, no FN)
    m_fp = grader.compute_link_metrics({"tp": 0, "fp": 5, "fn": 0, "tn": 10})
    assert m_fp["precision"]["value"] == 0.0
    assert m_fp["precision"]["numerator"] == 0
    assert m_fp["precision"]["denominator"] == 5
    assert m_fp["recall"]["value"] == 0.0
    assert m_fp["f1"]["value"] == 0.0

    # Only FN (no TP, no FP)
    m_fn = grader.compute_link_metrics({"tp": 0, "fp": 0, "fn": 5, "tn": 10})
    assert m_fn["precision"]["value"] == 0.0
    assert m_fn["recall"]["value"] == 0.0
    assert m_fn["recall"]["numerator"] == 0
    assert m_fn["recall"]["denominator"] == 5
    assert m_fn["f1"]["value"] == 0.0

    # Perfect score: tp=10, fp=0, fn=0
    m_perf = grader.compute_link_metrics({"tp": 10, "fp": 0, "fn": 0, "tn": 10})
    assert m_perf["precision"] == {"value": 1.0, "numerator": 10, "denominator": 10}
    assert m_perf["recall"] == {"value": 1.0, "numerator": 10, "denominator": 10}
    assert m_perf["f1"] == {"value": 1.0, "numerator": 20, "denominator": 20}


def test_grader_unlisted_candidate_pair_defaults_to_false() -> None:
    """Candidate pairs absent from truth_links default to truth=False (TN when unpredicted)."""
    grader = LinkGrader()
    decisions = grader.grade(
        link_type="bank_payout",
        candidate_pairs=[("BNK-UNLISTED", "POUT-UNLISTED")],
        predicted_groups=[],
        truth_links=[],  # Empty truth links map
    )
    assert len(decisions) == 1
    assert decisions[0].truth is False
    assert decisions[0].predicted is False
    assert decisions[0].outcome == "TN"


def test_compute_link_metrics_unit_counts() -> None:
    """Exact boundary where p_den == 1, r_den == 1, and f1_den == 1.0."""
    grader = LinkGrader()

    # Unit TP (p_den=1, r_den=1)
    m1 = grader.compute_link_metrics({"tp": 1, "fp": 0, "fn": 0, "tn": 0})
    assert m1["precision"]["value"] == 1.0
    assert m1["precision"]["denominator"] == 1
    assert m1["recall"]["value"] == 1.0
    assert m1["recall"]["denominator"] == 1
    assert m1["f1"]["value"] == 1.0

    # f1_den == 1.0 (p_val=0.5, r_val=0.5 -> f1_den=1.0)
    m_half = grader.compute_link_metrics({"tp": 1, "fp": 1, "fn": 1, "tn": 0})
    assert m_half["precision"]["value"] == 0.5
    assert m_half["recall"]["value"] == 0.5
    assert m_half["f1"]["value"] == pytest.approx(0.5)
