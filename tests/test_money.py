"""Tests for integer-paise money arithmetic (I1)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from engine.core.money import paise_to_display, sum_paise, validate_paise


class TestValidatePaise:
    """I1: no float in any money path."""

    def test_int_accepted(self) -> None:
        assert validate_paise(12500) == 12500

    def test_zero_accepted(self) -> None:
        assert validate_paise(0) == 0

    def test_negative_accepted(self) -> None:
        assert validate_paise(-500) == -500

    def test_float_rejected(self) -> None:
        with pytest.raises(TypeError, match="Float not allowed"):
            validate_paise(125.00)  # type: ignore[arg-type]

    def test_string_rejected(self) -> None:
        with pytest.raises(TypeError, match="Money must be int"):
            validate_paise("100")  # type: ignore[arg-type]

    def test_bool_is_int_subclass(self) -> None:
        # bool is subclass of int in Python — validate_paise accepts it
        # This is by design; the key guard is against float
        assert validate_paise(True) == 1


class TestPaiseToDisplay:
    """Format integer paise as INR display string."""

    def test_basic(self) -> None:
        assert paise_to_display(12500) == "₹125.00"

    def test_zero(self) -> None:
        assert paise_to_display(0) == "₹0.00"

    def test_negative(self) -> None:
        assert paise_to_display(-500) == "-₹5.00"

    def test_single_digit_paise(self) -> None:
        assert paise_to_display(9) == "₹0.09"

    def test_float_rejected(self) -> None:
        with pytest.raises(TypeError):
            paise_to_display(125.0)  # type: ignore[arg-type]


class TestSumPaise:
    """Sum integer paise amounts."""

    def test_basic_sum(self) -> None:
        assert sum_paise(100, 200, 300) == 600

    def test_empty_sum(self) -> None:
        assert sum_paise() == 0

    def test_negative_sum(self) -> None:
        assert sum_paise(100, -100) == 0

    def test_float_rejected(self) -> None:
        with pytest.raises(TypeError):
            sum_paise(100, 200.5)  # type: ignore[arg-type]


class TestNoFloatInMoneyModule:
    """Structural test: no float literal in money.py source (I1)."""

    def test_no_float_literals(self) -> None:
        # Parse AST and check for float constants in the money module
        money_path = Path(__file__).resolve().parents[1] / "engine" / "core" / "money.py"
        tree = ast.parse(money_path.read_text())
        float_nodes = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, float)
        ]
        assert len(float_nodes) == 0, (
            f"Float literals found in money.py: {[n.value for n in float_nodes]}"
        )
