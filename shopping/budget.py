"""Camp budget: shopping-list quantities x ingredient prices (SPEC §13).

Costs roll up per shop (so you know what each errand costs), per trip, and
per camp.
"""

import logging
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from camps.models import Camp
from recipes.models import Ingredient
from shopping.services import ShoppingPlan, TripShoppingList, build_shopping_plan

logger = logging.getLogger(__name__)

CENT = Decimal("0.01")


@dataclass(frozen=True)
class BudgetLine:
    ingredient: Ingredient
    quantity: Decimal
    unit: str
    unit_price: Decimal | None
    cost: Decimal | None  # None when the ingredient has no price yet


@dataclass
class ShopBudget:
    shop: str
    label: str
    lines_by_category: dict[str, list[BudgetLine]] = field(default_factory=dict)
    total: Decimal = Decimal("0")
    missing_count: int = 0


@dataclass
class ShopTotal:
    """Camp-wide cost for one shop; `missing_count` items lack a price, so
    the total is a floor rather than the full bill."""

    label: str
    total: Decimal = Decimal("0")
    missing_count: int = 0


@dataclass
class TripBudget:
    trip_list: TripShoppingList
    shops: list[ShopBudget]
    total: Decimal
    missing: list[Ingredient]


@dataclass
class CampBudget:
    plan: ShoppingPlan
    trips: list[TripBudget]
    total: Decimal
    shop_totals: list[ShopTotal]  # per shop across the whole camp
    missing: list[Ingredient]  # unique ingredients without a price

    @property
    def cost_per_portion_day(self) -> Decimal | None:
        camp = self.plan.camp
        divisor = camp.demand_portions * len(camp.days)
        if divisor <= 0:
            return None
        return (self.total / divisor).quantize(CENT, rounding=ROUND_HALF_UP)


def build_budget(camp: Camp) -> CampBudget:
    plan = build_shopping_plan(camp)
    trips: list[TripBudget] = []
    camp_total = Decimal("0")
    shop_totals: dict[str, ShopTotal] = {}
    missing: dict[int, Ingredient] = {}

    for trip_list in plan.trip_lists:
        shops: list[ShopBudget] = []
        trip_total = Decimal("0")
        trip_missing: dict[int, Ingredient] = {}

        for section in trip_list.shop_sections:
            shop_budget = ShopBudget(shop=section.shop, label=section.label)
            for category, items in section.items_by_category.items():
                lines = []
                for item in items:
                    price = item.ingredient.price_per_unit
                    cost = None
                    if price is not None:
                        cost = (item.quantity * price).quantize(
                            CENT, rounding=ROUND_HALF_UP
                        )
                        shop_budget.total += cost
                    else:
                        shop_budget.missing_count += 1
                        trip_missing[item.ingredient.pk] = item.ingredient
                        missing[item.ingredient.pk] = item.ingredient
                    lines.append(
                        BudgetLine(
                            ingredient=item.ingredient,
                            quantity=item.quantity,
                            unit=item.unit,
                            unit_price=price,
                            cost=cost,
                        )
                    )
                shop_budget.lines_by_category[category] = lines
            shops.append(shop_budget)
            trip_total += shop_budget.total
            running = shop_totals.setdefault(
                section.label, ShopTotal(label=section.label)
            )
            running.total += shop_budget.total
            running.missing_count += shop_budget.missing_count

        trips.append(
            TripBudget(
                trip_list=trip_list,
                shops=shops,
                total=trip_total,
                missing=sorted(trip_missing.values(), key=lambda i: i.name),
            )
        )
        camp_total += trip_total

    return CampBudget(
        plan=plan,
        trips=trips,
        total=camp_total,
        shop_totals=list(shop_totals.values()),
        missing=sorted(missing.values(), key=lambda i: i.name),
    )
