"""Create the example camp everyone can look at (SPEC §9.16).

It uses the recipes already in the database; everything else is made up: dates,
headcount, contacts, stock, shopping days and bills. Run it again with --reset to
start over. Its prices stay with the example and never become anyone's estimate.
"""

import datetime
import logging
import random
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Chiro
from bills.models import Bill, BillLine
from bills.services import apply_review
from camps.models import Camp, CampGroup, DayNote, DietaryNeed
from core.constants import (
    Course,
    Diet,
    DishType,
    IngredientCategory,
    MealType,
    Shop,
    Unit,
)
from kitchen.models import CampUtensil, Utensil
from kitchen.services import add_to_stock
from planning.models import MenuEntry
from recipes.models import Ingredient, Recipe
from recipes.prices import resolve_prices
from shopping.models import PantryItem, ShoppingTrip
from shopping.services import build_shopping_plan

logger = logging.getLogger(__name__)

CHIRO_NAME = "Voorbeeldchiro"
CAMP_NAME = "Voorbeeldkamp 2026"
START = datetime.date(2026, 7, 21)
DAYS = 10

# 34 under 12, 22 aged 12+, 12 staff.
GROUPS = [
    ("Ribbels", CampGroup.Kind.CHILDREN, 10),
    ("Speelclub", CampGroup.Kind.CHILDREN, 12),
    ("Rakwi's", CampGroup.Kind.CHILDREN, 12),
    ("Tito's", CampGroup.Kind.TEENS, 9),
    ("Keti's", CampGroup.Kind.TEENS, 7),
    ("Aspi's", CampGroup.Kind.TEENS, 6),
    ("Leiding", CampGroup.Kind.STAFF, 9),
    ("Kookploeg", CampGroup.Kind.STAFF, 3),
]

CAMP_INFO = {
    "breakfast_time": datetime.time(8, 30),
    "lunch_time": datetime.time(12, 30),
    "teatime_time": datetime.time(16, 0),
    "dinner_time": datetime.time(18, 0),
    "cook_team": "An Peeters +32 470 00 00 01\n"
    "Bert Janssens +32 470 00 00 02\n"
    "Lies Maes +32 470 00 00 03",
    "location": "Kampterrein De Brem\nBremstraat 1, 3999 Voorbeeldegem",
    "contact_leader": "Jonas Wouters (hoofdleiding) +32 470 00 00 04",
    "contact_rental": "Vzw De Brem, Mieke Claes +32 11 00 00 05, verhuur@example.org",
    "bakery": "Bakkerij Het Korenaar\nDorpsstraat 5, 3999 Voorbeeldegem\n"
    "+32 11 00 00 06, brood elke ochtend om 7u30",
    "general_notes": "Afwas na elke maaltijd door de groep van dienst.\n"
    "Vuilniszakken buiten op dinsdag en vrijdag.\n"
    "EHBO-koffer in de keuken, naast de deur.",
}

SHOPPING_DAYS = [-1, 2, 5, 7]  # days after the start; -1 is the day before
DIETS = [
    (Diet.VEGETARIAN, 3, "2 leden, 1 leider"),
    (Diet.GLUTEN_FREE, 1, "Lid van de Aspi's"),
    (Diet.NO_PORK, 2, ""),
]
UTENSILS = [
    ("Kookpot 50 l", 3, "Inox, in de grote kast"),
    ("Kookpot 30 l", 2, ""),
    ("Gasvuur 3 pitten", 2, "Slang in 2023 vervangen"),
    ("Gasfles 10 kg", 3, ""),
    ("Vuurkorf", 1, ""),
    ("Pollepel", 4, ""),
    ("Snijplank", 6, ""),
    ("Afwasbak", 2, ""),
]
NEEDS = [
    ("Kookpot 50 l", 4),
    ("Gasvuur 3 pitten", 2),
    ("Gasfles 10 kg", 4),
    ("Pollepel", 4),
    ("Snijplank", 6),
]
NOTES = {
    0: "Aankomst om 14u. Vieruurtje meteen bij aankomst, op het grasveld.",
    3: "Dagtocht: lunchpakket meegeven om 9u30.",
    DAYS - 1: "Alles opruimen en de koelkast leegmaken voor 14u.",
}
# Per unit, when no price is known yet.
FALLBACK_PRICES = {
    Unit.KG: Decimal("3.20"),
    Unit.LITER: Decimal("1.45"),
    Unit.PIECE: Decimal("0.85"),
}
# Lines that aren't camp food, on the first bill of the first shop.
EXTRA_LINES = [
    ("KOOKPOT INOX 50L", 1, "54.99", BillLine.Category.UTENSILS),
    ("FRISDRANK LEIDING 6X1.5L", 2, "9.20", BillLine.Category.PERSONAL),
    ("SNOEP LEIDINGSAVOND", 1, "12.75", BillLine.Category.PERSONAL),
    ("WATERBALLONNEN 100ST", 1, "6.99", BillLine.Category.ACTIVITY),
    ("LEEGGOED BAK", 2, "1.80", BillLine.Category.OTHER),
]
LATER_PERSONAL_LINES = [("BIER LEIDINGSAVOND 24X25CL", 1, "21.60")]


