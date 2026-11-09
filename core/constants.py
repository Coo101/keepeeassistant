"""Shared choice sets and constants (SPEC §4-6)."""

from dataclasses import dataclass
from decimal import Decimal

from django.utils.translation import gettext_lazy as _

CHILD_PORTION_FACTOR = Decimal("0.7")


class PriceSource:
    MANUAL = "manual"
    IMPORT = "import"
    BILL = "bill"
    CHOICES = [
        (MANUAL, _("Entered by hand")),
        (IMPORT, _("Earlier stored price")),
        (BILL, _("From a bill")),
    ]


class Unit:
    PIECE = "piece"
    KG = "kg"
    LITER = "liter"

    CHOICES = [
        (PIECE, _("piece")),
        (KG, _("kg")),
        (LITER, _("liter")),
    ]


class Shop:
    VANZON = "vanzon"
    COLRUYT = "colruyt"
    BAKKER = "bakker"
    BEENHOUWER = "beenhouwer"

    CHOICES = [
        (VANZON, "Van Zon"),
        (COLRUYT, "Colruyt"),
        (BAKKER, _("Baker")),
        (BEENHOUWER, _("Butcher")),
    ]


class IngredientCategory:
    PRODUCE = "produce"
    DAIRY = "dairy"
    MEAT = "meat"
    BAKERY = "bakery"
    DRY_GOODS = "dry_goods"
    OTHER = "other"

    CHOICES = [
        (PRODUCE, _("Produce")),
        (DAIRY, _("Dairy")),
        (MEAT, _("Meat")),
        (BAKERY, _("Bakery")),
        (DRY_GOODS, _("Dry goods")),
        (OTHER, _("Other")),
    ]


class DishType:
    SOUP = "soup"
    HOT_MEAL = "hot_meal"
    BREAD_MEAL = "bread_meal"
    BREAD_MEAL_EXTRA = "bread_meal_extra"
    DESSERT = "dessert"
    SNACK_FRUITVEG = "snack_fruitveg"
    SNACK_SAVORY = "snack_savory"
    SNACK_SWEET = "snack_sweet"
    OTHER = "other"

    CHOICES = [
        (SOUP, _("Soup")),
        (HOT_MEAL, _("Hot meal")),
        (BREAD_MEAL, _("Bread meal")),
        (BREAD_MEAL_EXTRA, _("Bread meal extra")),
        (DESSERT, _("Dessert")),
        (SNACK_FRUITVEG, _("Snack (fruit/veg)")),
        (SNACK_SAVORY, _("Snack (savory)")),
        (SNACK_SWEET, _("Snack (sweet)")),
        (OTHER, _("Other")),
    ]


class MealType:
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    TEA = "tea"
    DINNER = "dinner"

    CHOICES = [
        (BREAKFAST, _("Breakfast")),
        (LUNCH, _("Lunch")),
        (TEA, _("Tea time")),
        (DINNER, _("Dinner")),
    ]

    ORDER = [BREAKFAST, LUNCH, TEA, DINNER]


class Course:
    SOUP = "soup"
    MAIN = "main"
    DESSERT = "dessert"
    EXTRA = "extra"

    CHOICES = [
        (SOUP, _("Soup")),
        (MAIN, _("Main")),
        (DESSERT, _("Dessert")),
        (EXTRA, _("Extra")),
    ]


@dataclass(frozen=True)
class MealSlot:
    """One plannable slot of a meal (SPEC §5)."""

    meal_type: str
    course: str  # "" for the meal's single/main slot
    label: str  # shown in the planner grid
    dish_types: tuple[str, ...]
    required: bool = False  # flagged in the planner when left empty


