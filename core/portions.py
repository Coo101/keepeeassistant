"""Portion maths and rounding (SPEC §4, §7)."""

from decimal import ROUND_HALF_UP, Decimal

from core.constants import CHILD_PORTION_FACTOR, Unit


def portions(children: int, teens: int, staff: int = 0) -> Decimal:
    """Portions for a headcount: teens and staff count 1, under-12s 0.7."""
    return Decimal(teens) + Decimal(staff) + CHILD_PORTION_FACTOR * Decimal(children)


def scale_factor(demand_portions: Decimal, base_portions: Decimal) -> Decimal:
    """How much to multiply a recipe's quantities by to feed the demand."""
    if base_portions <= 0:
        raise ValueError("Recipe base portions must be positive")
    return demand_portions / base_portions


def round_quantity(quantity: Decimal, unit: str) -> Decimal:
    """SPEC §7: 1 decimal for kg/liter, whole numbers for piece."""
    if unit == Unit.PIECE:
        return quantity.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return quantity.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def format_quantity(quantity: Decimal) -> str:
    """Human display without trailing zeros (2.500 -> 2.5, 130.000 -> 130)."""
    quantity = quantity.normalize()
    if quantity.as_tuple().exponent > 0:
        quantity = quantity.quantize(Decimal("1"))
    return str(quantity)
