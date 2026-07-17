"""Shared choice sets and constants (SPEC §4-6)."""

from dataclasses import dataclass
from decimal import Decimal

CHILD_PORTION_FACTOR = Decimal("0.7")


class Unit:
    PIECE = "piece"
    KG = "kg"
    LITER = "liter"

    CHOICES = [
        (PIECE, "piece"),
        (KG, "kg"),
        (LITER, "liter"),
    ]


class IngredientCategory:
    PRODUCE = "produce"
    DAIRY = "dairy"
    MEAT = "meat"
    BAKERY = "bakery"
    DRY_GOODS = "dry_goods"
    OTHER = "other"

    CHOICES = [
        (PRODUCE, "Produce"),
        (DAIRY, "Dairy"),
        (MEAT, "Meat"),
        (BAKERY, "Bakery"),
        (DRY_GOODS, "Dry goods"),
        (OTHER, "Other"),
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
        (SOUP, "Soup"),
        (HOT_MEAL, "Hot meal"),
        (BREAD_MEAL, "Bread meal"),
        (BREAD_MEAL_EXTRA, "Bread meal extra"),
        (DESSERT, "Dessert"),
        (SNACK_FRUITVEG, "Snack (fruit/veg)"),
        (SNACK_SAVORY, "Snack (savory)"),
        (SNACK_SWEET, "Snack (sweet)"),
        (OTHER, "Other"),
    ]


class MealType:
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    TEA = "tea"
    DINNER = "dinner"

    CHOICES = [
        (BREAKFAST, "Breakfast"),
        (LUNCH, "Lunch"),
        (TEA, "Tea time"),
        (DINNER, "Dinner"),
    ]

    ORDER = [BREAKFAST, LUNCH, TEA, DINNER]


class Course:
    SOUP = "soup"
    MAIN = "main"
    DESSERT = "dessert"
    EXTRA = "extra"

    CHOICES = [
        (SOUP, "Soup"),
        (MAIN, "Main"),
        (DESSERT, "Dessert"),
        (EXTRA, "Extra"),
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
    MealSlot(MealType.BREAKFAST, "", "main", (DishType.BREAD_MEAL,), required=True),
    MealSlot(MealType.BREAKFAST, Course.EXTRA, "extra", (DishType.BREAD_MEAL_EXTRA,)),
    MealSlot(MealType.LUNCH, Course.SOUP, "soup", (DishType.SOUP,)),
    MealSlot(
        MealType.LUNCH,
        Course.MAIN,
        "main",
        (DishType.HOT_MEAL, DishType.BREAD_MEAL),
        required=True,
    ),
    MealSlot(MealType.LUNCH, Course.EXTRA, "extra", (DishType.BREAD_MEAL_EXTRA,)),
    MealSlot(MealType.LUNCH, Course.DESSERT, "dessert", (DishType.DESSERT,)),
    MealSlot(
        MealType.TEA,
        "",
        "snack",
        (DishType.SNACK_FRUITVEG, DishType.SNACK_SAVORY, DishType.SNACK_SWEET),
        required=True,
    ),
    MealSlot(
        MealType.DINNER,
        "",
        "main",
        (DishType.HOT_MEAL, DishType.BREAD_MEAL),
        required=True,
    ),
    MealSlot(MealType.DINNER, Course.EXTRA, "extra", (DishType.BREAD_MEAL_EXTRA,)),
    MealSlot(MealType.DINNER, Course.DESSERT, "dessert", (DishType.DESSERT,)),
)


def allowed_dish_types(meal_type: str, course: str) -> list[str]:
    """Dish types that may fill the given (meal_type, course) slot."""
    for slot in MEAL_SLOTS:
        if slot.meal_type == meal_type and slot.course == course:
            return list(slot.dish_types)
    return []
