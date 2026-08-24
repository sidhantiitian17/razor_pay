"""Tests for largest-remainder cohort allocation (D11, check 1.1)."""

import pytest
from engine.core.generator.allocate import COHORT_PERCENTAGES, allocate_cohorts
from engine.core.models import CohortName


def test_cohort_percentages_sum_to_100() -> None:
    """Percentages across all 13 cohorts must sum to exactly 100."""
    total = sum(COHORT_PERCENTAGES.values())
    assert total == 100
    assert len(COHORT_PERCENTAGES) == 13
    assert set(COHORT_PERCENTAGES.keys()) == set(CohortName)


@pytest.mark.parametrize("n", [50, 60, 77, 100, 1000])
def test_allocate_sum(n: int) -> None:
    """Cohort allocations must sum to exactly n for any n >= 50 (D11)."""
    counts = allocate_cohorts(n)
    assert sum(counts.values()) == n
    assert len(counts) == 13
    assert all(isinstance(c, int) and c >= 0 for c in counts.values())


def test_allocate_minimum_n() -> None:
    """Allocating with n < 50 raises ValueError."""
    with pytest.raises(ValueError, match="n must be >= 50"):
        allocate_cohorts(49)
