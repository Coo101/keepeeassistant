"""Portion maths and rounding (SPEC §4, §7)."""

from decimal import Decimal

import pytest

from core.constants import Unit
from core.portions import portions, round_quantity, scale_factor


def test_portions_child_factor() -> None:
    assert portions(children=10, teens=0) == Decimal("7.0")


def test_portions_mixed_headcount() -> None:
    # 20 children * 0.7 + 30 teens + 8 staff = 52
    assert portions(children=20, teens=30, staff=8) == Decimal("52.0")


def test_portions_staff_counts_full() -> None:
    assert portions(children=0, teens=0, staff=5) == Decimal("5")


def test_scale_factor() -> None:
    assert scale_factor(Decimal("52"), Decimal("13")) == Decimal("4")


def test_scale_factor_rejects_zero_base() -> None:
    with pytest.raises(ValueError):
        scale_factor(Decimal("52"), Decimal("0"))


def test_round_kg_one_decimal() -> None:
    assert round_quantity(Decimal("3.14"), Unit.KG) == Decimal("3.1")
    assert round_quantity(Decimal("3.15"), Unit.KG) == Decimal("3.2")


def test_round_liter_one_decimal() -> None:
    assert round_quantity(Decimal("0.44"), Unit.LITER) == Decimal("0.4")


def test_round_piece_whole() -> None:
    assert round_quantity(Decimal("52.5"), Unit.PIECE) == Decimal("53")
    assert round_quantity(Decimal("52.4"), Unit.PIECE) == Decimal("52")
