"""Shopping list generation (SPEC §8)."""

import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from camps.models import Camp
from core.portions import round_quantity, scale_factor
from planning.models import MenuEntry
from recipes.models import Ingredient
from shopping.models import ShoppingTrip

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ListItem:
    ingredient: Ingredient
    quantity: Decimal
    unit: str

    @property
    def category(self) -> str:
        return self.ingredient.category


@dataclass
class TripShoppingList:
    trip: ShoppingTrip
    cover_start: datetime.date
    cover_end: datetime.date
    covered_days: list[datetime.date]
    # category label -> items, in category order
    items_by_category: dict[str, list[ListItem]] = field(default_factory=dict)


@dataclass
class ShoppingPlan:
    camp: Camp
    trip_lists: list[TripShoppingList]
    uncovered_days: list[datetime.date]


def _coverage_windows(
    camp: Camp, trips: list[ShoppingTrip]
) -> list[tuple[ShoppingTrip, datetime.date, datetime.date]]:
    """Per SPEC §8: a trip covers the day after it up to and including the
    next trip's date (or the camp end for the last trip). Never its own day."""
    windows = []
    for i, trip in enumerate(trips):
        cover_start = trip.date + datetime.timedelta(days=1)
        cover_end = trips[i + 1].date if i + 1 < len(trips) else camp.end_date
        windows.append((trip, cover_start, cover_end))
    return windows


def _aggregate_days(camp: Camp, days: list[datetime.date]) -> dict[str, list[ListItem]]:
    """Aggregate scaled ingredient quantities for the given camp days,
    grouped by ingredient category (SPEC §8)."""
    totals: dict[tuple[int, str], Decimal] = defaultdict(Decimal)
    ingredients: dict[int, Ingredient] = {}

    entries = MenuEntry.objects.filter(camp=camp, date__in=days).select_related(
        "recipe"
    )
    for entry in entries:
        scale = scale_factor(camp.demand_portions, entry.recipe.base_portions)
        for ri in entry.recipe.ingredients.select_related("ingredient"):
            totals[(ri.ingredient_id, ri.unit)] += ri.quantity * scale
            ingredients[ri.ingredient_id] = ri.ingredient

    by_category: dict[str, list[ListItem]] = defaultdict(list)
    for (ingredient_id, unit), quantity in totals.items():
        ingredient = ingredients[ingredient_id]
        by_category[ingredient.get_category_display()].append(
            ListItem(
                ingredient=ingredient,
                quantity=round_quantity(quantity, unit),
                unit=unit,
            )
        )
    for items in by_category.values():
        items.sort(key=lambda item: item.ingredient.name.lower())
    return dict(sorted(by_category.items()))


def build_shopping_plan(camp: Camp) -> ShoppingPlan:
    """One aggregated list per shopping trip, plus uncovered-day warnings."""
    trips = list(camp.shopping_trips.order_by("date"))
    camp_days = camp.days

    trip_lists: list[TripShoppingList] = []
    covered: set[datetime.date] = set()
    for trip, cover_start, cover_end in _coverage_windows(camp, trips):
        days = [d for d in camp_days if cover_start <= d <= cover_end]
        covered.update(days)
        trip_lists.append(
            TripShoppingList(
                trip=trip,
                cover_start=cover_start,
                cover_end=cover_end,
                covered_days=days,
                items_by_category=_aggregate_days(camp, days),
            )
        )

    uncovered = [d for d in camp_days if d not in covered]
    if uncovered:
        logger.info(
            "Camp %s has %d uncovered day(s): %s", camp, len(uncovered), uncovered
        )
    return ShoppingPlan(camp=camp, trip_lists=trip_lists, uncovered_days=uncovered)
