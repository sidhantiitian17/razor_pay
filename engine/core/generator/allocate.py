"""Largest-remainder cohort allocation algorithm (§3.5, D11).

Guarantees that cohort allocations sum to exactly `n` for any `n >= 50`,
without rounding errors or dropped remainder items.
"""

from __future__ import annotations

import math

from engine.core.models import CohortName

COHORT_PERCENTAGES: dict[CohortName, int] = {
    CohortName.CLEAN: 44,
    CohortName.DRIFT_TOLERATED: 8,
    CohortName.DRIFT_EXCEPTION: 4,
    CohortName.SKEW_TOLERATED: 8,
    CohortName.SKEW_EXCEPTION: 5,
    CohortName.MISSING_UTR_RECOVERABLE: 6,
    CohortName.MISSING_UTR_UNRECOVERABLE: 3,
    CohortName.DUPLICATE_PAYOUT: 5,
    CohortName.REFUND_PAIR: 5,
    CohortName.REFUND_UNPAIRED: 2,
    CohortName.FEE_MISMATCH: 4,
    CohortName.ORPHAN_BANK: 3,
    CohortName.ORPHAN_LEDGER: 3,
}


def allocate_cohorts(n: int) -> dict[CohortName, int]:
    """Allocate `n` cases across all 13 cohorts using the largest-remainder method.

    Args:
        n: Total number of records to generate (must be >= 50).

    Returns:
        Mapping from CohortName to exact count, where sum(counts.values()) == n.

    Raises:
        ValueError: If n < 50.
    """
    if n < 50:
        raise ValueError(f"n must be >= 50 (got {n})")

    exact_quotas: list[tuple[CohortName, float, int, float]] = []
    total_integer = 0

    for cohort, pct in COHORT_PERCENTAGES.items():
        exact = n * (pct / 100.0)
        integer_part = math.floor(exact)
        remainder = exact - integer_part
        total_integer += integer_part
        exact_quotas.append((cohort, exact, integer_part, remainder))

    shortfall = n - total_integer

    # Sort by remainder descending, tie-break by cohort value for determinism
    sorted_by_remainder = sorted(
        exact_quotas,
        key=lambda item: (-item[3], item[0].value),
    )

    allocated: dict[CohortName, int] = {}
    for i, (cohort, _, integer_part, _) in enumerate(sorted_by_remainder):
        extra = 1 if i < shortfall else 0
        allocated[cohort] = integer_part + extra

    # Re-order according to CohortName declaration
    return {cohort: allocated[cohort] for cohort in CohortName}
