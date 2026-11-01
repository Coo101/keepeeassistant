"""Small helpers to build test data."""

import datetime
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.test import Client

from accounts.models import Chiro, Membership, Role
from camps.models import Camp
from core.constants import DishType, IngredientCategory, Unit
from planning.models import MenuEntry
from recipes.models import Ingredient, IngredientPrice, Recipe, RecipeIngredient


def make_camp(
    start: datetime.date = datetime.date(2026, 8, 1),
    days: int = 5,
    children: int = 20,
    teens: int = 30,
    staff: int = 8,
    chiro: Chiro | None = None,
) -> Camp:
    return Camp.objects.create(
        chiro=chiro or Chiro.objects.get_or_create(name="Test Chiro")[0],
        name="Test Camp",
        start_date=start,
        end_date=start + datetime.timedelta(days=days - 1),
        num_children=children,
        num_teens=teens,
        num_staff=staff,
    )


def account_client(username: str = "kok", **extra: Any) -> Client:
    """Logged in, but not linked to any Chiro."""
    user, _ = User.objects.get_or_create(username=username, defaults=extra)
    client = Client()
    client.force_login(user)
    return client


def member_client(camp: Camp, username: str = "kok", role: str = Role.MEMBER) -> Client:
    """Logged in as a member of the camp's Chiro."""
    client = account_client(username)
    Membership.objects.update_or_create(
        user=User.objects.get(username=username),
        chiro=camp.chiro,
        defaults={"role": role},
    )
    return client


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


def set_price(
    name: str,
    price: str,
    camp: Camp | None = None,
    date: datetime.date = datetime.date(2026, 1, 1),
) -> IngredientPrice:
    return IngredientPrice.objects.create(
        ingredient=Ingredient.objects.get(name=name),
        price=Decimal(price),
        camp=camp,
        date=date,
    )


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
BAKERY = IngredientCategory.BAKERY
KG = Unit.KG
PIECE = Unit.PIECE
LITER = Unit.LITER
