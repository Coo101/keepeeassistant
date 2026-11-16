"""The financial report: what every planned meal cost, from the bills
(docs/spec/finance.md).

A meal's cost is its scaled recipe at the camp's prices from the bills. Where a bill
has no price for an ingredient the latest known price stands in, and the meal is
marked as partly estimated; the report lists those ingredients up front.
"""

import datetime
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from bills.models import BillLine
from bills.services import CampSpending, camp_spending
from camps.models import Camp
from core.constants import MEAL_SLOTS, MealType
from core.portions import scale_factor
from recipes.models import Ingredient, Recipe
from recipes.prices import resolve_prices

CENT = Decimal("0.01")
_MEAL_LABELS = dict(MealType.CHOICES)
_SLOTS = {(slot.meal_type, slot.course): (i, slot) for i, slot in enumerate(MEAL_SLOTS)}


def _cents(amount: Decimal) -> Decimal:
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass
class MealCost:
    date: datetime.date
    meal: str
    slot: str
    recipe: Recipe
    cost: Decimal
    per_portion: Decimal | None
    estimated: bool  # an ingredient wasn't on this camp's bills
    unpriced: list[str]  # ingredients without any price, left out of `cost`
    has_ingredients: bool = True


@dataclass
class DayCosts:
    date: datetime.date
    meals: list[MealCost]

    @property
    def total(self) -> Decimal:
        return sum((meal.cost for meal in self.meals), Decimal("0"))


@dataclass
class MealTypeTotal:
    label: str
    count: int
    total: Decimal
    per_portion: Decimal | None  # average per portion for one such meal


@dataclass
class FinancialReport:
    camp: Camp
    days: list[DayCosts]
    meal_types: list[MealTypeTotal]
    planned_total: Decimal
    not_in_bills: list[Ingredient]  # priced, but not from this camp's bills
    unpriced: list[Ingredient]  # no price at all
    spending: CampSpending
    personal_lines: list[BillLine] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return not (self.not_in_bills or self.unpriced or self.spending.open_bills)

    @property
    def personal_total(self) -> Decimal:
        return sum((line.line_total for line in self.personal_lines), Decimal("0"))

    @property
    def food_per_portion_day(self) -> Decimal | None:
        divisor = self.camp.demand_portions * len(self.camp.days)
        if divisor <= 0:
            return None
        return _cents(self.spending.food / divisor)

    @property
    def not_explained(self) -> Decimal:
        """Paid for food beyond the planned meals: leftovers, waste, extras."""
        return self.spending.food - self.planned_total


def build_report(camp: Camp) -> FinancialReport:
    entries = list(
        camp.menu_entries.filter(date__range=(camp.start_date, camp.end_date))
        .select_related("recipe")
        .prefetch_related("recipe__ingredients__ingredient")
    )
    entries.sort(key=lambda e: (e.date, _SLOTS[(e.meal_type, e.course)][0]))
    ingredients = {
        ri.ingredient_id: ri.ingredient
        for entry in entries
        for ri in entry.recipe.ingredients.all()
    }
    prices = resolve_prices(camp, ingredients)
    portions = camp.demand_portions

    days: dict[datetime.date, DayCosts] = {}
    by_meal_type: dict[str, list[Decimal]] = {meal: [] for meal in MealType.ORDER}
    not_in_bills: set[int] = set()
    unpriced: set[int] = set()
    for entry in entries:
        scale = scale_factor(portions, entry.recipe.base_portions)
        cost = Decimal("0")
        estimated = False
        missing = []
        for ri in entry.recipe.ingredients.all():
            price = prices.get(ri.ingredient_id)
            # A recipe in another unit than the price can't be costed
            # (docs/spec/recipes.md).
            if price is None or ri.unit != ri.ingredient.unit:
                unpriced.add(ri.ingredient_id)
                missing.append(ri.ingredient.name)
                continue
            if not price.is_camp_price:
                not_in_bills.add(ri.ingredient_id)
                estimated = True
            cost += ri.quantity * scale * price.price
        cost = _cents(cost)
        meal = MealCost(
            date=entry.date,
            meal=_MEAL_LABELS[entry.meal_type],
            slot=_SLOTS[(entry.meal_type, entry.course)][1].label,
            recipe=entry.recipe,
            cost=cost,
            per_portion=_cents(cost / portions) if portions else None,
            estimated=estimated,
            unpriced=missing,
            has_ingredients=bool(entry.recipe.ingredients.all()),
        )
        days.setdefault(entry.date, DayCosts(entry.date, [])).meals.append(meal)
        by_meal_type[entry.meal_type].append(cost)

    # Several dishes of one meal (soup, main, dessert) together make one meal.
    meal_counts = {
        meal_type: len({e.date for e in entries if e.meal_type == meal_type})
        for meal_type in MealType.ORDER
    }
    meal_types = []
    for meal_type, costs in by_meal_type.items():
        if not costs:
            continue
        total = sum(costs, Decimal("0"))
        count = meal_counts[meal_type]
        meal_types.append(
            MealTypeTotal(
                label=_MEAL_LABELS[meal_type],
                count=count,
                total=total,
                per_portion=_cents(total / count / portions) if portions else None,
            )
        )

    personal = BillLine.objects.filter(
        bill__camp=camp, category=BillLine.Category.PERSONAL, skipped=False
    ).select_related("bill")
    return FinancialReport(
        camp=camp,
        days=list(days.values()),
        meal_types=meal_types,
        planned_total=sum((day.total for day in days.values()), Decimal("0")),
        not_in_bills=sorted(
            (ingredients[i] for i in not_in_bills - unpriced), key=lambda i: i.name
        ),
        unpriced=sorted((ingredients[i] for i in unpriced), key=lambda i: i.name),
        spending=camp_spending(camp),
        personal_lines=sorted(personal, key=lambda line: (line.bill.date, line.pk)),
    )
