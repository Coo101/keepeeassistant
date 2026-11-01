"""Seed demo data: a dev admin, ingredients, recipes, a camp with a planned
menu and shopping trips. Idempotent — safe to run twice."""

import datetime
import logging
from decimal import Decimal
from typing import Any

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from camps.models import Camp
from core.constants import Course, DishType, IngredientCategory, MealType, Unit
from planning.models import MenuEntry
from recipes.models import Ingredient, Recipe, RecipeIngredient, RecipeStep
from shopping.models import ShoppingTrip

logger = logging.getLogger(__name__)

INGREDIENTS = [
    # name, unit, category
    ("Bread", Unit.PIECE, IngredientCategory.BAKERY),
    ("Butter", Unit.KG, IngredientCategory.DAIRY),
    ("Milk", Unit.LITER, IngredientCategory.DAIRY),
    ("Oats", Unit.KG, IngredientCategory.DRY_GOODS),
    ("Apples", Unit.KG, IngredientCategory.PRODUCE),
    ("Carrots", Unit.KG, IngredientCategory.PRODUCE),
    ("Onions", Unit.KG, IngredientCategory.PRODUCE),
    ("Potatoes", Unit.KG, IngredientCategory.PRODUCE),
    ("Tomatoes", Unit.KG, IngredientCategory.PRODUCE),
    ("Minced beef", Unit.KG, IngredientCategory.MEAT),
    ("Chicken thighs", Unit.KG, IngredientCategory.MEAT),
    ("Pasta", Unit.KG, IngredientCategory.DRY_GOODS),
    ("Rice", Unit.KG, IngredientCategory.DRY_GOODS),
    ("Lentils", Unit.KG, IngredientCategory.DRY_GOODS),
    ("Sugar", Unit.KG, IngredientCategory.DRY_GOODS),
    ("Vanilla pudding mix", Unit.PIECE, IngredientCategory.DRY_GOODS),
    ("Cheese", Unit.KG, IngredientCategory.DAIRY),
    ("Cucumbers", Unit.PIECE, IngredientCategory.PRODUCE),
]

# name, dish_type, base_children, base_teens, [(ingredient, qty, unit)], [steps]
RECIPES: list[dict[str, Any]] = [
    {
        "name": "Porridge with apples",
        "dish_type": DishType.BREAD_MEAL,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Oats", "1.5", Unit.KG),
            ("Milk", "4", Unit.LITER),
            ("Apples", "2", Unit.KG),
            ("Sugar", "0.3", Unit.KG),
        ],
        "steps": [
            ("Bring milk to a simmer in the large kettle.", 10),
            ("Stir in oats and cook, stirring often.", 15),
            ("Dice apples, fold in with sugar.", 10),
        ],
    },
    {
        "name": "Bread breakfast",
        "dish_type": DishType.BREAD_MEAL,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Bread", "3", Unit.PIECE),
            ("Butter", "0.5", Unit.KG),
            ("Cheese", "0.8", Unit.KG),
        ],
        "steps": [("Slice bread and cheese, set out butter.", 15)],
    },
    {
        "name": "Tomato soup",
        "dish_type": DishType.SOUP,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Tomatoes", "3", Unit.KG),
            ("Onions", "0.5", Unit.KG),
            ("Butter", "0.1", Unit.KG),
        ],
        "steps": [
            ("Sweat onions in butter.", 10),
            ("Add tomatoes, simmer and blend.", 30),
        ],
    },
    {
        "name": "Lentil soup",
        "dish_type": DishType.SOUP,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Lentils", "1.2", Unit.KG),
            ("Carrots", "1", Unit.KG),
            ("Onions", "0.5", Unit.KG),
        ],
        "steps": [("Simmer everything until soft.", 40)],
    },
    {
        "name": "Spaghetti bolognese",
        "dish_type": DishType.HOT_MEAL,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Pasta", "2.5", Unit.KG),
            ("Minced beef", "2", Unit.KG),
            ("Tomatoes", "2.5", Unit.KG),
            ("Onions", "0.8", Unit.KG),
        ],
        "steps": [
            ("Brown the beef with onions.", 20),
            ("Add tomatoes, simmer the sauce.", 40),
            ("Cook pasta in batches.", 25),
        ],
    },
    {
        "name": "Chicken and rice",
        "dish_type": DishType.HOT_MEAL,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Chicken thighs", "3", Unit.KG),
            ("Rice", "2", Unit.KG),
            ("Carrots", "1.5", Unit.KG),
        ],
        "steps": [
            ("Roast chicken thighs.", 45),
            ("Cook rice; glaze carrots.", 30),
        ],
    },
    {
        "name": "Vanilla pudding",
        "dish_type": DishType.DESSERT,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Vanilla pudding mix", "4", Unit.PIECE),
            ("Milk", "5", Unit.LITER),
            ("Sugar", "0.2", Unit.KG),
        ],
        "steps": [("Cook pudding, chill in trays.", 25)],
    },
    {
        "name": "Apple wedges",
        "dish_type": DishType.SNACK_FRUITVEG,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [("Apples", "3", Unit.KG)],
        "steps": [("Wash and cut apples into wedges.", 15)],
    },
    {
        "name": "Cucumber & cheese bites",
        "dish_type": DishType.SNACK_SAVORY,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Cucumbers", "8", Unit.PIECE),
            ("Cheese", "0.6", Unit.KG),
        ],
        "steps": [("Slice cucumbers and cheese.", 15)],
    },
    {
        "name": "Potato-carrot stew",
        "dish_type": DishType.HOT_MEAL,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Potatoes", "3.5", Unit.KG),
            ("Carrots", "1.5", Unit.KG),
            ("Onions", "0.7", Unit.KG),
        ],
        "steps": [("Chop everything, stew until tender.", 50)],
    },
    {
        "name": "Bread meal with toppings",
        "dish_type": DishType.BREAD_MEAL,
        "base_children": 10,
        "base_teens": 10,
        "ingredients": [
            ("Bread", "4", Unit.PIECE),
            ("Butter", "0.5", Unit.KG),
            ("Cheese", "1", Unit.KG),
            ("Cucumbers", "6", Unit.PIECE),
        ],
        "steps": [("Set out bread, spreads and toppings.", 20)],
    },
]


