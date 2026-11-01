"""Warnings for the planner: diets and allergies, and balance (SPEC §9.11, §9.13).

They read the tags on ingredients, so they're only as good as those tags: a
planned ingredient nobody checked is reported, not assumed safe.
"""

import datetime
from collections import defaultdict
from dataclasses import dataclass, field

from camps.models import Camp
from core.constants import Diet, DishType, FoodTag, MealType
from planning.models import MenuEntry

MAX_SWEET_RECIPES_PER_DAY = 2
_TAG_LABELS = dict(FoodTag.CHOICES)
_DIET_LABELS = dict(Diet.CHOICES)
_MEAL_LABELS = dict(MealType.CHOICES)


@dataclass(frozen=True)
class DietConflict:
    date: datetime.date
    meal: str
    recipe: str
    diet: str
    people: int
    contains: str


@dataclass
class MenuChecks:
    conflicts: list[DietConflict] = field(default_factory=list)
    balance: dict[datetime.date, list[str]] = field(default_factory=dict)
    unchecked: list[str] = field(default_factory=list)


def _entry_tags(entry: MenuEntry) -> set[str]:
    return {tag for ri in entry.recipe.ingredients.all() for tag in ri.ingredient.tags}


def _diet_conflicts(entries: list[MenuEntry], camp: Camp) -> list[DietConflict]:
    conflicts = []
    needs = list(camp.dietary_needs.all())
    for entry in entries:
        tags = _entry_tags(entry)
        for need in needs:
            found = tags & Diet.FORBIDS[need.diet]
            if found:
                conflicts.append(
                    DietConflict(
                        date=entry.date,
                        meal=_MEAL_LABELS[entry.meal_type],
                        recipe=entry.recipe.name,
                        diet=_DIET_LABELS[need.diet],
                        people=need.count,
                        contains=", ".join(sorted(_TAG_LABELS[t] for t in found)),
                    )
                )
    return conflicts


def _all_known(entries: list[MenuEntry]) -> bool:
    """An ingredient nobody looked at might be a vegetable: don't call that missing."""
    return all(
        ri.ingredient.tags or ri.ingredient.tags_checked
        for entry in entries
        for ri in entry.recipe.ingredients.all()
    )


def _day_balance(entries: list[MenuEntry]) -> list[str]:
    warnings = []
    day_tags: set[str] = set()
    sweet = []
    for entry in entries:
        tags = _entry_tags(entry)
        day_tags |= tags
        if FoodTag.SUGAR in tags:
            sweet.append(entry.recipe.name)
        if (
            entry.recipe.dish_type == DishType.HOT_MEAL
            and FoodTag.VEGETABLE not in tags
            and _all_known([entry])
        ):
            warnings.append(f"{entry.recipe.name} has no vegetables")
    if _all_known(entries):
        if FoodTag.VEGETABLE not in day_tags:
            warnings.append("No vegetables this day")
        if FoodTag.FRUIT not in day_tags:
            warnings.append("No fruit this day")
    if len(sweet) > MAX_SWEET_RECIPES_PER_DAY:
        warnings.append(f"A lot of sugar: {', '.join(sweet)}")
    return warnings


def menu_checks(camp: Camp) -> MenuChecks:
    entries = list(
        camp.menu_entries.filter(date__range=(camp.start_date, camp.end_date))
        .select_related("recipe")
        .prefetch_related("recipe__ingredients__ingredient")
    )
    ingredients = {
        ri.ingredient.pk: ri.ingredient
        for entry in entries
        for ri in entry.recipe.ingredients.all()
    }
    checks = MenuChecks(
        conflicts=_diet_conflicts(entries, camp),
        unchecked=sorted(i.name for i in ingredients.values() if not i.tags_checked),
    )
    by_day: dict[datetime.date, list[MenuEntry]] = defaultdict(list)
    for entry in entries:
        by_day[entry.date].append(entry)
    for day in sorted(by_day):
        warnings = _day_balance(by_day[day])
        if warnings:
            checks.balance[day] = warnings
    return checks
