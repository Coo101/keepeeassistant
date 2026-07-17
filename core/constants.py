"""Shared choice sets and constants (SPEC §4-6)."""

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
    BREAKFAST = "breakfast"
    SOUP = "soup"
    MAIN = "main"
    DESSERT = "dessert"
    SNACK_FRUITVEG = "snack_fruitveg"
    SNACK_SAVORY = "snack_savory"
    HOT_MEAL = "hot_meal"
    BREAD_MEAL = "bread_meal"
    OTHER = "other"

    CHOICES = [
        (BREAKFAST, "Breakfast"),
        (SOUP, "Soup"),
        (MAIN, "Main"),
        (DESSERT, "Dessert"),
        (SNACK_FRUITVEG, "Snack (fruit/veg)"),
        (SNACK_SAVORY, "Snack (savory)"),
        (HOT_MEAL, "Hot meal"),
        (BREAD_MEAL, "Bread meal"),
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

    CHOICES = [
        (SOUP, "Soup"),
        (MAIN, "Main"),
        (DESSERT, "Dessert"),
    ]


# Meal slots (SPEC §5): each slot is (meal_type, course, allowed dish types).
# Course is "" for single-slot meals; lunch has three courses.
MEAL_SLOTS: list[tuple[str, str, list[str]]] = [
    (MealType.BREAKFAST, "", [DishType.BREAKFAST]),
    (MealType.LUNCH, Course.SOUP, [DishType.SOUP]),
    (MealType.LUNCH, Course.MAIN, [DishType.MAIN]),
    (MealType.LUNCH, Course.DESSERT, [DishType.DESSERT]),
    (MealType.TEA, "", [DishType.SNACK_FRUITVEG, DishType.SNACK_SAVORY]),
    (MealType.DINNER, "", [DishType.HOT_MEAL, DishType.BREAD_MEAL]),
]


def allowed_dish_types(meal_type: str, course: str) -> list[str]:
    """Dish types that may fill the given (meal_type, course) slot."""
    for slot_meal, slot_course, dish_types in MEAL_SLOTS:
        if slot_meal == meal_type and slot_course == course:
            return dish_types
    return []