class Command(BaseCommand):
    help = "Seed demo data (dev admin, ingredients, recipes, one planned camp)."

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG:
            raise CommandError(
                "seed_demo creates the login admin/admin, so it only runs with "
                "DJANGO_DEBUG=1."
            )
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", password="admin")
            self.stdout.write("Created dev superuser admin/admin — change it!")

        for name, unit, category in INGREDIENTS:
            Ingredient.objects.get_or_create(
                name=name, defaults={"unit": unit, "category": category}
            )

        recipes: dict[str, Recipe] = {}
        for spec in RECIPES:
            recipe, created = Recipe.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "dish_type": spec["dish_type"],
                    "base_children": spec["base_children"],
                    "base_teens": spec["base_teens"],
                },
            )
            recipes[recipe.name] = recipe
            if not created:
                continue
            for ing_name, qty, unit in spec["ingredients"]:
                RecipeIngredient.objects.create(
                    recipe=recipe,
                    ingredient=Ingredient.objects.get(name=ing_name),
                    quantity=Decimal(qty),
                    unit=unit,
                )
            for order, (instruction, minutes) in enumerate(spec["steps"], start=1):
                RecipeStep.objects.create(
                    recipe=recipe,
                    order=order,
                    instruction=instruction,
                    duration_minutes=minutes,
                )

        start = datetime.date(2026, 8, 3)
        camp, created = Camp.objects.get_or_create(
            name="Summer Camp 2026",
            defaults={
                "start_date": start,
                "end_date": start + datetime.timedelta(days=6),
                "num_children": 28,
                "num_teens": 26,
                "num_staff": 9,
            },
        )
        if created:
            menu = {
                (MealType.BREAKFAST, ""): ["Porridge with apples", "Bread breakfast"],
                (MealType.LUNCH, Course.SOUP): ["Tomato soup", "Lentil soup"],
                (MealType.LUNCH, Course.MAIN): [
                    "Spaghetti bolognese",
                    "Chicken and rice",
                ],
                (MealType.LUNCH, Course.DESSERT): ["Vanilla pudding"],
                (MealType.TEA, ""): ["Apple wedges", "Cucumber & cheese bites"],
                (MealType.DINNER, ""): [
                    "Potato-carrot stew",
                    "Bread meal with toppings",
                ],
            }
            for i, day in enumerate(camp.days):
                for (meal_type, course), names in menu.items():
                    entry = MenuEntry(
                        camp=camp,
                        date=day,
                        meal_type=meal_type,
                        course=course,
                        recipe=recipes[names[i % len(names)]],
                    )
                    entry.full_clean()
                    entry.save()
            for trip_day in [start - datetime.timedelta(days=1), camp.days[2]]:
                ShoppingTrip.objects.get_or_create(camp=camp, date=trip_day)

        logger.info("Demo data seeded")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
