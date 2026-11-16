"""Turn a bill's text into lines. Pure functions, no database.

The patterns are generic until they've been tuned on real bills; a person
reviews every result, and whatever isn't recognised can be added by hand.
"""

import re
from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from core.constants import Unit

_MONEY = r"-?\d{1,5}[.,]\d{2}"
_LINE = re.compile(
    rf"^(?:(?P<prefix>\d{{1,3}})\s*[xX*]\s+)?"
    rf"(?P<description>.*?\S)"
    rf"(?:(?:\s+(?P<quantity>\d{{1,3}}(?:[.,]\d{{3}})?))?"
    rf"\s+€?\s*(?P<unit_price>{_MONEY}))?"
    rf"\s+€?\s*(?P<total>{_MONEY})\s*(?:€|EUR)?(?:\s+[A-D])?$"
)
_TOTAL = re.compile(r"^(?:te betalen|totaal|total)\b", re.IGNORECASE)
_NOT_A_PURCHASE = re.compile(
    r"\b(?:subtotaal|btw|tva|bancontact|maestro|visa|mastercard|wisselgeld|contant"
    r"|cash|factuur|klant|datum|pagina|rekening|totale korting)\b",
    re.IGNORECASE,
)
_OTHER = re.compile(
    r"\b(?:leeggoed|statiegeld|korting|reductie|bon|waardebon|waarborg|servicekost)\b",
    re.IGNORECASE,
)

# Invoices (Collect&Go) list amounts without VAT, each line with a VAT code that a
# table further down explains: "A 6% € 727.80 € 43.67 € 771.47".
_EXCLUDES_VAT = re.compile(r"\bBEDRAG EXC\b")
_VAT_RATE = re.compile(r"^(?P<code>[A-Z])\s+(?P<rate>\d{1,2})%\s+€", re.MULTILINE)
_ARTICLE = re.compile(r"^(?P<vat>[A-Z])?\s*(?P<article>\d{3,6}\b|\d+-SCP-)\s+")

# Wholesale invoices (Van Zon): article, name, quantity, unit, unit price, promotion,
# subtotal, discount, total without VAT, VAT rate. A long name continues on the next
# line, and a quantity with decimals is a weight (unit WUK).
_WHOLESALE_LINE = re.compile(
    rf"^(?P<article>\d{{1,6}})\s+(?P<description>.+?)"
    rf"\s+(?P<quantity>\d{{1,4}}(?:,\d{{1,3}})?)\s+[A-Z]{{2,4}}\s+\d+,\d{{4}}"
    rf"(?:\s+{_MONEY})?\s+{_MONEY}\s+{_MONEY}\s+(?P<total>{_MONEY})"
    rf"\s+(?P<vat>\d{{1,2}})\s*%$"
)
_WHOLESALE_NAME_CONTINUES = re.compile(r"^[A-Z0-9][A-Z0-9 ,.+'/-]{0,39}$")
_WHOLESALE_TOTAL = re.compile(rf"^(?:{_MONEY}\s+){{4}}(?P<total>{_MONEY})\s+EUR$")

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
    weighed: bool = False  # the quantity is a weight in kg
    article: str = ""  # the shop's article number, which stays the same across bills


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


def _vat_rates(text: str) -> dict[str, Decimal] | None:
    """VAT per code when the amounts exclude it, otherwise None."""
    if not _EXCLUDES_VAT.search(text):
        return None
    return {match["code"]: Decimal(match["rate"]) for match in _VAT_RATE.finditer(text)}


def _invoice_line(
    description: str, total: Decimal, rates: dict[str, Decimal]
) -> tuple[str, Decimal, str]:
    """Split off the VAT code and article number, and add the VAT: what was paid."""
    article = _ARTICLE.match(description)
    if not article:
        return description, total, ""
    paid = _with_vat(total, rates.get(article["vat"], Decimal("0")))
    # A discount's promotion code isn't an article.
    number = article["article"] if article["article"].isdigit() else ""
    return description[article.end() :], paid, number


def _with_vat(total: Decimal, rate: Decimal) -> Decimal:
    return (total * (100 + rate) / 100).quantize(Decimal("0.01"), ROUND_HALF_UP)


def _with_rounding(
    lines: list[ParsedLine], printed_total: Decimal | None
) -> list[ParsedLine]:
    """VAT is charged per rate, not per line, so a few cents can be left over."""
    if printed_total is None:
        return lines
    left = printed_total - sum(line.line_total for line in lines)
    if left and abs(left) <= Decimal("0.005") * len(lines):
        return [*lines, ParsedLine("VAT rounding", Decimal("1"), left, is_other=True)]
    return lines


def _parse_wholesale(text: str) -> ParsedBill:
    lines: list[ParsedLine] = []
    printed_total = None
    after_line = False
    for raw in text.splitlines():
        raw = " ".join(raw.split())
        match = _WHOLESALE_LINE.match(raw)
        if match:
            total = _with_vat(to_decimal(match["total"]), Decimal(match["vat"]))
            lines.append(
                ParsedLine(
                    description=match["description"][:200],
                    quantity=to_decimal(match["quantity"]),
                    line_total=total,
                    is_other=total < 0,
                    weighed="," in match["quantity"],
                    article=match["article"],
                )
            )
        elif after_line and _WHOLESALE_NAME_CONTINUES.match(raw):
            name = f"{lines[-1].description} {raw}"[:200]
            lines[-1] = replace(lines[-1], description=name)
        elif total_match := _WHOLESALE_TOTAL.match(raw):
            printed_total = to_decimal(total_match["total"])
        after_line = bool(match)
    return ParsedBill(_with_rounding(lines, printed_total), printed_total)


def parse_text(text: str) -> ParsedBill:
    wholesale = _parse_wholesale(text)
    if wholesale.lines:
        return wholesale
    lines: list[ParsedLine] = []
    printed_total = None
    rates = _vat_rates(text)
    for raw in text.splitlines():
        raw = " ".join(raw.split())
        match = _LINE.match(raw)
        if not match:
            continue
        total = to_decimal(match["total"])
        if _NOT_A_PURCHASE.search(raw) or _VAT_RATE.match(raw):
            continue
        if _TOTAL.match(raw):
            printed_total = total
            continue
        quantity = _quantity(match, total)
        description = match["description"]
        article = ""
        if rates is not None:
            description, total, article = _invoice_line(description, total, rates)
        lines.append(
            ParsedLine(
                description=description[:200],
                quantity=quantity,
                line_total=total,
                is_other=total < 0 or bool(_OTHER.search(raw)),
                weighed=bool(re.search(r"[.,]", match["quantity"] or "")),
                article=article,
            )
        )
    if rates is not None:
        lines = _with_rounding(lines, printed_total)
    return ParsedBill(lines=lines, printed_total=printed_total)


def parse_pack(description: str, unit: str | None = None) -> tuple[Decimal, str] | None:
    """Pack size from a description: '6X1,5L' is (9, liter), '500G' (0.5, kg).

    With a unit, only a size in that unit counts: 'KAAS 24ST 400G' has two.
    """
    for match in _PACK.finditer(description):
        pack_unit, factor = _UNITS[match["unit"].lower()]
        if unit and pack_unit != unit:
            continue
        amount = to_decimal(match["amount"]) * factor
        if match["count"]:
            amount *= int(match["count"])
        # Outside this range it's a misread, and it wouldn't fit the field either.
        return (amount, pack_unit) if Decimal("0.001") <= amount < 10000 else None
    return None


def normalise(description: str) -> str:
    return " ".join(re.sub(r"[^\w\s]", " ", description.lower()).split())[:200]
