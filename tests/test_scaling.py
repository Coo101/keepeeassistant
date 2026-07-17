"""Recipe scaling for menu entries (SPEC §7)."""

import datetime
from decimal import Decimal

import pytest

from core.constants import DishType, MealType
from planning.models import MenuEntry
from planning.services import scale_entry
from tests.factories import DRY, KG, PIECE, PRODUCE, assign, make_camp, make_recipe

pytestmark = pytest.mark.django_db

AUG_1 = datetime.date(2026, 8, 1)


def test_scale_entry_quantities() -> None:
    # camp demand: 30 + 8 + 0.7*20 = 52 portions; recipe base: 10 + 0.7*10 = 17...
    # use base 13 portions for a clean factor: teens=13 -> scale 4.
    camp = make_camp()  # 52 portions
    recipe = make_recipe(
        "Stew",
        dish_type=DishType.HOT_MEAL,
        teens=13,
        ingredients=[
            ("Potatoes", "2.5", KG, PRODUCE),
            ("Onions", "3", PIECE, PRODUCE),
        ],
    )
    entry = assign(camp, AUG_1, MealType.DINNER, recipe)

    scaled = scale_entry(entry, camp)
    assert scaled.scale == Decimal("4")
    by_name = {s.ingredient.name: s for s in scaled.ingredients}
    assert by_name["Potatoes"].quantity == Decimal("10.0")
    assert by_name["Onions"].quantity == Decimal("12")


def test_scale_entry_rounds_per_unit() -> None:
    camp = make_camp(children=0, teens=50, staff=0)  # 50 portions
    recipe = make_recipe(
        "Soup",
        dish_type=DishType.SOUP,
        teens=12,  # scale = 50/12 = 4.1666...
        ingredients=[
            ("Lentils", "1", KG, DRY),
            ("Carrots", "5", PIECE, PRODUCE),
        ],
    )
    entry = assign(camp, AUG_1, MealType.LUNCH, recipe, course="soup")

    scaled = scale_entry(entry, camp)
    by_name = {s.ingredient.name: s for s in scaled.ingredients}
    assert by_name["Lentils"].quantity == Decimal("4.2")  # 4.1666 -> 1 decimal
    assert by_name["Carrots"].quantity == Decimal("21")  # 20.83 -> whole


def test_dish_type_must_fit_slot() -> None:
    camp = make_camp()
    dessert = make_recipe("Ice cream", dish_type=DishType.DESSERT)
    entry = MenuEntry(
        camp=camp,
        date=AUG_1,
        meal_type=MealType.LUNCH,
        course="soup",
        recipe=dessert,
    )
    with pytest.raises(Exception, match="does not fit"):
        entry.full_clean()


def test_dinner_accepts_optional_dessert_course() -> None:
    camp = make_camp()
    dessert = make_recipe("Messinaroom", dish_type=DishType.DESSERT)
    entry = MenuEntry(
        camp=camp,
        date=AUG_1,
        meal_type=MealType.DINNER,
        course="dessert",
        recipe=dessert,
    )
    entry.full_clean()  # must not raise
    entry.save()
    assert camp.menu_entries.count() == 1


def test_breakfast_accepts_optional_extra_course() -> None:
    camp = make_camp()
    extra = make_recipe("Cornflakes", dish_type=DishType.BREAKFAST_EXTRA)
    entry = MenuEntry(
        camp=camp,
        date=AUG_1,
        meal_type=MealType.BREAKFAST,
        course="extra",
        recipe=extra,
    )
    entry.full_clean()  # must not raise


def test_breakfast_extra_rejected_in_main_breakfast_slot() -> None:
    camp = make_camp()
    extra = make_recipe("Beleg", dish_type=DishType.BREAKFAST_EXTRA)
    entry = MenuEntry(
        camp=camp,
        date=AUG_1,
        meal_type=MealType.BREAKFAST,
        course="",
        recipe=extra,
    )
    with pytest.raises(Exception, match="does not fit"):
        entry.full_clean()


def test_sweet_snack_fits_tea_slot() -> None:
    camp = make_camp()
    waffles = make_recipe("Wafels", dish_type=DishType.SNACK_SWEET)
    entry = MenuEntry(
        camp=camp, date=AUG_1, meal_type=MealType.TEA, course="", recipe=waffles
    )
    entry.full_clean()  # must not raise


def test_date_must_be_within_camp() -> None:
    camp = make_camp()
    recipe = make_recipe("Pancakes", dish_type=DishType.BREAKFAST)
    entry = MenuEntry(
        camp=camp,
        date=camp.end_date + datetime.timedelta(days=1),
        meal_type=MealType.BREAKFAST,
        course="",
        recipe=recipe,
    )
    with pytest.raises(Exception, match="outside camp dates"):
        entry.full_clean()
