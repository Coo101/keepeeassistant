"""Shopping list generation (SPEC §8).

Lists are grouped per shop (Colruyt / Van Zon / bakker / beenhouwer) so each
trip maps onto the errands you actually run, and per ingredient category
within a shop so the list follows the aisles.
"""

import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from camps.models import Camp
from core.constants import Shop
from core.portions import round_quantity, scale_factor
from planning.models import MenuEntry
from recipes.models import Ingredient
from shopping.models import ShoppingTrip

logger = logging.getLogger(__name__)

SHOP_LABELS = dict(Shop.CHOICES)
SHOP_ORDER = [code for code, _ in Shop.CHOICES]


@dataclass(frozen=True)
class ListItem:
    ingredient: Ingredient
    quantity: Decimal
    unit: str

    @property
    def category(self) -> str:
        return self.ingredient.category


@dataclass
class ShopSection:
    """One shop's part of a trip list, grouped by ingredient category."""

    shop: str
    label: str
    items_by_category: dict[str, list[ListItem]] = field(default_factory=dict)

    @property
    def item_count(self) -> int:
        return sum(len(items) for items in self.items_by_category.values())


@dataclass
class TripShoppingList:
    trip: ShoppingTrip
    cover_start: datetime.date
    cover_end: datetime.date
    covered_days: list[datetime.date]
    shop_sections: list[ShopSection] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.shop_sections


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


def _entries_by_date(camp: Camp) -> dict[datetime.date, list[MenuEntry]]:
    """All of the camp's menu entries in one query, keyed by date."""
    by_date: dict[datetime.date, list[MenuEntry]] = defaultdict(list)
    entries = camp.menu_entries.select_related("recipe").prefetch_related(
        "recipe__ingredients__ingredient"
    )
    for entry in entries:
        by_date[entry.date].append(entry)
    return by_date


def _aggregate_days(
    camp: Camp,
    days: list[datetime.date],
    entries_by_date: dict[datetime.date, list[MenuEntry]],
    pantry: dict[int, Decimal],
) -> list[ShopSection]:
    """Aggregate scaled ingredient quantities for the given camp days,
    grouped by shop and then by ingredient category (SPEC §8). What's used from
    `pantry` is taken out of it, so a later trip doesn't count it again."""
    totals: dict[tuple[int, str], Decimal] = defaultdict(Decimal)
    ingredients: dict[int, Ingredient] = {}

    for day in days:
        for entry in entries_by_date.get(day, []):
            scale = scale_factor(camp.demand_portions, entry.recipe.base_portions)
            for ri in entry.recipe.ingredients.all():
                totals[(ri.ingredient_id, ri.unit)] += ri.quantity * scale
                ingredients[ri.ingredient_id] = ri.ingredient

    by_shop: dict[str, dict[str, list[ListItem]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for (ingredient_id, unit), quantity in totals.items():
        ingredient = ingredients[ingredient_id]
        if unit == ingredient.unit:
            used = min(pantry.get(ingredient_id, Decimal("0")), quantity)
            pantry[ingredient_id] = pantry.get(ingredient_id, Decimal("0")) - used
            quantity -= used
            if quantity <= 0:
                continue
        item = ListItem(
            ingredient=ingredient,
            quantity=round_quantity(quantity, unit),
            unit=unit,
        )
        by_shop[ingredient.shop][ingredient.get_category_display()].append(item)

    sections = []
    for shop in SHOP_ORDER:
        if shop not in by_shop:
            continue
        categories = by_shop[shop]
        for items in categories.values():
            items.sort(key=lambda item: item.ingredient.name.lower())
        sections.append(
            ShopSection(
                shop=shop,
                label=str(SHOP_LABELS[shop]),
                items_by_category=dict(sorted(categories.items())),
            )
        )
    return sections


def build_shopping_plan(camp: Camp) -> ShoppingPlan:
    """One aggregated list per shopping trip, plus uncovered-day warnings."""
    trips = list(camp.shopping_trips.order_by("date"))
    camp_days = camp.days
    entries_by_date = _entries_by_date(camp)
    pantry = {
        item.ingredient_id: item.quantity for item in camp.chiro.pantry_items.all()
    }

    trip_lists: list[TripShoppingList] = []
    covered: set[datetime.date] = set()
    windows = _coverage_windows(camp, trips)
    if windows:
        # Days before the first trip's coverage are on no list, but they do use up
        # the pantry before the lists get to it.
        opening_days = [d for d in camp_days if d < windows[0][1]]
        _aggregate_days(camp, opening_days, entries_by_date, pantry)
    for trip, cover_start, cover_end in windows:
        days = [d for d in camp_days if cover_start <= d <= cover_end]
        covered.update(days)
        trip_lists.append(
            TripShoppingList(
                trip=trip,
                cover_start=cover_start,
                cover_end=cover_end,
                covered_days=days,
                shop_sections=_aggregate_days(camp, days, entries_by_date, pantry),
            )
        )

    uncovered = [d for d in camp_days if d not in covered]
    if uncovered:
        logger.info(
            "Camp %s has %d uncovered day(s): %s", camp, len(uncovered), uncovered
        )
    return ShoppingPlan(camp=camp, trip_lists=trip_lists, uncovered_days=uncovered)
