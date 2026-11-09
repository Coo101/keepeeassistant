"""Bill lines to ingredient matches, camp prices and totals (SPEC §9.10)."""

import difflib
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from bills.models import Bill, BillLine, LineMatch
from bills.parsing import ParsedBill, ParsedLine, normalise, parse_pack
from camps.models import Camp
from core.constants import PriceSource, Unit
from recipes.models import Ingredient, IngredientPrice
from shopping.budget import build_budget


def _guess_ingredient(description: str, ingredients: list[Ingredient]):
    """The longest ingredient name in the text, otherwise a close spelling."""
    text = normalise(description)
    # Whole words only: 'Ui' isn't in 'Fruitsap'.
    named = [i for i in ingredients if f" {normalise(i.name)} " in f" {text} "]
    if named:
        return max(named, key=lambda i: len(i.name))
    names = {normalise(i.name): i for i in ingredients}
    for word in text.split():
        close = difflib.get_close_matches(word, names, n=1, cutoff=0.85)
        if close:
            return names[close[0]]
    return None


def _guess_amount(parsed: ParsedLine, ingredient: Ingredient) -> Decimal | None:
    if parsed.weighed:
        # The quantity already is the weight, whatever '±1kg' the name mentions.
        return Decimal("1") if ingredient.unit == Unit.KG else None
    pack = parse_pack(parsed.description, ingredient.unit)
    if pack:
        return pack[0]
    return Decimal("1") if ingredient.unit == Unit.PIECE else None


def _new_line(
    bill: Bill,
    parsed: ParsedLine,
    ingredients: list[Ingredient],
    matches: dict[str, LineMatch],
) -> BillLine:
    line = BillLine(
        bill=bill,
        description=parsed.description,
        article=parsed.article,
        quantity=parsed.quantity,
        line_total=parsed.line_total,
    )
    if parsed.is_other:
        line.category = BillLine.Category.OTHER
        return line
    match = matches.get(parsed.article) or matches.get(normalise(parsed.description))
    if match and match.unit == match.ingredient.unit:
        line.ingredient = match.ingredient
        line.pack_amount = match.pack_amount
        return line
    line.ingredient = _guess_ingredient(parsed.description, ingredients)
    if line.ingredient:
        line.pack_amount = _guess_amount(parsed, line.ingredient)
    return line


@transaction.atomic
def store_parsed_bill(bill: Bill, parsed: ParsedBill) -> None:
    """Add the lines as suggestions; nothing changes a price until reviewed.

    A read can take minutes, so check the bill is still waiting and empty: someone
    may have deleted it or entered the lines by hand in the meantime.
    """
    bill = Bill.objects.select_for_update().filter(pk=bill.pk).first()
    if bill is None or bill.status != Bill.Status.WAITING or bill.lines.exists():
        return
    ingredients = list(Ingredient.objects.all())
    matches = {
        match.key: match
        for match in LineMatch.objects.filter(shop=bill.shop).select_related(
            "ingredient"
        )
    }
    BillLine.objects.bulk_create(
        _new_line(bill, line, ingredients, matches) for line in parsed.lines
    )
    bill.printed_total = parsed.printed_total
    bill.status = Bill.Status.REVIEW
    bill.error = ""
    bill.save(update_fields=["printed_total", "status", "error"])


def _sync_price(line: BillLine) -> None:
    """Make the line's camp price match what the line now says."""
    value = line.unit_price
    if value is None:
        if line.price:
            line.price.delete()
            line.price = None
        return
    price = line.price or IngredientPrice(source=PriceSource.BILL)
    price.ingredient = line.ingredient
    price.unit = line.ingredient.unit
    price.price = value
    price.camp = line.bill.camp
    price.date = line.bill.date
    price.created_by = price.created_by or line.bill.uploaded_by
    price.save()
    line.price = price


def _remember_match(line: BillLine) -> None:
    if line.unit_price is None:
        return
    LineMatch.objects.update_or_create(
        shop=line.bill.shop,
        key=line.article or normalise(line.description),
        defaults={
            "ingredient": line.ingredient,
            "pack_amount": line.pack_amount,
            "unit": line.ingredient.unit,
        },
    )


@transaction.atomic
def apply_review(bill: Bill, remember_matches: bool = True) -> None:
    """After a person saved the lines: record prices, matches and the status.
    Made-up bills (the example camp) don't teach matches for real ones."""
    lines = list(bill.lines.select_related("ingredient", "price", "bill__camp"))
    if not lines and bill.status in {Bill.Status.WAITING, Bill.Status.FAILED}:
        return  # nothing was entered, so it stays in the reading queue
    for line in lines:
        _sync_price(line)
        line.save(update_fields=["price"])
        if remember_matches:
            _remember_match(line)
    open_lines = any(line.needs_review for line in lines)
    bill.status = Bill.Status.REVIEW if open_lines or not lines else Bill.Status.DONE
    bill.error = ""
    bill.save(update_fields=["status", "error"])


@dataclass
class ShopComparison:
    label: str
    estimate: Decimal | None
    paid: Decimal


@dataclass
class CampSpending:
    shops: list[ShopComparison]
    estimate: Decimal
    food: Decimal
    by_category: list[tuple[str, Decimal]]
    total: Decimal
    open_bills: int


def camp_spending(camp: Camp) -> CampSpending:
    """What was paid, split by category; only food compares with the budget."""
    budget = build_budget(camp)
    estimates = {shop.label: shop.total for shop in budget.shop_totals}
    food_counts = {BillLine.Category.FOOD, BillLine.Category.OTHER}
    paid_by_shop: dict[str, Decimal] = {}
    by_category = dict.fromkeys(BillLine.Category.values, Decimal("0"))
    lines = BillLine.objects.filter(bill__camp=camp, skipped=False).select_related(
        "bill"
    )
    for line in lines:
        by_category[line.category] += line.line_total
        if line.category in food_counts:
            label = line.bill.get_shop_display()
            paid_by_shop[label] = paid_by_shop.get(label, Decimal("0")) + (
                line.line_total
            )
    shops = [
        ShopComparison(label, estimates.get(label), paid_by_shop.get(label, Decimal(0)))
        for label in sorted({*estimates, *paid_by_shop})
    ]
    return CampSpending(
        shops=shops,
        estimate=budget.total,
        food=sum(paid_by_shop.values(), Decimal("0")),
        by_category=[
            (str(BillLine.Category(key).label), value)
            for key, value in by_category.items()
        ],
        total=sum(by_category.values(), Decimal("0")),
        open_bills=camp.bills.exclude(status=Bill.Status.DONE).count(),
    )
