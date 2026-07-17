"""Shopping list coverage and aggregation (SPEC §8)."""

import datetime
from decimal import Decimal

import pytest

from core.constants import DishType, MealType
from shopping.models import ShoppingTrip
from shopping.services import build_shopping_plan
from tests.factories import KG, PIECE, PRODUCE, assign, make_camp, make_recipe

pytestmark = pytest.mark.django_db

AUG = lambda d: datetime.date(2026, 8, d)  # noqa: E731


def test_trip_covers_next_days_not_its_own() -> None:
    camp = make_camp(start=AUG(1), days=5)  # Aug 1-5
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    ShoppingTrip.objects.create(camp=camp, date=AUG(3))

    plan = build_shopping_plan(camp)
    first, second = plan.trip_lists
    # Trip Aug 1 covers Aug 2-3 (up to and including next trip day)
    assert first.covered_days == [AUG(2), AUG(3)]
    # Trip Aug 3 covers Aug 4-5 (to camp end)
    assert second.covered_days == [AUG(4), AUG(5)]
    # Aug 1 itself is covered by nobody
    assert plan.uncovered_days == [AUG(1)]


def test_pre_camp_trip_covers_opening_days() -> None:
    camp = make_camp(start=AUG(1), days=3)
    ShoppingTrip.objects.create(camp=camp, date=AUG(1) - datetime.timedelta(days=1))

    plan = build_shopping_plan(camp)
    assert plan.trip_lists[0].covered_days == [AUG(1), AUG(2), AUG(3)]
    assert plan.uncovered_days == []


def test_no_trips_all_days_uncovered() -> None:
    camp = make_camp(start=AUG(1), days=3)
    plan = build_shopping_plan(camp)
    assert plan.trip_lists == []
    assert plan.uncovered_days == [AUG(1), AUG(2), AUG(3)]


def test_aggregation_sums_across_meals_and_scales() -> None:
    camp = make_camp(children=0, teens=52, staff=0)  # 52 portions, Aug 1-5
    # Two recipes sharing an ingredient, base 13 teens -> scale 4 each.
    stew = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[("Potatoes", "2", KG, PRODUCE), ("Onions", "4", PIECE, PRODUCE)],
    )
    soup = make_recipe(
        "Potato soup",
        dish_type=DishType.SOUP,
        teens=13,
        ingredients=[("Potatoes", "1.5", KG, PRODUCE)],
    )
    assign(camp, AUG(2), MealType.DINNER, stew)
    assign(camp, AUG(2), MealType.LUNCH, soup, course="soup")

    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    plan = build_shopping_plan(camp)
    items = plan.trip_lists[0].items_by_category["Produce"]
    by_name = {i.ingredient.name: i for i in items}
    # Potatoes: (2 + 1.5) * 4 = 14 kg; Onions: 4 * 4 = 16 pieces
    assert by_name["Potatoes"].quantity == Decimal("14.0")
    assert by_name["Potatoes"].unit == KG
    assert by_name["Onions"].quantity == Decimal("16")


def test_meals_outside_coverage_excluded() -> None:
    camp = make_camp(children=0, teens=13, staff=0, start=AUG(1), days=5)
    stew = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[("Potatoes", "2", KG, PRODUCE)],
    )
    assign(camp, AUG(1), MealType.DINNER, stew)  # day 1: not covered by Aug 1 trip
    assign(camp, AUG(2), MealType.DINNER, stew)

    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    plan = build_shopping_plan(camp)
    items = plan.trip_lists[0].items_by_category["Produce"]
    # Only Aug 2's stew counts (scale 1): 2 kg, not 4.
    assert items[0].quantity == Decimal("2.0")
