"""Small helpers to build test data."""

import datetime
from decimal import Decimal

from camps.models import Camp
from core.constants import DishType, IngredientCategory, Unit
from planning.models import MenuEntry
from recipes.models import Ingredient, Recipe, RecipeIngredient


def make_camp(
    start: datetime.date = datetime.date(2026, 8, 1),
    days: int = 5,
    children: int = 20,
    teens: int = 30,
    staff: int = 8,
) -> Camp:
    return Camp.objects.create(
        name="Test Camp",
        start_date=start,
        end_date=start + datetime.timedelta(days=days - 1),
        num_children=children,
        num_teens=teens,
        num_staff=staff,
    )


def make_recipe(
    name: str,
    dish_type: str = DishType.HOT_MEAL,
    children: int = 0,
    teens: int = 10,
    ingredients: list[tuple[str, str, str, str]] | None = None,
) -> Recipe:
    """ingredients: list of (ingredient name, quantity, unit, category)."""
    recipe = Recipe.objects.create(
        name=name, dish_type=dish_type, base_children=children, base_teens=teens
    )
    for ing_name, quantity, unit, category in ingredients or []:
        ingredient, _ = Ingredient.objects.get_or_create(
            name=ing_name, defaults={"unit": unit, "category": category}
        )
        RecipeIngredient.objects.create(
            recipe=recipe,
            ingredient=ingredient,
            quantity=Decimal(quantity),
            unit=unit,
        )
    return recipe


def assign(
    camp: Camp,
    date: datetime.date,
    meal_type: str,
    recipe: Recipe,
    course: str = "",
) -> MenuEntry:
    entry = MenuEntry(
        camp=camp, date=date, meal_type=meal_type, course=course, recipe=recipe
    )
    entry.full_clean()
    entry.save()
    return entry


PRODUCE = IngredientCategory.PRODUCE
DRY = IngredientCategory.DRY_GOODS
KG = Unit.KG
PIECE = Unit.PIECE
LITER = Unit.LITER