MEAL_SLOTS: tuple[MealSlot, ...] = (
    # Breakfast is a bread meal, plus an optional extra (beleg, cornflakes, ...).
    MealSlot(MealType.BREAKFAST, "", _("main"), (DishType.BREAD_MEAL,), required=True),
    MealSlot(
        MealType.BREAKFAST, Course.EXTRA, _("extra"), (DishType.BREAD_MEAL_EXTRA,)
    ),
    MealSlot(MealType.LUNCH, Course.SOUP, _("soup"), (DishType.SOUP,)),
    MealSlot(
        MealType.LUNCH,
        Course.MAIN,
        _("main"),
        (DishType.HOT_MEAL, DishType.BREAD_MEAL),
        required=True,
    ),
    MealSlot(MealType.LUNCH, Course.EXTRA, _("extra"), (DishType.BREAD_MEAL_EXTRA,)),
    MealSlot(MealType.LUNCH, Course.DESSERT, _("dessert"), (DishType.DESSERT,)),
    MealSlot(
        MealType.TEA,
        "",
        _("snack"),
        (DishType.SNACK_FRUITVEG, DishType.SNACK_SAVORY, DishType.SNACK_SWEET),
        required=True,
    ),
    MealSlot(
        MealType.DINNER,
        "",
        _("main"),
        (DishType.HOT_MEAL, DishType.BREAD_MEAL),
        required=True,
    ),
    MealSlot(MealType.DINNER, Course.EXTRA, _("extra"), (DishType.BREAD_MEAL_EXTRA,)),
    MealSlot(MealType.DINNER, Course.DESSERT, _("dessert"), (DishType.DESSERT,)),
)


def allowed_dish_types(meal_type: str, course: str) -> list[str]:
    """Dish types that may fill the given (meal_type, course) slot."""
    for slot in MEAL_SLOTS:
        if slot.meal_type == meal_type and slot.course == course:
            return list(slot.dish_types)
    return []


class FoodTag:
    """What's in an ingredient, for the diet and balance checks."""

    GLUTEN = "gluten"
    LACTOSE = "lactose"
    NUTS = "nuts"
    EGG = "egg"
    SOY = "soy"
    FISH = "fish"
    MEAT = "meat"
    PORK = "pork"
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    SUGAR = "sugar"

    CHOICES = [
        (GLUTEN, _("Gluten")),
        (LACTOSE, _("Lactose")),
        (NUTS, _("Nuts")),
        (EGG, _("Egg")),
        (SOY, _("Soy")),
        (FISH, _("Fish")),
        (MEAT, _("Meat")),
        (PORK, _("Pork")),
        (VEGETABLE, _("Vegetable")),
        (FRUIT, _("Fruit")),
        (SUGAR, _("High in sugar")),
    ]


class Diet:
    GLUTEN_FREE = "gluten_free"
    LACTOSE_FREE = "lactose_free"
    NUT_FREE = "nut_free"
    EGG_FREE = "egg_free"
    SOY_FREE = "soy_free"
    FISH_FREE = "fish_free"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    NO_PORK = "no_pork"

    CHOICES = [
        (GLUTEN_FREE, _("Gluten-free")),
        (LACTOSE_FREE, _("Lactose-free")),
        (NUT_FREE, _("Nut allergy")),
        (EGG_FREE, _("Egg allergy")),
        (SOY_FREE, _("Soy allergy")),
        (FISH_FREE, _("Fish allergy")),
        (VEGETARIAN, _("Vegetarian")),
        (VEGAN, _("Vegan")),
        (NO_PORK, _("No pork")),
    ]

    FORBIDS = {
        GLUTEN_FREE: {FoodTag.GLUTEN},
        LACTOSE_FREE: {FoodTag.LACTOSE},
        NUT_FREE: {FoodTag.NUTS},
        EGG_FREE: {FoodTag.EGG},
        SOY_FREE: {FoodTag.SOY},
        FISH_FREE: {FoodTag.FISH},
        VEGETARIAN: {FoodTag.MEAT, FoodTag.PORK, FoodTag.FISH},
        VEGAN: {
            FoodTag.MEAT,
            FoodTag.PORK,
            FoodTag.FISH,
            FoodTag.LACTOSE,
            FoodTag.EGG,
        },
        NO_PORK: {FoodTag.PORK},
    }
