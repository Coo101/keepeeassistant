"""Portion maths and rounding (docs/spec/planning.md)."""

from decimal import ROUND_HALF_UP, Decimal

from django.utils.formats import number_format

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
    """1 decimal for kg/liter, whole numbers for piece (docs/spec/planning.md).
    Anything needed rounds to at least the smallest step, so it stays on the
    shopping list."""
    step = Decimal("1") if unit == Unit.PIECE else Decimal("0.1")
    rounded = quantity.quantize(step, rounding=ROUND_HALF_UP)
    if quantity > 0 and rounded == 0:
        return step
    return rounded


def format_quantity(quantity: Decimal) -> str:
    """Human display without trailing zeros (2.500 -> 2.5, 130.000 -> 130), with
    the decimal separator of the active language (2,5 in Dutch)."""
    quantity = quantity.normalize()
    if quantity.as_tuple().exponent > 0:
        quantity = quantity.quantize(Decimal("1"))
    return number_format(quantity)
