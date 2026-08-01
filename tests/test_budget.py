"""Budgeting: product matching, unit prices, and camp cost roll-up."""

import datetime
from decimal import Decimal

import pytest

from core.constants import DishType, MealType, Shop
from recipes.colruyt import (
    Product,
    find_match,
    parse_products,
    product_details,
    unit_price_for,
)
from recipes.models import Ingredient
from shopping.budget import build_budget
from shopping.models import ShoppingTrip
from tests.factories import KG, PIECE, PRODUCE, assign, make_camp, make_recipe

pytestmark = pytest.mark.django_db

AUG = lambda d: datetime.date(2026, 8, d)  # noqa: E731


def make_product(**overrides) -> Product:
    defaults = dict(
        product_id="1",
        long_name="EVERYDAY aardappelen 5kg",
        brand="EVERYDAY",
        content="5kg",
        basic_price=Decimal("3.95"),
        measurement_unit="KG",
        unit_price=Decimal("0.79"),
    )
    defaults.update(overrides)
    return Product(**defaults)


def test_unit_price_kg_uses_measurement_unit_price() -> None:
    ingredient = Ingredient(name="Aardappelen", unit="kg")
    assert unit_price_for(ingredient, make_product()) == Decimal("0.79")


def test_unit_price_piece_divides_by_pack_count() -> None:
    ingredient = Ingredient(name="Eieren", unit="piece")
    product = make_product(
        long_name="EVERYDAY eieren M 30st",
        content="30st",
        basic_price=Decimal("6.00"),
        measurement_unit="",
        unit_price=Decimal("0"),
    )
    assert unit_price_for(ingredient, product) == Decimal("0.2000")


def test_unit_price_incompatible_unit_is_none() -> None:
    ingredient = Ingredient(name="Melk", unit="liter")
    assert unit_price_for(ingredient, make_product()) is None


def test_unit_price_piece_rejects_loose_weight_articles() -> None:
    ingredient = Ingredient(name="Tomaat", unit="piece")
    loose = make_product(long_name="tomaten extra", content="", measurement_unit="K")
    assert unit_price_for(ingredient, loose) is None
    # ... but a packaged kg-priced item (one bread) is one piece
    packaged = make_product(
        long_name="wit brood 800g", content="800g", measurement_unit="K"
    )
    assert unit_price_for(ingredient, packaged) == Decimal("3.95")


def test_product_details_includes_content_and_los_for_unbranded() -> None:
    branded = make_product(long_name="EVERYDAY spaghetti", content="500g")
    assert product_details(branded) == "EVERYDAY spaghetti 500g [EVERYDAY]"
    loose = make_product(long_name="tomaten extra", content="", brand="")
    assert product_details(loose) == "tomaten extra [LOS]"
    # content already in the name is not repeated
    full = make_product(long_name="BONI frieten 1kg", content="1kg", brand="BONI")
    assert product_details(full) == "BONI frieten 1kg [BONI]"


def test_find_match_prefers_cheapest_house_brand() -> None:
    ingredient = Ingredient(name="Aardappelen", unit="kg")
    products = [
        make_product(product_id="1", unit_price=Decimal("0.99")),
        make_product(
            product_id="2",
            long_name="BONI aardappelen bloemig 5kg",
            brand="BONI",
            unit_price=Decimal("0.79"),
        ),
        make_product(
            product_id="3",
            long_name="DUURMERK aardappelen 2kg",
            brand="DUURMERK",
            unit_price=Decimal("0.10"),
        ),
    ]
    match = find_match(ingredient, products)
    assert match is not None
    product, price = match
    assert product.product_id == "2"
    assert price == Decimal("0.79")


def test_find_match_uses_alias_for_flemish_names() -> None:
    ingredient = Ingredient(name="Ajuin", unit="kg")
    products = [
        make_product(long_name="BONI uien 2kg", brand="BONI"),
    ]
    assert find_match(ingredient, products) is not None


def test_parse_products_skips_unavailable() -> None:
    raw = [
        {
            "productId": "1",
            "LongName": "EVERYDAY x",
            "brand": "EVERYDAY",
            "isAvailable": False,
            "isPriceAvailable": True,
            "price": {"basicPrice": 1},
        },
        {
            "productId": "2",
            "LongName": "EVERYDAY y",
            "brand": "EVERYDAY",
            "isAvailable": True,
            "isPriceAvailable": True,
            "price": {
                "basicPrice": 2.5,
                "measurementUnit": "KG",
                "measurementUnitPrice": 1.25,
            },
        },
    ]
    products = parse_products(raw)
    assert [p.product_id for p in products] == ["2"]


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
    # 52 portions x 5 days = 260 portion-days -> 6.32/260 ~ 0.02
    assert budget.cost_per_portion_day == Decimal("0.02")


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
