"""Turn a bill's text into lines. Pure functions, no database.

The patterns are generic until they've been tuned on real bills; a person
reviews every result, and whatever isn't recognised can be added by hand.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from core.constants import Unit

_MONEY = r"-?\d{1,5}[.,]\d{2}"
_LINE = re.compile(
    rf"^(?:(?P<prefix>\d{{1,3}})\s*[xX*]\s+)?"
    rf"(?P<description>.*?\S)"
    rf"(?:(?:\s+(?P<quantity>\d{{1,3}}))?\s+€?\s*(?P<unit_price>{_MONEY}))?"
    rf"\s+€?\s*(?P<total>{_MONEY})\s*(?:€|EUR)?(?:\s+[A-D])?$"
)
_TOTAL = re.compile(r"^(?:te betalen|totaal|total)\b", re.IGNORECASE)
_NOT_A_PURCHASE = re.compile(
    r"\b(?:subtotaal|btw|tva|bancontact|maestro|visa|mastercard|wisselgeld|contant"
    r"|cash|factuur|klant|datum|pagina|rekening)\b",
    re.IGNORECASE,
)
_OTHER = re.compile(
    r"\b(?:leeggoed|statiegeld|korting|reductie|bon|waardebon)\b", re.IGNORECASE
)

_PACK = re.compile(
    r"(?:(?P<count>\d{1,3})\s*[xX*]\s*)?"
    r"(?P<amount>\d{1,4}(?:[.,]\d{1,3})?)\s*"
    r"(?P<unit>kg|gr|g|cl|ml|l|lt|st|stuks?)\b",
    re.IGNORECASE,
)
_UNITS = {
    "kg": (Unit.KG, Decimal("1")),
    "g": (Unit.KG, Decimal("0.001")),
    "gr": (Unit.KG, Decimal("0.001")),
    "l": (Unit.LITER, Decimal("1")),
    "lt": (Unit.LITER, Decimal("1")),
    "cl": (Unit.LITER, Decimal("0.01")),
    "ml": (Unit.LITER, Decimal("0.001")),
    "st": (Unit.PIECE, Decimal("1")),
    "stuk": (Unit.PIECE, Decimal("1")),
    "stuks": (Unit.PIECE, Decimal("1")),
}


@dataclass(frozen=True)
class ParsedLine:
    description: str
    quantity: Decimal
    line_total: Decimal
    is_other: bool = False  # deposit, discount: money, but not a product


@dataclass(frozen=True)
class ParsedBill:
    lines: list[ParsedLine]
    printed_total: Decimal | None = None


def to_decimal(value: object) -> Decimal | None:
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _quantity(match: re.Match, total: Decimal) -> Decimal:
    quantity = to_decimal(match["prefix"] or match["quantity"] or "0")
    if quantity:
        return quantity
    # Only a unit price and a total: their ratio is the count, if it's whole.
    unit_price = to_decimal(match["unit_price"] or "0")
    if unit_price and total / unit_price == int(total / unit_price) and total > 0:
        return total / unit_price
    return Decimal("1")


def parse_text(text: str) -> ParsedBill:
    lines: list[ParsedLine] = []
    printed_total = None
    for raw in text.splitlines():
        raw = " ".join(raw.split())
        match = _LINE.match(raw)
        if not match:
            continue
        total = to_decimal(match["total"])
        if _NOT_A_PURCHASE.search(raw):
            continue
        if _TOTAL.match(raw):
            printed_total = total
            continue
        lines.append(
            ParsedLine(
                description=match["description"][:200],
                quantity=_quantity(match, total),
                line_total=total,
                is_other=total < 0 or bool(_OTHER.search(raw)),
            )
        )
    return ParsedBill(lines=lines, printed_total=printed_total)


def parse_pack(description: str) -> tuple[Decimal, str] | None:
    """Pack size from a description: '6X1,5L' is (9, liter), '500G' (0.5, kg)."""
    match = _PACK.search(description)
    if not match:
        return None
    unit, factor = _UNITS[match["unit"].lower()]
    amount = to_decimal(match["amount"]) * factor
    if match["count"]:
        amount *= int(match["count"])
    # Outside this range it's a misread, and it wouldn't fit the field either.
    return (amount, unit) if Decimal("0.001") <= amount < 10000 else None


def normalise(description: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", description.lower()).split())[:200]