def _pick(
    recipes: dict[str, list[Recipe]], dish_type: str, index: int
) -> Recipe | None:
    """Recipes take turns, so the example has some variety."""
    options = recipes.get(dish_type) or []
    return options[index % len(options)] if options else None


class Command(BaseCommand):
    help = "Create the read-only example camp from the existing recipes."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset", action="store_true", help="Remove the example and start over."
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        chiro, _ = Chiro.objects.get_or_create(
            name=CHIRO_NAME, defaults={"is_example": True}
        )
        if not chiro.is_example:
            raise CommandError(f"{CHIRO_NAME} exists but isn't an example Chiro.")
        existing = chiro.camps.filter(name=CAMP_NAME)
        if existing.exists():
            if not options["reset"]:
                self.stdout.write(f"{CAMP_NAME} exists already; use --reset.")
                return
            for camp in existing:
                camp.delete()
            CampUtensil.objects.filter(utensil__chiro=chiro).delete()
            chiro.utensils.all().delete()
            chiro.pantry_items.all().delete()

        recipes = self._recipes()
        camp = Camp.objects.create(
            chiro=chiro,
            name=CAMP_NAME,
            start_date=START,
            end_date=START + datetime.timedelta(days=DAYS - 1),
            **CAMP_INFO,
        )
        CampGroup.objects.bulk_create(
            CampGroup(camp=camp, name=name, kind=kind, count=count)
            for name, kind, count in GROUPS
        )
        camp.update_headcount()
        self._plan_menu(camp, recipes)
        for offset, text in NOTES.items():
            DayNote.objects.create(
                camp=camp, date=START + datetime.timedelta(days=offset), text=text
            )
        for diet, count, note in DIETS:
            DietaryNeed.objects.create(camp=camp, diet=diet, count=count, note=note)
        ShoppingTrip.objects.bulk_create(
            ShoppingTrip(camp=camp, date=START + datetime.timedelta(days=offset))
            for offset in SHOPPING_DAYS
        )
        self._stock(chiro, camp)
        bills = self._bills(camp)
        logger.info("Created example camp %s with %d bills", camp.pk, bills)
        self.stdout.write(
            self.style.SUCCESS(f"{CAMP_NAME} created, with {bills} bills.")
        )

    def _recipes(self) -> dict[str, list[Recipe]]:
        recipes: dict[str, list[Recipe]] = {}
        for recipe in Recipe.objects.order_by("name"):
            recipes.setdefault(recipe.dish_type, []).append(recipe)
        needed = [DishType.BREAD_MEAL, DishType.HOT_MEAL]
        missing = [dish for dish in needed if not recipes.get(dish)]
        if missing:
            raise CommandError(f"Needs recipes of these dish types first: {missing}")
        return recipes

    def _plan_menu(self, camp: Camp, recipes: dict[str, list[Recipe]]) -> None:
        """Warm at noon, bread in the evening, as on most Chiro camps. The first
        day starts at tea time; the last day ends after lunch."""
        snacks = [
            *recipes.get(DishType.SNACK_FRUITVEG, []),
            *recipes.get(DishType.SNACK_SWEET, []),
            *recipes.get(DishType.SNACK_SAVORY, []),
        ]
        entries = []
        for offset, day in enumerate(camp.days):
            first, last = offset == 0, offset == DAYS - 1

            slots = []
            if not first:
                slots += [
                    (
                        MealType.BREAKFAST,
                        "",
                        _pick(recipes, DishType.BREAD_MEAL, offset),
                    ),
                    (
                        MealType.BREAKFAST,
                        Course.EXTRA,
                        _pick(recipes, DishType.BREAD_MEAL_EXTRA, offset),
                    ),
                    (
                        MealType.LUNCH,
                        Course.SOUP,
                        _pick(recipes, DishType.SOUP, offset),
                    ),
                    (
                        MealType.LUNCH,
                        Course.MAIN,
                        _pick(recipes, DishType.HOT_MEAL, offset),
                    ),
                ]
                if not last:
                    slots.append(
                        (
                            MealType.LUNCH,
                            Course.DESSERT,
                            _pick(recipes, DishType.DESSERT, offset),
                        )
                    )
            if not last:
                snack = snacks[offset % len(snacks)] if snacks else None
                slots += [
                    (MealType.TEA, "", snack),
                    (
                        MealType.DINNER,
                        "",
                        _pick(recipes, DishType.BREAD_MEAL, offset + 2),
                    ),
                    (
                        MealType.DINNER,
                        Course.EXTRA,
                        _pick(recipes, DishType.BREAD_MEAL_EXTRA, offset + 1),
                    ),
                ]
            entries += [
                MenuEntry(camp=camp, date=day, meal_type=meal, course=course, recipe=r)
                for meal, course, r in slots
                if r is not None
            ]
        MenuEntry.objects.bulk_create(entries)

    def _stock(self, chiro: Chiro, camp: Camp) -> None:
        for name, in_stock, note in UTENSILS:
            Utensil.objects.create(chiro=chiro, name=name, in_stock=in_stock, note=note)
        for name, needed in NEEDS:
            CampUtensil.objects.create(
                camp=camp, utensil=chiro.utensils.get(name=name), needed=needed
            )
        # Leftovers from last year: a few dry goods the menu uses.
        dry_goods = (
            Ingredient.objects.filter(
                recipeingredient__recipe__menuentry__camp=camp,
                category=IngredientCategory.DRY_GOODS,
            )
            .distinct()
            .order_by("name")[:3]
        )
        for ingredient in dry_goods:
            quantity = Decimal("10") if ingredient.unit == Unit.PIECE else Decimal("2")
            PantryItem.objects.create(
                chiro=chiro, ingredient=ingredient, quantity=quantity
            )

    def _bills(self, camp: Camp) -> int:
        """One bill per shopping trip and shop, for what the lists say, at about
        the latest known prices."""
        plan = build_shopping_plan(camp)
        ids = {
            item.ingredient.pk
            for trip in plan.trip_lists
            for section in trip.shop_sections
            for items in section.items_by_category.values()
            for item in items
        }
        prices = resolve_prices(camp, ids)
        count = 0
        extras_done = later_done = False
        for trip in plan.trip_lists:
            for section in trip.shop_sections:
                bill = Bill.objects.create(
                    camp=camp,
                    shop=section.shop,
                    date=trip.trip.date,
                    original_name="voorbeeld.pdf",
                )
                for items in section.items_by_category.values():
                    for item in items:
                        self._food_line(bill, item.ingredient, item.quantity, prices)
                if section.shop == Shop.COLRUYT and not extras_done:
                    extras_done = True
                    for description, quantity, price, category in EXTRA_LINES:
                        line = bill.lines.create(
                            description=description,
                            quantity=Decimal(quantity),
                            line_total=Decimal(price) * quantity,
                            category=category,
                        )
                        if category == BillLine.Category.UTENSILS:
                            line.utensil = add_to_stock(
                                camp.chiro,
                                str(camp.chiro.utensils.get(name="Kookpot 50 l").pk),
                                "",
                                line.quantity,
                            )
                            line.save(update_fields=["utensil"])
                elif section.shop == Shop.COLRUYT and not later_done:
                    later_done = True
                    for description, quantity, price in LATER_PERSONAL_LINES:
                        bill.lines.create(
                            description=description,
                            quantity=Decimal(quantity),
                            line_total=Decimal(price) * quantity,
                            category=BillLine.Category.PERSONAL,
                        )
                bill.printed_total = bill.lines_total()
                bill.save(update_fields=["printed_total"])
                apply_review(bill, remember_matches=False)
                count += 1
        return count

    def _food_line(self, bill: Bill, ingredient, quantity: Decimal, prices) -> None:
        resolved = prices.get(ingredient.pk)
        unit_price = resolved.price if resolved else FALLBACK_PRICES[ingredient.unit]
        # Shop prices differ a little from the estimate; the same every run.
        factor = Decimal(random.Random(f"{bill.date}-{ingredient.pk}").randint(95, 108))
        packs = quantity.quantize(Decimal("1"), rounding=ROUND_CEILING)
        total = (packs * unit_price * factor / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        unit = "1KG" if ingredient.unit == Unit.KG else "1L"
        suffix = "" if ingredient.unit == Unit.PIECE else f" {unit}"
        bill.lines.create(
            description=f"{ingredient.name.upper()}{suffix}"[:200],
            quantity=packs,
            pack_amount=Decimal("1"),
            line_total=max(total, Decimal("0.01")),
            category=BillLine.Category.FOOD,
            ingredient=ingredient,
        )
