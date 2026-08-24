"""Tests for truth link grader and isolation (§4.1, §6, R8, D6, checks 5.2, 5.16)."""

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
        code = f.read()

    assert "matching" not in code
    assert "rules" not in code
    assert "blocker" not in code
    assert "agent" not in code
    assert "AgentRunner" not in code
