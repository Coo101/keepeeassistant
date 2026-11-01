"""Budgeting: camp cost roll-up from ingredient prices."""

import datetime
from decimal import Decimal

import pytest

from core.constants import DishType, MealType, Shop
from recipes.models import Ingredient
from shopping.budget import build_budget
from shopping.models import ShoppingTrip
from tests.factories import KG, PIECE, PRODUCE, assign, make_camp, make_recipe

pytestmark = pytest.mark.django_db

AUG = lambda d: datetime.date(2026, 8, d)  # noqa: E731


def test_build_budget_totals_and_missing_prices() -> None:
    camp = make_camp(children=0, teens=52, staff=0)  # 52 portions, Aug 1-5
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=13,  # scale x4
        ingredients=[
            ("Potatoes", "2", KG, PRODUCE),
            ("Onions", "3", PIECE, PRODUCE),
        ],
    )
    assign(camp, AUG(2), MealType.DINNER, recipe)
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))

    Ingredient.objects.filter(name="Potatoes").update(
        price_per_unit=Decimal("0.79")
    )  # Onions stays unpriced

    budget = build_budget(camp)
    # potatoes: 2kg x4 = 8kg x 0.79 = 6.32
    assert budget.total == Decimal("6.32")
    assert [i.name for i in budget.missing] == ["Onions"]
    trip = budget.trips[0]
    assert trip.total == Decimal("6.32")
    lines = trip.shops[0].lines_by_category["Produce"]
    by_name = {line.ingredient.name: line for line in lines}
    assert by_name["Potatoes"].cost == Decimal("6.32")
    assert by_name["Onions"].cost is None
    # 52 portions x 4 covered days (Aug 2-5) = 208 -> 6.32/208 ~ 0.03
    assert budget.cost_per_portion_day == Decimal("0.03")


def test_budget_totals_split_per_shop() -> None:
    camp = make_camp(children=0, teens=13, staff=0)
    recipe = make_recipe(
        "Broodmaaltijd",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[
            ("Potatoes", "2", KG, PRODUCE),
            ("Wit brood", "6", PIECE, PRODUCE),
        ],
    )
    assign(camp, AUG(2), MealType.DINNER, recipe)
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    Ingredient.objects.filter(name="Potatoes").update(
        price_per_unit=Decimal("1.00"), shop=Shop.COLRUYT
    )
    Ingredient.objects.filter(name="Wit brood").update(
        price_per_unit=Decimal("0.50"), shop=Shop.BAKKER
    )

    budget = build_budget(camp)
    totals = {st.label: st.total for st in budget.shop_totals}
    assert totals == {
        "Colruyt": Decimal("2.00"),  # 2 kg x 1.00
        "Bakker": Decimal("3.00"),  # 6 st x 0.50
    }
    assert budget.total == Decimal("5.00")
    shops = {shop.label: shop.total for shop in budget.trips[0].shops}
    assert shops == {"Colruyt": Decimal("2.00"), "Bakker": Decimal("3.00")}


def test_shop_total_reports_unpriced_items() -> None:
    camp = make_camp(children=0, teens=13, staff=0)
    recipe = make_recipe(
        "Broodmaaltijd",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[("Hamburgers", "60", PIECE, PRODUCE)],
    )
    assign(camp, AUG(2), MealType.DINNER, recipe)
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    Ingredient.objects.filter(name="Hamburgers").update(
        shop=Shop.BEENHOUWER, price_per_unit=None
    )

    budget = build_budget(camp)
    (beenhouwer,) = budget.shop_totals
    assert beenhouwer.label == "Beenhouwer"
    assert beenhouwer.total == Decimal("0")
    # the zero is qualified, not presented as a real bill
    assert beenhouwer.missing_count == 1


def test_cost_per_portion_day_ignores_uncovered_days() -> None:
    camp = make_camp(children=0, teens=10, staff=0)  # Aug 1-5
    recipe = make_recipe(
        "Stew", teens=10, ingredients=[("Potatoes", "10", KG, PRODUCE)]
    )
    assign(camp, AUG(5), MealType.DINNER, recipe)
    ShoppingTrip.objects.create(camp=camp, date=AUG(4))  # covers only Aug 5
    Ingredient.objects.filter(name="Potatoes").update(price_per_unit=Decimal("1.00"))

    # EUR 10 for 10 portions on the one covered day, not spread over 5 days
    assert build_budget(camp).cost_per_portion_day == Decimal("1.00")


def test_cost_per_portion_day_is_none_without_covered_days() -> None:
    assert build_budget(make_camp()).cost_per_portion_day is None


def test_unit_mismatch_is_reported_instead_of_miscosted() -> None:
    camp = make_camp(children=0, teens=10, staff=0)
    recipe = make_recipe(
        "BBQ", teens=10, ingredients=[("BBQ-vlees", "7", PIECE, PRODUCE)]
    )
    assign(camp, AUG(2), MealType.DINNER, recipe)
    ShoppingTrip.objects.create(camp=camp, date=AUG(1))
    Ingredient.objects.filter(name="BBQ-vlees").update(
        unit=KG, price_per_unit=Decimal("11.24")
    )

    budget = build_budget(camp)
    assert budget.total == Decimal("0")
    assert [i.name for i in budget.unit_conflicts] == ["BBQ-vlees"]
    assert budget.missing == []
    assert budget.shop_totals[0].missing_count == 1
