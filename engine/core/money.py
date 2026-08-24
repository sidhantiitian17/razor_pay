"""Money arithmetic — integer paise only, no floats ever."""

from __future__ import annotations


def paise_to_display(paise: int) -> str:
    """Format integer paise as INR display string.

    Args:
        paise: Amount in integer paise (100 paise = 1 INR).

    Returns:
        Formatted string like "₹125.00".
    """
    if not isinstance(paise, int):
        raise TypeError(f"Money must be int paise, got {type(paise).__name__}")
    sign = "-" if paise < 0 else ""
    abs_paise = abs(paise)
    rupees = abs_paise // 100
    remaining = abs_paise % 100
    return f"{sign}₹{rupees}.{remaining:02d}"


def validate_paise(value: int) -> int:
    """Validate that a value is integer paise.

    Args:
        value: The value to validate.

    Returns:
        The validated integer.

    Raises:
        TypeError: If value is not an int (especially if it's a float).
    """
    if isinstance(value, float):
        raise TypeError("Float not allowed for money — use integer paise")
    if not isinstance(value, int):
        raise TypeError(f"Money must be int paise, got {type(value).__name__}")
    return value


def sum_paise(*amounts: int) -> int:
    """Sum integer paise amounts.

    Args:
        *amounts: Integer paise values to sum.

    Returns:
        Sum as integer paise.

    Raises:
        TypeError: If any amount is not an int.
    """
    for a in amounts:
        validate_paise(a)
    return sum(amounts)
